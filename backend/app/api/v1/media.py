import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, get_storage_service
from app.core.config import settings
from app.core.errors import AppException
from app.db.session import get_db
from app.models.post import Post, PostImage, PostStatus
from app.models.user import User
from app.schemas.auth import MessageResponse
from app.schemas.media import (
    CompleteUploadRequest,
    PostImageResponse,
    UploadUrlRequest,
    UploadUrlResponse,
)
from app.services.storage import StorageService

router = APIRouter(prefix="/media", tags=["Media"])


@router.post(
    "/upload-url",
    response_model=UploadUrlResponse,
    summary="Request a presigned upload URL for direct object storage transfer",
)
def get_upload_url(
    payload: UploadUrlRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    storage_service: StorageService = Depends(get_storage_service),
) -> UploadUrlResponse:
    """Generate a presigned PUT upload URL.

    Enforces authentication, post ownership, MIME whitelist, and size limit.
    Browser uploads directly to MinIO/S3 without streaming bytes through FastAPI.
    """
    post = db.scalar(select(Post).where(Post.id == payload.post_id))
    if post is None:
        raise AppException(
            code="POST_NOT_FOUND",
            message="Post not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    if post.author_id != current_user.id:
        raise AppException(
            code="FORBIDDEN_NOT_AUTHOR",
            message="You do not have permission to attach media to this post.",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    if post.status in (PostStatus.CLOSED, PostStatus.ARCHIVED):
        raise AppException(
            code="INVALID_POST_STATUS",
            message="Cannot attach media to a closed or archived post.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # Generate safe collision-resistant key namespaced by post ID
    safe_key = storage_service.build_safe_storage_key(post.id, payload.content_type)
    expires_in = settings.STORAGE_PRESIGNED_EXPIRATION_SECONDS

    upload_url = storage_service.generate_upload_url(
        storage_key=safe_key,
        content_type=payload.content_type,
        expires_in=expires_in,
    )

    return UploadUrlResponse(
        upload_url=upload_url,
        storage_key=safe_key,
        expires_in=expires_in,
    )


@router.post(
    "/complete",
    response_model=PostImageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register uploaded media after browser upload completes",
)
def complete_upload(
    payload: CompleteUploadRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    storage_service: StorageService = Depends(get_storage_service),
) -> PostImageResponse:
    """Verify and persist metadata for direct browser upload.

    Verifies post ownership, restricts storage keys to the post prefix,
    and checks that the object actually exists in object storage.
    """
    post = db.scalar(select(Post).where(Post.id == payload.post_id))
    if post is None:
        raise AppException(
            code="POST_NOT_FOUND",
            message="Post not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    if post.author_id != current_user.id:
        raise AppException(
            code="FORBIDDEN_NOT_AUTHOR",
            message="You do not have permission to attach media to this post.",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    # Restrict storage keys: must begin with posts/{post_id}/
    expected_prefix = f"posts/{post.id}/"
    if not payload.storage_key.startswith(expected_prefix):
        raise AppException(
            code="INVALID_STORAGE_KEY",
            message="Storage key does not belong to the specified post.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # Check for duplicate registration
    existing = db.scalar(select(PostImage).where(PostImage.storage_key == payload.storage_key))
    if existing is not None:
        raise AppException(
            code="MEDIA_ALREADY_ATTACHED",
            message="This media has already been attached to the post.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # Verify object existence in object store
    if not storage_service.object_exists(payload.storage_key):
        raise AppException(
            code="OBJECT_NOT_FOUND",
            message=(
                "Uploaded file not found in storage. Ensure upload succeeded before completing."
            ),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # Auto-assign position if not provided
    if payload.position is None:
        max_pos = db.scalar(
            select(func.coalesce(func.max(PostImage.position), -1)).where(
                PostImage.post_id == post.id
            )
        )
        position = (max_pos or 0) + 1
    else:
        position = payload.position

    # Construct public resolvable download URL
    if storage_service.public_endpoint_url:
        endpoint = storage_service.public_endpoint_url.rstrip("/")
        public_url = f"{endpoint}/{storage_service.bucket_name}/{payload.storage_key}"
    else:
        public_url = storage_service.generate_download_url(payload.storage_key)

    post_image = PostImage(
        post_id=post.id,
        storage_key=payload.storage_key,
        public_url=public_url,
        position=position,
    )
    db.add(post_image)
    db.commit()
    db.refresh(post_image)

    return PostImageResponse.model_validate(post_image)


@router.delete(
    "/{media_id}",
    response_model=MessageResponse,
    summary="Delete an uploaded media item",
)
def delete_media(
    media_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    storage_service: StorageService = Depends(get_storage_service),
) -> MessageResponse:
    """Delete an image from both object storage and PostgreSQL database.

    Enforces that only the author of the post can delete its attached media.
    """
    media = db.scalar(
        select(PostImage).options(joinedload(PostImage.post)).where(PostImage.id == media_id)
    )
    if media is None:
        raise AppException(
            code="MEDIA_NOT_FOUND",
            message="Media item not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    if media.post.author_id != current_user.id:
        raise AppException(
            code="FORBIDDEN_NOT_AUTHOR",
            message="You do not have permission to delete this media item.",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    # Delete from object store (MinIO / S3)
    storage_service.delete_object(media.storage_key)

    # Delete database record
    db.delete(media)
    db.commit()

    return MessageResponse(message="Media item deleted successfully.")
