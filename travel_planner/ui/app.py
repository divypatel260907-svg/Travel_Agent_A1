"""
Travel Planner Agent – Streamlit UI  (Premium Edition)
=======================================================
Run:  streamlit run ui/app.py   (from the travel_planner/ directory)

Two modes:
  • Demo  – no keys needed; mock preferences + live Open-Meteo weather.
  • Live  – enter keys in the sidebar ⚙️ panel OR set them in .env.
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import date, timedelta
from pathlib import Path

# ── path fix: make `travel_planner` importable ──────────────────────────────
_PACKAGE_DIR = Path(__file__).resolve().parent.parent   # ibm-bob/travel_planner/
_WORKSPACE   = _PACKAGE_DIR.parent                      # ibm-bob/
for _p in (_WORKSPACE, _PACKAGE_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from dotenv import load_dotenv
load_dotenv(_PACKAGE_DIR / ".env", override=False)

import streamlit as st

st.set_page_config(
    page_title="Travel Planner AI",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

from travel_planner.agents.preference_extractor import PreferenceExtractorAgent
from travel_planner.agents.weather_agent import WeatherAgent, WeatherAgentError
from travel_planner.models.schemas import (
    DailyWeather, GroupType, Pace, TravelPreferences, WeatherForecast,
)

# ─────────────────────────────────────────────────────────────────────────────
# Premium CSS injection
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ═══════════════════════════════════════════════════════════════
   TRAVEL PLANNER AI — Premium Design System
   Inspired by: Inter · shadcn/ui · Framer Motion · Tailwind v4
   tech_stack.md: hierarchy, spacing, animation, dark mode, a11y
═══════════════════════════════════════════════════════════════ */

/* ── CSS variable tokens (shadcn/ui pattern) ── */
:root {
  --bg-base:       #050810;
  --bg-surface:    #07091a;
  --bg-card:       rgba(255,255,255,0.028);
  --bg-hover:      rgba(255,255,255,0.048);
  --border:        rgba(120,150,255,0.10);
  --border-active: rgba(120,150,255,0.42);
  --accent:        #4f6ef7;
  --accent-glow:   rgba(79,110,247,0.35);
  --violet:        #8b5cf6;
  --text-1:        #eef2ff;
  --text-2:        #8896c0;
  --text-3:        #3d4d70;
  --success:       #34d399;
  --warning:       #fbbf24;
  --danger:        #f87171;
  --r-sm:          8px;
  --r-md:          14px;
  --r-lg:          20px;
  --shadow:        0 1px 3px rgba(0,0,0,.55), 0 8px 28px rgba(0,0,0,.4);
  --ease:          cubic-bezier(0.4, 0, 0.2, 1);
  --t:             all 0.22s var(--ease);
}

/* ── Inter + Geist font (tech_stack.md: Geist/Inter) ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
html, body, [class*="css"], .stApp * {
    font-family: 'Inter','Geist',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif !important;
    -webkit-font-smoothing: antialiased !important;
}

/* ── Deep layered mesh background ── */
.stApp {
    background:
        radial-gradient(ellipse 90% 55% at 15%  8%, rgba(79,110,247,0.08)  0%, transparent 65%),
        radial-gradient(ellipse 60% 45% at 85% 85%, rgba(139,92,246,0.07)  0%, transparent 65%),
        radial-gradient(ellipse 50% 35% at 50% 50%, rgba(79,110,247,0.03)  0%, transparent 70%),
        linear-gradient(165deg, #050810 0%, #06091a 55%, #050810 100%) !important;
    background-attachment: fixed !important;
    min-height: 100vh !important;
}

/* ── Sidebar — deep glass panel ── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg,#060918 0%,#07091c 100%) !important;
    border-right: 1px solid var(--border) !important;
}
section[data-testid="stSidebar"] > div { padding-top: 0 !important; }
section[data-testid="stSidebar"] * { color: var(--text-2) !important; }

/* ── Main content — Tailwind-style spacing ── */
.main .block-container {
    padding: 2.5rem 3.5rem 5rem !important;
    max-width: 1280px !important;
}

/* ── Typography hierarchy (tech_stack: visual hierarchy first) ── */
h1 { color: var(--text-1) !important; font-weight: 800 !important; letter-spacing: -1px !important; line-height: 1.1 !important; }
h2 { color: var(--text-1) !important; font-weight: 700 !important; }
h3 { color: var(--text-2) !important; font-weight: 600 !important; text-transform: uppercase !important; letter-spacing: 1.3px !important; font-size: 0.7rem !important; }
p, li { color: var(--text-2) !important; line-height: 1.75 !important; }
.stCaption { color: var(--text-3) !important; font-size: 11px !important; }

/* ── Textarea — shadcn Input ── */
textarea {
    background: rgba(255,255,255,0.032) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--r-md) !important;
    color: var(--text-1) !important;
    font-size: 15px !important;
    line-height: 1.65 !important;
    padding: 14px 16px !important;
    transition: var(--t) !important;
    box-shadow: inset 0 1px 3px rgba(0,0,0,.25) !important;
    resize: vertical !important;
}
textarea:focus {
    border-color: var(--border-active) !important;
    box-shadow: 0 0 0 3px rgba(79,110,247,0.14), inset 0 1px 3px rgba(0,0,0,.25) !important;
    background: rgba(255,255,255,0.048) !important;
    outline: none !important;
}
textarea::placeholder { color: var(--text-3) !important; }

/* ── Primary button — gradient + glow (Framer Motion principle) ── */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg,#3d5ce8 0%,#6b82f7 100%) !important;
    border: 1px solid rgba(107,130,247,0.5) !important;
    border-radius: var(--r-sm) !important;
    color: #fff !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    letter-spacing: 0.2px !important;
    padding: 0.58rem 1.5rem !important;
    transition: var(--t) !important;
    box-shadow: 0 4px 18px var(--accent-glow), inset 0 1px 0 rgba(255,255,255,0.13) !important;
    text-shadow: 0 1px 2px rgba(0,0,0,.25) !important;
}
.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg,#4f70f5 0%,#7d96ff 100%) !important;
    box-shadow: 0 8px 28px rgba(79,110,247,0.58), inset 0 1px 0 rgba(255,255,255,0.18) !important;
    transform: translateY(-2px) scale(1.015) !important;
    border-color: rgba(125,150,255,0.65) !important;
}
.stButton > button[kind="primary"]:active {
    transform: translateY(0) scale(0.985) !important;
    box-shadow: 0 2px 8px var(--accent-glow) !important;
}

/* ── Ghost / secondary buttons ── */
.stButton > button[kind="secondary"],
.stButton > button:not([kind="primary"]) {
    background: rgba(255,255,255,0.032) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--r-sm) !important;
    color: var(--text-2) !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    transition: var(--t) !important;
}
.stButton > button[kind="secondary"]:hover,
.stButton > button:not([kind="primary"]):hover {
    background: rgba(79,110,247,0.09) !important;
    border-color: rgba(79,110,247,0.38) !important;
    color: var(--text-1) !important;
    transform: translateY(-1px) !important;
}

/* ── Metric cards (shadcn Card) ── */
[data-testid="stMetric"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--r-md) !important;
    padding: 16px 18px !important;
    box-shadow: var(--shadow) !important;
    transition: var(--t) !important;
}
[data-testid="stMetric"]:hover {
    background: var(--bg-hover) !important;
    border-color: rgba(120,150,255,0.22) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 20px rgba(0,0,0,.5) !important;
}
[data-testid="stMetricLabel"] {
    color: var(--text-3) !important;
    font-size: 10px !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 1.1px !important;
}
[data-testid="stMetricValue"] {
    color: var(--text-1) !important;
    font-size: 24px !important;
    font-weight: 800 !important;
    letter-spacing: -0.5px !important;
}

/* ── Status widget ── */
[data-testid="stStatusWidget"] {
    background: rgba(7,9,26,0.92) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--r-md) !important;
    box-shadow: var(--shadow) !important;
}

/* ── Alert ── */
[data-testid="stAlert"] {
    border-radius: var(--r-md) !important;
    border: 1px solid rgba(79,110,247,0.18) !important;
    background: rgba(79,110,247,0.05) !important;
    box-shadow: var(--shadow) !important;
}

/* ── Expander ── */
[data-testid="stExpander"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--r-md) !important;
    box-shadow: var(--shadow) !important;
    transition: var(--t) !important;
}
[data-testid="stExpander"]:hover { border-color: rgba(120,150,255,0.2) !important; }
details summary { color: var(--text-2) !important; font-weight: 500 !important; }

/* ── Divider ── */
hr { border-color: var(--border) !important; margin: 14px 0 !important; }

/* ── Code ── */
code {
    background: rgba(79,110,247,0.11) !important;
    color: #93c5fd !important;
    border: 1px solid rgba(79,110,247,0.2) !important;
    border-radius: 5px !important;
    padding: 1px 6px !important;
    font-size: 12px !important;
    font-family: 'JetBrains Mono','Fira Code',monospace !important;
}

/* ── Skeleton shimmer (tech_stack: loading states) ── */
@keyframes shimmer {
    0%   { background-position: -700px 0; }
    100% { background-position:  700px 0; }
}
.skeleton {
    background: linear-gradient(90deg,
        rgba(255,255,255,0.03) 25%,
        rgba(255,255,255,0.07) 50%,
        rgba(255,255,255,0.03) 75%) !important;
    background-size: 700px 100% !important;
    animation: shimmer 1.6s ease-in-out infinite !important;
    border-radius: var(--r-sm) !important;
}

/* ── Card entrance (Framer Motion fadeSlideUp equivalent) ── */
@keyframes fadeUp {
    from { opacity:0; transform:translateY(16px); }
    to   { opacity:1; transform:translateY(0); }
}
.animate-in           { animation: fadeUp 0.38s var(--ease) forwards; }
.animate-in-d1        { animation: fadeUp 0.38s 0.07s var(--ease) both; }
.animate-in-d2        { animation: fadeUp 0.38s 0.14s var(--ease) both; }
.animate-in-d3        { animation: fadeUp 0.38s 0.21s var(--ease) both; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(79,110,247,0.18); border-radius: 10px; }
::-webkit-scrollbar-thumb:hover { background: rgba(79,110,247,0.4); }

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden !important; }
.stDeployButton { display: none !important; }
</style>
""", unsafe_allow_html=True)

