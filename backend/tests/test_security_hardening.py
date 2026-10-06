import uuid
from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_storage_service
from app.core.config import Settings
from app.core.limiter import rate_limiter
from app.core.security import create_access_token, create_refresh_token
from app.db.session import SessionLocal
from app.main import app
from app.models.category import Category


@pytest.fixture
def mock_storage():
    """Mock storage service for upload validation tests."""
    mock = MagicMock()
    mock.bucket_name = "ramaiahmart-media"
    mock.public_endpoint_url = "http://localhost:9100"
    mock.presigned_expiration = 900

    def mock_build_key(post_id: uuid.UUID, content_type: str) -> str:
        ext = ".jpg" if "jpeg" in content_type or "jpg" in content_type else ".png"
        return f"posts/{post_id}/{uuid.uuid4()}{ext}"

    mock.build_safe_storage_key.side_effect = mock_build_key
    mock.generate_upload_url.return_value = "http://localhost:9100/upload"
    mock.generate_download_url.return_value = "http://localhost:9100/download"
    mock.object_exists.return_value = True
    mock.get_object_metadata.return_value = {
        "content_length": 2048,
        "content_type": "image/jpeg",
    }
    mock.get_object_header.return_value = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00"
    return mock


@pytest.fixture
def test_category() -> Category:
    session = SessionLocal()
    slug = f"sec_cat_{uuid.uuid4().hex[:6]}"
    cat = Category(name=f"Security Cat {uuid.uuid4().hex[:6]}", slug=slug, is_active=True)
    session.add(cat)
    session.commit()
    session.refresh(cat)
    session.close()
    return cat


async def create_test_user(client: AsyncClient, prefix: str) -> tuple[str, str, uuid.UUID]:
    email = f"{prefix}_{uuid.uuid4().hex[:8]}@msrit.edu"
    password = "SecPassword123!"
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "name": f"User {prefix}",
            "accepted_terms": True,
            "accepted_privacy": True,
        },
    )
    assert reg_res.status_code == 201

    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]

    me_res = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200
    user_id = uuid.UUID(me_res.json()["id"])
    return email, token, user_id


# ==============================================================================
# 1. AUTHENTICATION SECURITY & TOKEN VALIDATION
# ==============================================================================


@pytest.mark.asyncio
async def test_auth_rate_limiting():
    """Verify in-memory rate limiting triggers 429 on login spam."""
    rate_limiter.clear()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Trigger rate limit for login with failed attempts
        email = f"spam_{uuid.uuid4().hex[:6]}@msrit.edu"
        for _ in range(10):
            res = await client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": "WrongPassword!"},
            )
            if res.status_code == 429:
                assert "Retry-After" in res.headers
                assert res.json()["error"]["code"] == "RATE_LIMITED"
                break
        else:
            pytest.fail("Expected 429 rate limit after repeated login attempts")


