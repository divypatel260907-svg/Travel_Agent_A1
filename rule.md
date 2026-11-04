# Rules for Travel Planner Agent (IBM Bob)

## General Rules
1. Always prefer free / free-tier services. Never introduce paid APIs without explicit user approval.
2. All LLM calls must route through either **Google Gemini** or **Groq**. Prefer Groq for speed-critical agents and Gemini for complex reasoning / multimodal if needed.
3. Never hard-code API keys. Always use environment variables (`.env`).
4. Every external API call must have timeout, retry (max 2), and graceful fallback.
5. Keep responses structured (JSON or Pydantic models) between agents.
6. User-facing language must be friendly, concise, and actionable.
7. Respect rate limits. Cache results aggressively for the same destination + dates.
8. When data is missing or uncertain, clearly say so and offer alternatives.
9. Privacy: Do not store personal data beyond the current session unless the user explicitly opts into preference memory (local only).
10. Accessibility: Generated plans must consider mobility constraints if provided.

## Agent-Specific Rules
- Preference Extractor: Extract only what is explicitly or strongly implied. Ask clarifying questions when critical info is missing (budget, dates, group type).
- Weather Agent: Always fetch forecast for the exact travel dates. Suggest indoor alternatives on high-rain probability days.
- Budget Agent: Always show running total + remaining budget. Flag when an item would exceed the hard limit.
- Itinerary Builder: Never schedule more than 3 major activities per day unless user requests high-pace. Include travel time and rest buffers.
- Contingency Agent: Every plan must have at least one “Plan B” (rain / low energy / transport disruption).
- Export Agent: Always generate a clean Markdown version + a self-contained HTML version.

## Coding Rules
- Use type hints and Pydantic models everywhere possible.
- Prefer async for API calls.
- Write unit tests for pure logic (budget calculation, day splitting, packing list rules).
- Document every tool with clear description so Bob can discover and reuse it.
- Keep files modular: one agent or tool per file when reasonable.

## Safety & Compliance
- Do not provide medical, legal, or visa advice beyond publicly available free data.
- Include a short disclaimer on every plan: “This is an AI-generated suggestion. Always verify bookings, opening hours, and travel requirements independently.”