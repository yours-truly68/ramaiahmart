import uuid
from datetime import timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token, verify_password
from app.db.session import SessionLocal
from app.main import app
from app.models.user import User


@pytest.mark.asyncio
async def test_auth_registration_and_verification_flow() -> None:
    """Test full registration, OTP verification, and login flow."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        unique_email = f"student_{uuid.uuid4().hex[:8]}@ramaiah.edu"

        # 1. Register
        reg_payload = {
            "email": unique_email,
            "password": "SecurePassword123!",
            "name": "Test Student",
            "accepted_terms": True,
            "accepted_privacy": True,
        }
        reg_res = await client.post("/api/v1/auth/register", json=reg_payload)
        assert reg_res.status_code == 201
        reg_data = reg_res.json()
        assert reg_data["email"] == unique_email
        assert reg_data["verification_code"] is not None
        code = reg_data["verification_code"]

        # Verify password is not plaintext in database
        db = SessionLocal()
        user_db = db.query(User).filter(User.email == unique_email).first()
        assert user_db is not None
        assert user_db.hashed_password != "SecurePassword123!"
        assert verify_password("SecurePassword123!", user_db.hashed_password)
        assert user_db.university_verified is False
        db.close()

        # 2. Reject duplicate registration
        dup_res = await client.post("/api/v1/auth/register", json=reg_payload)
        assert dup_res.status_code == 409
        assert dup_res.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"

        # 3. Verify Email
        verify_res = await client.post(
            "/api/v1/auth/verify",
            json={"email": unique_email, "code": code},
        )
        assert verify_res.status_code == 200
        assert verify_res.json()["university_verified"] is True

        # Check DB state
        db = SessionLocal()
        user_db = db.query(User).filter(User.email == unique_email).first()
        assert user_db.university_verified is True
        db.close()

        # 4. Login
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": unique_email, "password": "SecurePassword123!"},
        )
        assert login_res.status_code == 200
        tokens = login_res.json()
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens["token_type"] == "bearer"

        # 5. Access protected /users/me
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        me_res = await client.get("/api/v1/users/me", headers=headers)
        assert me_res.status_code == 200
        assert me_res.json()["email"] == unique_email
        assert me_res.json()["university_verified"] is True

        # 6. Update own profile via PATCH /users/me
        patch_res = await client.patch(
            "/api/v1/users/me",
            headers=headers,
            json={"bio": "CS student passionate about open source", "name": "Updated Name"},
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["bio"] == "CS student passionate about open source"
        assert patch_res.json()["name"] == "Updated Name"

        # 7. Refresh token
        refresh_res = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert refresh_res.status_code == 200
        assert "access_token" in refresh_res.json()

        # 8. Logout
        logout_res = await client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert logout_res.status_code == 200

        # Refresh with revoked token must now fail
        revoked_refresh = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert revoked_refresh.status_code == 401
        assert revoked_refresh.json()["error"]["code"] == "TOKEN_REVOKED_OR_EXPIRED"


@pytest.mark.asyncio
async def test_auth_invalid_credentials_and_expired_tokens() -> None:
    """Test security boundaries: invalid credentials, invalid domain, expired token."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Invalid email domain
        res = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "hacker@unknown-domain.com",
                "password": "Password123!",
                "name": "Attacker",
                "accepted_terms": True,
                "accepted_privacy": True,
            },
        )
        assert res.status_code == 400
        assert res.json()["error"]["code"] == "INVALID_UNIVERSITY_EMAIL"

        # Invalid login
        login_fail = await client.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent@ramaiah.edu", "password": "wrong"},
        )
        assert login_fail.status_code == 401
        assert login_fail.json()["error"]["code"] == "INVALID_CREDENTIALS"

        # Unauthenticated request to protected endpoint
        unauth_res = await client.get("/api/v1/users/me")
        assert unauth_res.status_code == 401
        assert unauth_res.json()["error"]["code"] == "UNAUTHORIZED"

        # Expired access token
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
