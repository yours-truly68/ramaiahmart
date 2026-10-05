import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.message import Message
    from app.models.post import Post
    from app.models.user import User


class Conversation(Base):
    """Conversation between post owner and an interested user."""

    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    post_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    initiator_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    last_message_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        index=True,
        nullable=True,
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    post: Mapped["Post"] = relationship(
        "Post",
        back_populates="conversations",
    )
    initiator: Mapped["User"] = relationship(
        "User",
        foreign_keys=[initiator_id],
        back_populates="initiated_conversations",
    )
    owner: Mapped["User"] = relationship(
        "User",
        foreign_keys=[owner_id],
        back_populates="owned_conversations",
    )
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )

    __table_args__ = (
        CheckConstraint("initiator_id != owner_id", name="ck_conversation_initiator_not_owner"),
        UniqueConstraint("post_id", "initiator_id", name="uq_conversation_post_initiator"),
    )
