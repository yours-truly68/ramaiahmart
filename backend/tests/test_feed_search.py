"""Search contract regression coverage; all fixture changes roll back."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import engine, get_db
from app.main import app
from app.models.category import Category
from app.models.post import Post, PostStatus, PostType
from app.models.user import User


@pytest.fixture
def search_feed():
    with engine.connect() as connection:
        transaction = connection.begin()
        session = Session(bind=connection)
        category = Category(name="Search test", slug=f"search-{uuid.uuid4()}", is_active=True)
        author = User(
            name="Search tester",
            email=f"{uuid.uuid4()}@msrit.edu",
            hashed_password="unused",
            university_verified=True,
        )
        session.add_all([category, author])
        session.flush()
        rows = [
            ("Casio calculator", "Scientific, 100% working", PostType.OFFER, PostStatus.PUBLISHED),
            ("Need study gear", "Looking for a CALCULATOR", PostType.REQUEST, PostStatus.PUBLISHED),
            ("Calculator draft", "Private", PostType.OFFER, PostStatus.DRAFT),
            ("Desk lamp", "Model study_lamp", PostType.OFFER, PostStatus.PUBLISHED),
        ]
        session.add_all(
            [
                Post(
                    author_id=author.id,
                    category_id=category.id,
                    title=title,
                    description=description,
                    type=kind,
                    status=status,
                    price=100,
                )
                for title, description, kind, status in rows
            ]
        )
        session.flush()
        app.dependency_overrides[get_db] = lambda: session
        try:
            with TestClient(app) as client:
                yield client, category.slug
        finally:
            app.dependency_overrides.pop(get_db, None)
            session.close()
            transaction.rollback()


def test_search_matches_title_description_and_paginated_count(search_feed):
    client, slug = search_feed
    params = {"category_slug": slug, "q": "  CaLcUlAtOr  ", "page_size": 1}
    first = client.get("/api/v1/posts", params=params).json()
    second = client.get("/api/v1/posts", params={**params, "page": 2}).json()
    assert first["total"] == 2
    assert first["pages"] == 2
    assert len(first["items"]) == len(second["items"]) == 1
    assert first["items"][0]["id"] != second["items"][0]["id"]
    assert all(p["status"] == "PUBLISHED" for p in first["items"] + second["items"])
    offers = client.get("/api/v1/posts", params={**params, "type": "OFFER"}).json()
    assert offers["total"] == 1
    assert offers["items"][0]["title"] == "Casio calculator"


@pytest.mark.parametrize("term,title", [("%", "Casio calculator"), ("_", "Desk lamp")])
def test_search_treats_wildcards_as_text(search_feed, term, title):
    client, slug = search_feed
    data = client.get("/api/v1/posts", params={"category_slug": slug, "q": term}).json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == title


def test_search_empty_no_match_and_length_limit(search_feed):
    client, slug = search_feed
    assert (
        client.get("/api/v1/posts", params={"category_slug": slug, "q": "  "}).json()["total"] == 3
    )
    empty = client.get("/api/v1/posts", params={"category_slug": slug, "q": "no-such-thing"}).json()
    assert empty["items"] == [] and empty["total"] == 0 and empty["pages"] == 0
    assert client.get("/api/v1/posts", params={"q": "x" * 201}).status_code == 422