@pytest.mark.asyncio
async def test_auth_token_security():
    """Verify rejection of invalid, expired, or wrong-type JWT tokens."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Invalid signature / random token
        res_invalid = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer invalid.jwt.token"},
        )
        assert res_invalid.status_code == 401
        assert res_invalid.json()["error"]["code"] == "TOKEN_INVALID"

        # 2. Expired access token
        user_id = uuid.uuid4()
        expired_token = create_access_token(
            subject=user_id,
            expires_delta=timedelta(seconds=-60),
        )
        res_expired = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert res_expired.status_code == 401
        assert res_expired.json()["error"]["code"] == "TOKEN_EXPIRED"

        # 3. Wrong token type: sending a refresh_token to an access-token endpoint
        refresh_token = create_refresh_token(subject=user_id)
        res_wrong_type = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {refresh_token}"},
        )
        assert res_wrong_type.status_code == 401
        assert res_wrong_type.json()["error"]["code"] == "TOKEN_INVALID"
        assert res_wrong_type.json()["error"]["message"] == "Invalid token type."


# ==============================================================================
# 2. AUTHORIZATION & IDOR ENFORCEMENT
# ==============================================================================


@pytest.mark.asyncio
async def test_post_authorization_boundaries(test_category: Category):
    """User B must not be able to edit, delete, publish, or close User A's post."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        _, token_a, _ = await create_test_user(client, "author_a")
        _, token_b, _ = await create_test_user(client, "attacker_b")

        # User A creates a post
        create_res = await client.post(
            "/api/v1/posts",
            headers={"Authorization": f"Bearer {token_a}"},
            json={
                "type": "OFFER",
                "category_id": str(test_category.id),
                "title": "Textbook for User A",
                "description": "Calculus textbook edition 8",
                "price": 450,
            },
        )
        assert create_res.status_code == 201
        post_id = create_res.json()["id"]

        # User B attempts to edit User A's post -> 403 Forbidden
        edit_res = await client.patch(
            f"/api/v1/posts/{post_id}",
            headers={"Authorization": f"Bearer {token_b}"},
            json={"title": "Hacked Title"},
        )
        assert edit_res.status_code == 403
        assert edit_res.json()["error"]["code"] == "FORBIDDEN_NOT_AUTHOR"

        # User B attempts to publish User A's post -> 403 Forbidden
        pub_res = await client.post(
            f"/api/v1/posts/{post_id}/publish",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert pub_res.status_code == 403
        assert pub_res.json()["error"]["code"] == "FORBIDDEN_NOT_AUTHOR"

        # User A publishes post
        await client.post(
            f"/api/v1/posts/{post_id}/publish",
            headers={"Authorization": f"Bearer {token_a}"},
        )

        # User B attempts to close User A's post -> 403 Forbidden
        close_res = await client.post(
            f"/api/v1/posts/{post_id}/close",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert close_res.status_code == 403
        assert close_res.json()["error"]["code"] == "FORBIDDEN_NOT_AUTHOR"

        # User B attempts to delete User A's post -> 403 Forbidden
        del_res = await client.delete(
            f"/api/v1/posts/{post_id}",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert del_res.status_code == 403
        assert del_res.json()["error"]["code"] == "FORBIDDEN_NOT_AUTHOR"


@pytest.mark.asyncio
async def test_conversation_authorization_boundaries(test_category: Category):
    """User C must not be able to read, send to, or close conversations between A and B."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        _, token_a, _ = await create_test_user(client, "seller")
        _, token_b, _ = await create_test_user(client, "buyer")
        _, token_c, _ = await create_test_user(client, "eavesdropper")

        # Seller publishes post
        post_res = await client.post(
            "/api/v1/posts",
            headers={"Authorization": f"Bearer {token_a}"},
            json={
                "type": "OFFER",
                "category_id": str(test_category.id),
                "title": "Secret Item",
                "description": "Private trade item",
                "price": 100,
            },
        )
        post_id = post_res.json()["id"]
        await client.post(
            f"/api/v1/posts/{post_id}/publish",
            headers={"Authorization": f"Bearer {token_a}"},
        )

        # Buyer initiates conversation
        conv_res = await client.post(
            f"/api/v1/posts/{post_id}/conversations",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert conv_res.status_code == 200
        conv_id = conv_res.json()["id"]

        # Buyer sends a message
        msg_res = await client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            headers={"Authorization": f"Bearer {token_b}"},
            json={"content": "Hello, is this item available?"},
        )
        assert msg_res.status_code == 201

        # User C attempts to view conversation details -> 403 Forbidden
        res_get_c = await client.get(
            f"/api/v1/conversations/{conv_id}",
            headers={"Authorization": f"Bearer {token_c}"},
        )
        assert res_get_c.status_code == 403
        assert res_get_c.json()["error"]["code"] == "FORBIDDEN_NOT_PARTICIPANT"

        # User C attempts to read messages -> 403 Forbidden
        res_read_c = await client.get(
            f"/api/v1/conversations/{conv_id}/messages",
            headers={"Authorization": f"Bearer {token_c}"},
        )
        assert res_read_c.status_code == 403
        assert res_read_c.json()["error"]["code"] == "FORBIDDEN_NOT_PARTICIPANT"

        # User C attempts to send a message -> 403 Forbidden
        res_send_c = await client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            headers={"Authorization": f"Bearer {token_c}"},
            json={"content": "I am eavesdropping!"},
        )
        assert res_send_c.status_code == 403
        assert res_send_c.json()["error"]["code"] == "FORBIDDEN_NOT_PARTICIPANT"

        # User C attempts to close the conversation -> 403 Forbidden
        res_close_c = await client.post(
            f"/api/v1/conversations/{conv_id}/close",
            headers={"Authorization": f"Bearer {token_c}"},
        )
        assert res_close_c.status_code == 403
        assert res_close_c.json()["error"]["code"] == "FORBIDDEN_NOT_PARTICIPANT"


@pytest.mark.asyncio
async def test_report_authorization_boundaries(test_category: Category):
    """User B must not be able to retrieve User A's submitted report."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        _, token_author, _ = await create_test_user(client, "listing_author")
        _, token_reporter, _ = await create_test_user(client, "reporter_a")
        _, token_other, _ = await create_test_user(client, "stranger_b")

        # Create published post
        post_res = await client.post(
            "/api/v1/posts",
            headers={"Authorization": f"Bearer {token_author}"},
            json={
                "type": "OFFER",
                "category_id": str(test_category.id),
                "title": "Item to Report",
                "description": "Item description",
                "price": 200,
            },
        )
        post_id = post_res.json()["id"]
        await client.post(
            f"/api/v1/posts/{post_id}/publish",
            headers={"Authorization": f"Bearer {token_author}"},
        )

        # Reporter A reports post
        rep_res = await client.post(
            "/api/v1/reports",
            headers={"Authorization": f"Bearer {token_reporter}"},
            json={
                "post_id": post_id,
                "reason": "SCAM_OR_MISLEADING",
                "description": "Suspected fraudulent listing",
            },
        )
        assert rep_res.status_code == 201
        report_id = rep_res.json()["id"]

        # Reporter A can view own report
        rep_self = await client.get(
            f"/api/v1/reports/{report_id}",
            headers={"Authorization": f"Bearer {token_reporter}"},
        )
        assert rep_self.status_code == 200

        # Stranger B cannot view Reporter A's report -> 403 Forbidden
        rep_stranger = await client.get(
            f"/api/v1/reports/{report_id}",
            headers={"Authorization": f"Bearer {token_other}"},
        )
        assert rep_stranger.status_code == 403
        assert rep_stranger.json()["error"]["code"] == "FORBIDDEN_NOT_REPORTER"


@pytest.mark.asyncio
async def test_media_authorization_and_validation(test_category: Category, mock_storage):
    """Test media ownership and upload validation boundaries."""
    app.dependency_overrides[get_storage_service] = lambda: mock_storage
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            _, token_a, _ = await create_test_user(client, "owner_a")
            _, token_b, _ = await create_test_user(client, "intruder_b")

            # Owner A creates post
            post_res = await client.post(
                "/api/v1/posts",
                headers={"Authorization": f"Bearer {token_a}"},
                json={
                    "type": "OFFER",
                    "category_id": str(test_category.id),
                    "title": "Post for Media",
                    "description": "Post with media",
                    "price": 300,
                },
            )
            post_id = post_res.json()["id"]

            # User B attempts to get upload URL for User A's post -> 403 Forbidden
            res_unauth_upload = await client.post(
                "/api/v1/media/upload-url",
                headers={"Authorization": f"Bearer {token_b}"},
                json={
                    "post_id": post_id,
                    "content_type": "image/jpeg",
                    "file_size": 1024,
                },
            )
            assert res_unauth_upload.status_code == 403
            assert res_unauth_upload.json()["error"]["code"] == "FORBIDDEN_NOT_AUTHOR"

            # Owner A requests valid upload URL
            upload_url_res = await client.post(
                "/api/v1/media/upload-url",
                headers={"Authorization": f"Bearer {token_a}"},
                json={
                    "post_id": post_id,
                    "content_type": "image/jpeg",
                    "file_size": 1024,
                },
            )
            assert upload_url_res.status_code == 200
            storage_key = upload_url_res.json()["storage_key"]

            # User B attempts to complete upload for User A's post -> 403 Forbidden
            res_unauth_complete = await client.post(
                "/api/v1/media/complete",
                headers={"Authorization": f"Bearer {token_b}"},
                json={
                    "post_id": post_id,
                    "storage_key": storage_key,
                    "content_type": "image/jpeg",
                    "position": 0,
                },
            )
            assert res_unauth_complete.status_code == 403
            assert res_unauth_complete.json()["error"]["code"] == "FORBIDDEN_NOT_AUTHOR"

            # Tampered storage key prefix -> 400 Bad Request
            res_tampered_key = await client.post(
                "/api/v1/media/complete",
                headers={"Authorization": f"Bearer {token_a}"},
                json={
                    "post_id": post_id,
                    "storage_key": f"posts/{uuid.uuid4()}/other.jpg",
                    "content_type": "image/jpeg",
                    "position": 0,
                },
            )
            assert res_tampered_key.status_code == 400
            assert res_tampered_key.json()["error"]["code"] == "INVALID_STORAGE_KEY"

            # Owner completes media upload
            complete_res = await client.post(
                "/api/v1/media/complete",
                headers={"Authorization": f"Bearer {token_a}"},
                json={
                    "post_id": post_id,
                    "storage_key": storage_key,
                    "content_type": "image/jpeg",
                    "position": 0,
                },
            )
            assert complete_res.status_code == 201
            media_id = complete_res.json()["id"]

            # User B attempts to delete User A's media -> 403 Forbidden
            del_unauth = await client.delete(
                f"/api/v1/media/{media_id}",
                headers={"Authorization": f"Bearer {token_b}"},
            )
            assert del_unauth.status_code == 403
            assert del_unauth.json()["error"]["code"] == "FORBIDDEN_NOT_AUTHOR"
    finally:
        app.dependency_overrides.clear()


# ==============================================================================
# 3. XSS PAYLOAD IMMUNITY & TEXT PRESERVATION
# ==============================================================================


@pytest.mark.asyncio
async def test_xss_payloads_rendered_as_verbatim_text(test_category: Category):
    """Verify that script tags and HTML injection payloads are preserved as literal text."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        _, token_a, _ = await create_test_user(client, "xss_tester")

        xss_title = "<script>alert('xss-title')</script>"
        xss_description = '<img src=x onerror=alert("xss-desc")> & <p>Hello World</p>'

        post_res = await client.post(
            "/api/v1/posts",
            headers={"Authorization": f"Bearer {token_a}"},
            json={
                "type": "OFFER",
                "category_id": str(test_category.id),
                "title": xss_title,
                "description": xss_description,
                "price": 100,
            },
        )
        assert post_res.status_code == 201
        data = post_res.json()
        assert data["title"] == xss_title
        assert data["description"] == xss_description

        # Profile bio update with HTML payload
        xss_bio = "<script>document.location='http://attacker.com'</script>"
        patch_res = await client.patch(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"bio": xss_bio},
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["bio"] == xss_bio


# ==============================================================================
# 4. PRODUCTION SETTINGS INTEGRITY CHECKS
# ==============================================================================


def test_production_settings_validation_rules():
    """Verify production settings validator enforces all critical boundaries."""
    # 1. Dev DB url rejected
    with pytest.raises(ValueError, match="Cannot use default development postgres credentials"):
        Settings(
            APP_ENV="production",
            JWT_SECRET_KEY="a" * 32,
            DEBUG=False,
            DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/ramaiahmart",
            AWS_ACCESS_KEY_ID="prod-key",
            AWS_SECRET_ACCESS_KEY="prod-secret",
        )

    # 2. Minioadmin credentials rejected
    with pytest.raises(ValueError, match="Cannot use default development minioadmin credentials"):
        Settings(
            APP_ENV="production",
            JWT_SECRET_KEY="a" * 32,
            DEBUG=False,
            DATABASE_URL="postgresql+psycopg://prod:pass@db.example.com:5432/db",
            AWS_ACCESS_KEY_ID="minioadmin",
            AWS_SECRET_ACCESS_KEY="minioadmin",
        )

    # 3. Wildcard CORS origin rejected
    with pytest.raises(ValueError, match=r"Wildcard '\*' CORS origins are not permitted"):
        Settings(
            APP_ENV="production",
            JWT_SECRET_KEY="a" * 32,
            DEBUG=False,
            DATABASE_URL="postgresql+psycopg://prod:pass@db.example.com:5432/db",
            AWS_ACCESS_KEY_ID="prod-key",
            AWS_SECRET_ACCESS_KEY="prod-secret",
            CORS_ORIGINS=["*"],
        )

    # 4. AI external provider enabled without API key rejected
    with pytest.raises(ValueError, match="AI_TEXT_API_KEY"):
        Settings(
            APP_ENV="production",
            JWT_SECRET_KEY="a" * 32,
            DEBUG=False,
            DATABASE_URL="postgresql+psycopg://prod:pass@db.example.com:5432/db",
            AWS_ACCESS_KEY_ID="prod-key",
            AWS_SECRET_ACCESS_KEY="prod-secret",
            AI_TEXT_PROVIDER="groq",
            AI_TEXT_API_KEY=None,
            AI_PROVIDER_API_KEY=None,
        )
