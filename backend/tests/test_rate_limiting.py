import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.core.limiter import rate_limiter
from app.core.proxy import is_trusted_proxy
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.main import app
from app.models.user import User


@pytest.fixture(autouse=True)
def clean_rate_limiter():
    """Ensure in-memory rate limiter is fresh for every test."""
    rate_limiter.clear()
    yield
    rate_limiter.clear()


@pytest.mark.asyncio
async def test_login_ip_rate_limiting():
    """Repeated failed logins from the same IP trigger HTTP 429."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Attempt 15 failed logins
        for i in range(15):
            resp = await client.post(
                "/api/v1/auth/login",
                json={"email": f"failed_{i}@msrit.edu", "password": "WrongPassword123!"},
                headers={"X-Forwarded-For": "198.51.100.1"},
            )
            assert resp.status_code == 401

        # 16th failed login from the same IP must be rate limited
        resp_blocked = await client.post(
            "/api/v1/auth/login",
            json={"email": "failed_16@msrit.edu", "password": "WrongPassword123!"},
            headers={"X-Forwarded-For": "198.51.100.1"},
        )
        assert resp_blocked.status_code == 429
        assert resp_blocked.json()["error"]["code"] == "RATE_LIMITED"
        assert "Retry-After" in resp_blocked.headers


@pytest.mark.asyncio
async def test_login_email_account_rate_limiting():
    """Repeated failed logins targeting the same account trigger HTTP 429 across IPs."""
    target_email = f"victim_{uuid.uuid4().hex[:6]}@msrit.edu"

    # Seed user in DB
    db = SessionLocal()
    user = User(
        email=target_email,
        name="Target Student",
        hashed_password=hash_password("ValidPassword123!"),
        university_verified=True,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 5 failed login attempts from different client IPs
        for i in range(5):
            resp = await client.post(
                "/api/v1/auth/login",
                json={"email": target_email, "password": "WrongPassword!"},
                headers={"X-Forwarded-For": f"198.51.100.{i + 10}"},
            )
            assert resp.status_code == 401

        # 6th attempt targeting the same email is rate limited
        resp_blocked = await client.post(
            "/api/v1/auth/login",
            json={"email": target_email, "password": "WrongPassword!"},
            headers={"X-Forwarded-For": "198.51.100.99"},
        )
        assert resp_blocked.status_code == 429
        assert resp_blocked.json()["error"]["code"] == "RATE_LIMITED"
        assert "Retry-After" in resp_blocked.headers


@pytest.mark.asyncio
async def test_login_successful_does_not_count_as_failure_and_resets():
    """Successful login does not trigger failure rate limits and clears failure bucket."""
    email = f"good_{uuid.uuid4().hex[:6]}@msrit.edu"
    password = "CorrectPassword123!"

    db = SessionLocal()
    user = User(
        email=email,
        name="Good Student",
        hashed_password=hash_password(password),
        university_verified=True,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Successful logins can be performed without rate limiting
        for _ in range(6):
            resp = await client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": password},
            )
            assert resp.status_code == 200
            assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_registration_rate_limiting():
    """Excessive registration attempts from the same IP return HTTP 429."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for i in range(10):
            resp = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": f"student_{i}_{uuid.uuid4().hex[:6]}@msrit.edu",
                    "password": "Password123!",
                    "name": f"Student {i}",
                    "accepted_terms": True,
                    "accepted_privacy": True,
                },
                headers={"X-Forwarded-For": "203.0.113.42"},
            )
            assert resp.status_code == 201

        # 11th registration from the same IP should be blocked
        resp_blocked = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"student_blocked_{uuid.uuid4().hex[:6]}@msrit.edu",
                "password": "Password123!",
                "name": "Blocked Student",
                "accepted_terms": True,
                "accepted_privacy": True,
            },
            headers={"X-Forwarded-For": "203.0.113.42"},
        )
        assert resp_blocked.status_code == 429
        assert resp_blocked.json()["error"]["code"] == "RATE_LIMITED"
        assert "Retry-After" in resp_blocked.headers


def test_trusted_proxy_client_ip_resolution():
    """Verify that proxy headers are accepted only from trusted proxies."""
    trusted_networks = ["127.0.0.1", "172.16.0.0/12", "10.0.0.0/8"]

    assert is_trusted_proxy("127.0.0.1", trusted_networks)
    assert is_trusted_proxy("172.18.0.5", trusted_networks)
    assert is_trusted_proxy("10.5.0.2", trusted_networks)
    assert not is_trusted_proxy("203.0.113.195", trusted_networks)


def test_production_jwt_secret_validation():
    """Production mode must reject default or weak secrets."""
    # Default secret in production raises ValueError
    with pytest.raises(ValueError, match="Cannot use the default development secret"):
        Settings(
            APP_ENV="production",
            JWT_SECRET_KEY="dev-insecure-secret-key-change-in-production-min-32-chars",
            DEBUG=False,
        )

    # Too short secret in production raises ValueError
    with pytest.raises(ValueError, match="at least 32 characters"):
        Settings(
            APP_ENV="production",
            JWT_SECRET_KEY="too-short-secret",
            DEBUG=False,
        )

    # DEBUG=True in production raises ValueError
    with pytest.raises(ValueError, match="DEBUG mode must be set to False"):
        Settings(
            APP_ENV="production",
            JWT_SECRET_KEY="a" * 32,
            DEBUG=True,
        )

    # Valid production settings pass
    valid = Settings(
        APP_ENV="production",
        JWT_SECRET_KEY="a" * 32,
        DEBUG=False,
    )
    assert valid.APP_ENV == "production"
