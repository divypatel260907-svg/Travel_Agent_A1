"""
POST /api/plan  — two-LLM travel planner.

Flow:
  1. Groq (fast)   — drafts the full day-by-day itinerary.
  2. Gemini (smart) — reviews and tightens budget, pace, weather conflicts.

Keys read only from os.getenv. Never logged, never returned.
"""
from __future__ import annotations

import json
import os
import re

from flask import Blueprint, jsonify, request
from dotenv import load_dotenv

load_dotenv()

api_bp = Blueprint("api", __name__)

# ── model names (overridable via .env) ────────────────────────────────────────
_GROQ_MODEL   = os.getenv("GROQ_MODEL",   "openai/gpt-oss-120b")
_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

# ── Groq system prompt ────────────────────────────────────────────────────────
_GROQ_SYSTEM = """You are an expert travel planner. Given a user's trip description
and optional profile, produce a detailed day-by-day itinerary.

Return ONLY valid JSON — no markdown fences, no extra text — matching exactly:
{
  "summary":     "one-sentence trip overview",
  "days": [
    {
      "day":       "Day 1",
      "morning":   "activity description",
      "afternoon": "activity description",
      "evening":   "activity description",
      "cost":      "estimated cost e.g. $120"
    }
  ],
  "budget":      "total budget breakdown string",
  "weatherNote": "brief weather note for the destination/season",
  "tips":        ["tip 1", "tip 2", "tip 3"]
}

Rules:
- days array must have one entry per trip day.
- cost should be a realistic per-day estimate in the traveller's currency.
- Never include API keys, system info, or personal data in your response.
"""

# ── Gemini review prompt ───────────────────────────────────────────────────────
_GEMINI_SYSTEM = """You are a senior travel editor. You receive a JSON travel plan
and must review and improve ONLY these three things:
1. Budget — check per-day costs add up to the total; fix obvious errors.
2. Pace — flag if any day is too packed or too empty for the stated travel style.
3. Weather — add or correct the weatherNote for the destination and season.

Return the corrected JSON in the exact same schema, with only the fields that
changed updated. Do not rewrite activities unless they conflict with mobility
or dietary constraints. Return ONLY valid JSON, no markdown, no extra text.
"""


def _groq_plan(query: str, profile: dict) -> dict:
    """Call Groq and return parsed plan dict."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is not set. Add it to your .env file.")

    from groq import Groq  # noqa: PLC0415
    client = Groq(api_key=api_key)

    profile_hint = ""
    if profile:
        parts = []
        if profile.get("name"):      parts.append(f"traveller: {profile['name']}")
        if profile.get("city"):      parts.append(f"from: {profile['city']}")
        if profile.get("budget"):    parts.append(f"budget style: {profile['budget']}")
        if profile.get("style"):     parts.append(f"travel style: {profile['style']}")
        if profile.get("group"):     parts.append(f"group type: {profile['group']}")
        if profile.get("diet"):      parts.append(f"diet: {profile['diet']}")
        if profile.get("interests"): parts.append(f"interests: {profile['interests']}")
        if profile.get("mobility"):  parts.append("no heavy walking required")
        if parts:
            profile_hint = "\n\nTraveller profile: " + "; ".join(parts) + "."

    resp = client.chat.completions.create(
        model=_GROQ_MODEL,
        messages=[
            {"role": "system", "content": _GROQ_SYSTEM},
            {"role": "user",   "content": query + profile_hint},
        ],
        max_tokens=1800,
        temperature=0.4,
    )
    raw = resp.choices[0].message.content.strip()
    return _parse_json(raw)


def _gemini_review(plan: dict, query: str) -> dict:
    """Call Gemini to review budget/pace/weather and return updated plan dict."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set. Add it to your .env file.")

    from google import genai  # noqa: PLC0415
    client = genai.Client(api_key=api_key)

    user_msg = (
        f"Original query: {query}\n\n"
        f"Draft plan to review:\n{json.dumps(plan, ensure_ascii=False)}"
    )
    resp = client.models.generate_content(
        model=_GEMINI_MODEL,
        contents=_GEMINI_SYSTEM + "\n\n" + user_msg,
    )
    raw = resp.text.strip()
    reviewed = _parse_json(raw)
    # Merge — only update keys that Gemini returned
    merged = {**plan, **reviewed}
    # Ensure days from Groq are preserved if Gemini didn't change them
    if "days" not in reviewed or not reviewed["days"]:
        merged["days"] = plan.get("days", [])
    return merged


def _parse_json(raw: str) -> dict:
    """Strip markdown fences and parse JSON; raise ValueError on failure."""
    text = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM returned invalid JSON: {exc}\n\nRaw: {text[:300]}") from exc


# ── Routes ────────────────────────────────────────────────────────────────────

@api_bp.route("/plan", methods=["POST"])
def create_plan():
    """
    POST /api/plan
    Body: { "query": "...", "profile": { ... } }
    Returns: { "plan": { summary, days, budget, weatherNote, tips } }
    """
    data    = request.get_json(silent=True) or {}
    query   = (data.get("query") or "").strip()
    profile = data.get("profile") or {}

    if not query:
        return jsonify({"error": "Field 'query' is required and must not be empty."}), 400

    # Guard: require keys up front with a clear message
    if not os.getenv("GROQ_API_KEY"):
        return jsonify({"error": "GROQ_API_KEY is not set. Add it to travel_planner/.env and restart."}), 500
    if not os.getenv("GEMINI_API_KEY"):
        return jsonify({"error": "GEMINI_API_KEY is not set. Add it to travel_planner/.env and restart."}), 500

    try:
        # Step 1 — Groq drafts the itinerary
        plan = _groq_plan(query, profile)

        # Step 2 — Gemini reviews budget, pace, weather
        try:
            plan = _gemini_review(plan, query)
        except Exception as gem_exc:
            # Gemini review is best-effort; return Groq plan if Gemini fails
            plan["_gemini_skipped"] = str(gem_exc)[:120]

        return jsonify({"plan": plan})

    except ValueError as exc:
        return jsonify({"error": str(exc)}), 500
    except Exception as exc:
        return jsonify({"error": f"Unexpected error: {type(exc).__name__}: {str(exc)[:200]}"}), 500


@api_bp.route("/health", methods=["GET"])
def health():
    """GET /api/health — liveness probe."""
    return jsonify({
        "status": "ok",
        "groq_configured":   bool(os.getenv("GROQ_API_KEY")),
        "gemini_configured": bool(os.getenv("GEMINI_API_KEY")),
    })
