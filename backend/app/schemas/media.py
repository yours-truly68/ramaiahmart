import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.core.config import settings


class PostImageResponse(BaseModel):
    """Media object details attached to a post."""

    id: uuid.UUID
    post_id: uuid.UUID
    storage_key: str
    public_url: str | None = None
    position: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("public_url")
    def resolve_image_url(self, value: str | None) -> str:
        # Refresh expiring URLs at read time; the canonical key remains in the DB.
        from app.services.storage import storage_service

        return storage_service.generate_download_url(self.storage_key)


class UploadUrlRequest(BaseModel):
    """Payload to request a presigned upload URL for direct storage upload."""

    post_id: uuid.UUID = Field(..., description="Post UUID to attach the image to")
    content_type: str = Field(
        ...,
        description="MIME type of the media file (e.g., image/jpeg, image/png, image/webp)",
    )
    file_size: int = Field(..., gt=0, description="Size of the file in bytes")

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, v: str) -> str:
        clean = v.lower().strip()
        allowed = [mime.lower().strip() for mime in settings.ALLOWED_IMAGE_MIME_TYPES]
        if clean not in allowed:
            raise ValueError(
                f"Unsupported media type '{clean}'. Allowed types: {', '.join(allowed)}."
            )
        return clean

    @field_validator("file_size")
    @classmethod
    def validate_file_size(cls, v: int) -> int:
        if v > settings.MAX_UPLOAD_SIZE_BYTES:
            max_mb = settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
            raise ValueError(f"File size exceeds maximum allowed limit of {max_mb} MB.")
        return v


class UploadUrlResponse(BaseModel):
    """Presigned upload credentials for direct browser-to-storage transfer."""

    upload_url: str = Field(..., description="Presigned PUT URL for upload")
    storage_key: str = Field(..., description="Canonical safe storage key")
    expires_in: int = Field(..., description="Presigned URL expiration in seconds")


class CompleteUploadRequest(BaseModel):
    """Payload to finalize an upload and link the stored object to the post."""

    post_id: uuid.UUID = Field(..., description="Post UUID")
    storage_key: str = Field(..., min_length=5, max_length=512, description="Storage key")
    position: int | None = Field(
        default=None,
        ge=0,
        description="Display order index (auto-assigned if not provided)",
    )
