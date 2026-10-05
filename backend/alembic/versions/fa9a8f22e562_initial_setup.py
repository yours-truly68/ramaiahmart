"""initial_setup

Revision ID: fa9a8f22e562
Revises:
Create Date: 2026-10-05 14:15:04.783110

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "fa9a8f22e562"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
