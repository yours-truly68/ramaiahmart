import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.auth import EmailVerificationCode, RefreshToken
    from app.models.conversation import Conversation
    from app.models.message import Message
    from app.models.post import Post


class User(Base):
    """Registered student user model."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    bio: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    profile_image_key: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )
    university_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    posts: Mapped[list["Post"]] = relationship(
        "Post",
        back_populates="author",
        cascade="all, delete-orphan",
    )
    initiated_conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation",
        foreign_keys="[Conversation.initiator_id]",
        back_populates="initiator",
        cascade="all, delete-orphan",
    )
    owned_conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation",
        foreign_keys="[Conversation.owner_id]",
        back_populates="owner",
        cascade="all, delete-orphan",
    )
    sent_messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="sender",
        cascade="all, delete-orphan",
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    verification_codes: Mapped[list["EmailVerificationCode"]] = relationship(
        "EmailVerificationCode",
        back_populates="user",
        cascade="all, delete-orphan",
    )
