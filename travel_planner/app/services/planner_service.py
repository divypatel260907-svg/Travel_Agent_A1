"""
Planner Service — single orchestration entry point.

This replaces the Streamlit agent pipeline. All logic lives here;
routes stay thin. Runs async agents synchronously via asyncio.run().
"""
from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from typing import Any

from travel_planner.agents.preference_extractor import PreferenceExtractorAgent
from travel_planner.agents.weather_agent import WeatherAgent
from travel_planner.models.schemas import TravelPreferences


def _run(coro) -> Any:
    """Run an async coroutine from synchronous Flask context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


def generate_travel_plan(user_query: str) -> dict:
    """
    Main orchestration function — replaces the Streamlit agent pipeline.

    Steps:
      1. Extract structured preferences from natural language (Groq).
      2. Fetch live weather forecast from Open-Meteo (keyless).
      3. Assemble the plan dict for the template.

    Args:
        user_query: Free-form trip description from the user.

    Returns:
        dict with keys: preferences, weather, clarification_needed,
                        clarification_questions, generated_at.

    Raises:
        Exception: Propagated to the caller (route catches and flashes it).
    """
    demo_mode = not bool(os.getenv("GROQ_API_KEY"))

    # ── Step 1: Preferences ───────────────────────────────────────────────────
    if demo_mode:
        prefs = _mock_preferences(user_query)
    else:
        extractor = PreferenceExtractorAgent()
        prefs = _run(extractor.extract(user_query))

    prefs_dict = prefs.model_dump(mode="json")

    # Build clarification questions if needed
    clarification_questions: list[str] = []
    if prefs.clarification_needed:
        extractor_inst = PreferenceExtractorAgent.__new__(PreferenceExtractorAgent)
        clarification_questions = extractor_inst.build_clarification_questions(prefs)

    # ── Step 2: Weather ───────────────────────────────────────────────────────
    weather_dict: dict | None = None
    indoor_alternatives: dict = {}
    weather_error: str | None = None

    if prefs.destination and prefs.start_date and prefs.end_date:
        try:
            if demo_mode and str(prefs.destination).lower() == "kyoto":
                from travel_planner.agents.weather_agent import _mock_forecast_data  # noqa: PLC0415
                forecast = _mock_forecast_data()
            else:
                wa = WeatherAgent()
                forecast = _run(wa.get_forecast(prefs.destination, prefs.start_date, prefs.end_date))

            weather_dict = forecast.model_dump(mode="json")
            wa_inst = WeatherAgent()
            indoor_alternatives = wa_inst.suggest_indoor_alternatives(forecast)
            weather_dict["indoor_alternatives"] = indoor_alternatives
            weather_dict["summary"] = wa_inst.format_summary(forecast)
        except Exception as exc:
            weather_error = str(exc)

    # ── Step 3: Assemble plan ─────────────────────────────────────────────────
    return {
        "query": user_query,
        "preferences": prefs_dict,
        "weather": weather_dict,
        "weather_error": weather_error,
        "clarification_needed": prefs.clarification_needed,
        "clarification_questions": clarification_questions,
        "demo_mode": demo_mode,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
    }


# ── Mock data helpers (demo mode) ─────────────────────────────────────────────

def _mock_preferences(raw: str) -> TravelPreferences:
    from datetime import date  # noqa: PLC0415
    from travel_planner.models.schemas import GroupType, Pace  # noqa: PLC0415
    return TravelPreferences(
        destination="Kyoto",
        start_date=date(2024, 4, 10),
        end_date=date(2024, 4, 14),
        duration_days=5,
        budget_amount=1800,
        budget_currency="USD",
        budget_style="mid_range",  # type: ignore[arg-type]
        group_type=GroupType.COUPLE,
        group_size=2,
        pace=Pace.RELAXED,
        interests=["temples", "food", "gardens"],
        accessibility_needs=["no heavy walking"],
        must_do=["Fushimi Inari", "Arashiyama bamboo grove"],
        clarification_needed=False,
        missing_fields=[],
        raw_input=raw,
    )
