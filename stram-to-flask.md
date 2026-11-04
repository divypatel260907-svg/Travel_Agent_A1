# Travel Planner Agent — Streamlit → Flask Migration Guide

## Why Move to Flask?
- Full control over UI/UX (no Streamlit limitations)
- Better performance and customization
- Easier to add authentication, file downloads, real-time updates later
- Cleaner separation of backend logic and frontend

---

## Recommended Architecture

```
Option A (Recommended - Best UI)
Flask (API only)  +  Next.js / React frontend

Option B (Simpler - Pure Flask)
Flask + Jinja2 templates + Tailwind CSS
```

We will focus on **Option B** first (pure Flask) so you can fully replace Streamlit quickly.  
You can later upgrade the frontend to Next.js easily because the backend will already be clean APIs.

---

## New Project Structure

```
travel-planner-flask/
├── app/
│   ├── __init__.py              # Flask app factory
│   ├── config.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── main.py              # Home, plan form
│   │   └── api.py               # JSON API endpoints
│   ├── agents/                  # Keep your existing agents
│   │   ├── preference_extractor.py
│   │   ├── weather_agent.py
│   │   ├── itinerary_agent.py
│   │   ├── budget_agent.py
│   │   └── ...
│   ├── tools/                   # Weather, POI, etc.
│   ├── services/
│   │   └── planner_service.py   # Orchestrates the whole plan
│   ├── models/                  # Pydantic models
│   └── utils/
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── plan.html
│   └── components/
├── static/
│   ├── css/
│   ├── js/
│   └── images/
├── .env
├── requirements.txt
└── run.py
```

---

## Step-by-Step Migration

### 1. Install Dependencies

```bash
pip install flask python-dotenv pydantic langchain langgraph groq google-generativeai httpx
# Optional but recommended
pip install flask-cors
```

### 2. Create `requirements.txt`

```txt
flask>=3.0.0
python-dotenv
pydantic>=2.0
langchain
langgraph
groq
google-generativeai
httpx
flask-cors
jinja2
```

### 3. App Factory (`app/__init__.py`)

```python
from flask import Flask
from dotenv import load_dotenv
import os

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key-change-me")

    from app.routes.main import main_bp
    from app.routes.api import api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    return app
```

### 4. Main Routes (`app/routes/main.py`)

```python
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.services.planner_service import generate_travel_plan

main_bp = Blueprint("main", __name__)

@main_bp.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        user_input = request.form.get("query", "").strip()
        if not user_input:
            flash("Please enter your travel request.", "error")
            return redirect(url_for("main.index"))

        try:
            plan = generate_travel_plan(user_input)
            session["last_plan"] = plan
            return redirect(url_for("main.show_plan"))
        except Exception as e:
            flash(f"Error generating plan: {str(e)}", "error")
            return redirect(url_for("main.index"))

    return render_template("index.html")


@main_bp.route("/plan")
def show_plan():
    plan = session.get("last_plan")
    if not plan:
        flash("No plan found. Please create one first.", "warning")
        return redirect(url_for("main.index"))
    return render_template("plan.html", plan=plan)
```

### 5. API Routes (`app/routes/api.py`) — for future frontend

```python
from flask import Blueprint, request, jsonify
from app.services.planner_service import generate_travel_plan

api_bp = Blueprint("api", __name__)

@api_bp.route("/plan", methods=["POST"])
def create_plan():
    data = request.get_json() or {}
    user_input = data.get("query", "").strip()

    if not user_input:
        return jsonify({"error": "Query is required"}), 400

    try:
        plan = generate_travel_plan(user_input)
        return jsonify({"success": True, "plan": plan})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

### 6. Planner Service (Core Logic)

```python
# app/services/planner_service.py

from app.agents.preference_extractor import extract_preferences
from app.agents.weather_agent import get_weather
from app.agents.itinerary_agent import build_itinerary
from app.agents.budget_agent import calculate_budget
# import other agents...

