"""add_whatsapp_fields_to_users

Revision ID: d9a1f2e3b4c5
Revises: c8f5e3a1b2d4
Create Date: 2026-10-06 15:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d9a1f2e3b4c5"
down_revision: Union[str, Sequence[str], None] = "c8f5e3a1b2d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("whatsapp_number", sa.String(length=32), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "whatsapp_enabled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "whatsapp_enabled")
    op.drop_column("users", "whatsapp_number")
