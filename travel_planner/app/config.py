"""Flask configuration loaded from environment variables."""
from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

_BASE_DIR = Path(__file__).resolve().parent.parent  # travel_planner/


class Config:
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-change-me-in-production")
    DEBUG: bool = False
    TESTING: bool = False

    # ── Database ──────────────────────────────────────────────────────────────
    # SQLite by default; swap DATABASE_URL for PostgreSQL in production
    SQLALCHEMY_DATABASE_URI: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{_BASE_DIR / 'instance' / 'travel.db'}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SQLALCHEMY_ENGINE_OPTIONS: dict = {"pool_pre_ping": True}

    # ── Flask-Login ───────────────────────────────────────────────────────────
    LOGIN_VIEW: str = "auth.login"          # redirect target for @login_required
    REMEMBER_COOKIE_DURATION_DAYS: int = 30

    # ── LLM ──────────────────────────────────────────────────────────────────
    GROQ_API_KEY: str | None = os.getenv("GROQ_API_KEY")
    GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

    # ── Cache / storage ───────────────────────────────────────────────────────
    CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "3600"))
    PREFERENCE_STORAGE: str = os.getenv("PREFERENCE_STORAGE", "session")
    SESSION_COOKIE_SIZE_LIMIT: int = 4000


class DevelopmentConfig(Config):
    DEBUG = True