# ── API keys: loaded from .env only (no UI exposure) ─────────────────────────
_DEMO_MODE = not bool(os.getenv("GROQ_API_KEY"))

with st.sidebar:
    # ── Wordmark ──────────────────────────────────────────────────────────────
    st.markdown("""
    <div style="padding:20px 4px 16px;border-bottom:1px solid rgba(120,150,255,0.07);margin-bottom:16px;">
      <div style="display:flex;align-items:center;gap:10px;">
        <div style="width:36px;height:36px;border-radius:10px;
                    background:linear-gradient(135deg,#3d5ce8,#7b5cf6);
                    display:flex;align-items:center;justify-content:center;
                    font-size:19px;box-shadow:0 4px 14px rgba(79,110,247,0.4);">✈️</div>
        <div>
          <div style="font-size:15px;font-weight:700;color:#eef2ff;letter-spacing:-0.3px;">Travel Planner AI</div>
          <div style="font-size:10px;color:#3d4d70;letter-spacing:1.2px;margin-top:1px;">MULTI-AGENT SYSTEM</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Agent pipeline ────────────────────────────────────────────────────────
    st.markdown(
        '<div style="font-size:10px;font-weight:600;color:#3d4d70;'
        'letter-spacing:1.5px;margin-bottom:10px;padding:0 2px;">AGENT PIPELINE</div>',
        unsafe_allow_html=True,
    )
    AGENTS = [
        ("Preference Extractor", True,  "Parses your natural language"),
        ("Weather Agent",        True,  "Open-Meteo · keyless"),
        ("Attractions & POI",    False, "OpenTripMap · Phase 2"),
        ("Itinerary Builder",    False, "Day-by-day planner"),
        ("Budget & Transport",   False, "Running total tracker"),
        ("Contingency Planner",  False, "Rainy-day alternatives"),
        ("Export Suite",         False, "MD · HTML · ICS · JSON"),
    ]
    for label, done, hint in AGENTS:
        if done:
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:10px;padding:8px 10px;'
                f'border-radius:8px;margin-bottom:3px;background:rgba(52,211,153,0.055);'
                f'border:1px solid rgba(52,211,153,0.11);">'
                f'<div style="width:6px;height:6px;border-radius:50%;background:#34d399;'
                f'box-shadow:0 0 8px rgba(52,211,153,0.55);flex-shrink:0;"></div>'
                f'<div><div style="font-size:12px;font-weight:500;color:#a7d9c4;">{label}</div>'
                f'<div style="font-size:10px;color:#2d5540;margin-top:1px;">{hint}</div></div></div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:10px;padding:8px 10px;'
                f'border-radius:8px;margin-bottom:3px;background:rgba(255,255,255,0.015);'
                f'border:1px solid rgba(120,150,255,0.06);">'
                f'<div style="width:6px;height:6px;border-radius:50%;background:#1a2438;flex-shrink:0;'
                f'border:1px solid #2a3855;"></div>'
                f'<div><div style="font-size:12px;font-weight:500;color:#3a4a65;">{label}</div>'
                f'<div style="font-size:10px;color:#242f48;margin-top:1px;">{hint}</div></div></div>',
                unsafe_allow_html=True,
            )

    # ── Progress bar ──────────────────────────────────────────────────────────
    done_count = sum(1 for _, d, _ in AGENTS if d)
    pct = int(done_count / len(AGENTS) * 100)
    st.markdown(
        f'<div style="margin-top:16px;">'
        f'<div style="font-size:10px;color:#3d4d70;letter-spacing:1px;margin-bottom:6px;">'
        f'PROGRESS · {done_count}/{len(AGENTS)} ACTIVE</div>'
        f'<div style="background:rgba(255,255,255,0.04);border-radius:20px;height:4px;overflow:hidden;">'
        f'<div style="width:{pct}%;height:100%;border-radius:20px;'
        f'background:linear-gradient(90deg,#34d399,#4f6ef7);'
        f'box-shadow:0 0 8px rgba(52,211,153,0.35);"></div></div></div>',
        unsafe_allow_html=True,
    )

    # ── Footer ────────────────────────────────────────────────────────────────
    st.markdown(
        '<div style="margin-top:28px;padding-top:12px;'
        'border-top:1px solid rgba(120,150,255,0.06);">'
        '<div style="font-size:10px;color:#1e2a40;text-align:center;letter-spacing:.5px;">'
        'Built with IBM Bob · Free APIs only</div></div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Mock helpers
# ─────────────────────────────────────────────────────────────────────────────

def _mock_preferences(raw: str) -> TravelPreferences:
    return TravelPreferences(
        destination="Kyoto", start_date=date(2024, 4, 10), end_date=date(2024, 4, 14),
        duration_days=5, budget_amount=1800, budget_currency="USD",
        budget_style="mid_range",  # type: ignore[arg-type]
        group_type=GroupType.COUPLE, group_size=2, pace=Pace.RELAXED,
        interests=["temples", "food", "gardens"],
        accessibility_needs=["no heavy walking"],
        must_do=["Fushimi Inari", "Arashiyama bamboo grove"],
        clarification_needed=False, missing_fields=[], raw_input=raw,
    )

def _mock_forecast() -> WeatherForecast:
    base = date(2024, 4, 10)
    return WeatherForecast(
        destination="Kyoto", latitude=35.0116, longitude=135.7681,
        timezone="Asia/Tokyo", fetched_at="2024-04-01T09:00:00+00:00",
        days=[
            DailyWeather(date=base,              temperature_max_c=19, temperature_min_c=11, precipitation_probability_max=10, weather_code=1,  weather_summary="Mainly clear",   outdoor_suitability_score=9,  wind_speed_max_kmh=8,  uv_index_max=5),
            DailyWeather(date=base+timedelta(1), temperature_max_c=21, temperature_min_c=13, precipitation_probability_max=15, weather_code=0,  weather_summary="Clear sky",      outdoor_suitability_score=10, wind_speed_max_kmh=5,  uv_index_max=6),
            DailyWeather(date=base+timedelta(2), temperature_max_c=16, temperature_min_c=10, precipitation_probability_max=70, weather_code=63, weather_summary="Moderate rain",  outdoor_suitability_score=3,  wind_speed_max_kmh=18, uv_index_max=2),
            DailyWeather(date=base+timedelta(3), temperature_max_c=14, temperature_min_c=9,  precipitation_probability_max=85, weather_code=65, weather_summary="Heavy rain",     outdoor_suitability_score=1,  wind_speed_max_kmh=22, uv_index_max=1),
            DailyWeather(date=base+timedelta(4), temperature_max_c=22, temperature_min_c=13, precipitation_probability_max=5,  weather_code=0,  weather_summary="Clear sky",      outdoor_suitability_score=10, wind_speed_max_kmh=4,  uv_index_max=7),
        ],
    )

# ─────────────────────────────────────────────────────────────────────────────
# Async bridge
# ─────────────────────────────────────────────────────────────────────────────

def _run(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(asyncio.run, coro).result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)

# ─────────────────────────────────────────────────────────────────────────────
# UI helpers
# ─────────────────────────────────────────────────────────────────────────────

def _score_emoji(s: int) -> str:
    if s <= 2: return "⛈️"
    if s <= 4: return "🌧️"
    if s <= 6: return "🌥️"
    if s <= 8: return "⛅"
    return "☀️"

def _score_color(s: int) -> str:
    if s <= 2: return "#f87171"
    if s <= 5: return "#fb923c"
    if s <= 7: return "#facc15"
    return "#4ade80"

def _chip(label: str, color: str = "#3b5bdb") -> str:
    bg = color + "22"
    return (
        f'<span style="display:inline-block;background:{bg};color:{color};'
        f'border:1px solid {color}44;border-radius:20px;'
        f'padding:3px 12px;font-size:12px;font-weight:500;margin:2px 2px 2px 0;">'
        f'{label}</span>'
    )

def _row(icon: str, label: str, value: str) -> None:
    st.markdown(
        f'<div style="display:flex;align-items:baseline;gap:10px;padding:7px 0;'
        f'border-bottom:1px solid rgba(99,145,255,0.07);">'
        f'<span style="font-size:16px;min-width:22px;">{icon}</span>'
        f'<span style="color:#4a5a8a;font-size:12px;min-width:90px;text-transform:uppercase;letter-spacing:.5px;">{label}</span>'
        f'<span style="color:#c9d4f0;font-weight:500;font-size:14px;">{value}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

def _weather_card(day: DailyWeather) -> None:
    color  = _score_color(day.outdoor_suitability_score)
    emoji  = _score_emoji(day.outdoor_suitability_score)
    score  = day.outdoor_suitability_score
    filled = int(score)
    bar    = "".join(
        f'<div style="flex:1;height:4px;border-radius:2px;background:{color if i < filled else "rgba(255,255,255,0.07)"};margin:0 1px;"></div>'
        for i in range(10)
    )
    rain_badge = (
        f'<span style="background:rgba(99,145,255,0.12);color:#93c5fd;border-radius:20px;'
        f'padding:2px 8px;font-size:11px;margin-left:8px;">🌧 {day.precipitation_probability_max}%</span>'
        if day.precipitation_probability_max >= 40 else ""
    )
    st.markdown(
        f"""<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(99,145,255,0.12);
                        border-radius:12px;padding:14px 16px;margin-bottom:8px;
                        transition:border-color .2s;"
             onmouseover="this.style.borderColor='rgba(99,145,255,0.3)'"
             onmouseout="this.style.borderColor='rgba(99,145,255,0.12)'">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
            <span style="font-weight:600;font-size:14px;color:#e8eeff;">{emoji} {day.date.strftime('%A, %b %d')}</span>
            <span style="color:{color};font-weight:700;font-size:13px;">{score}/10</span>
          </div>
          <div style="display:flex;margin-bottom:8px;">{bar}</div>
          <div style="color:#8a9ac0;font-size:13px;">
            {day.weather_summary}
            &nbsp;·&nbsp; <span style="color:#c9d4f0;font-weight:600;">↑{day.temperature_max_c:.0f}°</span>
            / <span style="color:#8a9ac0;">↓{day.temperature_min_c:.0f}°C</span>
            {rain_badge}
          </div>
        </div>""",
        unsafe_allow_html=True,
    )

def _section_header(title: str) -> None:
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:10px;margin:24px 0 16px;">'
        f'<div style="height:1px;flex:1;background:rgba(99,145,255,0.15);"></div>'
        f'<span style="font-size:11px;font-weight:600;color:#4a5a8a;letter-spacing:2px;text-transform:uppercase;">{title}</span>'
        f'<div style="height:1px;flex:1;background:rgba(99,145,255,0.15);"></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

# ─────────────────────────────────────────────────────────────────────────────
# Page header
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<div style="padding:8px 0 24px;">
  <div style="font-size:12px;color:#3b5bdb;font-weight:600;letter-spacing:2px;margin-bottom:6px;">AI-POWERED TRAVEL PLANNING</div>
  <h1 style="margin:0;font-size:2.4rem;font-weight:800;color:#e8eeff;line-height:1.1;">
    Plan your perfect trip,<br>
    <span style="background:linear-gradient(90deg,#5c7cfa,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">in seconds.</span>
  </h1>
  <p style="margin:12px 0 0;color:#5a6a9a;font-size:15px;max-width:560px;">
    Describe your trip in plain English. Our AI agents handle weather, preferences,
    activities, budget, and contingency planning — all free, no subscriptions.
  </p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Example prompts
# ─────────────────────────────────────────────────────────────────────────────

EXAMPLES = [
    ("🏯", "Kyoto Couple",   "5-day romantic trip to Kyoto under $1800 in mid-April, no heavy walking, love food & temples"),
    ("🌮", "Bangkok Solo",   "Solo adventure in Bangkok for 7 days, $1200 budget, street food addict, fast pace"),
    ("🏛️", "Rome Family",   "Family trip to Rome, 4 days, 2 adults 2 kids, €2000, must see Colosseum"),
    ("🚲", "Amsterdam Crew", "Friends weekend in Amsterdam, 3 days, mid-range budget, love cycling & museums"),
]

_section_header("Quick Start")
ex_cols = st.columns(4)
for col, (icon, label, prompt) in zip(ex_cols, EXAMPLES):
    with col:
        if st.button(f"{icon}  {label}", key=f"ex_{label}", use_container_width=True):
            st.session_state["user_input"] = prompt
            st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# Input area
# ─────────────────────────────────────────────────────────────────────────────

_section_header("Describe Your Trip")

user_input: str = st.text_area(
    "trip_input",
    value=st.session_state.get("user_input", ""),
    height=110,
    placeholder="e.g.  5-day romantic trip to Kyoto under $1800 in mid-April, no heavy walking, love food & temples…",
    label_visibility="collapsed",
)

btn_col, clear_col, spacer = st.columns([2, 1, 7])
with btn_col:
    plan_clicked = st.button("✈️  Plan my trip", type="primary", use_container_width=True)
with clear_col:
    if st.button("✕  Clear", use_container_width=True):
        for k in ("user_input", "prefs", "forecast"):
            st.session_state.pop(k, None)
        st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# Processing pipeline
# ─────────────────────────────────────────────────────────────────────────────

_DEMO_MODE = not bool(os.getenv("GROQ_API_KEY"))

if plan_clicked and user_input.strip():
    st.session_state["user_input"] = user_input

    # Step 1 – Preferences
    with st.status("🧠  Extracting travel preferences…", expanded=True) as st_status:
        try:
            if _DEMO_MODE:
                st.write("Demo mode — using illustrative preferences for Kyoto.")
                prefs: TravelPreferences = _mock_preferences(user_input)
            else:
                prefs = _run(PreferenceExtractorAgent().extract(user_input))
            st.session_state["prefs"] = prefs
            st_status.update(label="✅  Preferences extracted", state="complete")
        except Exception as exc:
            st_status.update(label=f"❌  Failed: {exc}", state="error")
            st.stop()

    # Step 2 – Clarification gate
    prefs = st.session_state.get("prefs")
    if prefs and prefs.clarification_needed:
        st.markdown("""
        <div style="background:rgba(250,204,21,0.07);border:1px solid rgba(250,204,21,0.25);
                    border-radius:12px;padding:16px 20px;margin:12px 0;">
          <div style="font-weight:600;color:#fbbf24;margin-bottom:8px;">❓ A few things are missing…</div>
        """, unsafe_allow_html=True)
        aq = PreferenceExtractorAgent.__new__(PreferenceExtractorAgent)
        for q in aq.build_clarification_questions(prefs):
            st.markdown(f'<div style="color:#c9d4f0;padding:4px 0;">• {q}</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        st.stop()

    # Step 3 – Weather
    if prefs and prefs.destination and prefs.start_date and prefs.end_date:
        with st.status(f"🌤️  Fetching weather for {prefs.destination}…", expanded=True) as w_status:
            try:
                if _DEMO_MODE and prefs.destination.lower() == "kyoto":
                    st.write("Demo mode — returning mock Kyoto forecast.")
                    forecast = _mock_forecast()
                else:
                    st.write("Calling Open-Meteo (keyless) + Nominatim geocoding…")
                    forecast = _run(WeatherAgent().get_forecast(prefs.destination, prefs.start_date, prefs.end_date))
                st.session_state["forecast"] = forecast
                w_status.update(label="✅  Weather loaded", state="complete")
            except WeatherAgentError as exc:
                w_status.update(label=f"⚠️  Weather unavailable: {exc}", state="error")
                st.session_state["forecast"] = None
            except Exception as exc:
                w_status.update(label=f"⚠️  Error: {exc}", state="error")
                st.session_state["forecast"] = None

# ─────────────────────────────────────────────────────────────────────────────
# Results
# ─────────────────────────────────────────────────────────────────────────────

prefs: TravelPreferences | None    = st.session_state.get("prefs")
forecast: WeatherForecast | None   = st.session_state.get("forecast")

if prefs:
    # ── Destination hero card ─────────────────────────────────────────────────
    _section_header("Your Journey")

    dest_icon = (
        "🗾" if any(x in (prefs.destination or "").lower() for x in ["kyoto","tokyo","osaka","japan"])
        else "🗼" if "paris" in (prefs.destination or "").lower()
        else "🏛️" if "rome"  in (prefs.destination or "").lower()
        else "🌃" if any(x in (prefs.destination or "").lower() for x in ["bangkok","singapore"])
        else "🌍"
    )
    budget_sym = "$" if prefs.budget_currency == "USD" else ("€" if prefs.budget_currency == "EUR" else prefs.budget_currency + " ")
    budget_str = f"{budget_sym}{int(prefs.budget_amount):,}" if prefs.budget_amount else "—"

    st.markdown(
        f"""<div style="
              background:linear-gradient(135deg,rgba(59,91,219,0.25) 0%,rgba(92,124,250,0.1) 100%);
              border:1px solid rgba(99,145,255,0.25);border-radius:18px;
              padding:28px 32px;margin-bottom:24px;position:relative;overflow:hidden;">
          <div style="position:absolute;top:-30px;right:-30px;font-size:120px;opacity:0.06;line-height:1;">{dest_icon}</div>
          <div style="font-size:13px;color:#5c7cfa;font-weight:600;letter-spacing:1.5px;margin-bottom:6px;">DESTINATION</div>
          <div style="font-size:32px;font-weight:800;color:#e8eeff;margin-bottom:10px;">{dest_icon} {prefs.destination or "Your Trip"}</div>
          <div style="display:flex;flex-wrap:wrap;gap:12px;">
            <span style="background:rgba(255,255,255,0.06);border-radius:8px;padding:6px 14px;font-size:13px;color:#c9d4f0;">📅 {prefs.start_date} → {prefs.end_date}</span>
            <span style="background:rgba(255,255,255,0.06);border-radius:8px;padding:6px 14px;font-size:13px;color:#c9d4f0;">⏱ {prefs.duration_days or "?"} days</span>
            <span style="background:rgba(255,255,255,0.06);border-radius:8px;padding:6px 14px;font-size:13px;color:#c9d4f0;">👥 {(prefs.group_type.value if prefs.group_type else "Travellers").title()}{f", {prefs.group_size}" if prefs.group_size else ""}</span>
            <span style="background:rgba(255,255,255,0.06);border-radius:8px;padding:6px 14px;font-size:13px;color:#c9d4f0;">💰 {budget_str}</span>
            {f'<span style="background:rgba(255,255,255,0.06);border-radius:8px;padding:6px 14px;font-size:13px;color:#c9d4f0;">🏃 {prefs.pace.value.title()}</span>' if prefs.pace else ""}
          </div>
        </div>""",
        unsafe_allow_html=True,
    )

    # ── Two-column: Preferences | Weather ────────────────────────────────────
    left, right = st.columns([1, 1], gap="large")

    # ── LEFT: preferences ─────────────────────────────────────────────────────
    with left:
        st.markdown(
            '<div style="background:rgba(255,255,255,0.02);border:1px solid rgba(99,145,255,0.12);'
            'border-radius:16px;padding:24px;">',
            unsafe_allow_html=True,
        )
        st.markdown('<div style="font-size:11px;font-weight:600;color:#4a5a8a;letter-spacing:2px;margin-bottom:14px;">PREFERENCES</div>', unsafe_allow_html=True)

        _row("📅", "Dates",    f"{prefs.start_date} → {prefs.end_date}" if prefs.has_dates else "Not set")
        _row("⏱️", "Duration", f"{prefs.duration_days} days" if prefs.duration_days else "—")
        _row("👥", "Group",    f"{prefs.group_type.value.title() if prefs.group_type else '—'}, {prefs.group_size or '?'} pax")
        _row("💰", "Budget",   f"{prefs.budget_currency} {int(prefs.budget_amount):,}" if prefs.budget_amount else "—")
        _row("🏃", "Pace",     prefs.pace.value.title() if prefs.pace else "—")

        if prefs.interests:
            st.markdown('<div style="margin-top:14px;margin-bottom:6px;font-size:11px;color:#4a5a8a;letter-spacing:1px;">INTERESTS</div>', unsafe_allow_html=True)
            st.markdown(" ".join(_chip(i, "#5c7cfa") for i in prefs.interests), unsafe_allow_html=True)

        if prefs.accessibility_needs:
            st.markdown('<div style="margin-top:12px;margin-bottom:6px;font-size:11px;color:#4a5a8a;letter-spacing:1px;">ACCESSIBILITY</div>', unsafe_allow_html=True)
            st.markdown(" ".join(_chip(a, "#a78bfa") for a in prefs.accessibility_needs), unsafe_allow_html=True)

        if prefs.must_do:
            st.markdown('<div style="margin-top:12px;margin-bottom:6px;font-size:11px;color:#4a5a8a;letter-spacing:1px;">MUST-DO</div>', unsafe_allow_html=True)
            for item in prefs.must_do:
                st.markdown(f'<div style="color:#c9d4f0;padding:3px 0;font-size:13px;">✦ {item}</div>', unsafe_allow_html=True)

        if prefs.dietary:
            st.markdown('<div style="margin-top:12px;margin-bottom:6px;font-size:11px;color:#4a5a8a;letter-spacing:1px;">DIETARY</div>', unsafe_allow_html=True)
            st.markdown(" ".join(_chip(d, "#34d399") for d in prefs.dietary), unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    # ── RIGHT: weather ────────────────────────────────────────────────────────
    with right:
        st.markdown(
            '<div style="background:rgba(255,255,255,0.02);border:1px solid rgba(99,145,255,0.12);'
            'border-radius:16px;padding:24px;">',
            unsafe_allow_html=True,
        )
        st.markdown('<div style="font-size:11px;font-weight:600;color:#4a5a8a;letter-spacing:2px;margin-bottom:14px;">WEATHER FORECAST</div>', unsafe_allow_html=True)

        if forecast:
            avg  = sum(d.outdoor_suitability_score for d in forecast.days) / len(forecast.days)
            best = forecast.best_day
            rain = len(forecast.rainy_days)

            m1, m2, m3 = st.columns(3)
            m1.metric("Avg Score",   f"{avg:.1f}/10")
            m2.metric("Rainy Days",  f"{rain}/{len(forecast.days)}")
            m3.metric("Best Day",    best.date.strftime("%a %d") if best else "—")

            st.markdown("<div style='margin:16px 0 10px;'></div>", unsafe_allow_html=True)
            for day in forecast.days:
                _weather_card(day)

            # Indoor alternatives
            wa = WeatherAgent()
            indoors = wa.suggest_indoor_alternatives(forecast)
            if indoors:
                with st.expander(f"🌧️  Indoor alternatives — {len(indoors)} rainy day(s)"):
                    for ds, suggestions in indoors.items():
                        st.markdown(f'<div style="color:#5c7cfa;font-weight:600;font-size:13px;margin:8px 0 4px;">{ds}</div>', unsafe_allow_html=True)
                        for s in suggestions:
                            st.markdown(f'<div style="color:#8a9ac0;font-size:13px;padding:2px 0;">· {s}</div>', unsafe_allow_html=True)

            st.markdown(f'<div style="font-size:11px;color:#2a3a5a;margin-top:10px;">Source: {forecast.source}</div>', unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="text-align:center;padding:40px 20px;color:#3a4a6a;">
              <div style="font-size:40px;margin-bottom:12px;">🌤️</div>
              <div style="font-size:14px;">Weather data unavailable.<br>Itinerary will use seasonal averages.</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    # ── Phase 2 preview strip ─────────────────────────────────────────────────
    _section_header("Coming in Phase 2")
    p2 = st.columns(4)
    for col, (icon, title, desc) in zip(p2, [
        ("🗺️", "Attractions & POI",    "Curated places matched to your interests"),
        ("📅", "Day-by-Day Itinerary", "Optimised schedule with travel time buffers"),
        ("💸", "Budget Breakdown",     "Running total + what-if recalculator"),
        ("⚡", "Quick Re-plan",        '"Cheaper / Less walking / More food" shortcuts'),
    ]):
        col.markdown(
            f"""<div style="background:rgba(255,255,255,0.02);border:1px solid rgba(99,145,255,0.1);
                            border-radius:14px;padding:18px;min-height:110px;">
                  <div style="font-size:22px;margin-bottom:8px;">{icon}</div>
                  <div style="font-weight:600;font-size:13px;color:#c9d4f0;margin-bottom:6px;">{title}</div>
                  <div style="color:#3a4a6a;font-size:12px;">{desc}</div>
                </div>""",
            unsafe_allow_html=True,
        )

elif not plan_clicked:
    # ── Landing hero ──────────────────────────────────────────────────────────
    _section_header("How it works")
    lc = st.columns(3)
    for col, icon, title, body in [
        (lc[0], "🧠", "Smart Preference Extraction",
         "Understands destination, dates, budget, pace, dietary needs and accessibility from plain English."),
        (lc[1], "🌤️", "Live Weather Intelligence",
         "Scores each day for outdoor suitability. Suggests indoor alternatives on rainy days automatically."),
        (lc[2], "🗺️", "Full Itinerary Engine",
         "Day-by-day optimised plan with activities, travel buffers, and budget tracking. *(Phase 2)*"),
    ]:
        col.markdown(
            f"""<div style="background:rgba(255,255,255,0.02);border:1px solid rgba(99,145,255,0.1);
                            border-radius:16px;padding:24px;min-height:150px;">
                  <div style="font-size:32px;margin-bottom:12px;">{icon}</div>
                  <div style="font-weight:600;color:#c9d4f0;font-size:14px;margin-bottom:8px;">{title}</div>
                  <div style="color:#3a4a6a;font-size:13px;line-height:1.6;">{body}</div>
                </div>""",
            unsafe_allow_html=True,
        )
    st.markdown("""
    <div style="text-align:center;margin-top:28px;padding:16px;
                background:rgba(59,91,219,0.06);border:1px solid rgba(59,91,219,0.2);
                border-radius:12px;color:#5a6a9a;font-size:14px;">
      💡 Pick a quick-start example above or type your own trip request, then click <strong style="color:#5c7cfa;">✈️ Plan my trip</strong>
    </div>""", unsafe_allow_html=True)
