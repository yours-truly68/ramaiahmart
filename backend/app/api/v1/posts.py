import math
import uuid

from fastapi import APIRouter, Depends, Query, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.api.deps import get_current_user, get_moderation_service, security_scheme
from app.core.errors import AppException
from app.core.security import decode_token
from app.db.session import get_db
from app.models.category import Category
from app.models.post import Post, PostStatus, PostType
from app.models.user import User
from app.schemas.auth import MessageResponse
from app.schemas.post import (
    PostCreateRequest,
    PostListResponse,
    PostResponse,
    PostUpdateRequest,
)
from app.services.moderation import ModerationService

router = APIRouter(prefix="/posts", tags=["Posts"])


@router.post(
    "",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new listing (Draft)",
)
def create_post(
    data: PostCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PostResponse:
    """Create a new post in DRAFT status."""
    category = db.scalar(
        select(Category).where(
            Category.id == data.category_id,
            Category.is_active.is_(True),
        )
    )
    if category is None:
        raise AppException(
            code="CATEGORY_NOT_FOUND",
            message="Category not found or is currently inactive.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    post = Post(
        author_id=current_user.id,
        category_id=category.id,
        type=data.type,
        title=data.title.strip(),
        description=data.description.strip(),
        price=data.price,
        price_unit=data.price_unit.strip() if data.price_unit else None,
        status=PostStatus.DRAFT,
    )
    db.add(post)
    db.commit()
    db.refresh(post)

    return PostResponse.model_validate(post)


@router.get(
    "",
    response_model=PostListResponse,
    summary="Get public published posts feed",
)
def list_posts(
    category_id: uuid.UUID | None = Query(default=None, description="Filter by category UUID"),
    category_slug: str | None = Query(default=None, description="Filter by category slug"),
    type: PostType | None = Query(default=None, description="Filter by OFFER or REQUEST"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
) -> PostListResponse:
    """Retrieve paginated published marketplace posts with optional filtering."""
    base_query = (
        select(Post)
        .join(Post.category)
        .options(
            joinedload(Post.author),
            joinedload(Post.category),
            selectinload(Post.images),
        )
        .where(Post.status == PostStatus.PUBLISHED)
    )

    if category_id is not None:
        base_query = base_query.where(Post.category_id == category_id)

    if category_slug is not None:
        base_query = base_query.where(Category.slug == category_slug.strip().lower())

    if type is not None:
        base_query = base_query.where(Post.type == type)

    # Count total matching rows
    count_subquery = (
        select(func.count(Post.id)).join(Post.category).where(Post.status == PostStatus.PUBLISHED)
    )
    if category_id is not None:
        count_subquery = count_subquery.where(Post.category_id == category_id)
    if category_slug is not None:
        count_subquery = count_subquery.where(Category.slug == category_slug.strip().lower())
    if type is not None:
        count_subquery = count_subquery.where(Post.type == type)

    total = db.scalar(count_subquery) or 0
    pages = math.ceil(total / page_size) if total > 0 else 0

    # Paginate and order by recency
    offset = (page - 1) * page_size
    stmt = base_query.order_by(Post.created_at.desc()).offset(offset).limit(page_size)
    items = db.scalars(stmt).all()

    return PostListResponse(
        items=[PostResponse.model_validate(p) for p in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get(
    "/{post_id}",
    response_model=PostResponse,
    summary="Get post details",
)
def get_post(
    post_id: uuid.UUID,
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> PostResponse:
    """Retrieve post details. Published posts are public; drafts are restricted to author."""
    post = db.scalar(
        select(Post)
        .options(
            joinedload(Post.author),
            joinedload(Post.category),
            selectinload(Post.images),
        )
        .where(Post.id == post_id)
    )
    if post is None:
        raise AppException(
            code="POST_NOT_FOUND",
            message="Post not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    # If post is not published, only the post author may view it
    if post.status != PostStatus.PUBLISHED:
        if credentials is None:
            raise AppException(
                code="POST_NOT_FOUND",
                message="Post not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        try:
            payload = decode_token(credentials.credentials)
            user_id = uuid.UUID(payload.get("sub", ""))
            if post.author_id != user_id:
                raise AppException(
                    code="POST_NOT_FOUND",
                    message="Post not found.",
                    status_code=status.HTTP_404_NOT_FOUND,
                )
        except Exception:
            raise AppException(
                code="POST_NOT_FOUND",
                message="Post not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            ) from None

    return PostResponse.model_validate(post)


@router.patch(
    "/{post_id}",
    response_model=PostResponse,
    summary="Update own post",
)
def update_post(
    post_id: uuid.UUID,
    data: PostUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PostResponse:
    """Update post title, description, price, or category. Author only."""
    post = db.scalar(
        select(Post)
        .options(
            joinedload(Post.author),
            joinedload(Post.category),
            selectinload(Post.images),
        )
        .where(Post.id == post_id)
    )
    if post is None:
        raise AppException(
            code="POST_NOT_FOUND",
            message="Post not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    if post.author_id != current_user.id:
        raise AppException(
            code="FORBIDDEN_NOT_AUTHOR",
            message="You do not have permission to modify this post.",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    if post.status == PostStatus.CLOSED:
        raise AppException(
            code="POST_CLOSED",
            message="Closed posts cannot be modified.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if data.category_id is not None:
        cat = db.scalar(
            select(Category).where(
                Category.id == data.category_id,
                Category.is_active.is_(True),
            )
        )
        if cat is None:
            raise AppException(
                code="CATEGORY_NOT_FOUND",
                message="Target category not found or is inactive.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        post.category_id = cat.id

    if data.title is not None:
        post.title = data.title.strip()
    if data.description is not None:
        post.description = data.description.strip()
    if data.price is not None:
        post.price = data.price
    if data.price_unit is not None:
        post.price_unit = data.price_unit.strip()

    db.commit()
    db.refresh(post)

    return PostResponse.model_validate(post)


@router.delete(
    "/{post_id}",
    response_model=MessageResponse,
    summary="Delete own post",
)
def delete_post(
    post_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Permanently delete author's own post."""
    post = db.scalar(select(Post).where(Post.id == post_id))
    if post is None:
        raise AppException(
            code="POST_NOT_FOUND",
            message="Post not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    if post.author_id != current_user.id:
        raise AppException(
            code="FORBIDDEN_NOT_AUTHOR",
            message="You do not have permission to delete this post.",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    db.delete(post)
    db.commit()

    return MessageResponse(message="Post deleted successfully.")


@router.post(
    "/{post_id}/publish",
    response_model=PostResponse,
    summary="Submit post for publishing and review",
)
def publish_post(
    post_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    moderation_service: ModerationService = Depends(get_moderation_service),
) -> PostResponse:
    """Submit post for publication.

    Requires university verification. Evaluates post through moderation service.
    Transitions DRAFT/REJECTED -> PUBLISHED (if approved), PENDING_REVIEW (if review),
    or REJECTED (if rejected/prohibited).
    """
    if not current_user.university_verified:
        raise AppException(
            code="FORBIDDEN_UNVERIFIED",
            message="University email verification is required to publish a post.",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    post = db.scalar(
        select(Post)
        .options(
            joinedload(Post.author),
            joinedload(Post.category),
            selectinload(Post.images),
        )
        .where(Post.id == post_id)
    )
    if post is None:
        raise AppException(
            code="POST_NOT_FOUND",
            message="Post not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    if post.author_id != current_user.id:
        raise AppException(
            code="FORBIDDEN_NOT_AUTHOR",
            message="You do not have permission to publish this post.",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    if post.status not in (PostStatus.DRAFT, PostStatus.REJECTED):
        raise AppException(
            code="INVALID_STATE_TRANSITION",
            message=f"Cannot publish a post that is already {post.status.value}.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # Route through moderation service boundary
    post = moderation_service.process_post_publication(post, db)

    return PostResponse.model_validate(post)


@router.post(
    "/{post_id}/close",
    response_model=PostResponse,
    summary="Close post",
)
def close_post(
    post_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PostResponse:
    """Close post when sold, rented, or fulfilled. Author only."""
    post = db.scalar(
        select(Post)
        .options(
            joinedload(Post.author),
            joinedload(Post.category),
            selectinload(Post.images),
        )
        .where(Post.id == post_id)
    )
    if post is None:
        raise AppException(
            code="POST_NOT_FOUND",
            message="Post not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    if post.author_id != current_user.id:
        raise AppException(
            code="FORBIDDEN_NOT_AUTHOR",
            message="You do not have permission to close this post.",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    post.status = PostStatus.CLOSED
    db.commit()
    db.refresh(post)

    return PostResponse.model_validate(post)
