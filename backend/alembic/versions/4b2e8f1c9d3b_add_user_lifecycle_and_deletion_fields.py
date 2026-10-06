"""add_user_lifecycle_and_deletion_fields

Revision ID: 4b2e8f1c9d3b
Revises: 3a1c5d9e0f2a
Create Date: 2026-10-06 03:50:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4b2e8f1c9d3b"
down_revision: Union[str, Sequence[str], None] = "3a1c5d9e0f2a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add account lifecycle and deletion tracking fields to users table."""
    op.add_column(
        "users",
        sa.Column("status", sa.String(length=32), server_default="ACTIVE", nullable=False),
    )
    op.create_index("ix_users_status", "users", ["status"])
    op.add_column(
        "users",
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("inactive_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("deletion_requested_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("deletion_scheduled_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Initialize last_activity_at and last_login_at from created_at for existing users
    op.execute(
        sa.text(
            "UPDATE users SET last_activity_at = created_at, last_login_at = created_at WHERE last_activity_at IS NULL"
        )
    )


def downgrade() -> None:
    """Remove account lifecycle and deletion tracking fields from users table."""
    op.drop_column("users", "deletion_scheduled_at")
    op.drop_column("users", "deletion_requested_at")
    op.drop_column("users", "inactive_at")
    op.drop_column("users", "last_login_at")
    op.drop_column("users", "last_activity_at")
    op.drop_index("ix_users_status", table_name="users")
    op.drop_column("users", "status")
