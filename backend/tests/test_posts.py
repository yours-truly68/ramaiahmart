import uuid
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import SessionLocal
from app.main import app
from app.models.category import Category
from app.models.post import Post, PostStatus, PostType
from app.models.user import User


@pytest.fixture
def test_category() -> Category:
    """Ensure a valid test category exists in the database."""
    session = SessionLocal()
    slug = f"electronics_{uuid.uuid4().hex[:6]}"
    cat = Category(name=f"Electronics {uuid.uuid4().hex[:6]}", slug=slug, is_active=True)
    session.add(cat)
    session.commit()
    session.refresh(cat)
    session.close()
    return cat


@pytest.mark.asyncio
async def test_categories_endpoint(test_category: Category) -> None:
    """Verify GET /api/v1/categories returns list of active categories."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        res = await client.get("/api/v1/categories")
        assert res.status_code == 200
        cats = res.json()
        assert isinstance(cats, list)
        slugs = [c["slug"] for c in cats]
        assert test_category.slug in slugs


@pytest.mark.asyncio
async def test_posts_creation_and_validation(test_category: Category) -> None:
    """Verify creating OFFER and REQUEST posts, and input validation rules."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Register and login student
        email = f"seller_{uuid.uuid4().hex[:8]}@ramaiah.edu"
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "Password123!",
                "name": "Seller Student",
                "accepted_terms": True,
                "accepted_privacy": True,
            },
        )
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "Password123!"},
        )
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Create valid OFFER post
        offer_payload = {
            "type": "OFFER",
            "category_id": str(test_category.id),
            "title": "Casio FX-991EX Calculator",
            "description": "Mint condition scientific calculator used for 1 semester.",
            "price": "1200.00",
            "price_unit": "total",
        }
        res = await client.post("/api/v1/posts", json=offer_payload, headers=headers)
        assert res.status_code == 201
        data = res.json()
        assert data["title"] == "Casio FX-991EX Calculator"
        assert data["type"] == "OFFER"
        assert data["status"] == "DRAFT"
        assert data["price"] == "1200.00"
        assert data["category"]["id"] == str(test_category.id)
        assert data["author"]["name"] == "Seller Student"

        # 3. Create OFFER without price must fail
        invalid_offer = {
            "type": "OFFER",
            "category_id": str(test_category.id),
            "title": "Calculator without price",
            "description": "Valid description.",
        }
        fail_res = await client.post("/api/v1/posts", json=invalid_offer, headers=headers)
        assert fail_res.status_code == 422

        # 4. Create valid REQUEST post without price
        request_payload = {
            "type": "REQUEST",
            "category_id": str(test_category.id),
            "title": "Looking for DBMS Textbook",
            "description": "Need Silberschatz Database System Concepts 7th edition.",
        }
        req_res = await client.post("/api/v1/posts", json=request_payload, headers=headers)
        assert req_res.status_code == 201
        assert req_res.json()["type"] == "REQUEST"
        assert req_res.json()["price"] is None

        # 5. Invalid category UUID must fail
        invalid_cat_payload = {
            "type": "REQUEST",
            "category_id": str(uuid.uuid4()),
            "title": "Invalid Category Post",
            "description": "Testing non-existent category validation.",
        }
        cat_fail = await client.post("/api/v1/posts", json=invalid_cat_payload, headers=headers)
        assert cat_fail.status_code == 400
        assert cat_fail.json()["error"]["code"] == "CATEGORY_NOT_FOUND"

        # 6. Unauthorized access without token
        unauth = await client.post("/api/v1/posts", json=offer_payload)
        assert unauth.status_code == 401


