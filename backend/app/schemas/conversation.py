import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from app.models.post import PostStatus, PostType


class ParticipantSummary(BaseModel):
    """Safe public representation of a conversation participant."""

    id: uuid.UUID
    name: str
    university_verified: bool = True
    profile_image_key: str | None = None

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def profile_image_url(self) -> str | None:
        if not self.profile_image_key:
            return None
        from app.services.storage import storage_service

        return storage_service.generate_download_url(self.profile_image_key)


class ConversationPostSummary(BaseModel):
    """Essential post details for conversation context."""

    id: uuid.UUID
    title: str
    type: PostType
    status: PostStatus
    price: Decimal | None = None
    price_unit: str | None = None
    thumbnail_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ConversationResponse(BaseModel):
    """Detailed conversation state including other participant and post context."""

    id: uuid.UUID
    post_id: uuid.UUID
    post_title: str
    post_type: PostType
    post_image_url: str | None = None
    post: ConversationPostSummary | None = None
    other_participant: ParticipantSummary
    last_message_at: datetime | None = None
    closed_at: datetime | None = None
    unread_count: int = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MessageCreateRequest(BaseModel):
    """Payload to send a message within a conversation."""

    model_config = ConfigDict(str_strip_whitespace=True)

    content: str = Field(..., min_length=1, max_length=2000, description="Message text content")

    @field_validator("content")
    @classmethod
    def validate_content_non_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Message content cannot be blank.")
        if len(stripped) > 2000:
            raise ValueError("Message content cannot exceed 2000 characters.")
        return stripped


class MessageResponse(BaseModel):
    """Direct message within a conversation."""

    id: uuid.UUID
    conversation_id: uuid.UUID
    sender_id: uuid.UUID
    content: str
    created_at: datetime
    read_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ConversationListResponse(BaseModel):
    """List of user's active/past conversations."""

    items: list[ConversationResponse]
    total: int
    unread_total: int = 0
