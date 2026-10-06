import uuid
from datetime import timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token, verify_password
from app.db.session import SessionLocal
from app.main import app
from app.models.user import User


def register_payload(email: str, **overrides):
    payload = {
        "email": email,
        "password": "SecurePassword123!",
        "name": "Test Student",
        "accepted_terms": True,
        "accepted_privacy": True,
    }
    payload.update(overrides)
    return payload


async def register_and_login(client: AsyncClient, email: str, password: str = "SecurePassword123!"):
    reg = await client.post(
        "/api/v1/auth/register", json=register_payload(email, password=password)
    )
    assert reg.status_code == 201, reg.text
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    return login.json()


@pytest.mark.asyncio
async def test_registration_msrit_email_succeeds_without_email_step() -> None:
    """A valid @msrit.edu registration succeeds immediately; no verification code exists."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        unique_email = f"student_{uuid.uuid4().hex[:8]}@msrit.edu"

        reg_res = await client.post("/api/v1/auth/register", json=register_payload(unique_email))
        assert reg_res.status_code == 201
        reg_data = reg_res.json()
        assert reg_data["email"] == unique_email
        # No OTP/verification artifact may be exposed by registration
        assert "verification_code" not in reg_data

        db = SessionLocal()
        user_db = db.query(User).filter(User.email == unique_email).first()
        assert user_db is not None
        # Password is never stored in plaintext
        assert user_db.hashed_password != "SecurePassword123!"
        assert verify_password("SecurePassword123!", user_db.hashed_password)
        # V1 deadlock removal: registration is sufficient for full access
        assert user_db.university_verified is True
        assert user_db.status == "ACTIVE"
        db.close()


@pytest.mark.asyncio
async def test_registration_rejects_non_university_domains() -> None:
    """Non-@msrit.edu domains are rejected by the backend (not just the frontend)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        for email in (
            f"student_{uuid.uuid4().hex[:6]}@gmail.com",
            f"student_{uuid.uuid4().hex[:6]}@outlook.com",
            f"student_{uuid.uuid4().hex[:6]}@yahoo.com",
        ):
            res = await client.post("/api/v1/auth/register", json=register_payload(email))
            assert res.status_code == 400
            assert res.json()["error"]["code"] == "INVALID_UNIVERSITY_EMAIL"


@pytest.mark.asyncio
async def test_registration_normalizes_email_case() -> None:
    """Emails are trimmed and lowercased before validation and persistence."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        email = f"CaseStudy_{uuid.uuid4().hex[:6]}@MSRIT.edu"

        reg_res = await client.post("/api/v1/auth/register", json=register_payload(f"  {email}  "))
        assert reg_res.status_code == 201
        assert reg_res.json()["email"] == email.lower()

        db = SessionLocal()
        user_db = db.query(User).filter(User.email == email.lower()).first()
        assert user_db is not None
        db.close()

        # Duplicate detection after normalization (unique constraint on normalized email)
        dup = await client.post("/api/v1/auth/register", json=register_payload(email))
        assert dup.status_code == 409
        assert dup.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_registration_requires_legal_consent() -> None:
    """Legal consent is enforced server-side, not only in the browser."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        res = await client.post(
            "/api/v1/auth/register",
            json=register_payload(
                f"nogift_{uuid.uuid4().hex[:6]}@msrit.edu",
                accepted_terms=False,
                accepted_privacy=True,
            ),
        )
        assert res.status_code == 400
        assert res.json()["error"]["code"] == "LEGAL_CONSENT_REQUIRED"


@pytest.mark.asyncio
async def test_full_login_refresh_logout_flow() -> None:
    """Login, protected access, refresh, and logout/revocation all work end-to-end."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        email = f"flow_{uuid.uuid4().hex[:8]}@msrit.edu"
        tokens = await register_and_login(client, email)
        assert tokens["token_type"] == "bearer"
        assert "access_token" in tokens
        assert "refresh_token" in tokens

        headers = {"Authorization": f"Bearer {tokens['access_token']}"}

        me_res = await client.get("/api/v1/users/me", headers=headers)
        assert me_res.status_code == 200
        assert me_res.json()["email"] == email

        # Update own profile (counts as meaningful activity)
        patch_res = await client.patch(
            "/api/v1/users/me",
            headers=headers,
            json={"bio": "CS student passionate about open source", "name": "Updated Name"},
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["bio"] == "CS student passionate about open source"
        assert patch_res.json()["name"] == "Updated Name"

        # Refresh token
        refresh_res = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert refresh_res.status_code == 200
        assert "access_token" in refresh_res.json()

        # Logout revokes refresh token
        logout_res = await client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert logout_res.status_code == 200

        revoked_refresh = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert revoked_refresh.status_code == 401
        assert revoked_refresh.json()["error"]["code"] == "TOKEN_REVOKED_OR_EXPIRED"


@pytest.mark.asyncio
async def test_invalid_credentials_and_expired_tokens() -> None:
    """Security boundaries: invalid credentials, invalid domain, expired token."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        res = await client.post(
            "/api/v1/auth/register",
            json=register_payload(f"hacker_{uuid.uuid4().hex[:6]}@gmail.com"),
        )
        assert res.status_code == 400
        assert res.json()["error"]["code"] == "INVALID_UNIVERSITY_EMAIL"

        login_fail = await client.post(
            "/api/v1/auth/login",
            json={"email": f"nonexistent_{uuid.uuid4().hex[:6]}@msrit.edu", "password": "wrong"},
        )
        assert login_fail.status_code == 401
        assert login_fail.json()["error"]["code"] == "INVALID_CREDENTIALS"

        unauth_res = await client.get("/api/v1/users/me")
        assert unauth_res.status_code == 401
        assert unauth_res.json()["error"]["code"] == "UNAUTHORIZED"

        expired_token = create_access_token(
            subject=uuid.uuid4(),
            expires_delta=timedelta(seconds=-10),
        )
        expired_res = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert expired_res.status_code == 401
        assert expired_res.json()["error"]["code"] == "TOKEN_EXPIRED"


@pytest.mark.asyncio
async def test_wrong_password_rejected_and_hashing_remains_secure() -> None:
    """A wrong password is rejected; the stored hash verifies only the true password."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        email = f"pwcheck_{uuid.uuid4().hex[:8]}@msrit.edu"
        await register_and_login(client, email, password="TruePassword123!")

        wrong_res = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "FalsePassword456!"},
        )
        assert wrong_res.status_code == 401
        assert wrong_res.json()["error"]["code"] == "INVALID_CREDENTIALS"

        db = SessionLocal()
        user_db = db.query(User).filter(User.email == email).first()
        assert user_db.hashed_password.startswith("$2")
        assert not verify_password("wrong", user_db.hashed_password)
        assert verify_password("TruePassword123!", user_db.hashed_password)
        db.close()


@pytest.mark.asyncio
async def test_auth_config_has_no_email_delivery_contract() -> None:
    """The public auth config exposes university domains and password rules only."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        res = await client.get("/api/v1/auth/config")
        assert res.status_code == 200
        config = res.json()
        assert config["allowed_email_domains"] == ["msrit.edu"]
        assert config["password_min_length"] == 8
        # No verification/email-delivery keys may leak into the public contract
        assert "verification_code_available" not in config
        assert "email_delivery_available" not in config
