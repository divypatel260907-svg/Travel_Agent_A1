"""
Tests for the Preference Extractor Agent.

Pure-logic tests that mock the LLM so no API key is required.
Run with: pytest travel_planner/tests/test_preference_extractor.py -v
"""

from __future__ import annotations

import json
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from travel_planner.agents.preference_extractor import PreferenceExtractorAgent
from travel_planner.models.schemas import GroupType, Pace, TravelPreferences


# ── Helpers ───────────────────────────────────────────────────────────────────


def make_agent_with_mock_response(json_payload: dict) -> PreferenceExtractorAgent:
    """Create an agent whose LLM always returns the given dict as JSON."""
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(
        return_value=MagicMock(content=json.dumps(json_payload))
    )
    return PreferenceExtractorAgent(llm=mock_llm)


# ── Tests: successful extractions ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_extract_full_kyoto_trip():
    """A complete request should produce a fully-populated, non-clarification model."""
    payload = {
        "destination": "Kyoto",
        "start_date": "2024-04-10",
        "end_date": "2024-04-14",
        "duration_days": 5,
        "budget_amount": 1800,
        "budget_currency": "USD",
        "budget_style": "mid_range",
        "group_type": "couple",
        "group_size": 2,
        "pace": "relaxed",
        "interests": ["temples", "food"],
        "dietary": [],
        "accessibility_needs": ["no heavy walking"],
        "must_do": [],
        "must_avoid": [],
        "preferred_language": "en",
        "user_nationality": None,
        "clarification_needed": False,
        "missing_fields": [],
        "alternate_destinations": [],
    }
    agent = make_agent_with_mock_response(payload)
    prefs = await agent.extract(
        "5-day romantic trip to Kyoto under $1800 in April, no heavy walking, love food & temples"
    )

    assert prefs.destination == "Kyoto"
    assert prefs.start_date == date(2024, 4, 10)
    assert prefs.end_date == date(2024, 4, 14)
    assert prefs.duration_days == 5
    assert prefs.budget_amount == 1800
    assert prefs.budget_currency == "USD"
    assert prefs.group_type == GroupType.COUPLE
    assert prefs.group_size == 2
    assert prefs.pace == Pace.RELAXED
    assert "temples" in prefs.interests
    assert "food" in prefs.interests
    assert "no heavy walking" in prefs.accessibility_needs
    assert prefs.clarification_needed is False
    assert prefs.missing_fields == []
    assert prefs.is_complete_for_planning is True


@pytest.mark.asyncio
async def test_extract_missing_budget_triggers_clarification():
    """When budget is absent the agent should mark clarification_needed=True."""
    payload = {
        "destination": "Paris",
        "start_date": "2024-06-01",
        "end_date": "2024-06-07",
        "duration_days": 7,
        "budget_amount": None,
        "budget_currency": "USD",
        "budget_style": None,
        "group_type": "solo",
        "group_size": 1,
        "pace": None,
        "interests": ["museums", "cafes"],
        "dietary": [],
        "accessibility_needs": [],
        "must_do": [],
        "must_avoid": [],
        "preferred_language": "en",
        "user_nationality": None,
        "clarification_needed": False,  # LLM may not set this; agent _check_completeness should
        "missing_fields": [],
        "alternate_destinations": [],
    }
    agent = make_agent_with_mock_response(payload)
    prefs = await agent.extract("Week in Paris in June, solo trip, love museums and cafes")

    assert prefs.clarification_needed is True
    assert "budget_amount" in prefs.missing_fields


@pytest.mark.asyncio
async def test_extract_missing_destination_triggers_clarification():
    """Missing destination must trigger clarification."""
    payload = {
        "destination": None,
        "start_date": "2024-08-01",
        "end_date": "2024-08-05",
        "duration_days": 5,
        "budget_amount": 2000,
        "budget_currency": "USD",
        "budget_style": "mid_range",
        "group_type": "friends",
        "group_size": 4,
        "pace": "fast",
        "interests": [],
        "dietary": [],
        "accessibility_needs": [],
        "must_do": [],
        "must_avoid": [],
        "preferred_language": "en",
        "user_nationality": None,
        "clarification_needed": False,
        "missing_fields": [],
        "alternate_destinations": [],
    }
    agent = make_agent_with_mock_response(payload)
    prefs = await agent.extract("5 days somewhere fun with friends, $2000 budget")

    assert prefs.clarification_needed is True
    assert "destination" in prefs.missing_fields


