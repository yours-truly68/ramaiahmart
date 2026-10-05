"""create_legal_tables

Revision ID: 3a1c5d9e0f2a
Revises: 224e9d0e8b4e
Create Date: 2026-10-06 02:50:00.000000

"""

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3a1c5d9e0f2a"
down_revision: Union[str, Sequence[str], None] = "224e9d0e8b4e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create legal_documents and legal_consents tables and seed initial 1.0 records."""
    legal_documents = op.create_table(
        "legal_documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_type", sa.String(length=32), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "effective_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "is_current",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_type", "version", name="uq_legal_documents_type_version"),
    )
    op.create_index(
        "ix_legal_documents_type_current",
        "legal_documents",
        ["document_type", "is_current"],
        unique=False,
    )
    op.create_index(
        op.f("ix_legal_documents_document_type"),
        "legal_documents",
        ["document_type"],
        unique=False,
    )

    op.create_table(
        "legal_consents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("document_type", sa.String(length=32), nullable=False),
        sa.Column("document_version", sa.String(length=32), nullable=False),
        sa.Column(
            "accepted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "document_type",
            "document_version",
            name="uq_legal_consents_user_doc_version",
        ),
    )
    op.create_index(
        "ix_legal_consents_lookup",
        "legal_consents",
        ["user_id", "document_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_legal_consents_user_id"),
        "legal_consents",
        ["user_id"],
        unique=False,
    )

    # Seed initial active versions: TERMS 1.0 and PRIVACY 1.0
    terms_id = uuid.uuid4()
    privacy_id = uuid.uuid4()
    op.bulk_insert(
        legal_documents,
        [
            {
                "id": terms_id,
                "document_type": "TERMS",
                "version": "1.0",
                "title": "RamaiahMart Terms & Conditions",
                "content": "Official RamaiahMart Terms & Conditions governing campus marketplace access, student verification, peer transactions, and conduct rules.",
                "is_current": True,
            },
            {
                "id": privacy_id,
                "document_type": "PRIVACY",
                "version": "1.0",
                "title": "RamaiahMart Privacy Policy",
                "content": "Official RamaiahMart Privacy Policy explaining information collection, university verification, cookies, and data retention on campus.",
                "is_current": True,
            },
        ],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_legal_consents_user_id"), table_name="legal_consents")
    op.drop_index("ix_legal_consents_lookup", table_name="legal_consents")
    op.drop_table("legal_consents")
    op.drop_index(op.f("ix_legal_documents_document_type"), table_name="legal_documents")
    op.drop_index("ix_legal_documents_type_current", table_name="legal_documents")
    op.drop_table("legal_documents")
