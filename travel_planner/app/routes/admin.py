"""Admin dashboard — requires is_admin flag on the User."""
from __future__ import annotations

from functools import wraps

from flask import Blueprint, abort, render_template
from flask_login import current_user, login_required

from app.extensions import db
from models.database import Booking, Trip, User

admin_bp = Blueprint("admin", __name__)


def admin_required(fn):
    @wraps(fn)
    @login_required
    def wrapper(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return fn(*args, **kwargs)
    return wrapper


@admin_bp.route("/")
@admin_required
def dashboard():
    stats = {
        "users":    User.query.count(),
        "trips":    Trip.query.count(),
        "bookings": Booking.query.count(),
    }
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()
    recent_trips = Trip.query.order_by(Trip.created_at.desc()).limit(10).all()
    return render_template("admin/dashboard.html",
                           stats=stats,
                           recent_users=recent_users,
                           recent_trips=recent_trips)


@admin_bp.route("/users")
@admin_required
def users():
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", users=all_users)
