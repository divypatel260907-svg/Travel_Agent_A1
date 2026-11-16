"""Security tests for backend auth, input validation, headers, and redirect protection."""
import sys
from pathlib import Path

_PKG = Path(__file__).resolve().parent.parent
if str(_PKG) not in sys.path:
    sys.path.insert(0, str(_PKG))

import pytest
from app import create_app
from app.extensions import db
from models.database import User


@pytest.fixture
def test_app():
    app = create_app("testing")
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["WTF_CSRF_ENABLED"] = False

    with app.app_context():
        db.create_all()
        # Seed test user
        user = User(email="test@example.com", display_name="Tester")
        user.set_password("SecurePassword123!")
        db.session.add(user)
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(test_app):
    return test_app.test_client()


def test_api_plan_requires_authentication(client):
    """POST /api/plan must return 401 when accessed without active session."""
    res = client.post("/api/plan", json={"query": "3-day trip to Tokyo"})
    assert res.status_code == 401
    assert "error" in res.get_json()


def test_api_plan_max_query_length(client):
    """POST /api/plan must reject inputs that exceed MAX_QUERY_LENGTH."""
    # Log in
    client.post("/auth/login", data={"email": "test@example.com", "password": "SecurePassword123!"})

    oversized_query = "A" * 2500
    res = client.post("/api/plan", json={"query": oversized_query})
    assert res.status_code == 400
    assert "too long" in res.get_json().get("error", "")


def test_open_redirect_mitigation(client):
    """Login with malicious external ?next= URL should redirect to index, not external site."""
    evil_urls = [
        "https://evil.com",
        "//evil.com",
        "\\\\evil.com",
        "http://attacker.com/steal",
    ]
    for evil in evil_urls:
        res = client.post(
            f"/auth/login?next={evil}",
            data={"email": "test@example.com", "password": "SecurePassword123!"},
            follow_redirects=False,
        )
        assert res.status_code == 302
        assert not res.location.startswith("https://evil.com")
        assert not res.location.startswith("//evil.com")
        assert not res.location.startswith("http://attacker.com")


def test_security_headers_present(client):
    """Responses must include modern security headers."""
    res = client.get("/")
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert res.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "Content-Security-Policy" in res.headers
