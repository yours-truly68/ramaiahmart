import math

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.post import Post, PostStatus, PostType
from app.models.user import User
from app.schemas.post import PostListResponse, PostResponse
from app.schemas.user import (
    DeletionRequestResponse,
    UserPostStats,
    UserResponse,
    UserUpdateRequest,
)
from app.services.lifecycle import (
    cancel_account_deletion,
    record_user_activity,
    request_account_deletion,
)

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Retrieve authenticated user's profile."""
    return UserResponse.model_validate(current_user)


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update own user profile",
)
def update_me(
    data: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    """Update profile information of the authenticated user."""
    if data.name is not None:
        current_user.name = data.name.strip()
    if data.bio is not None:
        current_user.bio = data.bio.strip()
    if data.profile_image_key is not None:
        current_user.profile_image_key = data.profile_image_key.strip()

    record_user_activity(current_user, db, commit=False)
    db.commit()
    db.refresh(current_user)

    return UserResponse.model_validate(current_user)


@router.post(
    "/me/deletion-request",
    response_model=DeletionRequestResponse,
    summary="Request account deletion with 15-day grace period",
)
def deletion_request(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeletionRequestResponse:
    """Initiate a 15-day account deletion grace period.

    During this 15-day period, logging in or performing meaningful authenticated activity
    automatically cancels deletion. If no activity occurs for 15 days, the account and
    associated data are permanently deleted.
    """
    return request_account_deletion(user=current_user, db=db)


@router.post(
    "/me/deletion-cancel",
    response_model=UserResponse,
    summary="Cancel pending account deletion request",
)
def deletion_cancel(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    """Explicitly cancel a pending deletion request and restore account to ACTIVE status."""
    updated_user = cancel_account_deletion(user=current_user, db=db)
    return UserResponse.model_validate(updated_user)


@router.get("/me/posts", response_model=PostListResponse, summary="List all of my posts")
def my_posts(
    type: PostType | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PostListResponse:
    filters = [Post.author_id == current_user.id]
    if type is not None:
        filters.append(Post.type == type)
    total = db.scalar(select(func.count(Post.id)).where(*filters)) or 0
    rows = db.scalars(
        select(Post)
        .where(*filters)
        .options(joinedload(Post.author), joinedload(Post.category), selectinload(Post.images))
        .order_by(Post.created_at.desc(), Post.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return PostListResponse(
        items=[PostResponse.model_validate(post) for post in rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size),
    )


@router.get("/me/stats", response_model=UserPostStats, summary="Counts of my marketplace posts")
def my_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserPostStats:
    rows = db.execute(
        select(Post.type, Post.status, func.count(Post.id))
        .where(Post.author_id == current_user.id)
        .group_by(Post.type, Post.status)
    ).all()
    return UserPostStats(
        listings=sum(count for kind, _, count in rows if kind == PostType.OFFER),
        requests=sum(count for kind, _, count in rows if kind == PostType.REQUEST),
        published=sum(count for _, status, count in rows if status == PostStatus.PUBLISHED),
    )
