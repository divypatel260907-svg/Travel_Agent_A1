"""
SQLAlchemy database models.

Tables
------
User         — registered accounts
Trip         — saved AI-generated plans
SharedTrip   — share tokens so others can view a trip via a link
Booking      — payment / booking history stubs (extend for real provider)
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


# ── User ─────────────────────────────────────────────────────────────────────

class User(UserMixin, db.Model):
    """Registered user account model."""
    __tablename__ = "users"

    id            = db.Column(db.Integer, primary_key=True)
    email         = db.Column(db.String(254), unique=True, nullable=False, index=True)
    display_name  = db.Column(db.String(80),  nullable=False, default="Traveller")
    password_hash = db.Column(db.String(256), nullable=False)
    preferences   = db.Column(db.Text,        nullable=True)   # JSON-encoded travel preferences
    is_admin      = db.Column(db.Boolean, default=False, nullable=False)
    created_at    = db.Column(db.DateTime(timezone=True), default=_now, nullable=False)
    last_login    = db.Column(db.DateTime(timezone=True), nullable=True)

    # relationships
    trips    = db.relationship("Trip",    back_populates="owner",   lazy="dynamic",
                               cascade="all, delete-orphan")
    bookings = db.relationship("Booking", back_populates="user",    lazy="dynamic",
                               cascade="all, delete-orphan")

    # ── Password helpers (Werkzeug security) ──
    def set_password(self, raw: str) -> None:
        """Hash password securely using Werkzeug generate_password_hash."""
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw: str) -> bool:
        """Verify plain password against stored hash."""
        return check_password_hash(self.password_hash, raw)

    # ── Preferences & Personalization helpers (works across multiple devices) ──
    def get_preferences(self) -> dict:
        """Return user preferences as dictionary (synced across devices)."""
        if not self.preferences:
            return {}
        try:
            return json.loads(self.preferences)
        except Exception:
            return {}

    def set_preferences(self, prefs: dict) -> None:
        """Store travel preferences as JSON string."""
        self.preferences = json.dumps(prefs, ensure_ascii=False)

    def get_recommendations(self) -> list[dict]:
        """
        Generate personalized destination recommendations tailored to user style,
        budget, and previous journeys.
        """
        prefs = self.get_preferences()
        user_style = prefs.get("style", "").lower()
        user_budget = prefs.get("budget", "").lower()

        # Curated catalog of destinations
        destinations = [
            {
                "destination": "Kyoto, Japan",
                "tagline": "Ancient Temples & Zen Gardens",
                "style": "relaxed",
                "budget": "mid",
                "icon": "🏯",
                "image_cue": "Gion lanterns, bamboo groves & matcha ceremonies",
                "prompt": "5-day romantic trip to Kyoto in mid-spring, peaceful temples, kaiseki dining, relaxed walking",
            },
            {
                "destination": "Amalfi Coast, Italy",
                "tagline": "Cliffside Splendor & Azure Seas",
                "style": "balanced",
                "budget": "premium",
                "icon": "🍋",
                "image_cue": "Positano cliffside villas, coastal boats & limoncello",
                "prompt": "6-day scenic vacation on Amalfi Coast, cliffside dinners, coastal boat tours, mid-range luxury",
            },
            {
                "destination": "Swiss Alps & Zermatt",
                "tagline": "Alpine Grandeur & Glacial Air",
                "style": "packed",
                "budget": "premium",
                "icon": "🏔️",
                "image_cue": "Matterhorn view chalets, scenic trains & fondue",
                "prompt": "5-day alpine journey in Zermatt and Lucerne, panoramic train rides, scenic mountain strolls",
            },
            {
                "destination": "Reykjavik, Iceland",
                "tagline": "Northern Lights & Volcanic Springs",
                "style": "balanced",
                "budget": "mid",
                "icon": "🌋",
                "image_cue": "Blue Lagoon, geothermal geysers and auroras",
                "prompt": "5-day adventure in Iceland, Golden Circle, geothermal baths, waterfalls, aurora hunting",
            },
            {
                "destination": "Chiang Mai, Thailand",
                "tagline": "Misty Hills & Artisan Markets",
                "style": "relaxed",
                "budget": "budget",
                "icon": "🐘",
                "image_cue": "Lanna temples, mountain sanctuaries & night bazaar",
                "prompt": "7-day cultural getaway in Chiang Mai, elephant sanctuary, cooking class, street food, budget friendly",
            },
            {
                "destination": "Santorini, Greece",
                "tagline": "Sun-Bleached Cyclades & Aegean Sunsets",
                "style": "relaxed",
                "budget": "premium",
                "icon": "🏛️",
                "image_cue": "Whitewashed Oia caldera, infinity pools & catamaran cruise",
                "prompt": "4-day romantic getaway to Santorini, caldera sunset dinners, wine tasting, catamaran sailing",
            },
        ]

        # Prioritize matching style or budget
        ranked = sorted(
            destinations,
            key=lambda d: (
                1 if user_style and d["style"] == user_style else 0,
                1 if user_budget and d["budget"] == user_budget else 0,
            ),
            reverse=True,
        )
        return ranked[:3]

    def __repr__(self) -> str:
        return f"<User {self.email}>"


# ── Trip ─────────────────────────────────────────────────────────────────────

class Trip(db.Model):
    """Saved AI-generated trip plan."""
    __tablename__ = "trips"

    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title       = db.Column(db.String(200), nullable=False)
    # Using 'query_text' mapped to column 'query' to prevent shadowing Flask-SQLAlchemy's Trip.query property
    query_text  = db.Column("query", db.Text, nullable=False)   # raw user query in DB column 'query'
    plan_json   = db.Column(db.Text,        nullable=False)   # JSON from /api/plan
    destination = db.Column(db.String(120), nullable=True)    # extracted for search
    created_at  = db.Column(db.DateTime(timezone=True), default=_now, nullable=False)
    updated_at  = db.Column(db.DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)
    is_public   = db.Column(db.Boolean, default=False, nullable=False)

    # relationships
    owner        = db.relationship("User",       back_populates="trips")
    shared_links = db.relationship("SharedTrip", back_populates="trip",
                                   cascade="all, delete-orphan", lazy="dynamic")
    bookings     = db.relationship("Booking",    back_populates="trip",
                                   cascade="all, delete-orphan", lazy="dynamic")

    def __init__(self, **kwargs):
        # Allow passing 'query' or 'query_text' seamlessly
        if "query" in kwargs and "query_text" not in kwargs:
            kwargs["query_text"] = kwargs.pop("query")
        super().__init__(**kwargs)

    @property
    def raw_query(self) -> str:
        return self.query_text

    @property
    def plan(self) -> dict:
        """Return parsed plan dictionary."""
        try:
            return json.loads(self.plan_json)
        except Exception:
            return {}

    def __repr__(self) -> str:
        return f"<Trip {self.id} '{self.title}'>"


# ── SharedTrip ────────────────────────────────────────────────────────────────

class SharedTrip(db.Model):
    """A unique token that lets anyone with the link view a trip (read-only)."""
    __tablename__ = "shared_trips"

    id         = db.Column(db.Integer, primary_key=True)
    trip_id    = db.Column(db.Integer, db.ForeignKey("trips.id"), nullable=False, index=True)
    token      = db.Column(db.String(64), unique=True, nullable=False,
                           default=lambda: uuid.uuid4().hex)
    created_at = db.Column(db.DateTime(timezone=True), default=_now, nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=True)  # None = never

    trip = db.relationship("Trip", back_populates="shared_links")

    def is_valid(self) -> bool:
        if self.expires_at is None:
            return True
        return _now() < self.expires_at

    def __repr__(self) -> str:
        return f"<SharedTrip token={self.token[:8]}…>"


# ── Booking ───────────────────────────────────────────────────────────────────

class Booking(db.Model):
    """Stub for future payment / booking integration."""
    __tablename__ = "bookings"

    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    trip_id      = db.Column(db.Integer, db.ForeignKey("trips.id"), nullable=True)
    provider     = db.Column(db.String(80),  nullable=False, default="manual")
    description  = db.Column(db.String(300), nullable=False)
    amount_cents = db.Column(db.Integer,     nullable=False, default=0)  # store in smallest unit
    currency     = db.Column(db.String(3),   nullable=False, default="USD")
    status       = db.Column(db.String(30),  nullable=False, default="pending")
    reference    = db.Column(db.String(120), nullable=True)   # external booking ref
    created_at   = db.Column(db.DateTime(timezone=True), default=_now, nullable=False)

    user = db.relationship("User", back_populates="bookings")
    trip = db.relationship("Trip", back_populates="bookings")

    @property
    def amount_display(self) -> str:
        return f"{self.currency} {self.amount_cents / 100:.2f}"

    def __repr__(self) -> str:
        return f"<Booking {self.id} {self.status}>"
