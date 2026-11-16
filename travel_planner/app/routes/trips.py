"""Trip management routes: save, list, view, share, delete."""
from __future__ import annotations

import json
import uuid

from flask import (Blueprint, abort, flash, jsonify, redirect,
                   render_template, request, url_for)
from flask_login import current_user, login_required

from app.extensions import db
from models.database import Booking, SharedTrip, Trip

trips_bp = Blueprint("trips", __name__)


@trips_bp.route("/")
@login_required
def list_trips():
    """Show all saved trips, recommendations, and bookings for the logged-in user."""
    trips = (Trip.query
             .filter_by(user_id=current_user.id)
             .order_by(Trip.created_at.desc())
             .all())
    bookings = current_user.bookings.order_by(Booking.created_at.desc()).all()
    recommendations = current_user.get_recommendations()
    return render_template("trips/list.html",
                           trips=trips,
                           bookings=bookings,
                           recommendations=recommendations)


@trips_bp.route("/save", methods=["POST"])
@login_required
def save_trip():
    """
    Save a plan from the AJAX planner.
    Body: { "title": "...", "query": "...", "plan": {...} }
    """
    data  = request.get_json(silent=True) or {}
    query = (data.get("query") or "").strip()
    plan  = data.get("plan")

    if not query or not plan:
        return jsonify({"error": "query and plan are required"}), 400

    title       = data.get("title") or plan.get("summary", "Untitled trip")[:120]
    destination = plan.get("destination") or ""

    trip = Trip(
        user_id     = current_user.id,
        title       = title,
        query       = query,
        plan_json   = json.dumps(plan, ensure_ascii=False),
        destination = destination,
    )
    db.session.add(trip)
    db.session.commit()

    return jsonify({"success": True, "trip_id": trip.id,
                    "url": url_for("trips.view_trip", trip_id=trip.id)})


@trips_bp.route("/<int:trip_id>")
@login_required
def view_trip(trip_id: int):
    """View a specific saved trip (owner only)."""
    trip = Trip.query.get_or_404(trip_id)
    if trip.user_id != current_user.id and not current_user.is_admin:
        abort(403)
    plan = json.loads(trip.plan_json)
    return render_template("trips/view.html", trip=trip, plan=plan)


@trips_bp.route("/<int:trip_id>/delete", methods=["POST"])
@login_required
def delete_trip(trip_id: int):
    trip = Trip.query.get_or_404(trip_id)
    if trip.user_id != current_user.id and not current_user.is_admin:
        abort(403)
    db.session.delete(trip)
    db.session.commit()
    flash("Trip deleted.", "info")
    return redirect(url_for("trips.list_trips"))


@trips_bp.route("/<int:trip_id>/share", methods=["POST"])
@login_required
def share_trip(trip_id: int):
    """Generate (or return existing) a public share link."""
    trip = Trip.query.get_or_404(trip_id)
    if trip.user_id != current_user.id:
        abort(403)

    link = trip.shared_links.first()
    if not link:
        link = SharedTrip(trip_id=trip.id, token=uuid.uuid4().hex)
        db.session.add(link)
        db.session.commit()

    share_url = url_for("trips.shared_view", token=link.token, _external=True)
    return jsonify({"url": share_url})


@trips_bp.route("/<int:trip_id>/export/<format>")
@login_required
def export_trip(trip_id: int, format: str):
    """Export a saved trip to markdown (.md) or calendar (.ics)."""
    trip = Trip.query.get_or_404(trip_id)
    if trip.user_id != current_user.id and not current_user.is_admin:
        abort(403)
    plan = json.loads(trip.plan_json)

    from flask import Response
    from datetime import datetime, timedelta

    if format == "markdown":
        lines = [
            f"# {trip.title}",
            f"**Destination:** {trip.destination or 'Custom Trip'}",
            f"**Created:** {trip.created_at.strftime('%Y-%m-%d') if trip.created_at else ''}",
            "",
            "## Summary",
            plan.get("summary", ""),
            "",
            "## Itinerary",
        ]
        for d in plan.get("days", []):
            lines.append(f"### {d.get('day', 'Day')}")
            if d.get("morning"):
                lines.append(f"- **Morning:** {d['morning']}")
            if d.get("afternoon"):
                lines.append(f"- **Afternoon:** {d['afternoon']}")
            if d.get("evening"):
                lines.append(f"- **Evening:** {d['evening']}")
            if d.get("cost"):
                lines.append(f"- **Estimated Cost:** {d['cost']}")
            lines.append("")

        if plan.get("budget"):
            lines.append("## Budget Breakdown")
            if isinstance(plan["budget"], dict):
                for k, v in plan["budget"].items():
                    lines.append(f"- **{k.capitalize()}:** {v}")
            else:
                lines.append(str(plan["budget"]))
            lines.append("")

        if plan.get("packingList"):
            lines.append("## Recommended Packing List")
            for item in plan["packingList"]:
                lines.append(f"- [ ] {item}")
            lines.append("")

        if plan.get("culturalTips"):
            lines.append("## Cultural & Etiquette Tips")
            for tip in plan["culturalTips"]:
                lines.append(f"- {tip}")
            lines.append("")

        md_content = "\n".join(lines)
        return Response(
            md_content,
            mimetype="text/markdown",
            headers={"Content-Disposition": f"attachment;filename=trip_{trip.id}_plan.md"}
        )

    elif format == "ics":
        ics_lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//VOYA AI Travel Planner//EN",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH"
        ]
        start_date = datetime.now()
        for i, d in enumerate(plan.get("days", [])):
            day_date = start_date + timedelta(days=i + 1)
            date_str = day_date.strftime("%Y%m%d")
            desc = f"Morning: {d.get('morning', '')}\\nAfternoon: {d.get('afternoon', '')}\\nEvening: {d.get('evening', '')}"
            summary = f"{trip.title} - {d.get('day', f'Day {i+1}')}"
            ics_lines.extend([
                "BEGIN:VEVENT",
                f"UID:voya-trip-{trip.id}-day-{i+1}@{request.host}",
                f"DTSTAMP:{datetime.now().strftime('%Y%m%dT%H%M%SZ')}",
                f"DTSTART;VALUE=DATE:{date_str}",
                f"DTEND;VALUE=DATE:{date_str}",
                f"SUMMARY:{summary}",
                f"DESCRIPTION:{desc}",
                f"LOCATION:{d.get('location_name', trip.destination or '')}",
                "STATUS:CONFIRMED",
                "END:VEVENT"
            ])
        ics_lines.append("END:VCALENDAR")
        ics_content = "\r\n".join(ics_lines)
        return Response(
            ics_content,
            mimetype="text/calendar",
            headers={"Content-Disposition": f"attachment;filename=trip_{trip.id}_calendar.ics"}
        )

    abort(400)


@trips_bp.route("/shared/<token>")
def shared_view(token: str):
    """Public read-only view of a shared trip."""
    link = SharedTrip.query.filter_by(token=token).first_or_404()
    if not link.is_valid():
        abort(410)  # Gone
    plan = json.loads(link.trip.plan_json)
    return render_template("trips/shared.html", trip=link.trip, plan=plan)
