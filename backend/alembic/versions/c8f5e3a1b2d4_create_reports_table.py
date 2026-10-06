"""create_reports_table_and_link_moderation

Revision ID: c8f5e3a1b2d4
Revises: b7e4a2c8d1f5
Create Date: 2026-10-06 14:50:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c8f5e3a1b2d4"
down_revision: Union[str, Sequence[str], None] = "b7e4a2c8d1f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

report_reason_enum = postgresql.ENUM(
    "EXPLICIT_IMAGE",
    "IMAGE_MISMATCH",
    "AUTHENTICITY_SUSPICION",
    "SCAM_OR_MISLEADING",
    "SPAM",
    "OTHER",
    name="report_reason",
    create_type=False,
)

report_status_enum = postgresql.ENUM(
    "OPEN",
    "AI_REVIEWED",
    "UNDER_REVIEW",
    "RESOLVED",
    "DISMISSED",
    name="report_status",
    create_type=False,
)


def upgrade() -> None:
    # 1. Create native enum types
    bind = op.get_bind()
    report_reason_enum.create(bind, checkfirst=True)
    report_status_enum.create(bind, checkfirst=True)

    # 2. Create reports table
    op.create_table(
        "reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("post_id", sa.Uuid(), nullable=False),
        sa.Column("reporter_id", sa.Uuid(), nullable=False),
        sa.Column("reason", report_reason_enum, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            report_status_enum,
            server_default="OPEN",
            nullable=False,
        ),
        sa.Column("ai_reviewed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("ai_decision", sa.String(length=50), nullable=True),
        sa.Column("ai_reason", sa.String(length=255), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reporter_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(op.f("ix_reports_post_id"), "reports", ["post_id"], unique=False)
    op.create_index(op.f("ix_reports_reporter_id"), "reports", ["reporter_id"], unique=False)
    op.create_index(op.f("ix_reports_reason"), "reports", ["reason"], unique=False)
    op.create_index(op.f("ix_reports_status"), "reports", ["status"], unique=False)
    op.create_index(op.f("ix_reports_created_at"), "reports", ["created_at"], unique=False)
    op.create_index("ix_reports_post_reporter", "reports", ["post_id", "reporter_id"], unique=False)
    op.create_index(
        "ix_reports_status_created_at", "reports", ["status", "created_at"], unique=False
    )

    # 3. Add report_id to moderation_results
    op.add_column("moderation_results", sa.Column("report_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_moderation_results_report_id",
        "moderation_results",
        "reports",
        ["report_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        op.f("ix_moderation_results_report_id"),
        "moderation_results",
        ["report_id"],
        unique=False,
    )


def downgrade() -> None:
    # 1. Remove report_id from moderation_results
    op.drop_index(op.f("ix_moderation_results_report_id"), table_name="moderation_results")
    op.drop_constraint("fk_moderation_results_report_id", "moderation_results", type_="foreignkey")
    op.drop_column("moderation_results", "report_id")

    # 2. Drop reports table
    op.drop_index("ix_reports_status_created_at", table_name="reports")
    op.drop_index("ix_reports_post_reporter", table_name="reports")
    op.drop_index(op.f("ix_reports_created_at"), table_name="reports")
    op.drop_index(op.f("ix_reports_status"), table_name="reports")
    op.drop_index(op.f("ix_reports_reason"), table_name="reports")
    op.drop_index(op.f("ix_reports_reporter_id"), table_name="reports")
    op.drop_index(op.f("ix_reports_post_id"), table_name="reports")
    op.drop_table("reports")

    # 3. Drop enum types
    bind = op.get_bind()
    report_status_enum.drop(bind, checkfirst=True)
    report_reason_enum.drop(bind, checkfirst=True)
