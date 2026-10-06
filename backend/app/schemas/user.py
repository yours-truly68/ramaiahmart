import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field


class UserResponse(BaseModel):
    """Public/private user profile representation."""

    id: uuid.UUID
    email: str
    name: str
    bio: str | None = None
    profile_image_key: str | None = None
    university_verified: bool
    is_active: bool
    status: str = "ACTIVE"
    last_activity_at: datetime | None = None
    last_login_at: datetime | None = None
    inactive_at: datetime | None = None
    deletion_requested_at: datetime | None = None
    deletion_scheduled_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def profile_image_url(self) -> str | None:
        if not self.profile_image_key:
            return None
        from app.services.storage import storage_service

        return storage_service.generate_download_url(self.profile_image_key)


class UserUpdateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    """Input for updating own user profile."""

    name: str | None = Field(default=None, min_length=2, max_length=255)
    bio: str | None = Field(default=None, max_length=500)
    profile_image_key: str | None = Field(default=None, max_length=512)


class UserPostStats(BaseModel):
    listings: int
    requests: int
    published: int


class DeletionRequestResponse(BaseModel):
    """Response returned when a user schedules account deletion."""

    status: str
    deletion_requested_at: datetime
    deletion_scheduled_at: datetime
