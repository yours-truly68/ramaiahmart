import logging
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import status
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.core.errors import AppException
from app.models.post import Post, PostImage
from app.models.user import User, UserStatus
from app.schemas.user import DeletionRequestResponse
from app.services.storage import StorageService, storage_service

logger = logging.getLogger(__name__)


def record_user_activity(user: User, db: Session, commit: bool = False) -> None:
    """Record meaningful user activity.

    Reactivates inactive accounts and cancels pending deletion requests
    when the user performs authentic marketplace actions.
    """
    now = datetime.now(UTC)
    user.last_activity_at = now

    if user.status == UserStatus.INACTIVE:
        user.status = UserStatus.ACTIVE
        user.inactive_at = None
        logger.info(
            "Account reactivated from INACTIVE due to meaningful activity: user_id=%s",
            user.id,
        )

    elif user.status == UserStatus.DELETION_PENDING:
        user.status = UserStatus.ACTIVE
        user.deletion_requested_at = None
        user.deletion_scheduled_at = None
        logger.info(
            "Account deletion cancelled due to authenticated activity: user_id=%s",
            user.id,
        )

    if commit:
        db.commit()


def mark_inactive_accounts(db: Session, threshold_days: int = 90) -> list[uuid.UUID]:
    """Identify accounts without meaningful activity for 90 days and mark them INACTIVE.

    Inactivity is non-destructive: accounts are not deleted, not suspended,
    do not lose posts or messages, and can return at any time.
    Idempotent: already-inactive accounts are not re-modified.
    """
    now = datetime.now(UTC)
    cutoff = now - timedelta(days=threshold_days)

    stmt = select(User).where(
        User.status == UserStatus.ACTIVE,
        or_(
            User.last_activity_at < cutoff,
            and_(User.last_activity_at.is_(None), User.created_at < cutoff),
        ),
    )
    users = db.scalars(stmt).all()

    marked_ids: list[uuid.UUID] = []
    for user in users:
        user.status = UserStatus.INACTIVE
        user.inactive_at = now
        marked_ids.append(user.id)

    if marked_ids:
        db.commit()
        logger.info("Marked %d accounts as INACTIVE", len(marked_ids))

    return marked_ids


def request_account_deletion(
    user: User, db: Session, grace_days: int = 15
) -> DeletionRequestResponse:
    """Initiate a 15-day account deletion grace period.

    Idempotent: if deletion is already pending, returns existing schedule without error.
    """
    if user.status == UserStatus.DELETION_PENDING and user.deletion_scheduled_at:
        return DeletionRequestResponse(
            status=user.status,
            deletion_requested_at=user.deletion_requested_at or datetime.now(UTC),
            deletion_scheduled_at=user.deletion_scheduled_at,
        )

    now = datetime.now(UTC)
    scheduled = now + timedelta(days=grace_days)

    user.status = UserStatus.DELETION_PENDING
    user.deletion_requested_at = now
    user.deletion_scheduled_at = scheduled

    db.commit()
    db.refresh(user)

    logger.info(
        "Account deletion requested: user_id=%s scheduled_at=%s",
        user.id,
        scheduled.isoformat(),
    )

    return DeletionRequestResponse(
        status=user.status,
        deletion_requested_at=user.deletion_requested_at,
        deletion_scheduled_at=user.deletion_scheduled_at,
    )


def cancel_account_deletion(user: User, db: Session) -> User:
    """Explicitly cancel a pending account deletion request during the 15-day window."""
    if user.status != UserStatus.DELETION_PENDING:
        raise AppException(
            code="ACCOUNT_DELETION_NOT_PENDING",
            message="Your account does not currently have a pending deletion request.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    user.status = UserStatus.ACTIVE
    user.deletion_requested_at = None
    user.deletion_scheduled_at = None

    record_user_activity(user, db, commit=False)
    db.commit()
    db.refresh(user)

    logger.info("Account deletion explicitly cancelled: user_id=%s", user.id)
    return user


def process_permanent_deletions(
    db: Session, storage: StorageService | None = None
) -> list[uuid.UUID]:
    """Permanently delete accounts that completed their 15-day deletion grace period.

    Cleans up:
      1. Associated storage objects (profile image, post images).
      2. Database records (user, posts, conversations, messages, tokens, consents)
         via relationship and foreign key CASCADE rules.

    Safe and retryable: storage failures for missing objects do not abort the process.
    """
    now = datetime.now(UTC)
    active_storage = storage or storage_service

    stmt = select(User).where(
        User.status == UserStatus.DELETION_PENDING,
        User.deletion_scheduled_at.is_not(None),
        User.deletion_scheduled_at <= now,
    )
    due_users = db.scalars(stmt).all()

    deleted_ids: list[uuid.UUID] = []

    for user in due_users:
        user_id = user.id
        logger.info("Executing permanent deletion for user_id=%s", user_id)

        # 1. Collect all storage keys owned by this user
        storage_keys: list[str] = []
        if user.profile_image_key:
            storage_keys.append(user.profile_image_key)

        post_images_stmt = (
            select(PostImage.storage_key)
            .join(Post, PostImage.post_id == Post.id)
            .where(Post.author_id == user_id)
        )
        post_keys = db.scalars(post_images_stmt).all()
        storage_keys.extend(post_keys)

        # 2. Delete storage objects safely
        for key in storage_keys:
            try:
                active_storage.delete_object(key)
            except Exception as e:
                logger.warning("Error deleting object key %s during user deletion: %s", key, e)

        # 3. Delete database user entity (cascades to all user records)
        db.delete(user)
        db.commit()

        deleted_ids.append(user_id)
        logger.info("Permanently deleted user_id=%s and associated data", user_id)

    return deleted_ids
