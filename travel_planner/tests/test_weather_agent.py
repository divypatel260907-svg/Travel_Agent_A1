"""
Tests for the Weather Agent.

HTTP calls are mocked via unittest.mock so no API key or network is needed.
Run with: pytest travel_planner/tests/test_weather_agent.py -v
"""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from travel_planner.agents.weather_agent import (
    WeatherAgent,
    WeatherAgentError,
    _adjust_score_for_rain,
    _wmo_summary_and_score,
)
from travel_planner.models.schemas import WeatherForecast


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _nominatim_response(lat: float = 35.0116, lon: float = 135.7681) -> list[dict]:
    return [{"lat": str(lat), "lon": str(lon), "display_name": "Kyoto, Japan"}]


def _open_meteo_timezone_response(tz: str = "Asia/Tokyo") -> dict:
    return {
        "timezone": tz,
        "daily": {"time": ["2024-04-10"], "temperature_2m_max": [20.0]},
    }


def _open_meteo_forecast_response() -> dict:
    return {
        "timezone": "Asia/Tokyo",
        "daily": {
            "time": ["2024-04-10", "2024-04-11", "2024-04-12", "2024-04-13", "2024-04-14"],
            "temperature_2m_max": [18.0, 20.0, 15.0, 12.0, 22.0],
            "temperature_2m_min": [10.0, 12.0, 9.0, 8.0, 13.0],
            "precipitation_probability_max": [10, 20, 70, 90, 5],
            "weathercode": [0, 1, 63, 65, 0],
            "windspeed_10m_max": [5.0, 8.0, 15.0, 20.0, 3.0],
            "uv_index_max": [4.0, 5.0, 2.0, 1.0, 6.0],
        },
    }


# ── Unit tests: pure helpers ───────────────────────────────────────────────────


def test_wmo_summary_and_score_clear():
    summary, score = _wmo_summary_and_score(0)
    assert summary == "Clear sky"
    assert score == 10


def test_wmo_summary_and_score_heavy_rain():
    summary, score = _wmo_summary_and_score(65)
    assert score == 1


def test_wmo_summary_and_score_unknown_code():
    summary, score = _wmo_summary_and_score(999)
    assert summary == "Unknown weather"
    assert score == 5


def test_adjust_score_for_rain_high_prob():
    """80%+ rain probability should cap score at 2."""
    assert _adjust_score_for_rain(10, 80) == 2
    assert _adjust_score_for_rain(10, 95) == 2


def test_adjust_score_for_rain_moderate_prob():
    assert _adjust_score_for_rain(10, 60) == 4
    assert _adjust_score_for_rain(10, 40) == 6


def test_adjust_score_no_rain():
    """Low precipitation probability should leave base score unchanged."""
    assert _adjust_score_for_rain(10, 10) == 10
    assert _adjust_score_for_rain(7, 0) == 7


# ── Integration-style tests (mocked HTTP) ────────────────────────────────────


@pytest.mark.asyncio
async def test_get_forecast_returns_correct_days():
    """get_forecast should return 5 DailyWeather entries for a 5-day trip."""
    agent = WeatherAgent()

    with (
        patch(
            "travel_planner.agents.weather_agent.get",
            new=AsyncMock(
                side_effect=[
                    _nominatim_response(),          # 1st call: Nominatim geocode
                    _open_meteo_timezone_response(), # 2nd call: timezone detection
                    _open_meteo_forecast_response(), # 3rd call: actual forecast
                ]
            ),
        ),
        patch("travel_planner.utils.cache.TwoTierCache.get", new=AsyncMock(return_value=None)),
        patch("travel_planner.utils.cache.TwoTierCache.set", new=AsyncMock()),
    ):
        forecast = await agent.get_forecast("Kyoto", date(2024, 4, 10), date(2024, 4, 14))

    assert isinstance(forecast, WeatherForecast)
    assert len(forecast.days) == 5
    assert forecast.destination == "Kyoto"
    assert forecast.latitude == pytest.approx(35.0116, abs=0.001)
    assert forecast.longitude == pytest.approx(135.7681, abs=0.001)


