import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.post import Post
    from app.models.user import User


class ReportReason(enum.StrEnum):
    """Supported reasons for reporting a marketplace listing."""

    EXPLICIT_IMAGE = "EXPLICIT_IMAGE"
    IMAGE_MISMATCH = "IMAGE_MISMATCH"
    AUTHENTICITY_SUSPICION = "AUTHENTICITY_SUSPICION"
    SCAM_OR_MISLEADING = "SCAM_OR_MISLEADING"
    SPAM = "SPAM"
    OTHER = "OTHER"


class ReportStatus(enum.StrEnum):
    """Lifecycle state of a content report."""

    OPEN = "OPEN"
    AI_REVIEWED = "AI_REVIEWED"
    UNDER_REVIEW = "UNDER_REVIEW"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"


class Report(Base):
    """User-submitted report regarding a marketplace listing."""

    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    post_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    reporter_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    reason: Mapped[ReportReason] = mapped_column(
        Enum(ReportReason, name="report_reason", native_enum=True),
        nullable=False,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus, name="report_status", native_enum=True),
        default=ReportStatus.OPEN,
        nullable=False,
        index=True,
    )
    ai_reviewed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    ai_decision: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    ai_reason: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # Relationships
    post: Mapped["Post"] = relationship(
        "Post",
        back_populates="reports",
    )
    reporter: Mapped["User"] = relationship(
        "User",
        back_populates="reports",
    )

    __table_args__ = (
        Index("ix_reports_post_reporter", "post_id", "reporter_id"),
        Index("ix_reports_status_created_at", "status", "created_at"),
    )