@pytest.mark.asyncio
async def test_extract_dates_derived_from_duration():
    """If end_date is missing but start_date + duration_days are present, derive end_date."""
    from datetime import timedelta

    payload = {
        "destination": "Tokyo",
        "start_date": "2024-10-01",
        "end_date": None,  # missing – should be derived
        "duration_days": 7,
        "budget_amount": 3000,
        "budget_currency": "USD",
        "budget_style": "mid_range",
        "group_type": "solo",
        "group_size": 1,
        "pace": "moderate",
        "interests": ["anime", "street food"],
        "dietary": [],
        "accessibility_needs": [],
        "must_do": [],
        "must_avoid": [],
        "preferred_language": "en",
        "user_nationality": None,
        "clarification_needed": False,
        "missing_fields": [],
        "alternate_destinations": [],
    }
    agent = make_agent_with_mock_response(payload)
    prefs = await agent.extract("7 days in Tokyo from October 1st, budget $3000")

    assert prefs.start_date == date(2024, 10, 1)
    assert prefs.end_date == date(2024, 10, 7)  # start + 6 days
    assert prefs.duration_days == 7


@pytest.mark.asyncio
async def test_extract_budget_currency_uppercased():
    """Budget currency must always be uppercased regardless of LLM output."""
    payload = {
        "destination": "Rome",
        "start_date": "2024-05-01",
        "end_date": "2024-05-04",
        "duration_days": 4,
        "budget_amount": 1200,
        "budget_currency": "eur",  # lowercase – should be uppercased
        "budget_style": "budget",
        "group_type": "couple",
        "group_size": 2,
        "pace": "moderate",
        "interests": [],
        "dietary": [],
        "accessibility_needs": [],
        "must_do": [],
        "must_avoid": [],
        "preferred_language": "en",
        "user_nationality": None,
        "clarification_needed": False,
        "missing_fields": [],
        "alternate_destinations": [],
    }
    agent = make_agent_with_mock_response(payload)
    prefs = await agent.extract("4 days in Rome, €1200 budget for two")

    assert prefs.budget_currency == "EUR"


@pytest.mark.asyncio
async def test_extract_invalid_json_returns_clarification():
    """When LLM returns malformed JSON the agent must return a safe fallback."""
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(
        return_value=MagicMock(content="Sorry, I cannot help with that.")
    )
    agent = PreferenceExtractorAgent(llm=mock_llm)
    prefs = await agent.extract("Take me somewhere nice!")

    assert isinstance(prefs, TravelPreferences)
    assert prefs.clarification_needed is True
    assert len(prefs.missing_fields) > 0


# ── Tests: clarification question builder ─────────────────────────────────────


def test_build_clarification_questions_all_fields():
    """Each missing field should map to a non-empty question string."""
    agent = PreferenceExtractorAgent.__new__(PreferenceExtractorAgent)
    prefs = TravelPreferences(
        clarification_needed=True,
        missing_fields=["destination", "start_date", "budget_amount"],
    )
    questions = agent.build_clarification_questions(prefs)

    assert len(questions) == 3
    assert all(isinstance(q, str) and len(q) > 5 for q in questions)


def test_build_clarification_questions_no_fields():
    """No missing fields → empty question list."""
    agent = PreferenceExtractorAgent.__new__(PreferenceExtractorAgent)
    prefs = TravelPreferences(clarification_needed=False, missing_fields=[])
    questions = agent.build_clarification_questions(prefs)
    assert questions == []


# ── Tests: TravelPreferences model properties ─────────────────────────────────


def test_is_complete_for_planning_true():
    prefs = TravelPreferences(
        destination="Kyoto",
        start_date=date(2024, 4, 10),
        end_date=date(2024, 4, 14),
        budget_amount=1800,
    )
    assert prefs.is_complete_for_planning is True


def test_is_complete_for_planning_missing_budget():
    prefs = TravelPreferences(
        destination="Kyoto",
        start_date=date(2024, 4, 10),
        end_date=date(2024, 4, 14),
        budget_amount=None,
    )
    assert prefs.is_complete_for_planning is False


def test_is_complete_for_planning_missing_destination():
    prefs = TravelPreferences(
        destination=None,
        start_date=date(2024, 4, 10),
        end_date=date(2024, 4, 14),
        budget_amount=1800,
    )
    assert prefs.is_complete_for_planning is False
