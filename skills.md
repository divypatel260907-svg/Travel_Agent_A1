# Skills for Travel Planner Agent (IBM Bob)

## Skill: preference_extraction
Extract structured travel preferences from natural language.  
Output a Pydantic model containing: destination(s), dates or duration, budget (amount + currency), group_type, pace, interests, dietary, accessibility, must_do, must_avoid, language.

## Skill: weather_tool
Fetch daily weather forecast for a city and date range using Open-Meteo (no key).  
Return temperature high/low, precipitation probability, weather code, and a short human summary.  
Also return a “suitability score” for outdoor activities.

## Skill: poi_search
Search points of interest near a location using OpenTripMap or Overpass/Nominatim.  
Filter by categories (culture, food, nature, photo, family, accessible).  
Return name, short description, coordinates, estimated visit duration, and popularity signal if available.

## Skill: itinerary_builder
Given preferences + weather + POIs + budget, produce a day-by-day itinerary.  
Rules: respect energy level, include travel time buffers, balance indoor/outdoor, never over-schedule.  
Output structured days with morning / afternoon / evening blocks + estimated cost per block.

## Skill: budget_calculator
Maintain a running budget. Accept list of items with estimated costs.  
Return total, remaining, percentage used, and suggestions to stay under budget.  
Support “what-if” recalculation when an item is removed or replaced.

## Skill: contingency_generator
Given a base itinerary and weather, generate:
1. Rainy-day version
2. Low-energy / relaxed version
3. Transport-disruption version  
Keep the same hotels and major must-do items when possible.

## Skill: packing_list
Generate a practical packing list based on destination climate, activities, duration, and group type.  
Categorize (clothes, documents, electronics, health, miscellaneous) and estimate total weight.

## Skill: cultural_tips
Produce 5–8 short, practical cultural & etiquette tips for the destination, tailored to the user’s likely origin if known.

## Skill: export_formatter
Convert the final plan into:
- Clean Markdown
- Self-contained HTML (with simple CSS, printable)
- .ics calendar events for major activities
- JSON for further processing

## Skill: replan_shortcut
Accept a high-level instruction (“make it cheaper”, “more food”, “less walking”) and only re-run the necessary agents while preserving the rest of the plan.

## Skill: safety_visa_check
Using REST Countries + free knowledge, surface basic visa notes, emergency numbers, and high-level safety considerations. Always add a disclaimer.