import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.main import app
from app.models.category import Category
from app.models.post import Post, PostImage, PostStatus, PostType
from app.models.user import User, UserStatus
from app.services.backup import BackupService
from app.services.lifecycle import (
    mark_inactive_accounts,
    process_permanent_deletions,
    record_user_activity,
)


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def create_verified_user(email_prefix: str, password: str = "Password123!") -> dict[str, Any]:
    email = f"{email_prefix}_{uuid.uuid4().hex[:6]}@msrit.edu"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        reg_resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": password,
                "name": "Lifecycle Test User",
                "accepted_terms": True,
                "accepted_privacy": True,
            },
        )
        assert reg_resp.status_code == 201
        # V1: registration with a valid @msrit.edu address is sufficient; no
        # email-verification step exists, so login works immediately.
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert login_resp.status_code == 200
        token_data = login_resp.json()

        db = SessionLocal()
        user = db.scalar(select(User).where(User.email == email))
        user_id = user.id
        db.close()

        return {
            "user_id": user_id,
            "email": email,
            "password": password,
            "access_token": token_data["access_token"],
            "refresh_token": token_data["refresh_token"],
        }


# ==========================================
# 1. INACTIVITY TESTS
# ==========================================


def test_active_account_remains_active_before_90_days(db_session):
    """Accounts active within 90 days are not marked INACTIVE."""
    user = User(
        email=f"active_{uuid.uuid4().hex[:6]}@msrit.edu",
        name="Active User",
        hashed_password="pw",
        status=UserStatus.ACTIVE,
        last_activity_at=datetime.now(UTC) - timedelta(days=30),
    )
    db_session.add(user)
    db_session.commit()

    marked = mark_inactive_accounts(db_session, threshold_days=90)
    db_session.refresh(user)

    assert user.id not in marked
    assert user.status == UserStatus.ACTIVE
    assert user.inactive_at is None


def test_account_becomes_inactive_after_90_days_without_destructive_consequence(db_session):
    """Accounts without meaningful activity for 90 days transition to INACTIVE non-destructively."""
    user = User(
        email=f"inactive_{uuid.uuid4().hex[:6]}@msrit.edu",
        name="Inactive User",
        hashed_password="pw",
        status=UserStatus.ACTIVE,
        last_activity_at=datetime.now(UTC) - timedelta(days=95),
    )
    db_session.add(user)
    db_session.commit()

    marked = mark_inactive_accounts(db_session, threshold_days=90)
    db_session.refresh(user)

    assert user.id in marked
    assert user.status == UserStatus.INACTIVE
    assert user.inactive_at is not None
    # Verify account is NOT deleted and is_active is preserved
    assert user.is_active is True

    # Running it again is idempotent
    second_run = mark_inactive_accounts(db_session, threshold_days=90)
    assert user.id not in second_run


def test_meaningful_activity_reactivates_inactive_account(db_session):
    """Meaningful authenticated activity restores ACTIVE and clears inactive_at."""
    user = User(
        email=f"reactivate_{uuid.uuid4().hex[:6]}@msrit.edu",
        name="Reactivate User",
        hashed_password="pw",
        status=UserStatus.INACTIVE,
        inactive_at=datetime.now(UTC) - timedelta(days=10),
        last_activity_at=datetime.now(UTC) - timedelta(days=100),
    )
    db_session.add(user)
    db_session.commit()

    record_user_activity(user, db_session, commit=True)
    db_session.refresh(user)

    assert user.status == UserStatus.ACTIVE
    assert user.inactive_at is None
    assert (datetime.now(UTC) - user.last_activity_at).total_seconds() < 5


