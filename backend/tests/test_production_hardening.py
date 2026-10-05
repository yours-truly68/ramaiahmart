import uuid
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.security import create_access_token
from app.db.session import SessionLocal, get_db
from app.main import app
from app.models.category import Category
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.moderation import ModerationDecision, ModerationResult
from app.models.post import Post, PostStatus, PostType
from app.models.user import User


@pytest.fixture
def hardening_setup():
    """Setup test fixture with users, categories, and tokens."""
    db = SessionLocal()
    try:
        owner = User(
            email=f"owner_hard_{uuid.uuid4().hex[:8]}@ramaiah.edu",
            name="Hardening Owner",
            hashed_password="hashed_pw_test_123",
            university_verified=True,
            is_active=True,
        )
        buyer = User(
            email=f"buyer_hard_{uuid.uuid4().hex[:8]}@ramaiah.edu",
            name="Hardening Buyer",
            hashed_password="hashed_pw_test_123",
            university_verified=True,
            is_active=True,
        )
        category = Category(
            name=f"Hardening Cat {uuid.uuid4().hex[:6]}",
            slug=f"hard-cat-{uuid.uuid4().hex[:6]}",
            is_active=True,
        )
        db.add_all([owner, buyer, category])
        db.commit()
        db.refresh(owner)
        db.refresh(buyer)
        db.refresh(category)

        post = Post(
            author_id=owner.id,
            category_id=category.id,
            type=PostType.OFFER,
            title="Production Test Textbook",
            description="Engineering Mathematics clean copy.",
            price=Decimal("450.00"),
            status=PostStatus.PUBLISHED,
        )
        db.add(post)
        db.commit()
        db.refresh(post)

        owner_token = create_access_token(subject=str(owner.id))
        buyer_token = create_access_token(subject=str(buyer.id))

        yield {
            "owner": owner,
            "buyer": buyer,
            "category": category,
            "post": post,
            "owner_token": owner_token,
            "buyer_token": buyer_token,
        }
    finally:
        db.close()


@pytest.mark.asyncio
async def test_security_headers_and_request_id():
    """Verify that every HTTP response carries strict security headers and correlation ID."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Standard request without incoming ID
        res = await client.get("/api/v1/health")
        assert res.status_code == 200
        assert res.headers.get("X-Content-Type-Options") == "nosniff"
        assert res.headers.get("X-Frame-Options") == "DENY"
        assert res.headers.get("X-XSS-Protection") == "1; mode=block"
        assert res.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
        assert "X-Request-ID" in res.headers
        assert len(res.headers["X-Request-ID"]) > 10

        # 2. Client-provided X-Request-ID is preserved
        custom_id = f"req-{uuid.uuid4().hex}"
        res_custom = await client.get("/api/v1/health", headers={"X-Request-ID": custom_id})
        assert res_custom.status_code == 200
        assert res_custom.headers.get("X-Request-ID") == custom_id


@pytest.mark.asyncio
async def test_cors_policy():
    """Verify CORS preflight and access control configuration."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Allowed Origin
        headers = {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        }
        res = await client.options("/api/v1/posts", headers=headers)
        assert res.status_code == 200
        assert res.headers.get("access-control-allow-origin") == "http://localhost:3000"
        assert res.headers.get("access-control-allow-credentials") == "true"

        # 2. Disallowed Origin
        headers_disallowed = {
            "Origin": "https://malicious-site.com",
            "Access-Control-Request-Method": "POST",
        }
        res_disallowed = await client.options("/api/v1/posts", headers=headers_disallowed)
        assert res_disallowed.headers.get("access-control-allow-origin") != (
            "https://malicious-site.com"
        )


