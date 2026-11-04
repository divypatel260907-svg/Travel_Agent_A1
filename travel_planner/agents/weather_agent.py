"""
Weather Agent
=============
Fetches real-time weather forecasts for a destination + date range using
Open-Meteo (keyless, free tier) and Nominatim for geocoding.

Skill (skills.md – weather_tool):
  - Return temperature high/low, precipitation probability, weather code,
    short human summary, and an outdoor suitability score.

Rule (rule.md – Weather Agent):
  - Always fetch forecast for the exact travel dates.
  - Suggest indoor alternatives on high-rain probability days.

Usage
-----
    from travel_planner.agents.weather_agent import WeatherAgent

    agent = WeatherAgent()
    forecast = await agent.get_forecast("Kyoto", date(2024, 4, 10), date(2024, 4, 14))
    print(forecast.rainy_days)
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any

from travel_planner.models.schemas import DailyWeather, WeatherForecast
from travel_planner.utils.cache import cache
from travel_planner.utils.http_client import HttpClientError, get

logger = logging.getLogger(__name__)

# ── API endpoints (all keyless) ───────────────────────────────────────────────
_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
_OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
_NOMINATIM_HEADERS = {"User-Agent": "TravelPlannerAgent/1.0 (educational project)"}

# ── WMO weather code → (summary, outdoor_score) ───────────────────────────────
_WMO_MAP: dict[int, tuple[str, int]] = {
    0: ("Clear sky", 10),
    1: ("Mainly clear", 9),
    2: ("Partly cloudy", 8),
    3: ("Overcast", 6),
    45: ("Foggy", 4),
    48: ("Freezing fog", 3),
    51: ("Light drizzle", 5),
    53: ("Moderate drizzle", 4),
    55: ("Dense drizzle", 3),
    56: ("Freezing drizzle", 2),
    57: ("Heavy freezing drizzle", 1),
    61: ("Slight rain", 5),
    63: ("Moderate rain", 3),
    65: ("Heavy rain", 1),
    66: ("Freezing rain", 1),
    67: ("Heavy freezing rain", 0),
    71: ("Slight snow", 4),
    73: ("Moderate snow", 3),
    75: ("Heavy snow", 1),
    77: ("Snow grains", 3),
    80: ("Slight rain showers", 6),
    81: ("Moderate rain showers", 4),
    82: ("Violent rain showers", 1),
    85: ("Slight snow showers", 4),
    86: ("Heavy snow showers", 2),
    95: ("Thunderstorm", 0),
    96: ("Thunderstorm with hail", 0),
    99: ("Thunderstorm with heavy hail", 0),
}

_UNKNOWN_WEATHER = ("Unknown weather", 5)


def _wmo_summary_and_score(code: int) -> tuple[str, int]:
    return _WMO_MAP.get(code, _UNKNOWN_WEATHER)


def _adjust_score_for_rain(base_score: int, precip_prob: int) -> int:
    """Reduce score when precipitation probability is high regardless of WMO code."""
    if precip_prob >= 80:
        return min(base_score, 2)
    if precip_prob >= 60:
        return min(base_score, 4)
    if precip_prob >= 40:
        return min(base_score, 6)
    return base_score


class WeatherAgent:
    """
    Fetches and interprets weather forecasts using Open-Meteo.

    The agent:
    1. Geocodes the destination via Nominatim.
    2. Calls Open-Meteo for daily forecasts over the travel period.
    3. Adds a human summary and outdoor suitability score per day.
    4. Caches results (TTL = CACHE_TTL_SECONDS env var, default 1 hour).
    5. Returns WeatherForecast or raises on complete failure.
    """

    async def get_forecast(
        self,
        destination: str,
        start_date: date,
        end_date: date,
    ) -> WeatherForecast:
        """
        Fetch the weather forecast for a destination over a date range.

        Open-Meteo supports forecasts up to 16 days ahead and historical
        data via the archive endpoint. This method uses the forecast endpoint;
        if dates are in the past the caller should use get_historical_forecast.

        Args:
            destination: City or region name (e.g. "Kyoto", "Paris, France").
            start_date: First day of the trip.
            end_date: Last day of the trip.

        Returns:
            WeatherForecast with one DailyWeather entry per day.

        Raises:
            WeatherAgentError: When geocoding or forecast fetch permanently fails.
        """
        cache_key = cache.make_key(
            "weather", destination, str(start_date), str(end_date)
        )
        cached = await cache.get(cache_key)
        if cached:
            logger.debug("Weather cache hit for %s %s→%s", destination, start_date, end_date)
            return WeatherForecast(**cached)

        # Step 1 – Geocode
        lat, lon, timezone_str = await self._geocode(destination)

        # Step 2 – Fetch forecast
        raw = await self._fetch_forecast(lat, lon, start_date, end_date, timezone_str)

        # Step 3 – Parse
        forecast = self._parse_forecast(destination, lat, lon, timezone_str, raw)

        # Step 4 – Cache
        await cache.set(cache_key, forecast.model_dump(mode="json"))

        return forecast

    async def _geocode(self, destination: str) -> tuple[float, float, str]:
        """
        Return (latitude, longitude, timezone) for a destination string.

        Uses Nominatim (OpenStreetMap). Falls back to a manual override table
        for common cities when Nominatim is unavailable.
        """
        cache_key = cache.make_key("geocode", destination)
        cached = await cache.get(cache_key)
        if cached:
            return cached["lat"], cached["lon"], cached["tz"]

        try:
            result: Any = await get(
                _NOMINATIM_URL,
                params={
                    "q": destination,
                    "format": "json",
                    "limit": 1,
                    "addressdetails": 0,
                },
                headers=_NOMINATIM_HEADERS,
            )
            if not result or not isinstance(result, list) or len(result) == 0:
                raise WeatherAgentError(f"Nominatim returned no results for '{destination}'")

            hit = result[0]
            lat = float(hit["lat"])
            lon = float(hit["lon"])
            # Nominatim doesn't return timezone; use Open-Meteo timezone detection
            tz = await self._detect_timezone(lat, lon)

            await cache.set(cache_key, {"lat": lat, "lon": lon, "tz": tz})
            logger.debug("Geocoded '%s' → lat=%.4f, lon=%.4f, tz=%s", destination, lat, lon, tz)
            return lat, lon, tz

        except HttpClientError as exc:
            logger.warning("Nominatim unavailable: %s – trying fallback table", exc)
            return self._fallback_geocode(destination)

    async def _detect_timezone(self, lat: float, lon: float) -> str:
        """Ask Open-Meteo for the timezone string of a coordinate pair."""
        try:
            data: Any = await get(
                _OPEN_METEO_URL,
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "timezone": "auto",
                    "forecast_days": 1,
                    "daily": "temperature_2m_max",
                },
            )
            return data.get("timezone", "UTC")
        except Exception:
            return "UTC"

    def _fallback_geocode(self, destination: str) -> tuple[float, float, str]:
        """Hardcoded fallback for popular cities when Nominatim is down."""
        FALLBACKS: dict[str, tuple[float, float, str]] = {
            "kyoto": (35.0116, 135.7681, "Asia/Tokyo"),
            "tokyo": (35.6762, 139.6503, "Asia/Tokyo"),
            "paris": (48.8566, 2.3522, "Europe/Paris"),
            "london": (51.5074, -0.1278, "Europe/London"),
            "new york": (40.7128, -74.0060, "America/New_York"),
            "bangkok": (13.7563, 100.5018, "Asia/Bangkok"),
            "rome": (41.9028, 12.4964, "Europe/Rome"),
            "barcelona": (41.3851, 2.1734, "Europe/Madrid"),
            "amsterdam": (52.3676, 4.9041, "Europe/Amsterdam"),
            "sydney": (-33.8688, 151.2093, "Australia/Sydney"),
        }
        key = destination.lower().strip()
        for city, coords in FALLBACKS.items():
            if city in key:
                return coords
        raise WeatherAgentError(
            f"Could not geocode '{destination}'. "
            "Please provide a more specific location name."
        )

    async def _fetch_forecast(
        self,
        lat: float,
        lon: float,
        start_date: date,
        end_date: date,
        timezone_str: str,
    ) -> dict[str, Any]:
        """Call Open-Meteo daily forecast API."""
        params: dict[str, Any] = {
            "latitude": lat,
            "longitude": lon,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "timezone": timezone_str,
            "daily": ",".join([
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_probability_max",
                "weathercode",
                "windspeed_10m_max",
                "uv_index_max",
            ]),
        }
        try:
            data: Any = await get(_OPEN_METEO_URL, params=params)
            if not isinstance(data, dict) or "daily" not in data:
                raise WeatherAgentError(
                    f"Open-Meteo returned unexpected response: {str(data)[:200]}"
                )
            return data
        except HttpClientError as exc:
            raise WeatherAgentError(
                f"Open-Meteo request failed: {exc}"
            ) from exc

    def _parse_forecast(
        self,
        destination: str,
        lat: float,
        lon: float,
        timezone_str: str,
        raw: dict[str, Any],
    ) -> WeatherForecast:
        """Convert raw Open-Meteo response into a WeatherForecast model."""
        daily = raw["daily"]
        dates: list[str] = daily.get("time", [])
        temp_max: list[float | None] = daily.get("temperature_2m_max", [])
        temp_min: list[float | None] = daily.get("temperature_2m_min", [])
        precip_prob: list[int | None] = daily.get("precipitation_probability_max", [])
        weather_codes: list[int | None] = daily.get("weathercode", [])
        wind_max: list[float | None] = daily.get("windspeed_10m_max", [])
        uv_max: list[float | None] = daily.get("uv_index_max", [])

        days: list[DailyWeather] = []
        for i, date_str in enumerate(dates):
            code = int(weather_codes[i]) if i < len(weather_codes) and weather_codes[i] is not None else 0
            prob = int(precip_prob[i]) if i < len(precip_prob) and precip_prob[i] is not None else 0
            summary, base_score = _wmo_summary_and_score(code)
            score = _adjust_score_for_rain(base_score, prob)

            days.append(
                DailyWeather(
                    date=date.fromisoformat(date_str),
                    temperature_max_c=float(temp_max[i]) if i < len(temp_max) and temp_max[i] is not None else 0.0,
                    temperature_min_c=float(temp_min[i]) if i < len(temp_min) and temp_min[i] is not None else 0.0,
                    precipitation_probability_max=prob,
                    weather_code=code,
                    weather_summary=summary,
                    outdoor_suitability_score=score,
                    wind_speed_max_kmh=float(wind_max[i]) if i < len(wind_max) and wind_max[i] is not None else None,
                    uv_index_max=float(uv_max[i]) if i < len(uv_max) and uv_max[i] is not None else None,
                )
            )

        return WeatherForecast(
            destination=destination,
            latitude=lat,
            longitude=lon,
            timezone=timezone_str,
            days=days,
            fetched_at=datetime.now(tz=timezone.utc).isoformat(),
        )

    def suggest_indoor_alternatives(self, forecast: WeatherForecast) -> dict[str, list[str]]:
        """
        Return a mapping of date → list of indoor activity suggestions for rainy days.

        Rule (rule.md): Suggest indoor alternatives on high-rain probability days.

        Args:
            forecast: WeatherForecast returned by get_forecast().

        Returns:
            Dict keyed by ISO date string, values are lists of suggestion strings.
            Only rainy days (precipitation >= 50%) are included.
        """
        suggestions: dict[str, list[str]] = {}
        for day in forecast.rainy_days:
            suggestions[str(day.date)] = _INDOOR_SUGGESTIONS.get(
                day.precipitation_probability_max // 10 * 10,  # bucket to nearest 10
                _DEFAULT_INDOOR_SUGGESTIONS,
            )
        return suggestions

    def format_summary(self, forecast: WeatherForecast) -> str:
        """
        Return a compact plain-text summary of the forecast suitable for
        inclusion in LLM prompts or user-facing messages.
        """
        lines = [f"Weather for {forecast.destination}:"]
        for day in forecast.days:
            rain_note = f", 🌧 {day.precipitation_probability_max}% rain" if day.precipitation_probability_max >= 40 else ""
            lines.append(
                f"  {day.date}  {day.weather_summary}  "
                f"↑{day.temperature_max_c:.0f}°C / ↓{day.temperature_min_c:.0f}°C"
                f"{rain_note}  (outdoor score: {day.outdoor_suitability_score}/10)"
            )
        return "\n".join(lines)


# ── Indoor activity suggestion tables ─────────────────────────────────────────

_INDOOR_SUGGESTIONS: dict[int, list[str]] = {
    50: [
        "Visit a local museum or art gallery",
        "Explore a covered market or food hall",
        "Attend a cooking class",
        "Relax at a spa or onsen",
    ],
    60: [
        "Explore a major indoor attraction (aquarium, science museum)",
        "Join a cultural workshop or craft class",
        "Watch a local film or theater performance",
        "Dine at a famous restaurant you've been curious about",
    ],
    70: [
        "Dedicate the day to a large museum (e.g. national history or art)",
        "Visit a shopping district with covered arcades",
        "Attend a tea ceremony or cultural experience indoors",
        "Rest and plan the rest of the trip at a café",
    ],
    80: [
        "Full rainy day: indoor cultural tour (museum hopping)",
        "Cooking class or hands-on local workshop",
        "Visit an indoor theme park or entertainment complex",
        "Use the day for long restaurant experiences",
    ],
    90: [
        "Stay near your accommodation; order local delivery or visit nearest covered venue",
        "Book an in-hotel wellness session (massage, sauna)",
        "Stream a documentary about local culture",
        "Pack for tomorrow and review the itinerary",
    ],
}

_DEFAULT_INDOOR_SUGGESTIONS = [
    "Visit a nearby museum or gallery",
    "Explore a covered market or shopping arcade",
    "Enjoy a long, leisurely meal at a local restaurant",
    "Relax at a café and plan the next day",
]


class WeatherAgentError(Exception):
    """Raised when the Weather Agent cannot retrieve a forecast."""


def _mock_forecast_data() -> WeatherForecast:
    """Return a fixed 5-day Kyoto forecast — used in demo mode without HTTP calls."""
    from datetime import timedelta  # noqa: PLC0415
    base = date(2024, 4, 10)
    return WeatherForecast(
        destination="Kyoto", latitude=35.0116, longitude=135.7681,
        timezone="Asia/Tokyo", fetched_at="2024-04-01T09:00:00+00:00",
        days=[
            DailyWeather(date=base,              temperature_max_c=19, temperature_min_c=11, precipitation_probability_max=10, weather_code=1,  weather_summary="Mainly clear",  outdoor_suitability_score=9,  wind_speed_max_kmh=8,  uv_index_max=5),
            DailyWeather(date=base+timedelta(1), temperature_max_c=21, temperature_min_c=13, precipitation_probability_max=15, weather_code=0,  weather_summary="Clear sky",     outdoor_suitability_score=10, wind_speed_max_kmh=5,  uv_index_max=6),
            DailyWeather(date=base+timedelta(2), temperature_max_c=16, temperature_min_c=10, precipitation_probability_max=70, weather_code=63, weather_summary="Moderate rain", outdoor_suitability_score=3,  wind_speed_max_kmh=18, uv_index_max=2),
            DailyWeather(date=base+timedelta(3), temperature_max_c=14, temperature_min_c=9,  precipitation_probability_max=85, weather_code=65, weather_summary="Heavy rain",    outdoor_suitability_score=1,  wind_speed_max_kmh=22, uv_index_max=1),
            DailyWeather(date=base+timedelta(4), temperature_max_c=22, temperature_min_c=13, precipitation_probability_max=5,  weather_code=0,  weather_summary="Clear sky",     outdoor_suitability_score=10, wind_speed_max_kmh=4,  uv_index_max=7),
        ],
    )