@pytest.mark.asyncio
async def test_token_refresh_does_not_count_as_activity(db_session):
    """Token refresh does not update last_activity_at or reactivate inactive accounts."""
    auth_data = await create_verified_user("refresh_test")
    user_id = auth_data["user_id"]

    user = db_session.scalar(select(User).where(User.id == user_id))
    user.status = UserStatus.INACTIVE
    old_time = datetime.now(UTC) - timedelta(days=95)
    user.last_activity_at = old_time
    user.inactive_at = old_time
    db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": auth_data["refresh_token"]},
        )
        assert resp.status_code == 200

    db_session.refresh(user)
    assert user.status == UserStatus.INACTIVE
    assert user.last_activity_at == old_time


@pytest.mark.asyncio
async def test_anonymous_and_read_requests_do_not_reactivate_account(db_session):
    """Anonymous browsing and ordinary GET requests do not update last_activity_at."""
    auth_data = await create_verified_user("get_test")
    user_id = auth_data["user_id"]

    user = db_session.scalar(select(User).where(User.id == user_id))
    user.status = UserStatus.INACTIVE
    old_time = datetime.now(UTC) - timedelta(days=92)
    user.last_activity_at = old_time
    user.inactive_at = old_time
    db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Anonymous GET
        resp1 = await client.get("/api/v1/posts")
        assert resp1.status_code == 200

        # Authenticated GET on /me
        resp2 = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {auth_data['access_token']}"},
        )
        assert resp2.status_code == 200

    db_session.refresh(user)
    assert user.status == UserStatus.INACTIVE
    assert user.last_activity_at == old_time


# ==========================================
# 2. ACCOUNT DELETION TESTS
# ==========================================


@pytest.mark.asyncio
async def test_user_can_request_deletion_with_15_day_grace_period():
    """Authenticated user can request deletion and enter a 15-day grace period."""
    auth_data = await create_verified_user("del_req")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/users/me/deletion-request",
            headers={"Authorization": f"Bearer {auth_data['access_token']}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "DELETION_PENDING"
        assert "deletion_requested_at" in data
        assert "deletion_scheduled_at" in data

        req_time = datetime.fromisoformat(data["deletion_requested_at"])
        sched_time = datetime.fromisoformat(data["deletion_scheduled_at"])
        delta = sched_time - req_time
        assert abs(delta.total_seconds() - (15 * 86400)) < 10

        # Idempotent second request returns same scheduled date
        resp2 = await client.post(
            "/api/v1/users/me/deletion-request",
            headers={"Authorization": f"Bearer {auth_data['access_token']}"},
        )
        assert resp2.status_code == 200
        assert resp2.json()["deletion_scheduled_at"] == data["deletion_scheduled_at"]


@pytest.mark.asyncio
async def test_user_can_cancel_deletion_explicitly():
    """Authenticated user can explicitly cancel a pending deletion."""
    auth_data = await create_verified_user("del_cancel")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Request deletion
        await client.post(
            "/api/v1/users/me/deletion-request",
            headers={"Authorization": f"Bearer {auth_data['access_token']}"},
        )

        # 2. Cancel deletion
        cancel_resp = await client.post(
            "/api/v1/users/me/deletion-cancel",
            headers={"Authorization": f"Bearer {auth_data['access_token']}"},
        )
        assert cancel_resp.status_code == 200
        user_data = cancel_resp.json()
        assert user_data["status"] == "ACTIVE"
        assert user_data["deletion_requested_at"] is None
        assert user_data["deletion_scheduled_at"] is None

        # 3. Cancelling when not pending returns 400
        fail_resp = await client.post(
            "/api/v1/users/me/deletion-cancel",
            headers={"Authorization": f"Bearer {auth_data['access_token']}"},
        )
        assert fail_resp.status_code == 400
        assert fail_resp.json()["error"]["code"] == "ACCOUNT_DELETION_NOT_PENDING"


@pytest.mark.asyncio
async def test_login_automatically_cancels_pending_deletion(db_session):
    """Logging in during the 15-day grace period automatically cancels pending deletion."""
    auth_data = await create_verified_user("login_cancel")
    user_id = auth_data["user_id"]

    user = db_session.scalar(select(User).where(User.id == user_id))
    user.status = UserStatus.DELETION_PENDING
    user.deletion_requested_at = datetime.now(UTC) - timedelta(days=5)
    user.deletion_scheduled_at = datetime.now(UTC) + timedelta(days=10)
    db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": auth_data["email"], "password": auth_data["password"]},
        )
        assert login_resp.status_code == 200

    db_session.refresh(user)
    assert user.status == UserStatus.ACTIVE
    assert user.deletion_requested_at is None
    assert user.deletion_scheduled_at is None


