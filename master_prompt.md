# Master Prompt – Travel Planner Agent (IBM Bob Project)

## Project Overview
Build a production-ready, multi-agent **Travel Planner Agent** that turns a user’s natural-language request into a complete, personalized, real-time travel plan in under 60 seconds.  
The agent must understand preferences, budget, constraints, group type, and travel style, then orchestrate specialized sub-agents to produce an actionable itinerary with weather, maps, attractions, transport suggestions, budget breakdown, packing list, and contingency plans.

This project is designed to be built and iterated with **IBM Bob** using Agent mode, sub-agents, skills, and rules.

## Expanded Problem Statement
Traditional travel planning is fragmented, time-consuming, and error-prone. Users jump between 8–12 tabs (Google Flights, Booking, TripAdvisor, weather apps, maps, currency converters, visa checkers, packing lists). Plans break when weather changes, attractions close, or budgets overrun.

**Travel Planner Agent** solves this by acting as an intelligent, always-on co-pilot that:

- Accepts free-form natural language (“I want a 5-day romantic trip to Kyoto under $1800 in mid-April, no heavy walking, love food & temples”)
- Extracts structured constraints (dates, budget, group size, mobility, interests, must-avoid)
- Calls real-time free data sources
- Generates a day-by-day itinerary optimized for time, cost, energy, and weather
- Continuously adapts the plan when conditions change
- Exports shareable, printable, offline-ready plans

### High-Impact Small & Medium Features (must implement)
These features are deliberately small/medium in implementation effort but deliver outsized user value:

1. **Smart Preference Memory** – Persist user preferences across sessions (dietary, pace, budget style, accessibility).
2. **Weather-Aware Rescheduling** – Automatically move outdoor activities to better days and suggest indoor alternatives.
3. **Budget Guardrails with Live Alerts** – Running total + soft/hard limits + “what if I drop this activity?” impact.
4. **One-Click Contingency Plans** – Rainy-day version, low-energy version, and “local transport strike” version of the same itinerary.
5. **Local Time & Jet-Lag Optimizer** – Suggest activity intensity based on arrival time and time-zone difference.
6. **Packing List Generator** – Climate + activity + duration aware packing list with weight estimates.
7. **Cultural & Etiquette Mini-Guide** – 5–7 bullet points tailored to the destination + user nationality.
8. **Photo Spot & Sunrise/Sunset Optimizer** – Recommend best photo times and locations.
9. **Group Mode** – Support couples, families, solo, friends with different energy levels.
10. **Export Suite** – Markdown, PDF-ready HTML, calendar (.ics), and shareable link (local or simple static).
11. **Offline Mode Snapshot** – Download the full plan as a self-contained HTML file.
12. **Quick Re-plan** – “Make it 20% cheaper”, “More food experiences”, “Less walking” buttons that re-run only the affected agents.
13. **Safety & Visa Quick Check** – Flag visa requirements, emergency numbers, and basic safety notes using free country data.
14. **Carbon Footprint Estimate** – Simple estimate + greener alternatives (optional but high perceived value).
15. **Multi-language Output** – Generate the plan in the user’s preferred language (powered by Gemini/Groq).

## What the Project Must Consist Of

### Core Architecture
- Multi-agent system (LangGraph or similar lightweight orchestration)
- Supervisor / Orchestrator agent
- Specialized agents:
  - Preference Extractor
  - Destination & Research Agent
  - Weather Agent
  - Attractions & POI Agent
  - Itinerary Builder Agent
  - Budget & Transport Agent
  - Contingency & Optimizer Agent
  - Export & Formatting Agent

### User Experience
- Clean chat + form hybrid UI (Streamlit or Gradio for speed, or simple Next.js if time allows)
- Progressive disclosure of the plan (day cards, map, budget pie, weather strip)
- Side-by-side comparison of original vs optimized plans
- Real-time streaming of agent thoughts (optional but impressive)

### Data & Tools
- Free real-time sources only (see Technology Stack)
- Caching layer for repeated queries
- Graceful degradation when an API is rate-limited

### Deliverables Expected
1. Working web application
2. Clear README with setup (API keys for Gemini + Groq only)
3. Architecture diagram
4. Example conversations / demo scripts
5. Tests for core agents
6. Rules & Skills files for IBM Bob so future improvements are easy

## Success Criteria
- End-to-end plan generation < 45–60 seconds on free tiers
- High personalization score (preferences reflected in >80% of suggestions)
- Zero paid APIs required for core functionality
- Fully usable offline once the plan is generated
- Easy for IBM Bob to extend (clear skills + rules)

## Development Philosophy for IBM Bob
- Explore → Plan → Implement → Verify cycle
- Keep context lean
- Use skills for repeated patterns (itinerary formatting, weather tool, budget calculation)
- Prefer free, key-light or keyless services
- Write defensive code around rate limits and missing data