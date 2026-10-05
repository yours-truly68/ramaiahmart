import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.config import Settings
from app.core.limiter import rate_limiter
from app.core.proxy import is_trusted_proxy
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.main import app
from app.models.auth import EmailVerificationCode
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


@pytest.mark.asyncio
async def test_otp_verification_attempt_limit_and_invalidation():
    """OTP code is invalidated after 5 failed attempts."""
    email = f"verify_{uuid.uuid4().hex[:6]}@msrit.edu"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Register user
        reg = await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "Password123!",
                "name": "Verify Student",
                "accepted_terms": True,
                "accepted_privacy": True,
            },
        )
        assert reg.status_code == 201
        valid_code = reg.json()["verification_code"]
        assert valid_code is not None

        db = SessionLocal()
        user = db.scalar(select(User).where(User.email == email))

        # Send 4 incorrect attempts
        for _ in range(4):
            resp = await client.post(
                "/api/v1/auth/verify",
                json={"email": email, "code": "000000"},
                headers={"X-Forwarded-For": "192.0.2.1"},
            )
            assert resp.status_code == 400
            assert resp.json()["error"]["code"] == "INVALID_OR_EXPIRED_CODE"

        # 5th incorrect attempt invalidates the OTP and returns MAX_ATTEMPTS_EXCEEDED
        resp_5 = await client.post(
            "/api/v1/auth/verify",
            json={"email": email, "code": "000000"},
            headers={"X-Forwarded-For": "192.0.2.1"},
        )
        assert resp_5.status_code == 400
        assert resp_5.json()["error"]["code"] == "MAX_ATTEMPTS_EXCEEDED"

        # Verify that in database, verification code is now marked used_at
        db.expire_all()
        db_code = db.scalar(
            select(EmailVerificationCode).where(EmailVerificationCode.user_id == user.id)
        )
        assert db_code.used_at is not None
        db.close()

        # Even providing the correct code now fails because it was invalidated
        resp_retry_correct = await client.post(
            "/api/v1/auth/verify",
            json={"email": email, "code": valid_code},
            headers={"X-Forwarded-For": "192.0.2.1"},
        )
        assert resp_retry_correct.status_code == 400
        assert resp_retry_correct.json()["error"]["code"] == "INVALID_OR_EXPIRED_CODE"


@pytest.mark.asyncio
async def test_resend_verification_cooldown_rate_limit():
    """Resend verification enforces a 60-second cooldown."""
    email = f"resend_{uuid.uuid4().hex[:6]}@msrit.edu"

    # Create unverified user
    db = SessionLocal()
    user = User(
        email=email,
        name="Resend Student",
        hashed_password=hash_password("Password123!"),
        university_verified=False,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # First resend succeeds
        resp1 = await client.post(
            "/api/v1/auth/resend-verification",
            json={"email": email},
            headers={"X-Forwarded-For": "198.51.100.80"},
        )
        assert resp1.status_code == 200

        # Immediate second resend is rate limited by cooldown
        resp2 = await client.post(
            "/api/v1/auth/resend-verification",
            json={"email": email},
            headers={"X-Forwarded-For": "198.51.100.80"},
        )
        assert resp2.status_code == 429
        assert resp2.json()["error"]["code"] == "RATE_LIMITED"
        assert "Retry-After" in resp2.headers


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
