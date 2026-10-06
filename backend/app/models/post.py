import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.conversation import Conversation
    from app.models.moderation import ModerationResult
    from app.models.report import Report
    from app.models.user import User


class PostType(enum.StrEnum):
    """Classification of the listing."""

    OFFER = "OFFER"
    REQUEST = "REQUEST"


class PostStatus(enum.StrEnum):
    """Lifecycle state of a post."""

    DRAFT = "DRAFT"
    PENDING_REVIEW = "PENDING_REVIEW"
    PUBLISHED = "PUBLISHED"
    REJECTED = "REJECTED"
    ARCHIVED = "ARCHIVED"
    SOLD = "SOLD"
    RENTED = "RENTED"
    CLOSED = "CLOSED"


class Post(Base):
    """Marketplace listing model."""

    __tablename__ = "posts"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    type: Mapped[PostType] = mapped_column(
        Enum(PostType, name="post_type", native_enum=True),
        index=True,
        nullable=False,
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )
    price_unit: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    status: Mapped[PostStatus] = mapped_column(
        Enum(PostStatus, name="post_status", native_enum=True),
        default=PostStatus.DRAFT,
        index=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        index=True,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    author: Mapped["User"] = relationship(
        "User",
        back_populates="posts",
    )
    category: Mapped["Category"] = relationship(
        "Category",
        back_populates="posts",
    )
    images: Mapped[list["PostImage"]] = relationship(
        "PostImage",
        back_populates="post",
        cascade="all, delete-orphan",
        order_by="PostImage.position",
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation",
        back_populates="post",
        cascade="all, delete-orphan",
    )
    moderation_results: Mapped[list["ModerationResult"]] = relationship(
        "ModerationResult",
        back_populates="post",
        cascade="all, delete-orphan",
    )
    reports: Mapped[list["Report"]] = relationship(
        "Report",
        back_populates="post",
        cascade="all, delete-orphan",
    )

    __table_args__ = (Index("ix_posts_status_created_at", "status", "created_at"),)

    @property
    def whatsapp_url(self) -> str | None:
        """Construct safe wa.me link if author has enabled WhatsApp enquiries."""
        try:
            author = self.author
        except Exception:
            return None
        if not author or not getattr(author, "whatsapp_enabled", False):
            return None
        raw_number = getattr(author, "whatsapp_number", None)
        if not raw_number:
            return None
        import re
        import urllib.parse

        digits = re.sub(r"\D", "", raw_number)
        if not digits or len(digits) < 7:
            return None
        msg = f"Hi, I found your RamaiahMart post: {self.title}. Is it still available?"
        return f"https://wa.me/{digits}?text={urllib.parse.quote(msg)}"


class PostImage(Base):
    """Image associated with a post."""

    __tablename__ = "post_images"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    post_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    storage_key: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )
    public_url: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
    )
    position: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    post: Mapped["Post"] = relationship(
        "Post",
        back_populates="images",
    )
