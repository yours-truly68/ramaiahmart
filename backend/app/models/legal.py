import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class LegalDocument(Base):
    """Versioned platform legal document (Terms of Service, Privacy Policy)."""

    __tablename__ = "legal_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    document_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
        doc="Document category: 'TERMS' or 'PRIVACY'",
    )
    version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        doc="Semantic version string, e.g. '1.0'",
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Full legal text content or markdown",
    )
    effective_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    is_current: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="True if this is the active enforceable version",
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

    __table_args__ = (
        UniqueConstraint("document_type", "version", name="uq_legal_documents_type_version"),
        Index("ix_legal_documents_type_current", "document_type", "is_current"),
    )


class LegalConsent(Base):
    """Server-side audit record of user acceptance of a legal document version."""

    __tablename__ = "legal_consents"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        doc="'TERMS' or 'PRIVACY'",
    )
    document_version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        doc="Version string accepted, e.g. '1.0'",
    )
    accepted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    ip_address: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        doc="Client IP address at acceptance for audit purposes",
    )
    user_agent: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        doc="Client user-agent string at acceptance",
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="legal_consents",
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "document_type",
            "document_version",
            name="uq_legal_consents_user_doc_version",
        ),
        Index("ix_legal_consents_lookup", "user_id", "document_type"),
    )
