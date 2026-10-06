"""remove_email_verification_and_clear_university_deadlock

V1 policy: RamaiahMart does not send authentication emails. The OTP
email-verification flow is removed entirely, and every existing account is
marked university_verified=True so no production flow waits for a verification
state that can no longer be reached.

Revision ID: b7e4a2c8d1f5
Revises: 4b2e8f1c9d3b
Create Date: 2026-10-06 10:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7e4a2c8d1f5"
down_revision: Union[str, Sequence[str], None] = "4b2e8f1c9d3b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop the OTP table and clear the university-verification deadlock."""
    op.drop_table("email_verification_codes")

    # V1 deadlock removal: automated email verification no longer exists, so no
    # account may remain blocked on a verification state that is unreachable.
    op.execute(sa.text("UPDATE users SET university_verified = true"))
    op.alter_column(
        "users",
        "university_verified",
        server_default=sa.text("true"),
        existing_type=sa.Boolean(),
        nullable=False,
    )


def downgrade() -> None:
    """Restore the OTP verification table (data is not recoverable)."""
    op.alter_column(
        "users",
        "university_verified",
        server_default=sa.text("false"),
        existing_type=sa.Boolean(),
        nullable=False,
    )
    op.execute(sa.text("UPDATE users SET university_verified = false"))
    op.create_table(
        "email_verification_codes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_email_verification_codes_user_id"),
        "email_verification_codes",
        ["user_id"],
    )
    op.create_index(
        op.f("ix_email_verification_codes_code"),
        "email_verification_codes",
        ["code"],
    )
