import uuid
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.security import create_access_token
from app.db.session import SessionLocal
from app.main import app
from app.models.category import Category
from app.models.moderation import ModerationResult
from app.models.post import Post, PostImage, PostStatus, PostType
from app.models.user import User


@pytest.fixture
def report_fixture():
    """Setup test users, category, and published post with images."""
    db = SessionLocal()
    try:
        author = User(
            email=f"author_{uuid.uuid4().hex[:8]}@msrit.edu",
            name="Post Author",
            hashed_password="hashed_pw_test_123",
            university_verified=True,
            is_active=True,
        )
        reporter = User(
            email=f"reporter_{uuid.uuid4().hex[:8]}@msrit.edu",
            name="Student Reporter",
            hashed_password="hashed_pw_test_123",
            university_verified=True,
            is_active=True,
        )
        other_user = User(
            email=f"other_{uuid.uuid4().hex[:8]}@msrit.edu",
            name="Other Student",
            hashed_password="hashed_pw_test_123",
            university_verified=True,
            is_active=True,
        )
        category = Category(
            name=f"Electronics {uuid.uuid4().hex[:6]}",
            slug=f"electronics-{uuid.uuid4().hex[:6]}",
            is_active=True,
        )
        db.add_all([author, reporter, other_user, category])
        db.commit()
        db.refresh(author)
        db.refresh(reporter)
        db.refresh(other_user)
        db.refresh(category)

        # Published post with an image
        post_with_image = Post(
            author_id=author.id,
            category_id=category.id,
            type=PostType.OFFER,
            title="Scientific Calculator fx-991",
            description="Used condition calculator in working order.",
            price=Decimal("500.00"),
            status=PostStatus.PUBLISHED,
        )
        db.add(post_with_image)
        db.flush()

        image = PostImage(
            post_id=post_with_image.id,
            storage_key=f"posts/{post_with_image.id}/calculator_photo.jpg",
            public_url=f"http://storage/posts/{post_with_image.id}/calculator_photo.jpg",
            position=0,
        )
        db.add(image)

        # Published post without images
        post_no_image = Post(
            author_id=author.id,
            category_id=category.id,
            type=PostType.OFFER,
            title="Chemistry Notes",
            description="Handwritten notes without photo.",
            price=Decimal("150.00"),
            status=PostStatus.PUBLISHED,
        )
        db.add(post_no_image)

        db.commit()
        db.refresh(post_with_image)
        db.refresh(post_no_image)

        reporter_token = create_access_token(subject=str(reporter.id))
        author_token = create_access_token(subject=str(author.id))
        other_token = create_access_token(subject=str(other_user.id))

        yield {
            "author": author,
            "reporter": reporter,
            "other_user": other_user,
            "category": category,
            "post_with_image": post_with_image,
            "post_no_image": post_no_image,
            "reporter_token": reporter_token,
            "author_token": author_token,
            "other_token": other_token,
        }
    finally:
        db.close()


