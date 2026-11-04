"""
Shared Pydantic v2 schemas used across all agents.
Keep this file as the single source of truth for inter-agent data contracts.
"""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ─── Enumerations ─────────────────────────────────────────────────────────────


class GroupType(str, Enum):
    SOLO = "solo"
    COUPLE = "couple"
    FAMILY = "family"
    FRIENDS = "friends"


class Pace(str, Enum):
    RELAXED = "relaxed"
    MODERATE = "moderate"
    FAST = "fast"


class BudgetStyle(str, Enum):
    BUDGET = "budget"
    MID_RANGE = "mid_range"
    LUXURY = "luxury"


class WeatherCode(int, Enum):
    """WMO Weather Interpretation Codes (subset used in summaries)."""

    CLEAR = 0
    PARTLY_CLOUDY = 2
    OVERCAST = 3
    DRIZZLE = 51
    RAIN = 61
    HEAVY_RAIN = 65
    SNOW = 71
    THUNDERSTORM = 95


# ─── Preferences ──────────────────────────────────────────────────────────────


class TravelPreferences(BaseModel):
    """
    Structured travel preferences extracted from natural language.
    All fields are optional so partial extractions are valid; missing critical
    fields trigger clarifying questions in the Preference Extractor agent.
    """

    destination: Optional[str] = Field(None, description="Primary destination city / region.")
    alternate_destinations: list[str] = Field(
        default_factory=list, description="Other destinations if the user mentioned alternatives."
    )
    start_date: Optional[date] = Field(None, description="Trip start date (YYYY-MM-DD).")
    end_date: Optional[date] = Field(None, description="Trip end date (YYYY-MM-DD).")
    duration_days: Optional[int] = Field(None, ge=1, le=90, description="Trip duration in days.")
    budget_amount: Optional[float] = Field(None, ge=0, description="Total budget (numeric).")
    budget_currency: str = Field("USD", description="ISO 4217 currency code.")
    budget_style: Optional[BudgetStyle] = None
    group_type: Optional[GroupType] = None
    group_size: Optional[int] = Field(None, ge=1, le=50)
    pace: Optional[Pace] = None
    interests: list[str] = Field(
        default_factory=list,
        description="E.g. ['temples', 'food', 'hiking', 'museums'].",
    )
    dietary: list[str] = Field(
        default_factory=list,
        description="E.g. ['vegetarian', 'halal', 'gluten-free'].",
    )
    accessibility_needs: list[str] = Field(
        default_factory=list,
        description="E.g. ['wheelchair', 'no heavy walking'].",
    )
    must_do: list[str] = Field(default_factory=list, description="Must-visit places or experiences.")
    must_avoid: list[str] = Field(default_factory=list, description="Places or activities to avoid.")
    preferred_language: str = Field("en", description="BCP-47 language tag for output.")
    user_nationality: Optional[str] = Field(None, description="ISO 3166-1 alpha-2 country code.")

    # ── clarification state ──────────────────────────────────────────────────
    clarification_needed: bool = Field(
        False, description="True when critical fields are missing and must be asked."
    )
    missing_fields: list[str] = Field(
        default_factory=list,
        description="List of field names still needed from the user.",
    )
    raw_input: Optional[str] = Field(None, description="Original natural language input (for logging).")

    @field_validator("budget_currency")
    @classmethod
    def upper_currency(cls, v: str) -> str:
        return v.upper()

    @field_validator("preferred_language")
    @classmethod
    def lower_language(cls, v: str) -> str:
        return v.lower()

    @property
    def has_dates(self) -> bool:
        return self.start_date is not None and self.end_date is not None

    @property
    def has_budget(self) -> bool:
        return self.budget_amount is not None

    @property
    def is_complete_for_planning(self) -> bool:
        """Returns True if enough data exists to start planning."""
        return bool(self.destination and self.has_dates and self.has_budget)


# ─── Weather ──────────────────────────────────────────────────────────────────


class DailyWeather(BaseModel):
    """Weather forecast for a single day."""

    date: date
    temperature_max_c: float
    temperature_min_c: float
    precipitation_probability_max: int = Field(ge=0, le=100)
    weather_code: int
    weather_summary: str = Field(description="Short human-readable description.")
    outdoor_suitability_score: int = Field(
        ge=0,
        le=10,
        description=(
            "0 = terrible (heavy rain/storm), 10 = perfect. "
            "Used by the Itinerary Builder to schedule outdoor activities."
        ),
    )
    wind_speed_max_kmh: Optional[float] = None
    uv_index_max: Optional[float] = None


class WeatherForecast(BaseModel):
    """Full weather forecast for a destination over the travel period."""

    destination: str
    latitude: float
    longitude: float
    timezone: str
    days: list[DailyWeather]
    source: str = "Open-Meteo (openmeteo.com)"
    fetched_at: Optional[str] = None  # ISO datetime string

    @property
    def worst_day(self) -> Optional[DailyWeather]:
        return min(self.days, key=lambda d: d.outdoor_suitability_score) if self.days else None

    @property
    def best_day(self) -> Optional[DailyWeather]:
        return max(self.days, key=lambda d: d.outdoor_suitability_score) if self.days else None

    @property
    def rainy_days(self) -> list[DailyWeather]:
        return [d for d in self.days if d.precipitation_probability_max >= 50]


# ─── Agent State (LangGraph shared state) ─────────────────────────────────────


class PlannerState(BaseModel):
    """
    Shared state passed between agents in the LangGraph graph.
    Each agent reads what it needs and writes its own output key.
    """

    user_input: str = ""
    preferences: Optional[TravelPreferences] = None
    weather: Optional[WeatherForecast] = None
    # Future agents will populate these:
    pois: Optional[list[dict]] = None
    itinerary: Optional[dict] = None
    budget_summary: Optional[dict] = None
    contingencies: Optional[dict] = None
    export_artifacts: Optional[dict] = None
    # Conversation / error tracking
    clarification_questions: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    messages: list[dict] = Field(
        default_factory=list,
        description="Raw message history for LLM context (role + content pairs).",
    )