def test_permanent_deletion_only_runs_after_deadline(db_session):
    """Pending deletion does NOT delete accounts before the 15-day deadline."""
    user = User(
        email=f"early_{uuid.uuid4().hex[:6]}@msrit.edu",
        name="Early User",
        hashed_password="pw",
        status=UserStatus.DELETION_PENDING,
        deletion_requested_at=datetime.now(UTC) - timedelta(days=5),
        deletion_scheduled_at=datetime.now(UTC) + timedelta(days=10),
    )
    db_session.add(user)
    db_session.commit()
    user_id = user.id

    deleted = process_permanent_deletions(db_session)
    assert user_id not in deleted

    existing = db_session.scalar(select(User).where(User.id == user_id))
    assert existing is not None


def test_permanent_deletion_cleans_up_relational_and_storage_data(db_session):
    """Accounts past the 15-day deadline are deleted with storage and relational data."""
    category = db_session.scalar(select(Category).where(Category.is_active.is_(True)))
    if not category:
        category = Category(name="Electronics", slug="electronics", is_active=True)
        db_session.add(category)
        db_session.commit()

    user = User(
        email=f"purge_{uuid.uuid4().hex[:6]}@msrit.edu",
        name="Purge User",
        hashed_password="pw",
        profile_image_key="profiles/test_user_pfp.jpg",
        status=UserStatus.DELETION_PENDING,
        deletion_requested_at=datetime.now(UTC) - timedelta(days=16),
        deletion_scheduled_at=datetime.now(UTC) - timedelta(hours=1),
    )
    db_session.add(user)
    db_session.commit()
    user_id = user.id

    # Create associated post with post image
    post = Post(
        author_id=user_id,
        category_id=category.id,
        type=PostType.OFFER,
        title="Scientific Calculator",
        description="Casio FX-991EX in great condition",
        status=PostStatus.PUBLISHED,
    )
    db_session.add(post)
    db_session.commit()

    image = PostImage(
        post_id=post.id,
        storage_key="posts/calculator_img.jpg",
        position=0,
    )
    db_session.add(image)
    db_session.commit()

    # Mock storage service to observe delete_object invocations
    mock_storage = MagicMock()

    deleted = process_permanent_deletions(db_session, storage=mock_storage)
    assert user_id in deleted

    # Storage cleanup verified
    mock_storage.delete_object.assert_any_call("profiles/test_user_pfp.jpg")
    mock_storage.delete_object.assert_any_call("posts/calculator_img.jpg")

    # Relational records verified gone
    assert db_session.scalar(select(User).where(User.id == user_id)) is None
    assert db_session.scalar(select(Post).where(Post.id == post.id)) is None
    assert db_session.scalar(select(PostImage).where(PostImage.id == image.id)) is None


def test_missing_storage_object_does_not_abort_deletion(db_session):
    """Missing or 404 storage objects do not abort account deletion."""
    user = User(
        email=f"missing_obj_{uuid.uuid4().hex[:6]}@msrit.edu",
        name="Missing Obj User",
        hashed_password="pw",
        profile_image_key="profiles/ghost_file.jpg",
        status=UserStatus.DELETION_PENDING,
        deletion_requested_at=datetime.now(UTC) - timedelta(days=16),
        deletion_scheduled_at=datetime.now(UTC) - timedelta(minutes=5),
    )
    db_session.add(user)
    db_session.commit()
    user_id = user.id

    mock_storage = MagicMock()
    mock_storage.delete_object.side_effect = RuntimeError("Object not found in bucket")

    # Process deletion with simulated storage error
    deleted = process_permanent_deletions(db_session, storage=mock_storage)
    assert user_id in deleted
    assert db_session.scalar(select(User).where(User.id == user_id)) is None


