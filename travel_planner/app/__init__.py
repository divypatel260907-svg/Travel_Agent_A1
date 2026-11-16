"""Flask application factory."""
from __future__ import annotations

import os
import sys
from datetime import timedelta
from pathlib import Path

from flask import Flask, flash, redirect, request, url_for
from flask_cors import CORS
from dotenv import load_dotenv

# Make the travel_planner package importable from any working directory
_HERE = Path(__file__).resolve().parent          # travel_planner/app/
_PKG  = _HERE.parent                             # travel_planner/
_ROOT = _PKG.parent                              # ibm-bob/
for _p in (_ROOT, _PKG):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

load_dotenv(_PKG / ".env", override=False)


def create_app(config_name: str = "development") -> Flask:
    """Application factory."""
    app = Flask(
        __name__,
        template_folder=str(_PKG / "templates"),
        static_folder=str(_PKG / "static"),
        instance_path=str(_PKG / "instance"),
        instance_relative_config=False,
    )

    # ── Config ────────────────────────────────────────────────────────────────
    from app.config import Config, DevelopmentConfig, ProductionConfig  # noqa: PLC0415
    if config_name == "production" or os.getenv("FLASK_ENV") == "production":
        cfg = ProductionConfig
    elif config_name == "development":
        cfg = DevelopmentConfig
    else:
        cfg = Config
    app.config.from_object(cfg)

    # ── CORS ──────────────────────────────────────────────────────────────────
    allowed_origins = app.config.get("ALLOWED_ORIGINS", [])
    if allowed_origins:
        CORS(app, origins=allowed_origins, supports_credentials=True)
    else:
        # Default: restrict to same origin
        CORS(app, origins=[], supports_credentials=True)

    # ── Extensions ────────────────────────────────────────────────────────────
    from app.extensions import bcrypt, db, limiter, login_manager  # noqa: PLC0415
    db.init_app(app)
    bcrypt.init_app(app)
    limiter.init_app(app)

    login_manager.init_app(app)
    login_manager.login_view     = "auth.login"          # type: ignore[assignment]
    login_manager.login_message  = "Please log in to access that page."
    login_manager.login_message_category = "warning"

    @login_manager.unauthorized_handler
    def unauthorized():
        if request.path.startswith("/api/") or request.is_json:
            return {"error": "Authentication required. Please sign in to access this endpoint."}, 401
        flash("Please log in to access that page.", "warning")
        return redirect(url_for("auth.login", next=request.full_path if request.method == "GET" else None))

    # Remember-me duration
    app.config["REMEMBER_COOKIE_DURATION"] = timedelta(
        days=app.config.get("REMEMBER_COOKIE_DURATION_DAYS", 30)
    )

    # ── User loader ───────────────────────────────────────────────────────────
    from models.database import User  # noqa: PLC0415

    @login_manager.user_loader
    def load_user(user_id: str):
        return db.session.get(User, int(user_id))

    # ── Blueprints ────────────────────────────────────────────────────────────
    from app.routes.main  import main_bp   # noqa: PLC0415
    from app.routes.api   import api_bp    # noqa: PLC0415
    from app.routes.auth  import auth_bp   # noqa: PLC0415
    from app.routes.trips import trips_bp  # noqa: PLC0415
    from app.routes.admin import admin_bp  # noqa: PLC0415

    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp,   url_prefix="/api")
    app.register_blueprint(auth_bp,  url_prefix="/auth")
    app.register_blueprint(trips_bp, url_prefix="/trips")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    # ── Security Headers ──────────────────────────────────────────────────────
    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if not app.debug:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Content-Security-Policy: allow self, Google Fonts, Leaflet CDN, OSM tiles
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://unpkg.com; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "img-src 'self' data: https://*.tile.openstreetmap.org https://unpkg.com; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        response.headers["Content-Security-Policy"] = csp
        return response

    # ── Rate Limit Error Handler ──────────────────────────────────────────────
    @app.errorhandler(429)
    def ratelimit_handler(e):
        if request.path.startswith("/api/"):
            return {"error": "Rate limit exceeded. Please wait a moment before trying again."}, 429
        flash("You are making requests too quickly. Please slow down.", "warning")
        return redirect(url_for("main.index"))

    # ── DB init (create tables if missing) ───────────────────────────────────
    with app.app_context():
        # Ensure instance directory exists if using SQLite relative path
        uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
        if uri.startswith("sqlite:////tmp/"):
            Path("/tmp").mkdir(parents=True, exist_ok=True)
        from models import database  # noqa: F401, PLC0415 — registers models
        try:
            db.create_all()
        except Exception as exc:
            app.logger.warning(f"Database auto-creation error: {exc}")

    # ── CLI: flask init-db (hard reset) ──────────────────────────────────────
    @app.cli.command("init-db")
    def init_db_command():
        """Drop and recreate all tables."""
        from models import database  # noqa: F401, PLC0415
        db.drop_all()
        db.create_all()
        print("✓ Database reset.")

    return app
