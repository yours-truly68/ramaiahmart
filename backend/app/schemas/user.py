import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserResponse(BaseModel):
    """Public/private user profile representation."""

    id: uuid.UUID
    email: str
    name: str
    bio: str | None = None
    profile_image_key: str | None = None
    university_verified: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserUpdateRequest(BaseModel):
    """Input for updating own user profile."""

    name: str | None = Field(default=None, min_length=2, max_length=255)
    bio: str | None = Field(default=None, max_length=500)
    profile_image_key: str | None = Field(default=None, max_length=512)
