import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.post import Post


class ModerationDecision(enum.StrEnum):
    """Result of content moderation review."""

    APPROVE = "APPROVE"
    REVIEW = "REVIEW"
    REJECT = "REJECT"


class ModerationResult(Base):
    """Automated or manual moderation evaluation for a post."""

    __tablename__ = "moderation_results"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    post_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    decision: Mapped[ModerationDecision] = mapped_column(
        Enum(ModerationDecision, name="moderation_decision", native_enum=True),
        nullable=False,
    )
    risk_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    reason_codes: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    provider: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    model: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    post: Mapped["Post"] = relationship(
        "Post",
        back_populates="moderation_results",
    )
