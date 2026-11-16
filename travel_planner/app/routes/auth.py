"""Authentication routes: login, register, logout, forgot-password."""
from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlsplit

from flask import (Blueprint, flash, redirect, render_template,
                   request, url_for)
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import db
from models.database import User

auth_bp = Blueprint("auth", __name__)


def _is_safe_url(target: str | None) -> bool:
    if not target or target.startswith("//") or target.startswith("\\"):
        return False
    ref_url = urlsplit(request.host_url)
    test_url = urlsplit(target)
    return test_url.scheme in ("", "http", "https") and (
        not test_url.netloc or test_url.netloc == ref_url.netloc
    )


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))

        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash("Incorrect email or password.", "error")
            return render_template("auth/login.html", email=email)

        user.last_login = datetime.now(tz=timezone.utc)
        db.session.commit()
        login_user(user, remember=remember)

        next_page = request.args.get("next")
        if next_page and _is_safe_url(next_page):
            return redirect(next_page)
        return redirect(url_for("main.index"))

    return render_template("auth/login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        email        = request.form.get("email", "").strip().lower()
        display_name = request.form.get("display_name", "").strip() or "Traveller"
        password     = request.form.get("password", "")
        confirm      = request.form.get("confirm_password", "")

        # Validate
        if not email or "@" not in email:
            flash("Please enter a valid email address.", "error")
            return render_template("auth/register.html", email=email, display_name=display_name)
        if len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
            return render_template("auth/register.html", email=email, display_name=display_name)
        if password != confirm:
            flash("Passwords do not match.", "error")
            return render_template("auth/register.html", email=email, display_name=display_name)
        if User.query.filter_by(email=email).first():
            flash("An account with that email already exists.", "error")
            return render_template("auth/register.html", email=email, display_name=display_name)

        user = User(email=email, display_name=display_name)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        flash(f"Welcome, {user.display_name}! Your account is ready.", "success")
        return redirect(url_for("main.index"))

    return render_template("auth/register.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    """Placeholder — wire up Flask-Mail + token when ready."""
    if request.method == "POST":
        flash("If that email is registered, a reset link has been sent.", "info")
        return redirect(url_for("auth.login"))
    return render_template("auth/forgot_password.html")


@auth_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    """Sync user travel preferences and profile across devices for personalized recommendations."""
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        current_user.set_preferences(data)
        if data.get("name"):
            current_user.display_name = data["name"].strip()[:80]
        db.session.commit()
        return {"success": True, "preferences": current_user.get_preferences()}
    return {
        "display_name": current_user.display_name,
        "email": current_user.email,
        "preferences": current_user.get_preferences(),
        "recommendations": current_user.get_recommendations(),
    }

