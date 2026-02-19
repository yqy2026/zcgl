"""enable_btree_gist_extension

Revision ID: 20260219_enable_btree_gist_extension
Revises: 20260211_add_organization_scope_columns
Create Date: 2026-02-19 11:20:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260219_enable_btree_gist_extension"
down_revision: str | None = "20260211_add_organization_scope_columns"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Ensure btree_gist is available for exclusion constraints."""
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")


def downgrade() -> None:
    """Keep extension in place to avoid side effects in shared databases."""
    return None
