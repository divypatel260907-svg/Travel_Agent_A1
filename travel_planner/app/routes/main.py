"""Main HTML page routes."""
from __future__ import annotations

import json

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from app.services.planner_service import generate_travel_plan

main_bp = Blueprint("main", __name__)


@main_bp.route("/", methods=["GET", "POST"])
def index():
    """Landing page with the trip request form."""
    if request.method == "POST":
        user_input = request.form.get("query", "").strip()
        if not user_input:
            flash("Please describe your trip first.", "error")
            return redirect(url_for("main.index"))

        try:
            plan = generate_travel_plan(user_input)
            # Store as JSON string to avoid Flask session size issues with nested objects
            session["last_plan"] = json.dumps(plan, default=str)
            return redirect(url_for("main.show_plan"))
        except Exception as exc:
            flash(f"Could not generate plan: {exc}", "error")
            return redirect(url_for("main.index"))

    return render_template("index.html")


@main_bp.route("/login")
def login_redirect():
    return redirect(url_for("auth.login"))


@main_bp.route("/register")
def register_redirect():
    return redirect(url_for("auth.register"))


@main_bp.route("/plan")
def show_plan():
    """Rendered plan page."""
    raw = session.get("last_plan")
    if not raw:
        flash("No plan found — please create one first.", "warning")
        return redirect(url_for("main.index"))

    plan = json.loads(raw)
    return render_template("plan.html", plan=plan)


@main_bp.route("/clear")
def clear():
    """Clear the current session plan and return home."""
    session.pop("last_plan", None)
    return redirect(url_for("main.index"))
