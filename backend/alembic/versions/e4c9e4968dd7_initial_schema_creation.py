"""Initial schema creation

Revision ID: e4c9e4968dd7
Revises:
Create Date: 2026-01-17 11:05:39.118899

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "e4c9e4968dd7"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