@pytest.mark.asyncio
async def test_unhandled_exception_fail_safe():
    """Verify that unhandled server errors return unified 500 without leaking stack traces."""

    def broken_endpoint():
        raise RuntimeError("Unexpected internal crash test")

    app.add_api_route("/api/v1/test-crash", broken_endpoint, methods=["GET"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/test-crash")
        assert res.status_code == 500
        data = res.json()
        assert data["error"]["code"] == "INTERNAL_SERVER_ERROR"
        assert "An unexpected error occurred" in data["error"]["message"]
        # Must not leak Python runtime crash trace in response payload
        assert "RuntimeError" not in data["error"]["message"]
        assert "X-Request-ID" in res.headers


@pytest.mark.asyncio
async def test_sql_injection_defense(hardening_setup):
    """Verify parameterized queries prevent SQL injection payloads from executing."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. SQL injection in category slug filter
        sqli_slug = "' OR '1'='1"
        res_slug = await client.get(f"/api/v1/posts?category_slug={sqli_slug}")
        assert res_slug.status_code == 200
        # Should return 0 items rather than all items in DB
        assert len(res_slug.json()["items"]) == 0

        # 2. SQL injection in type filter
        sqli_type = "OFFER' OR '1'='1"
        res_type = await client.get(f"/api/v1/posts?type={sqli_type}")
        # Enum validation in FastAPI rejects invalid string with 422
        assert res_type.status_code == 422
        assert res_type.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_database_rollback_on_session_error():
    """Verify get_db generator rolls back active transaction on unhandled exception."""
    db_gen = get_db()
    session = next(db_gen)

    try:
        # Add an invalid object or trigger exception
        session.add(
            User(
                email="will_fail_rollback@ramaiah.edu",
                name="Rollback Test",
                hashed_password=None,  # Not null violation
            )
        )
        with pytest.raises(ValueError, match="Simulated route handler exception"):
            try:
                raise ValueError("Simulated route handler exception")
            except Exception as exc:
                db_gen.throw(exc)
    finally:
        pass

    # Verify session was rolled back and nothing was committed to DB
    check_session = SessionLocal()
    try:
        user = check_session.scalar(
            select(User).where(User.email == "will_fail_rollback@ramaiah.edu")
        )
        assert user is None
    finally:
        check_session.close()


def test_conversation_cascade_and_security_invariants(hardening_setup):
    """Verify conversation constraints, cascade deletion, and message isolation."""
    db = SessionLocal()
    try:
        post = db.scalar(select(Post).where(Post.id == hardening_setup["post"].id))
        owner = db.scalar(select(User).where(User.id == hardening_setup["owner"].id))
        buyer = db.scalar(select(User).where(User.id == hardening_setup["buyer"].id))
        assert post is not None
        assert owner is not None
        assert buyer is not None

        # 1. Conversation initiator cannot be the post owner
        self_conv = Conversation(
            post_id=post.id,
            initiator_id=owner.id,
            owner_id=owner.id,
        )
        db.add(self_conv)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

        # 2. Legitimate conversation creation between buyer and owner
        valid_conv = Conversation(
            post_id=post.id,
            initiator_id=buyer.id,
            owner_id=owner.id,
        )
        db.add(valid_conv)
        db.commit()
        db.refresh(valid_conv)

        # 3. Prevent duplicate conversation for same post by same initiator
        dup_conv = Conversation(
            post_id=post.id,
            initiator_id=buyer.id,
            owner_id=owner.id,
        )
        db.add(dup_conv)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

        # 4. Add message to conversation
        msg = Message(
            conversation_id=valid_conv.id,
            sender_id=buyer.id,
            content="Hi! Is this textbook still available?",
        )
        db.add(msg)

        # Add moderation result to post
        mod = ModerationResult(
            post_id=post.id,
            decision=ModerationDecision.APPROVE,
            risk_score=0.01,
            reason_codes=["SAFE"],
            provider="test",
            model="v1",
        )
        db.add(mod)
        db.commit()

        # 5. Cascade deletion: Deleting the post must cascade and remove conversation & messages
        db.delete(post)
        db.commit()

        # Confirm post, conversation, and message are completely cleaned up
        conv_check = db.scalar(select(Conversation).where(Conversation.id == valid_conv.id))
        msg_check = db.scalar(select(Message).where(Message.id == msg.id))
        mod_check = db.scalar(select(ModerationResult).where(ModerationResult.id == mod.id))

        assert conv_check is None
        assert msg_check is None
        assert mod_check is None
    finally:
        db.close()