@pytest.mark.asyncio
async def test_get_forecast_rainy_days_identified():
    """Days with precipitation >= 50% should be in rainy_days."""
    agent = WeatherAgent()
    # Directly test _parse_forecast with controlled data
    raw = _open_meteo_forecast_response()
    forecast = agent._parse_forecast("Kyoto", 35.0116, 135.7681, "Asia/Tokyo", raw)

    rainy = forecast.rainy_days
    rainy_dates = [str(d.date) for d in rainy]
    # indices 2 (70%) and 3 (90%) should be rainy
    assert "2024-04-12" in rainy_dates
    assert "2024-04-13" in rainy_dates
    # index 0 (10%) should not be rainy
    assert "2024-04-10" not in rainy_dates


@pytest.mark.asyncio
async def test_get_forecast_best_and_worst_day():
    """best_day should have highest score; worst_day should have lowest."""
    agent = WeatherAgent()
    raw = _open_meteo_forecast_response()
    forecast = agent._parse_forecast("Kyoto", 35.0116, 135.7681, "Asia/Tokyo", raw)

    assert forecast.best_day is not None
    assert forecast.worst_day is not None
    assert forecast.best_day.outdoor_suitability_score >= forecast.worst_day.outdoor_suitability_score


@pytest.mark.asyncio
async def test_outdoor_suitability_score_reduced_on_rainy_day():
    """Days with 90% rain probability should have very low suitability scores."""
    agent = WeatherAgent()
    raw = _open_meteo_forecast_response()
    forecast = agent._parse_forecast("Kyoto", 35.0116, 135.7681, "Asia/Tokyo", raw)

    # April 13 has 90% rain
    day_13 = next(d for d in forecast.days if str(d.date) == "2024-04-13")
    assert day_13.outdoor_suitability_score <= 2


@pytest.mark.asyncio
async def test_fallback_geocode_known_city():
    """Fallback table should return coordinates for popular cities."""
    agent = WeatherAgent()
    lat, lon, tz = agent._fallback_geocode("Kyoto, Japan")
    assert abs(lat - 35.0116) < 0.1
    assert abs(lon - 135.7681) < 0.1
    assert tz == "Asia/Tokyo"


@pytest.mark.asyncio
async def test_fallback_geocode_unknown_city_raises():
    """Unknown cities not in the fallback table should raise WeatherAgentError."""
    agent = WeatherAgent()
    with pytest.raises(WeatherAgentError):
        agent._fallback_geocode("Obscure Place XYZ 12345")


def test_suggest_indoor_alternatives_has_rainy_days():
    """suggest_indoor_alternatives should return entries only for rainy days."""
    agent = WeatherAgent()
    raw = _open_meteo_forecast_response()
    forecast = agent._parse_forecast("Kyoto", 35.0116, 135.7681, "Asia/Tokyo", raw)

    suggestions = agent.suggest_indoor_alternatives(forecast)
    # Only days with >= 50% rain probability
    assert "2024-04-12" in suggestions
    assert "2024-04-13" in suggestions
    assert "2024-04-10" not in suggestions
    for date_str, alts in suggestions.items():
        assert isinstance(alts, list)
        assert len(alts) > 0


def test_format_summary_contains_destination():
    """format_summary should include the destination name."""
    agent = WeatherAgent()
    raw = _open_meteo_forecast_response()
    forecast = agent._parse_forecast("Kyoto", 35.0116, 135.7681, "Asia/Tokyo", raw)
    summary = agent.format_summary(forecast)
    assert "Kyoto" in summary
    assert "2024-04-10" in summary


@pytest.mark.asyncio
async def test_get_forecast_uses_cache_on_second_call():
    """Second call for same destination + dates should hit cache and skip HTTP."""
    from travel_planner.utils.cache import cache as real_cache

    agent = WeatherAgent()

    raw = _open_meteo_forecast_response()
    # Pre-populate the cache
    forecast = agent._parse_forecast("Kyoto", 35.0116, 135.7681, "Asia/Tokyo", raw)
    cache_key = real_cache.make_key("weather", "Kyoto", "2024-04-10", "2024-04-14")

    with patch(
        "travel_planner.utils.cache.TwoTierCache.get",
        new=AsyncMock(return_value=forecast.model_dump(mode="json")),
    ):
        with patch("travel_planner.agents.weather_agent.get", new=AsyncMock()) as mock_http:
            result = await agent.get_forecast("Kyoto", date(2024, 4, 10), date(2024, 4, 14))
            mock_http.assert_not_called()

    assert isinstance(result, WeatherForecast)
    assert len(result.days) == 5
