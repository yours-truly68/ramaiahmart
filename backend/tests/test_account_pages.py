"""Real API integration checks for account pages; use an isolated database."""

import uuid

from fastapi.testclient import TestClient

from app.main import app


def test_private_inventory_stats_edit_and_request_budget_clear():
    client = TestClient(app)
    accounts = []
    for name in ("Inventory Owner", "Other Student"):
        email = f"account-{uuid.uuid4().hex}@ramaiah.edu"
        registration = client.post(
            "/api/v1/auth/register",
            json={
                "name": name,
                "email": email,
                "password": "CampusPassword123!",
                "accepted_terms": True,
                "accepted_privacy": True,
            },
        )
        assert registration.status_code == 201
        login = client.post(
            "/api/v1/auth/login",
            json={
                "email": email,
                "password": "CampusPassword123!",
            },
        )
        accounts.append({"Authorization": f"Bearer {login.json()['access_token']}"})
    owner, other = accounts
    categories = client.get("/api/v1/categories").json()
    category_id = categories[0]["id"]
    request = client.post(
        "/api/v1/posts",
        headers=owner,
        json={
            "type": "REQUEST",
            "category_id": category_id,
            "title": "Integration verification request",
            "description": "Isolated API verification.",
            "price": "250",
            "price_unit": "per day",
        },
    ).json()
    updated = client.patch(
        f"/api/v1/posts/{request['id']}", headers=owner, json={"price": None, "price_unit": None}
    )
    assert updated.status_code == 200
    assert updated.json()["price"] is None and updated.json()["price_unit"] is None
    assert client.get("/api/v1/users/me/posts").status_code == 401
    mine = client.get("/api/v1/users/me/posts?type=REQUEST&page_size=1", headers=owner).json()
    assert mine["total"] == 1 and mine["items"][0]["id"] == request["id"]
    assert mine["items"][0]["status"] == "DRAFT"
    assert client.get("/api/v1/users/me/posts", headers=other).json()["total"] == 0
    assert client.get("/api/v1/users/me/stats", headers=owner).json() == {
        "listings": 0,
        "requests": 1,
        "published": 0,
    }
    assert client.get("/api/v1/users/me/stats", headers=other).json()["requests"] == 0
    edited = client.patch(
        "/api/v1/users/me",
        headers=owner,
        json={"name": "  Updated Student  ", "bio": "Campus reader"},
    )
    assert edited.status_code == 200
    assert edited.json()["name"] == "Updated Student"
    assert client.patch("/api/v1/users/me", headers=owner, json={"name": "  "}).status_code == 422
    assert (
        client.patch(
            f"/api/v1/posts/{request['id']}", headers=owner, json={"title": "   "}
        ).status_code
        == 422
    )


def test_public_requirements_and_registration_bounds():
    client = TestClient(app)
    config = client.get("/api/v1/auth/config").json()
    assert config["password_min_length"] == 8
    assert config["email_delivery_available"] is False
    assert "allowed_email_domains" in config
    media = client.get("/api/v1/media/config").json()
    assert media["max_file_size"] > 0
    assert "image/png" in media["content_types"]
    assert (
        client.post(
            "/api/v1/auth/register",
            json={
                "name": "Test Student",
                "email": f"{uuid.uuid4()}@ramaiah.edu",
                "password": "é" * 40,
            },
        ).status_code
        == 422
    )