@pytest.mark.asyncio
async def test_unauthorized_user_cannot_delete_other_accounts():
    """An unauthenticated request cannot schedule account deletion."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/users/me/deletion-request")
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_user_cannot_delete_another_users_account():
    """No id-scoped delete route exists: an authenticated user can never delete
    another user's account by changing a user id in the URL.

    Deletion is self-service only via /users/me/deletion-request.
    """
    victim = await create_verified_user("victim")
    attacker = await create_verified_user("attacker")
    attacker_headers = {"Authorization": f"Bearer {attacker['access_token']}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Id-scoped user deletion routes must not exist
        for method, path in (
            ("delete", f"/api/v1/users/{victim['user_id']}"),
            ("delete", f"/api/v1/users/{victim['user_id']}/delete"),
            ("post", f"/api/v1/users/{victim['user_id']}/delete"),
        ):
            call = getattr(client, method)
            resp = await call(path, headers=attacker_headers)
            assert resp.status_code in (404, 405), f"{method.upper()} {path} must not exist"

        # The victim's account is untouched and fully active
        db = SessionLocal()
        victim_user = db.scalar(select(User).where(User.id == victim["user_id"]))
        assert victim_user is not None
        assert victim_user.status == UserStatus.ACTIVE
        db.close()


# ==========================================
# 3. DISASTER RECOVERY BACKUP TESTS
# ==========================================


def test_backup_reconciliation_omits_deleted_accounts(db_session):
    """A permanently deleted account is present in generation 1, but omitted in generation 2."""
    backup = BackupService(max_retention=7)

    # 1. Create User A and User B
    user_a = User(
        email=f"backupa_{uuid.uuid4().hex[:6]}@msrit.edu",
        name="Backup User A",
        hashed_password="pw",
    )
    user_b = User(
        email=f"backupb_{uuid.uuid4().hex[:6]}@msrit.edu",
        name="Backup User B",
        hashed_password="pw",
    )
    db_session.add_all([user_a, user_b])
    db_session.commit()

    # 2. Run initial backup synchronization
    gen1 = backup.synchronize(db_session)
    assert backup.is_user_in_backup(gen1, user_a.id)
    assert backup.is_user_in_backup(gen1, user_b.id)
    assert backup.active_backup == gen1

    # 3. Permanently delete User A from production database
    db_session.delete(user_a)
    db_session.commit()

    # 4. Synchronize next backup generation
    gen2 = backup.synchronize(db_session)

    # The invariant: User A is omitted from newly synchronized backup; User B is retained
    assert not backup.is_user_in_backup(gen2, user_a.id)
    assert backup.is_user_in_backup(gen2, user_b.id)
    assert backup.active_backup == gen2


def test_failed_backup_preserves_previous_known_good_backup(db_session):
    """If a new backup generation fails, the previous active backup remains intact and promoted."""
    backup = BackupService(max_retention=7)

    gen1 = backup.synchronize(db_session)
    assert backup.active_backup == gen1

    # Attempt synchronizing with simulated failure
    with pytest.raises(RuntimeError):
        backup.synchronize(db_session, simulate_failure=True)

    # Previous active backup is unchanged and continues serving
    assert backup.active_backup == gen1


def test_backup_rolling_retention_caps_at_target(db_session):
    """Backups are rotated so at most max_retention (7) generations are preserved."""
    backup = BackupService(max_retention=7)

    for _ in range(10):
        backup.synchronize(db_session)

    assert len(backup.generations) == 7