@pytest.mark.asyncio
async def test_posts_authorization_updates_and_deletion(test_category: Category) -> None:
    """Verify author permissions: update, delete, close, and prevent modifying another's post."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Register user A (Author)
        email_a = f"author_{uuid.uuid4().hex[:8]}@ramaiah.edu"
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": email_a,
                "password": "Password123!",
                "name": "Author User",
                "accepted_terms": True,
                "accepted_privacy": True,
            },
        )
        login_a = await client.post(
            "/api/v1/auth/login",
            json={"email": email_a, "password": "Password123!"},
        )
        headers_a = {"Authorization": f"Bearer {login_a.json()['access_token']}"}

        # Register user B (Stranger)
        email_b = f"stranger_{uuid.uuid4().hex[:8]}@ramaiah.edu"
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": email_b,
                "password": "Password123!",
                "name": "Stranger User",
                "accepted_terms": True,
                "accepted_privacy": True,
            },
        )
        login_b = await client.post(
            "/api/v1/auth/login",
            json={"email": email_b, "password": "Password123!"},
        )
        headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}

        # User A creates a post
        create_res = await client.post(
            "/api/v1/posts",
            headers=headers_a,
            json={
                "type": "OFFER",
                "category_id": str(test_category.id),
                "title": "Lab Coat Size M",
                "description": "Chemistry lab coat in great condition.",
                "price": "300.00",
            },
        )
        post_id = create_res.json()["id"]

        # User B attempts to modify User A's post -> 403 Forbidden
        hack_res = await client.patch(
            f"/api/v1/posts/{post_id}",
            headers=headers_b,
            json={"title": "Hacked Title"},
        )
        assert hack_res.status_code == 403
        assert hack_res.json()["error"]["code"] == "FORBIDDEN_NOT_AUTHOR"

        # User B attempts to delete User A's post -> 403 Forbidden
        del_hack = await client.delete(f"/api/v1/posts/{post_id}", headers=headers_b)
        assert del_hack.status_code == 403

        # User A successfully updates own post
        update_res = await client.patch(
            f"/api/v1/posts/{post_id}",
            headers=headers_a,
            json={"title": "Chemistry Lab Coat Size M (Clean)", "price": "250.00"},
        )
        assert update_res.status_code == 200
        assert update_res.json()["title"] == "Chemistry Lab Coat Size M (Clean)"
        assert update_res.json()["price"] == "250.00"

        # User A closes post
        close_res = await client.post(f"/api/v1/posts/{post_id}/close", headers=headers_a)
        assert close_res.status_code == 200
        assert close_res.json()["status"] == "CLOSED"

        # User A deletes own post
        del_res = await client.delete(f"/api/v1/posts/{post_id}", headers=headers_a)
        assert del_res.status_code == 200


@pytest.mark.asyncio
async def test_public_feed_filtering_and_pagination(test_category: Category) -> None:
    """Verify that public feed returns only published posts with pagination and filters."""
    session = SessionLocal()
    # Create test author
    author = User(
        email=f"feed_author_{uuid.uuid4().hex[:8]}@ramaiah.edu",
        name="Feed Author",
        hashed_password="hashed_pw",
        university_verified=True,
    )
    session.add(author)
    session.flush()

    # Create published OFFER, published REQUEST, and a DRAFT post
    pub_offer = Post(
        author_id=author.id,
        category_id=test_category.id,
        type=PostType.OFFER,
        title="Published Offer Item",
        description="Publicly visible offer.",
        price=Decimal("100.00"),
        status=PostStatus.PUBLISHED,
    )
    pub_request = Post(
        author_id=author.id,
        category_id=test_category.id,
        type=PostType.REQUEST,
        title="Published Request Item",
        description="Publicly visible request.",
        status=PostStatus.PUBLISHED,
    )
    draft_post = Post(
        author_id=author.id,
        category_id=test_category.id,
        type=PostType.OFFER,
        title="Draft Secret Item",
        description="Private draft not visible publicly.",
        price=Decimal("500.00"),
        status=PostStatus.DRAFT,
    )
    session.add_all([pub_offer, pub_request, draft_post])
    session.commit()
    session.close()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Public feed contains published posts, never drafts
        res = await client.get("/api/v1/posts")
        assert res.status_code == 200
        data = res.json()
        titles = [p["title"] for p in data["items"]]
        assert "Published Offer Item" in titles
        assert "Published Request Item" in titles
        assert "Draft Secret Item" not in titles

        # 2. Filter by OFFER
        offer_res = await client.get("/api/v1/posts?type=OFFER")
        assert offer_res.status_code == 200
        offer_titles = [p["title"] for p in offer_res.json()["items"]]
        assert "Published Offer Item" in offer_titles
        assert "Published Request Item" not in offer_titles

        # 3. Filter by REQUEST
        req_res = await client.get("/api/v1/posts?type=REQUEST")
        assert req_res.status_code == 200
        req_titles = [p["title"] for p in req_res.json()["items"]]
        assert "Published Request Item" in req_titles
        assert "Published Offer Item" not in req_titles

        # 4. Filter by category slug
        cat_res = await client.get(f"/api/v1/posts?category_slug={test_category.slug}")
        assert cat_res.status_code == 200
        assert len(cat_res.json()["items"]) >= 2

        # 5. Pagination test
        page_res = await client.get("/api/v1/posts?page=1&page_size=1")
        assert page_res.status_code == 200
        assert len(page_res.json()["items"]) == 1
        assert page_res.json()["page"] == 1
        assert page_res.json()["page_size"] == 1
        assert page_res.json()["total"] >= 2


@pytest.mark.asyncio
async def test_publish_flow_and_moderation_transition(test_category: Category) -> None:
    """Verify DRAFT -> PENDING_REVIEW transition via publish endpoint."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        email = f"verified_publisher_{uuid.uuid4().hex[:8]}@ramaiah.edu"
        reg_res = await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "Password123!",
                "name": "Verified Student",
                "accepted_terms": True,
                "accepted_privacy": True,
            },
        )
        code = reg_res.json()["verification_code"]

        # Attempt to publish before email verification should fail
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "Password123!"},
        )
        headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}

        post_res = await client.post(
            "/api/v1/posts",
            headers=headers,
            json={
                "type": "OFFER",
                "category_id": str(test_category.id),
                "title": "Study Lamp",
                "description": "Desk LED lamp with 3 brightness modes.",
                "price": "400.00",
            },
        )
        post_id = post_res.json()["id"]

        unverified_pub = await client.post(f"/api/v1/posts/{post_id}/publish", headers=headers)
        assert unverified_pub.status_code == 403
        assert unverified_pub.json()["error"]["code"] == "FORBIDDEN_UNVERIFIED"

        # Now verify student email
        await client.post("/api/v1/auth/verify", json={"email": email, "code": code})

        # Publishing now succeeds: moderation approves clean listing -> PUBLISHED
        pub_res = await client.post(f"/api/v1/posts/{post_id}/publish", headers=headers)
        assert pub_res.status_code == 200
        assert pub_res.json()["status"] == "PUBLISHED"
        assert pub_res.json()["published_at"] is not None
