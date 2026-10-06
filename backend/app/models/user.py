import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy import true as sa_true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.auth import RefreshToken
    from app.models.conversation import Conversation
    from app.models.legal import LegalConsent
    from app.models.message import Message
    from app.models.post import Post


class UserStatus(enum.StrEnum):
    """Account lifecycle state."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    DELETION_PENDING = "DELETION_PENDING"


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
    # V1: a valid @msrit.edu registration is sufficient for full access.
    # The column is retained for a future automated email-verification
    # migration; it must never gate normal V1 operation.
    university_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=sa_true(),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="ACTIVE",
        server_default="ACTIVE",
        nullable=False,
        index=True,
    )
    last_activity_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    inactive_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    deletion_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    deletion_scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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
    legal_consents: Mapped[list["LegalConsent"]] = relationship(
        "LegalConsent",
        back_populates="user",
        cascade="all, delete-orphan",
    )
