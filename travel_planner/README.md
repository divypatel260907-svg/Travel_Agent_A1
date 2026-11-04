# ✈️ Travel Planner Agent

A production-ready, multi-agent **Travel Planner** that converts a natural-language request into a complete, personalized, real-time travel plan — powered by **Groq** (speed) + **Google Gemini** (reasoning) and 100% free APIs.

---

## Architecture

```
User Input
    │
    ▼
┌─────────────────────────┐
│   Preference Extractor  │  ← Groq (fast, tool-calling)
│   agents/preference_    │    Extracts structured TravelPreferences
│   extractor.py          │    Asks clarifying Qs if critical info missing
└────────────┬────────────┘
             │ TravelPreferences
             ▼
┌─────────────────────────┐
│     Weather Agent       │  ← Open-Meteo (keyless)
│   agents/weather_       │    Geocoding via Nominatim (keyless)
│   agent.py              │    Suitability scores + indoor alternatives
└────────────┬────────────┘
             │ WeatherForecast
             ▼
     [coming next]
  Attractions · Itinerary Builder
  Budget · Contingency · Export
```

All agents share the **`PlannerState`** model and are wired together via **LangGraph**.

---

## Implemented (Phase 1)

| Component | File | Status |
|---|---|---|
| Core schemas (Pydantic v2) | `models/schemas.py` | ✅ |
| Preference Extractor | `agents/preference_extractor.py` | ✅ |
| Weather Agent | `agents/weather_agent.py` | ✅ |
| HTTP client (retry + timeout) | `utils/http_client.py` | ✅ |
| Two-tier cache (memory + SQLite) | `utils/cache.py` | ✅ |
| LLM factory (Groq + Gemini) | `utils/llm.py` | ✅ |
| Tests (26 tests, 0 failures) | `tests/` | ✅ |

---

## Quick Start

### 1. Clone & install

```bash
git clone <repo>
cd travel_planner
pip install -r requirements.txt
```

### 2. Configure API keys

```bash
cp .env.example .env
# Edit .env and set:
#   GROQ_API_KEY   → https://console.groq.com  (free)
#   GEMINI_API_KEY → https://aistudio.google.com/app/apikey  (free)
```

### 3. Run tests (no keys needed)

```bash
pytest tests/ -v
```

---

## Usage Examples

### Preference Extractor

```python
import asyncio
from travel_planner.agents.preference_extractor import PreferenceExtractorAgent

agent = PreferenceExtractorAgent()

async def main():
    prefs = await agent.extract(
        "5-day romantic trip to Kyoto under $1800 in mid-April, "
        "no heavy walking, love food & temples"
    )
    print(prefs.destination)       # Kyoto
    print(prefs.budget_amount)     # 1800
    print(prefs.group_type)        # couple
    print(prefs.accessibility_needs)  # ['no heavy walking']

    if prefs.clarification_needed:
        questions = agent.build_clarification_questions(prefs)
        for q in questions:
            print(q)

asyncio.run(main())
```

### Weather Agent

```python
import asyncio
from datetime import date
from travel_planner.agents.weather_agent import WeatherAgent

agent = WeatherAgent()

async def main():
    forecast = await agent.get_forecast("Kyoto", date(2024, 4, 10), date(2024, 4, 14))
    print(agent.format_summary(forecast))

    # Rainy days and indoor alternatives
    indoors = agent.suggest_indoor_alternatives(forecast)
    for day, activities in indoors.items():
        print(f"{day}: {activities}")

asyncio.run(main())
```

---

## Free APIs Used

| Service | Purpose | Key required? |
|---|---|---|
| [Open-Meteo](https://open-meteo.com) | Weather forecasts | ❌ No |
| [Nominatim (OSM)](https://nominatim.openstreetmap.org) | Geocoding | ❌ No |
| [Groq](https://console.groq.com) | Fast LLM (Llama 3.3) | ✅ Free tier |
| [Google Gemini](https://aistudio.google.com) | Reasoning LLM | ✅ Free tier |
| [OpenTripMap](https://opentripmap.io) | POIs (Phase 2) | ✅ Free tier |

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `GROQ_API_KEY` | — | **Required.** Groq API key |
| `GEMINI_API_KEY` | — | **Required.** Google AI Studio key |
| `OPENTRIPMAP_API_KEY` | — | Optional. Used by Attractions agent |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Groq model name |
| `GEMINI_MODEL` | `gemini-1.5-flash` | Gemini model name |
| `PREFERENCE_STORAGE` | `session` | `session` = memory only; `local` = SQLite persistence |
| `CACHE_TTL_SECONDS` | `3600` | Cache TTL in seconds |

---

## Project Layout

```
travel_planner/
├── agents/
│   ├── preference_extractor.py  # NL → TravelPreferences (Groq)
│   └── weather_agent.py         # Open-Meteo forecast + scoring
├── models/
│   └── schemas.py               # All Pydantic v2 models
├── utils/
│   ├── cache.py                 # Memory + SQLite two-tier cache
│   ├── http_client.py           # Async HTTP with retry/timeout
│   └── llm.py                  # Groq / Gemini factory
├── tests/
│   ├── test_preference_extractor.py
│   └── test_weather_agent.py
├── .env.example
├── pytest.ini
└── requirements.txt
```

---

## Coding Rules (summary)

- All models are **Pydantic v2** with type hints
- All HTTP calls are **async** (`httpx`) with max 2 retries + timeout
- API keys are **environment variables only** — never hard-coded
- Missing data is surfaced gracefully; agents never crash silently
- Cache is aggressive (default 1 h TTL) to respect rate limits

> **Disclaimer:** This is an AI-generated suggestion. Always verify bookings, opening hours, and travel requirements independently.
