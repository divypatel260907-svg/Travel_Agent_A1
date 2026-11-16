# ✈️ VOYA — AI Travel Planner Agent

A production-ready, multi-agent **Travel Planner** web application that converts natural-language trip requests into complete, personalized travel plans in under 10 seconds — powered by **Groq LLM** and free APIs.

**Live:** [http://127.0.0.1:5000](http://127.0.0.1:5000) (local) · Vercel deployment ready

---

## Features

| Category | Features |
|---|---|
| **AI Planning** | Natural-language input → structured day-by-day itinerary with budget, weather, map, packing list, cultural tips |
| **Authentication** | Register, login, logout, forgot password, profile management |
| **Trip Management** | Save, view, list, share trips via unique links |
| **Export Suite** | Markdown (.md), Calendar (.ics), PDF export |
| **Interactive Map** | Leaflet.js map with day-by-day location markers |
| **Quick Re-plan** | "20% cheaper", "More food", "Less walking" one-click refinement |
| **Admin Dashboard** | User management, stats overview |
| **Sample Plan** | Demo tab with pre-built itinerary for instant preview |
| **Auth-gated Planner** | Planner section only visible after sign-in |

---

## Architecture

```
User (Browser)
     │
     ▼
┌────────────────────────────────────┐
│         Flask Application          │
│  (app factory, Jinja2 templates)   │
├────────────────────────────────────┤
│  Routes:                           │
│  ├── main.py    → Hero + Planner   │
│  ├── auth.py    → Login/Register   │
│  ├── api.py     → POST /api/plan   │
│  ├── trips.py   → CRUD + Export    │
│  └── admin.py   → Admin Dashboard  │
├────────────────────────────────────┤
│  Agents:                           │
│  ├── Preference Extractor (Groq)   │
│  └── Weather Agent (Open-Meteo)    │
├────────────────────────────────────┤
│  Services:                         │
│  ├── Groq LLM  (openai/gpt-oss-120b) │
│  ├── Open-Meteo (weather, keyless) │
│  └── Nominatim  (geocoding, keyless)│
├────────────────────────────────────┤
│  Data:                             │
│  ├── SQLite (local) / /tmp (Vercel)│
│  ├── Flask-Login sessions          │
│  └── Bcrypt password hashing       │
└────────────────────────────────────┘
```

### Request Flow

```
User types "5-day trip to Kyoto under $1800"
  → POST /api/plan
  → Groq LLM generates structured JSON itinerary (~4s)
  → Response includes: days[], budget{}, coordinates, packingList[], culturalTips[]
  → Frontend renders: day cards + Leaflet map + budget breakdown + packing checklist
```

---

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/divypatel260907-svg/Travel_Agent_A1.git
cd Travel_Agent_A1/travel_planner
pip install -r requirements.txt
```

### 2. Configure API Keys

```bash
# Create .env file in travel_planner/ directory:
GROQ_API_KEY=your_groq_key_here
GEMINI_API_KEY=your_gemini_key_here    # optional (review step disabled by default)
SECRET_KEY=any_random_secret_string
```

Get your free Groq key at [console.groq.com](https://console.groq.com)

### 3. Run

```bash
python run.py
# Open http://127.0.0.1:5000
```

### 4. Run Tests

```bash
pytest tests/ -v
# 26 tests, 0 failures
```

---

## Example Queries

Try these in the planner:

| Query | What you get |
|---|---|
| `5-day romantic trip to Kyoto under $1800 in April` | Day-by-day Kyoto itinerary with temples, food spots, cherry blossom timing |
| `3-day solo backpacking in Bangkok, street food focus, $500 budget` | Budget-friendly Bangkok plan with street food routes |
| `7-day family trip to Rome with kids, must see Colosseum` | Family-paced Rome itinerary with kid-friendly activities |
| `Weekend in Amsterdam with friends, nightlife + museums` | 2-day Amsterdam plan balancing culture and nightlife |

### Quick Start Chips

The planner includes 4 pre-built query chips:
- 🏯 **Kyoto Couple** — "5-day romantic trip to Kyoto under $1800..."
- 🌴 **Bangkok Solo** — "3-day solo backpacking in Bangkok..."
- 🏛️ **Rome Family** — "7-day family trip to Rome with kids..."
- 🌷 **Amsterdam Crew** — "Weekend in Amsterdam with friends..."

---

## Free APIs Used

| Service | Purpose | Key required? |
|---|---|---|
| [Groq](https://console.groq.com) | Fast LLM (openai/gpt-oss-120b) | ✅ Free tier |
| [Open-Meteo](https://open-meteo.com) | Weather forecasts | ❌ No |
| [Nominatim (OSM)](https://nominatim.openstreetmap.org) | Geocoding | ❌ No |
| [Leaflet.js](https://leafletjs.com) + OpenStreetMap | Interactive maps | ❌ No |
| [Google Gemini](https://aistudio.google.com) | Optional review step | ✅ Free tier (disabled by default) |

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `GROQ_API_KEY` | — | **Required.** Groq API key |
| `SECRET_KEY` | `dev-secret-key` | Flask session secret |
| `GEMINI_API_KEY` | — | Optional. For Gemini review step |
| `ENABLE_GEMINI_REVIEW` | `false` | Set to `true` to enable dual-LLM review |
| `GROQ_MODEL` | `openai/gpt-oss-120b` | Groq model name |
| `GEMINI_MODEL` | `gemini-3.5-flash` | Gemini model name |
| `DATABASE_URL` | `sqlite:///travel.db` | Database connection string |

---

## Project Layout

```
Travel_Agent_A1/
├── travel_planner/
│   ├── agents/
│   │   ├── preference_extractor.py   # NL → TravelPreferences (Groq)
│   │   └── weather_agent.py          # Open-Meteo forecast + scoring
│   ├── app/
│   │   ├── routes/
│   │   │   ├── main.py               # Hero page + planner
│   │   │   ├── auth.py               # Login, register, logout
│   │   │   ├── api.py                # POST /api/plan (Groq LLM)
│   │   │   ├── trips.py              # Trip CRUD + export
│   │   │   └── admin.py              # Admin dashboard
│   │   ├── services/
│   │   │   └── planner_service.py    # Plan orchestration
│   │   ├── config.py                 # App configuration
│   │   ├── extensions.py             # Flask extensions (db, bcrypt, login)
│   │   └── __init__.py               # App factory
│   ├── models/
│   │   ├── database.py               # SQLAlchemy models (User, Trip, etc.)
│   │   └── schemas.py                # Pydantic v2 schemas
│   ├── static/
│   │   ├── css/style.css             # Dark theme design system
│   │   └── js/main.js                # Plan rendering, map, export
│   ├── templates/
│   │   ├── auth/                     # Login, register, forgot password
│   │   ├── trips/                    # Trip list, view, shared
│   │   ├── admin/                    # Dashboard, user management
│   │   ├── base.html                 # Base layout
│   │   ├── index.html                # Hero + planner (auth-gated)
│   │   └── plan.html                 # Rendered plan page
│   ├── tests/                        # 26 tests (preference + weather)
│   ├── utils/                        # Cache, HTTP client, LLM factory
│   ├── requirements.txt
│   └── run.py                        # Local dev entrypoint
├── run.py                            # Vercel entrypoint
├── vercel.json                       # Vercel deployment config
├── requirements.txt                  # Root copy for Vercel
├── master_prompt.md                  # Full project specification
├── rule.md                           # Agent rules
├── skills.md                         # Agent skills
└── tech_stack.md                     # Technology stack reference
```

---

## Deployment (Vercel)

The app is configured for Vercel deployment via GitHub auto-deploy:

1. Push to `main` branch → auto-deploys
2. Set environment variables in Vercel dashboard: `GROQ_API_KEY`, `SECRET_KEY`
3. SQLite automatically uses `/tmp/travel.db` on Vercel (read-only filesystem)

---

## Tests

```bash
cd travel_planner
pytest tests/ -v

# Output:
# tests/test_preference_extractor.py — 11 tests (extraction, edge cases, formats)
# tests/test_weather_agent.py        — 15 tests (forecasts, geocoding, scoring)
# 26 passed in 0.63s
```

---

> **Disclaimer:** This is an AI-powered travel suggestion tool. Always verify bookings, opening hours, visa requirements, and travel advisories independently.
