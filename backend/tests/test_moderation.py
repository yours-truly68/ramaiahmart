import uuid
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.security import create_access_token
from app.db.session import SessionLocal
from app.main import app
from app.models.category import Category
from app.models.moderation import ModerationDecision, ModerationResult
from app.models.post import Post, PostStatus, PostType
from app.models.user import User
from app.services.moderation import (
    MockModerationProvider,
    ModerationInput,
)


@pytest.fixture
def moderation_setup():
    """Setup test user, category, and auth token."""
    db = SessionLocal()
    try:
        user = User(
            email=f"mod_user_{uuid.uuid4().hex[:8]}@msrit.edu",
            name="Moderation Tester",
            hashed_password="hashed_pw_test_123",
            university_verified=True,
            is_active=True,
        )
        category = Category(
            name=f"Books & Notes {uuid.uuid4().hex[:6]}",
            slug=f"books-notes-{uuid.uuid4().hex[:6]}",
            is_active=True,
        )
        db.add_all([user, category])
        db.commit()
        db.refresh(user)
        db.refresh(category)

        token = create_access_token(subject=str(user.id))

        yield {
            "user": user,
            "category": category,
            "token": token,
        }
    finally:
        db.close()


def test_mock_provider_deterministic_behavior():
    """Unit test deterministic evaluation of all risk categories."""
    provider = MockModerationProvider()

    # 1. Prohibited goods
    eval_drug = provider.evaluate_post(
        ModerationInput(title="Selling prescription adderall", description="Cheap prices")
    )
    assert eval_drug.decision == ModerationDecision.REJECT
    assert "PROHIBITED_GOODS" in eval_drug.reason_codes
    assert eval_drug.risk_score >= 0.9

    # 2. Prohibited services
    eval_cheat = provider.evaluate_post(
        ModerationInput(title="Final Exam leak available", description="Guaranteed A grade")
    )
    assert eval_cheat.decision == ModerationDecision.REJECT
    assert "PROHIBITED_SERVICES" in eval_cheat.reason_codes

    # 3. Scams & fraud
    eval_scam = provider.evaluate_post(
        ModerationInput(
            title="iPhone 15",
            description="Contact via Telegram for wire transfer only",
        )
    )
    assert eval_scam.decision == ModerationDecision.REJECT
    assert "SCAM_FRAUD" in eval_scam.reason_codes

    # 4. Abusive content
    eval_abuse = provider.evaluate_post(
        ModerationInput(title="Terrible roommate", description="Hate speech and harassment text")
    )
    assert eval_abuse.decision == ModerationDecision.REJECT
    assert "ABUSIVE_CONTENT" in eval_abuse.reason_codes

    # 5. Sexual content
    eval_sexual = provider.evaluate_post(
        ModerationInput(title="Listing", description="NSFW adult services offered")
    )
    assert eval_sexual.decision == ModerationDecision.REJECT
    assert "SEXUAL_CONTENT" in eval_sexual.reason_codes

    # 6. Spam
    eval_spam = provider.evaluate_post(
        ModerationInput(title="Free money now", description="Earn 5000 daily with zero work")
    )
    assert eval_spam.decision == ModerationDecision.REJECT
    assert "SPAM" in eval_spam.reason_codes

    # 7. Unrelated / Misleading image
    eval_image = provider.evaluate_post(
        ModerationInput(
            title="Textbook",
            description="Engineering Maths textbook",
            image_keys=["posts/123/meme_cat.jpg"],
        )
    )
    assert eval_image.decision == ModerationDecision.REJECT
    assert "UNRELATED_IMAGE" in eval_image.reason_codes

    # 8. Ambiguous / Review required
    eval_review = provider.evaluate_post(
        ModerationInput(
            title="Luxury Watch",
            description="Expensive luxury watch with suspicious serial number",
        )
    )
    assert eval_review.decision == ModerationDecision.REVIEW
    assert "MANUAL_REVIEW_REQUIRED" in eval_review.reason_codes

    # 9. Clean listing -> APPROVE
    eval_clean = provider.evaluate_post(
        ModerationInput(
            title="Data Structures and Algorithms Textbook",
            description="Used condition Cormen Leiserson textbook with clean notes.",
        )
    )
    assert eval_clean.decision == ModerationDecision.APPROVE
    assert "SAFE_LISTING" in eval_clean.reason_codes
    assert eval_clean.risk_score < 0.1


@pytest.mark.asyncio
async def test_moderation_approved_post(moderation_setup):
    """Test clean post passing moderation and becoming PUBLISHED."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {moderation_setup['token']}"}

        # 1. Create clean draft post
        create_res = await client.post(
            "/api/v1/posts",
            headers=headers,
            json={
                "type": "OFFER",
                "category_id": str(moderation_setup["category"].id),
                "title": "Clean Scientific Calculator",
                "description": (
                    "Casio fx-991EX in great condition, useful for 1st year engineering."
                ),
                "price": "600.00",
            },
        )
        assert create_res.status_code == 201
        post_id = create_res.json()["id"]

        # 2. Publish post -> should be APPROVED and PUBLISHED
        pub_res = await client.post(f"/api/v1/posts/{post_id}/publish", headers=headers)
        assert pub_res.status_code == 200
        post_data = pub_res.json()
        assert post_data["status"] == "PUBLISHED"
        assert post_data["published_at"] is not None

        # 3. Appears in public feed
        feed_res = await client.get("/api/v1/posts")
        assert feed_res.status_code == 200
        post_ids = [p["id"] for p in feed_res.json()["items"]]
        assert post_id in post_ids


@pytest.mark.asyncio
async def test_moderation_review_post(moderation_setup):
    """Test ambiguous post routed to REVIEW staying in PENDING_REVIEW and not in public feed."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {moderation_setup['token']}"}

        create_res = await client.post(
            "/api/v1/posts",
            headers=headers,
            json={
                "type": "OFFER",
                "category_id": str(moderation_setup["category"].id),
                "title": "Expensive luxury watch needs_review",
                "description": "Brand new luxury item without original receipt.",
                "price": "50000.00",
            },
        )
        assert create_res.status_code == 201
        post_id = create_res.json()["id"]

        # Publish triggers review
        pub_res = await client.post(f"/api/v1/posts/{post_id}/publish", headers=headers)
        assert pub_res.status_code == 200
        assert pub_res.json()["status"] == "PENDING_REVIEW"
        assert pub_res.json()["published_at"] is None

        # Must NOT appear in public feed
        feed_res = await client.get("/api/v1/posts")
        post_ids = [p["id"] for p in feed_res.json()["items"]]
        assert post_id not in post_ids


