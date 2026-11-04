"""
Preference Extractor Agent
==========================
Converts free-form natural language into a structured TravelPreferences model.

Rule (rule.md): Extract only what is explicitly or strongly implied. Ask
clarifying questions when critical info is missing (budget, dates, group type).

The agent uses Groq (fast, tool-calling) and returns either:
  - A fully populated TravelPreferences, OR
  - A partial TravelPreferences with clarification_needed=True and
    clarification_questions populated so the orchestrator can ask the user.

Usage
-----
    from travel_planner.agents.preference_extractor import PreferenceExtractorAgent

    agent = PreferenceExtractorAgent()
    prefs = await agent.extract("5-day romantic trip to Kyoto under $1800 in April")
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime
from typing import Any

from pydantic import ValidationError

from travel_planner.models.schemas import (
    BudgetStyle,
    GroupType,
    Pace,
    TravelPreferences,
)
from travel_planner.utils.llm import get_groq_llm

logger = logging.getLogger(__name__)

# ── System prompt ──────────────────────────────────────────────────────────────
_SYSTEM_PROMPT = """You are a travel preference extractor. Your job is to parse a user's natural-language travel request and extract structured preferences.

Return ONLY a valid JSON object matching this exact schema (omit fields that are truly absent – use null for unknown optional fields, empty arrays [] for unknown lists):

{
  "destination": string | null,
  "alternate_destinations": [],
  "start_date": "YYYY-MM-DD" | null,
  "end_date": "YYYY-MM-DD" | null,
  "duration_days": integer | null,
  "budget_amount": number | null,
  "budget_currency": "USD",
  "budget_style": "budget" | "mid_range" | "luxury" | null,
  "group_type": "solo" | "couple" | "family" | "friends" | null,
  "group_size": integer | null,
  "pace": "relaxed" | "moderate" | "fast" | null,
  "interests": [],
  "dietary": [],
  "accessibility_needs": [],
  "must_do": [],
  "must_avoid": [],
  "preferred_language": "en",
  "user_nationality": null,
  "clarification_needed": false,
  "missing_fields": []
}

