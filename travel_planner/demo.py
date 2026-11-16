"""
VOYA Travel Planner — Demo Script
Run this to see example inputs and expected outputs.

Usage:
    cd travel_planner
    python demo.py

Note: Requires the Flask server running on http://127.0.0.1:5000
      and a valid GROQ_API_KEY in .env
"""

import requests
import json
import sys

BASE_URL = "http://127.0.0.1:5000"

# ── Example Queries ──────────────────────────────────────────────────────────

DEMO_QUERIES = [
    {
        "name": "🏯 Kyoto Romantic Getaway",
        "query": (
            "Plan a 5-day romantic trip to Kyoto, Japan for a couple. "
            "Budget: $1800. Interests: temples, tea ceremonies, cherry blossoms, "
            "traditional Japanese cuisine. No heavy walking — partner has a knee issue. "
            "Traveling in mid-April."
        ),
    },
    {
        "name": "🌴 Bangkok Solo Backpacker",
        "query": (
            "3-day solo backpacking trip to Bangkok, Thailand. "
            "Budget: $500 total. Street food focus, night markets, "
            "temples in the morning, avoid touristy restaurants. "
            "Traveling light, staying in hostels."
        ),
    },
    {
        "name": "🏛️ Rome Family Adventure",
        "query": (
            "7-day family trip to Rome, Italy with 2 kids (ages 8 and 12). "
            "Budget: $4000. Must see Colosseum, Vatican, Trevi Fountain. "
            "Kids love gelato and pizza-making classes. "
            "Need kid-friendly restaurants and not too much walking per day."
        ),
    },
    {
        "name": "🌷 Amsterdam Weekend with Friends",
        "query": (
            "Weekend trip to Amsterdam with 4 friends. "
            "Budget: $800 per person. Mix of museums (Van Gogh, Anne Frank), "
            "canal tours, nightlife, and local food. Biking around the city preferred."
        ),
    },
]


def run_demo(query_index=None):
    """Run one or all demo queries against the local API."""

    print("=" * 60)
    print("  VOYA Travel Planner — Demo")
    print("=" * 60)
    print()

    # Check server is running
    try:
        resp = requests.get(f"{BASE_URL}/api/health", timeout=5)
        if resp.status_code == 200:
            print("✅ Server is running\n")
        else:
            print(f"⚠️  Server responded with {resp.status_code}\n")
    except requests.ConnectionError:
        print("❌ Server not running. Start it with: python run.py")
        print(f"   Expected at: {BASE_URL}")
        sys.exit(1)

    # Select queries
    queries = DEMO_QUERIES
    if query_index is not None:
        queries = [DEMO_QUERIES[query_index]]

    for i, demo in enumerate(queries):
        print(f"\n{'─' * 60}")
        print(f"  Demo {i + 1}: {demo['name']}")
        print(f"{'─' * 60}")
        print(f"\n📝 Query:\n   {demo['query']}\n")
        print("⏳ Generating plan...")

        try:
            resp = requests.post(
                f"{BASE_URL}/api/plan",
                json={"query": demo["query"]},
                timeout=60,
            )

            if resp.status_code == 200:
                data = resp.json()
                if data.get("success"):
                    plan = data.get("plan", {})
                    print(f"✅ Plan generated!\n")

                    # Show summary
                    if isinstance(plan, dict):
                        dest = plan.get("destination", "Unknown")
                        days = plan.get("days", [])
                        budget = plan.get("budget", {})
                        packing = plan.get("packingList", [])
                        tips = plan.get("culturalTips", [])

                        print(f"   📍 Destination: {dest}")
                        print(f"   📅 Days: {len(days)}")

                        if budget:
                            total = budget.get("total", "N/A")
                            print(f"   💰 Budget: {total}")

                        if days:
                            print(f"\n   📋 Itinerary Preview:")
                            for day in days[:3]:  # Show first 3 days
                                day_num = day.get("day", "?")
                                title = day.get("title", day.get("theme", ""))
                                print(f"      Day {day_num}: {title}")
                            if len(days) > 3:
                                print(f"      ... +{len(days) - 3} more days")

                        if packing:
                            print(f"\n   🎒 Packing items: {len(packing)}")

                        if tips:
                            print(f"   🌍 Cultural tips: {len(tips)}")
                    else:
                        # Plan might be a string
                        print(f"   {str(plan)[:200]}...")
                else:
                    print(f"❌ Error: {data.get('error', 'Unknown error')}")
            else:
                print(f"❌ HTTP {resp.status_code}: {resp.text[:200]}")

        except requests.Timeout:
            print("❌ Request timed out (>60s)")
        except Exception as e:
            print(f"❌ Error: {e}")

        print()

    print("=" * 60)
    print("  Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    idx = None
    if len(sys.argv) > 1:
        try:
            idx = int(sys.argv[1]) - 1
            if idx < 0 or idx >= len(DEMO_QUERIES):
                print(f"Invalid demo number. Choose 1-{len(DEMO_QUERIES)}")
                sys.exit(1)
        except ValueError:
            print(f"Usage: python demo.py [1-{len(DEMO_QUERIES)}]")
            sys.exit(1)

    run_demo(idx)