@pytest.mark.asyncio
async def test_moderation_rejected_post(moderation_setup):
    """Test prohibited post being REJECTED and excluded from public feed."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {moderation_setup['token']}"}

        create_res = await client.post(
            "/api/v1/posts",
            headers=headers,
            json={
                "type": "OFFER",
                "category_id": str(moderation_setup["category"].id),
                "title": "Cheap cigarettes and alcohol",
                "description": "Party supplies delivery on campus.",
                "price": "300.00",
            },
        )
        assert create_res.status_code == 201
        post_id = create_res.json()["id"]

        # Publish triggers rejection
        pub_res = await client.post(f"/api/v1/posts/{post_id}/publish", headers=headers)
        assert pub_res.status_code == 200
        assert pub_res.json()["status"] == "REJECTED"
        assert pub_res.json()["published_at"] is None

        # Must NOT appear in public feed
        feed_res = await client.get("/api/v1/posts")
        post_ids = [p["id"] for p in feed_res.json()["items"]]
        assert post_id not in post_ids


@pytest.mark.asyncio
async def test_moderation_provider_failure_fails_closed(moderation_setup):
    """Test that if the moderation provider crashes or fails, system fails closed to REVIEW."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {moderation_setup['token']}"}

        create_res = await client.post(
            "/api/v1/posts",
            headers=headers,
            json={
                "type": "OFFER",
                "category_id": str(moderation_setup["category"].id),
                "title": "Clean item with provider_crash",
                "description": "Simulates a provider failure or timeout during evaluation.",
                "price": "100.00",
            },
        )
        assert create_res.status_code == 201
        post_id = create_res.json()["id"]

        # When provider fails, post must NOT be published; it must fail closed to PENDING_REVIEW
        pub_res = await client.post(f"/api/v1/posts/{post_id}/publish", headers=headers)
        assert pub_res.status_code == 200
        assert pub_res.json()["status"] == "PENDING_REVIEW"
        assert pub_res.json()["published_at"] is None

        # Verify fallback moderation record in database
        db = SessionLocal()
        try:
            mod_record = db.scalar(
                select(ModerationResult)
                .where(ModerationResult.post_id == uuid.UUID(post_id))
                .order_by(ModerationResult.created_at.desc())
            )
            assert mod_record is not None
            assert mod_record.decision == ModerationDecision.REVIEW
            assert "PROVIDER_FAILURE_FALLBACK" in mod_record.reason_codes
            assert mod_record.provider == "system_fallback"
        finally:
            db.close()


@pytest.mark.asyncio
async def test_moderation_result_persistence(moderation_setup):
    """Verify that every moderation decision persists structured metadata without raw AI."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {moderation_setup['token']}"}

        create_res = await client.post(
            "/api/v1/posts",
            headers=headers,
            json={
                "type": "OFFER",
                "category_id": str(moderation_setup["category"].id),
                "title": "Semester 3 Notes and Lab Manual",
                "description": "Complete handwritten notes with lab experiments verified.",
                "price": "250.00",
            },
        )
        post_id = uuid.UUID(create_res.json()["id"])

        await client.post(f"/api/v1/posts/{post_id}/publish", headers=headers)

        db = SessionLocal()
        try:
            record = db.scalar(select(ModerationResult).where(ModerationResult.post_id == post_id))
            assert record is not None
            assert record.decision == ModerationDecision.APPROVE
            assert record.risk_score is not None
            assert isinstance(record.reason_codes, list)
            assert "SAFE_LISTING" in record.reason_codes
            assert record.provider == "mock_provider"
            assert record.model == "mock_rule_engine_v1"
            assert record.created_at is not None
        finally:
            db.close()


@pytest.mark.asyncio
async def test_post_cannot_bypass_moderation(moderation_setup):
    """Verify that unmoderated drafts and rejected posts cannot bypass moderation to public feed."""
    db = SessionLocal()
    try:
        # Create unmoderated DRAFT post directly in DB
        draft_post = Post(
            author_id=moderation_setup["user"].id,
            category_id=moderation_setup["category"].id,
            type=PostType.OFFER,
            title="Bypassed Draft",
            description="Attempting to appear in feed without publish/moderation",
            price=Decimal("150.00"),
            status=PostStatus.DRAFT,
        )
        db.add(draft_post)
        db.commit()
        db.refresh(draft_post)
        draft_id = draft_post.id
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Draft is NOT in public feed
        feed_res = await client.get("/api/v1/posts")
        feed_ids = [p["id"] for p in feed_res.json()["items"]]
        assert str(draft_id) not in feed_ids

        # 2. Public unauthenticated user cannot view draft details
        get_res = await client.get(f"/api/v1/posts/{draft_id}")
        assert get_res.status_code == 404