Inference rules:
- "romantic trip" → group_type: "couple", group_size: 2
- "no heavy walking" → accessibility_needs: ["no heavy walking"]
- "love food & temples" → interests: ["food", "temples"]
- "under $1800" → budget_amount: 1800, budget_currency: "USD"
- "mid-April" with no year → infer the nearest upcoming April
- "5-day trip" → duration_days: 5 (compute end_date if start_date is known)
- Infer budget_style from amount: <$100/day=budget, $100-300/day=mid_range, >$300/day=luxury
- Mark clarification_needed: true and list missing_fields when budget OR dates OR destination is absent
- Do NOT invent data. Only extract what is explicitly stated or strongly implied.
- Output ONLY the JSON. No markdown, no explanation, no code fences.
"""

# ── Clarifying question templates ─────────────────────────────────────────────
_CLARIFY_TEMPLATES: dict[str, str] = {
    "destination": "Where would you like to travel? (city, country, or region)",
    "start_date": "When do you plan to start your trip? (e.g. 'April 10' or '2024-04-10')",
    "end_date": "When do you plan to return, or how many days do you want to travel?",
    "budget_amount": "What is your total budget for the trip? (e.g. '$1500', '€2000')",
    "group_type": "Who is traveling? (solo, couple, family, or friends?)",
}


class PreferenceExtractorAgent:
    """
    Extracts structured TravelPreferences from a natural language string.

    Args:
        llm: Optional LangChain chat model. Defaults to ChatGroq.
    """

    def __init__(self, llm: Any | None = None) -> None:
        self._llm = llm  # lazy-loaded

    @property
    def llm(self) -> Any:
        if self._llm is None:
            self._llm = get_groq_llm(temperature=0.1)
        return self._llm

    async def extract(
        self,
        user_input: str,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> TravelPreferences:
        """
        Parse user_input and return a TravelPreferences model.

        Args:
            user_input: Free-form natural language travel request.
            conversation_history: Optional prior turns for multi-turn refinement.

        Returns:
            TravelPreferences with clarification_needed=False when complete,
            or clarification_needed=True with missing_fields + clarification_questions.
        """
        messages = [{"role": "system", "content": _SYSTEM_PROMPT}]

        # Include prior conversation to handle follow-up answers
        if conversation_history:
            messages.extend(conversation_history)

        messages.append({"role": "user", "content": user_input})

        raw_json = await self._call_llm(messages)
        prefs = self._parse_response(raw_json, user_input)
        prefs = self._post_process_dates(prefs)
        prefs = self._check_completeness(prefs)
        prefs.raw_input = user_input
        return prefs

    async def _call_llm(self, messages: list[dict]) -> str:
        """Invoke the LLM and return the raw text response.

        Tries to wrap messages as LangChain message objects when langchain_core
        is available; falls back to passing plain dicts directly (useful in tests
        where the LLM is a plain mock that accepts any input).
        """
        try:
            from langchain_core.messages import HumanMessage, SystemMessage  # noqa: PLC0415

            lc_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    lc_messages.append(SystemMessage(content=msg["content"]))
                else:
                    lc_messages.append(HumanMessage(content=msg["content"]))
            response = await self.llm.ainvoke(lc_messages)
        except ModuleNotFoundError:
            # langchain_core not installed – pass plain dicts (test/mock scenario)
            response = await self.llm.ainvoke(messages)

        return response.content.strip()

    def _parse_response(self, raw: str, original_input: str) -> TravelPreferences:
        """Parse LLM JSON output into TravelPreferences, with fallback on errors."""
        # Strip markdown code fences if the LLM included them despite instructions
        clean = raw.strip()
        if clean.startswith("```"):
            clean = "\n".join(clean.split("\n")[1:])
            clean = clean.rstrip("`").strip()

        try:
            data: dict = json.loads(clean)
            return TravelPreferences(**data)
        except json.JSONDecodeError as exc:
            logger.warning("LLM returned non-JSON for input %r: %s", original_input[:80], exc)
            # Return a minimal model signalling clarification is needed
            return TravelPreferences(
                clarification_needed=True,
                missing_fields=["destination", "start_date", "budget_amount"],
                raw_input=original_input,
            )
        except ValidationError as exc:
            logger.warning("Pydantic validation failed: %s", exc)
            # Attempt partial construction with only valid fields
            try:
                data = json.loads(clean)
                valid_data = {
                    k: v
                    for k, v in data.items()
                    if k in TravelPreferences.model_fields
                }
                prefs = TravelPreferences(**valid_data)
                prefs.clarification_needed = True
                prefs.raw_input = original_input
                return prefs
            except Exception:
                return TravelPreferences(
                    clarification_needed=True,
                    missing_fields=["destination", "start_date", "budget_amount"],
                    raw_input=original_input,
                )

    def _post_process_dates(self, prefs: TravelPreferences) -> TravelPreferences:
        """Derive end_date or duration_days when one can be calculated from the other."""
        if prefs.start_date and prefs.duration_days and prefs.end_date is None:
            from datetime import timedelta  # noqa: PLC0415

            prefs.end_date = prefs.start_date + timedelta(days=prefs.duration_days - 1)

        if prefs.start_date and prefs.end_date and prefs.duration_days is None:
            prefs.duration_days = (prefs.end_date - prefs.start_date).days + 1

        return prefs

    def _check_completeness(self, prefs: TravelPreferences) -> TravelPreferences:
        """
        Identify missing critical fields and build clarification questions.
        Rule (rule.md): Ask clarifying questions when critical info is missing
        (budget, dates, group type).
        """
        critical_missing: list[str] = []

        if not prefs.destination:
            critical_missing.append("destination")
        if not prefs.has_dates:
            if not prefs.start_date:
                critical_missing.append("start_date")
            if not prefs.end_date and not prefs.duration_days:
                critical_missing.append("end_date")
        if not prefs.has_budget:
            critical_missing.append("budget_amount")

        if critical_missing:
            prefs.clarification_needed = True
            prefs.missing_fields = critical_missing
        else:
            prefs.clarification_needed = False
            prefs.missing_fields = []

        return prefs

    def build_clarification_questions(self, prefs: TravelPreferences) -> list[str]:
        """
        Return a list of human-friendly questions for each missing field.

        Args:
            prefs: Partially filled TravelPreferences with missing_fields set.

        Returns:
            List of question strings, one per missing field.
        """
        return [
            _CLARIFY_TEMPLATES.get(field, f"Could you provide your {field.replace('_', ' ')}?")
            for field in prefs.missing_fields
        ]
