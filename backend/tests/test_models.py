import uuid
from decimal import Decimal

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models import (
    Category,
    Conversation,
    ModerationDecision,
    Post,
    PostStatus,
    PostType,
    User,
)


def test_models_can_be_imported() -> None:
    """Verify all domain models are properly defined and registered in metadata."""
    expected_tables = {
        "users",
        "categories",
        "posts",
        "post_images",
        "conversations",
        "messages",
        "moderation_results",
    }
    assert expected_tables.issubset(set(Base.metadata.tables.keys()))


def test_enum_values_are_valid() -> None:
    """Verify enumeration values conform to product specification."""
    assert set(PostType) == {PostType.OFFER, PostType.REQUEST}
    assert set(PostStatus) == {
        PostStatus.DRAFT,
        PostStatus.PENDING_REVIEW,
        PostStatus.PUBLISHED,
        PostStatus.REJECTED,
        PostStatus.ARCHIVED,
        PostStatus.SOLD,
        PostStatus.RENTED,
        PostStatus.CLOSED,
    }
    assert set(ModerationDecision) == {
        ModerationDecision.APPROVE,
        ModerationDecision.REVIEW,
        ModerationDecision.REJECT,
    }


def test_database_tables_and_foreign_keys_exist() -> None:
    """Verify that migration created tables and expected foreign key relationships."""
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    expected_tables = [
        "users",
        "categories",
        "posts",
        "post_images",
        "conversations",
        "messages",
        "moderation_results",
    ]
    for table in expected_tables:
        assert table in table_names, f"Table {table} missing from database"

    # Verify foreign keys for posts
    posts_fks = {
        fk["referred_table"]: fk["constrained_columns"]
        for fk in inspector.get_foreign_keys("posts")
    }
    assert "users" in posts_fks
    assert "author_id" in posts_fks["users"]
    assert "categories" in posts_fks
    assert "category_id" in posts_fks["categories"]

    # Verify foreign keys for conversations
    conv_fks = {
        fk["name"]: (fk["referred_table"], fk["constrained_columns"])
        for fk in inspector.get_foreign_keys("conversations")
    }
    referred_tables = [target for target, _ in conv_fks.values()]
    assert "posts" in referred_tables
    assert referred_tables.count("users") == 2

    # Verify foreign keys for messages
    msg_fks = {
        fk["referred_table"]: fk["constrained_columns"]
        for fk in inspector.get_foreign_keys("messages")
    }
    assert "conversations" in msg_fks
    assert "conversation_id" in msg_fks["conversations"]
    assert "users" in msg_fks
    assert "sender_id" in msg_fks["users"]


def test_required_indexes_exist() -> None:
    """Verify required indexes are present on Post, Conversation, and Message tables."""
    inspector = inspect(engine)

    # Post indexes
    post_index_cols = [tuple(idx["column_names"]) for idx in inspector.get_indexes("posts")]
    assert ("author_id",) in post_index_cols
    assert ("category_id",) in post_index_cols
    assert ("type",) in post_index_cols
    assert ("status",) in post_index_cols
    assert ("created_at",) in post_index_cols
    assert ("status", "created_at") in post_index_cols

    # Conversation indexes
    conv_index_cols = [tuple(idx["column_names"]) for idx in inspector.get_indexes("conversations")]
    assert ("post_id",) in conv_index_cols
    assert ("last_message_at",) in conv_index_cols

    # Message indexes
    msg_index_cols = [tuple(idx["column_names"]) for idx in inspector.get_indexes("messages")]
    assert ("conversation_id",) in msg_index_cols
    assert ("created_at",) in msg_index_cols
    assert ("conversation_id", "created_at") in msg_index_cols


def test_unique_constraint_on_user_email() -> None:
    """Verify unique constraint on user email."""
    session = SessionLocal()
    unique_email = f"student_{uuid.uuid4().hex[:8]}@msrit.edu"

    try:
        user1 = User(email=unique_email, name="Student One", hashed_password="pw1")
        session.add(user1)
        session.commit()

        user2 = User(email=unique_email, name="Student Duplicate", hashed_password="pw2")
        session.add(user2)
        with pytest.raises(IntegrityError):
            session.commit()
    finally:
        session.rollback()
        session.close()


def test_unique_constraint_on_category_slug() -> None:
    """Verify unique constraint on category slug."""
    session = SessionLocal()
    slug = f"electronics_{uuid.uuid4().hex[:8]}"

    try:
        cat1 = Category(name=f"Cat {uuid.uuid4().hex[:6]}", slug=slug)
        session.add(cat1)
        session.commit()

        cat2 = Category(name=f"Cat {uuid.uuid4().hex[:6]}", slug=slug)
        session.add(cat2)
        with pytest.raises(IntegrityError):
            session.commit()
    finally:
        session.rollback()
        session.close()


def test_conversation_initiator_not_owner_constraint() -> None:
    """Verify that a user cannot initiate a conversation with themselves."""
    session = SessionLocal()

    try:
        user = User(
            email=f"owner_{uuid.uuid4().hex[:8]}@msrit.edu",
            name="Owner",
            hashed_password="pw",
        )
        cat = Category(name=f"Cat_{uuid.uuid4().hex[:8]}", slug=f"slug_{uuid.uuid4().hex[:8]}")
        session.add_all([user, cat])
        session.flush()

        post = Post(
            author_id=user.id,
            category_id=cat.id,
            type=PostType.OFFER,
            title="Calculator",
            description="Casio FX-991EX",
            price=Decimal("1200.00"),
            status=PostStatus.PUBLISHED,
        )
        session.add(post)
        session.flush()

        # Same user as initiator and owner violates ck_conversation_initiator_not_owner
        invalid_conv = Conversation(
            post_id=post.id,
            initiator_id=user.id,
            owner_id=user.id,
        )
        session.add(invalid_conv)
        with pytest.raises(IntegrityError):
            session.commit()
    finally:
        session.rollback()
        session.close()


def test_conversation_duplicate_initiator_constraint() -> None:
    """Verify that an initiator cannot create multiple conversations for the same post."""
    session = SessionLocal()

    try:
        owner = User(
            email=f"owner_{uuid.uuid4().hex[:8]}@msrit.edu",
            name="Owner",
            hashed_password="pw",
        )
        buyer = User(
            email=f"buyer_{uuid.uuid4().hex[:8]}@msrit.edu",
            name="Buyer",
            hashed_password="pw",
        )
        cat = Category(name=f"Cat_{uuid.uuid4().hex[:8]}", slug=f"slug_{uuid.uuid4().hex[:8]}")
        session.add_all([owner, buyer, cat])
        session.flush()

        post = Post(
            author_id=owner.id,
            category_id=cat.id,
            type=PostType.OFFER,
            title="Book",
            description="DBMS textbook",
            price=Decimal("450.00"),
            status=PostStatus.PUBLISHED,
        )
        session.add(post)
        session.flush()

        conv1 = Conversation(
            post_id=post.id,
            initiator_id=buyer.id,
            owner_id=owner.id,
        )
        session.add(conv1)
        session.commit()

        # Second conversation by same buyer on same post violates unique constraint
        conv2 = Conversation(
            post_id=post.id,
            initiator_id=buyer.id,
            owner_id=owner.id,
        )
        session.add(conv2)
        with pytest.raises(IntegrityError):
            session.commit()
    finally:
        session.rollback()
        session.close()