def generate_travel_plan(user_query: str) -> dict:
    """
    Main orchestration function.
    This replaces the Streamlit flow.
    """
    # 1. Extract preferences
    preferences = extract_preferences(user_query)

    # 2. Get weather
    weather = get_weather(
        city=preferences.destination,
        start_date=preferences.start_date,
        end_date=preferences.end_date
    )

    # 3. Build itinerary
    itinerary = build_itinerary(preferences, weather)

    # 4. Budget
    budget = calculate_budget(itinerary, preferences.budget)

    # 5. Assemble final plan
    plan = {
        "preferences": preferences.model_dump(),
        "weather": weather,
        "itinerary": itinerary,
        "budget": budget,
        "generated_at": str(datetime.utcnow())
    }

    return plan
```

### 7. Basic Templates

**`templates/base.html`**
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Travel Planner{% endblock %}</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50 text-gray-800 min-h-screen">
    <nav class="bg-white shadow-sm">
        <div class="max-w-5xl mx-auto px-4 py-4 flex justify-between items-center">
            <a href="/" class="text-xl font-bold text-indigo-600">Travel Planner Agent</a>
        </div>
    </nav>

    <main class="max-w-5xl mx-auto px-4 py-8">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="mb-4 p-4 rounded-lg 
                        {% if category == 'error' %}bg-red-100 text-red-700
                        {% else %}bg-blue-100 text-blue-700{% endif %}">
                        {{ message }}
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        {% block content %}{% endblock %}
    </main>
</body>
</html>
```

**`templates/index.html`**
```html
{% extends "base.html" %}

{% block content %}
<div class="bg-white rounded-2xl shadow-sm p-8">
    <h1 class="text-3xl font-bold mb-2">Plan Your Perfect Trip</h1>
    <p class="text-gray-600 mb-6">Tell me where you want to go, your budget, and preferences.</p>

    <form method="POST" class="space-y-4">
        <div>
            <label class="block text-sm font-medium mb-1">Your travel request</label>
            <textarea name="query" rows="4" required
                class="w-full border border-gray-300 rounded-xl px-4 py-3 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                placeholder="Example: 5-day romantic trip to Kyoto under $1800 in April, love temples and food, no heavy walking"></textarea>
        </div>
        <button type="submit"
            class="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-3 px-6 rounded-xl transition">
            Generate Plan
        </button>
    </form>
</div>
{% endblock %}
```

### 8. Run the App

```python
# run.py
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
```

```bash
python run.py
```

---

## Important Migration Notes

| Streamlit Concept              | Flask Equivalent                          |
|--------------------------------|-------------------------------------------|
| `st.text_input` / `st.form`    | HTML form + `request.form`                |
| `st.session_state`             | Flask `session`                           |
| `st.write` / `st.markdown`     | Jinja templates                           |
| `st.spinner`                   | Frontend loading state (JS) or HTMX       |
| `st.button`                    | HTML button + form submit                 |
| Direct agent calls in UI       | Move all logic into `planner_service.py`  |

---

## Next Upgrades (After Basic Flask Works)

1. **Better UI** → Replace Jinja with Next.js + Tailwind + shadcn/ui (call the `/api/plan` endpoint)
2. **Loading states** → Add HTMX or simple JavaScript
3. **Download plan** → Add PDF / Markdown export route
4. **History** → Store past plans in SQLite
5. **Streaming** → Use Server-Sent Events if you want live agent thoughts

---

## Environment Variables (`.env`)

```env
SECRET_KEY=your-secret-key-here
GEMINI_API_KEY=your-gemini-key
GROQ_API_KEY=your-groq-key
OPENTRIPMAP_API_KEY=optional
```

---

## Summary Checklist

- [ ] Create new Flask project structure
- [ ] Move all agent & tool code into `app/agents` and `app/tools`
- [ ] Create `planner_service.py` as the single entry point
- [ ] Build basic form + plan display pages
- [ ] Test end-to-end with a real query
- [ ] (Optional) Add JSON API for future frontend upgrade
```