@pytest.mark.asyncio
async def test_explicit_image_report_triggers_vision_moderation(report_fixture):
    """Verify that EXPLICIT_IMAGE report reason triggers vision moderation and records result."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {report_fixture['reporter_token']}"}
        post = report_fixture["post_with_image"]

        response = await client.post(
            "/api/v1/reports",
            headers=headers,
            json={
                "post_id": str(post.id),
                "reason": "EXPLICIT_IMAGE",
                "description": "Inappropriate image detected in listing.",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["reason"] == "EXPLICIT_IMAGE"
        assert data["ai_reviewed"] is True
        assert data["status"] in ("AI_REVIEWED", "UNDER_REVIEW")
        assert data["ai_decision"] is not None

        # Verify structured ModerationResult was stored in DB linked to report
        db = SessionLocal()
        try:
            mod_record = db.scalar(
                select(ModerationResult).where(ModerationResult.report_id == uuid.UUID(data["id"]))
            )
            assert mod_record is not None
            assert mod_record.post_id == post.id
            assert "EXPLICIT_IMAGE" in mod_record.reason_codes
        finally:
            db.close()


@pytest.mark.asyncio
async def test_image_mismatch_report_triggers_vision_moderation(report_fixture):
    """Verify that IMAGE_MISMATCH report triggers vision moderation."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {report_fixture['reporter_token']}"}
        post = report_fixture["post_with_image"]

        response = await client.post(
            "/api/v1/reports",
            headers=headers,
            json={
                "post_id": str(post.id),
                "reason": "IMAGE_MISMATCH",
                "description": "The image shows clothes instead of the calculator.",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["reason"] == "IMAGE_MISMATCH"
        assert data["ai_reviewed"] is True
        assert data["status"] == "AI_REVIEWED"
        assert "IMAGE_MISMATCH" in data["ai_reason"]


@pytest.mark.asyncio
async def test_authenticity_suspicion_does_not_trigger_vision_moderation(report_fixture):
    """Authenticity suspicion must NOT invoke vision model and routes to human admin review."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {report_fixture['reporter_token']}"}
        post = report_fixture["post_with_image"]

        response = await client.post(
            "/api/v1/reports",
            headers=headers,
            json={
                "post_id": str(post.id),
                "reason": "AUTHENTICITY_SUSPICION",
                "description": "Suspected counterfeit product.",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["reason"] == "AUTHENTICITY_SUSPICION"
        # Must NOT be evaluated by AI vision
        assert data["ai_reviewed"] is False
        assert data["ai_decision"] is None
        assert data["status"] == "OPEN"

        # Verify no ModerationResult was generated for this report
        db = SessionLocal()
        try:
            mod_record = db.scalar(
                select(ModerationResult).where(ModerationResult.report_id == uuid.UUID(data["id"]))
            )
            assert mod_record is None
        finally:
            db.close()


@pytest.mark.asyncio
async def test_non_vision_reasons_do_not_trigger_vision(report_fixture):
    """SCAM_OR_MISLEADING, SPAM, and OTHER must never invoke vision models."""
    non_vision_reasons = ["SCAM_OR_MISLEADING", "SPAM", "OTHER"]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for reason in non_vision_reasons:
            # Create a unique post for each test
            db = SessionLocal()
            try:
                p = Post(
                    author_id=report_fixture["author"].id,
                    category_id=report_fixture["category"].id,
                    type=PostType.OFFER,
                    title=f"Item for {reason}",
                    description="Some description",
                    price=Decimal("100.00"),
                    status=PostStatus.PUBLISHED,
                )
                db.add(p)
                db.commit()
                db.refresh(p)
                post_id = p.id
            finally:
                db.close()

            headers = {"Authorization": f"Bearer {report_fixture['reporter_token']}"}
            res = await client.post(
                "/api/v1/reports",
                headers=headers,
                json={"post_id": str(post_id), "reason": reason},
            )
            assert res.status_code == 201
            data = res.json()
            assert data["reason"] == reason
            assert data["ai_reviewed"] is False
            assert data["status"] == "OPEN"


@pytest.mark.asyncio
async def test_report_post_without_images_handled_safely(report_fixture):
    """Reporting an image issue on a post with no images routes to UNDER_REVIEW without crashing."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {report_fixture['reporter_token']}"}
        post = report_fixture["post_no_image"]

        response = await client.post(
            "/api/v1/reports",
            headers=headers,
            json={
                "post_id": str(post.id),
                "reason": "EXPLICIT_IMAGE",
                "description": "User reported image on a post with no images.",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["ai_reviewed"] is False
        assert data["status"] == "UNDER_REVIEW"


@pytest.mark.asyncio
async def test_duplicate_report_prevention(report_fixture):
    """The same user cannot submit duplicate open reports for the same post."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {report_fixture['reporter_token']}"}
        post = report_fixture["post_with_image"]

        # First report succeeds
        res1 = await client.post(
            "/api/v1/reports",
            headers=headers,
            json={"post_id": str(post.id), "reason": "SPAM"},
        )
        assert res1.status_code == 201

        # Second report from same user on same post returns 409 Conflict
        res2 = await client.post(
            "/api/v1/reports",
            headers=headers,
            json={"post_id": str(post.id), "reason": "SCAM_OR_MISLEADING"},
        )
        assert res2.status_code == 409
        assert res2.json()["error"]["code"] == "DUPLICATE_REPORT"


@pytest.mark.asyncio
async def test_cannot_report_own_post(report_fixture):
    """An author cannot report their own post."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {report_fixture['author_token']}"}
        post = report_fixture["post_with_image"]

        res = await client.post(
            "/api/v1/reports",
            headers=headers,
            json={"post_id": str(post.id), "reason": "OTHER"},
        )
        assert res.status_code == 400
        assert res.json()["error"]["code"] == "CANNOT_REPORT_OWN_POST"


@pytest.mark.asyncio
async def test_unauthenticated_report_rejected(report_fixture):
    """Unauthenticated users cannot submit reports."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        post = report_fixture["post_with_image"]

        res = await client.post(
            "/api/v1/reports",
            json={"post_id": str(post.id), "reason": "SPAM"},
        )
        assert res.status_code == 401


@pytest.mark.asyncio
async def test_get_report_details_and_authorization(report_fixture):
    """Reporter can view their report status; other users cannot view it."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers_reporter = {"Authorization": f"Bearer {report_fixture['reporter_token']}"}
        headers_other = {"Authorization": f"Bearer {report_fixture['other_token']}"}
        post = report_fixture["post_with_image"]

        create_res = await client.post(
            "/api/v1/reports",
            headers=headers_reporter,
            json={"post_id": str(post.id), "reason": "SPAM"},
        )
        report_id = create_res.json()["id"]

        # Reporter can access
        get_res = await client.get(f"/api/v1/reports/{report_id}", headers=headers_reporter)
        assert get_res.status_code == 200
        assert get_res.json()["id"] == report_id

        # Other user cannot access
        forbidden_res = await client.get(f"/api/v1/reports/{report_id}", headers=headers_other)
        assert forbidden_res.status_code == 403


@pytest.mark.asyncio
async def test_vision_caching_deduplication_prevents_duplicate_calls(report_fixture):
    """Subsequent reports from different users on the same post reuse cached vision results."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        post = report_fixture["post_with_image"]

        # First report by reporter
        res1 = await client.post(
            "/api/v1/reports",
            headers={"Authorization": f"Bearer {report_fixture['reporter_token']}"},
            json={"post_id": str(post.id), "reason": "EXPLICIT_IMAGE"},
        )
        assert res1.status_code == 201
        data1 = res1.json()

        # Second report by a different user (other_user) on same post
        res2 = await client.post(
            "/api/v1/reports",
            headers={"Authorization": f"Bearer {report_fixture['other_token']}"},
            json={"post_id": str(post.id), "reason": "EXPLICIT_IMAGE"},
        )
        assert res2.status_code == 201
        data2 = res2.json()
        assert data2["ai_reviewed"] is True
        assert data2["ai_decision"] == data1["ai_decision"]
