"""Flask application factory."""
from __future__ import annotations

import sys
from datetime import timedelta
from pathlib import Path

from flask import Flask
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
    from app.config import Config, DevelopmentConfig  # noqa: PLC0415
    cfg = DevelopmentConfig if config_name == "development" else Config
    app.config.from_object(cfg)

    # ── Extensions ────────────────────────────────────────────────────────────
    from app.extensions import bcrypt, db, login_manager  # noqa: PLC0415
    db.init_app(app)
    bcrypt.init_app(app)

    login_manager.init_app(app)
    login_manager.login_view     = "auth.login"          # type: ignore[assignment]
    login_manager.login_message  = "Please log in to access that page."
    login_manager.login_message_category = "warning"

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

    # ── DB init (create tables if missing) ───────────────────────────────────
    with app.app_context():
        from models import database  # noqa: F401, PLC0415 — registers models
        db.create_all()

    # ── CLI: flask init-db (hard reset) ──────────────────────────────────────
    @app.cli.command("init-db")
    def init_db_command():
        """Drop and recreate all tables."""
        from models import database  # noqa: F401, PLC0415
        db.drop_all()
        db.create_all()
        print("✓ Database reset.")

    return app
