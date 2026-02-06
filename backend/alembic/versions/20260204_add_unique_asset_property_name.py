"""add_unique_asset_property_name

Revision ID: 20260204_add_unique_asset_property_name
Revises: c6fd8148eb25
Create Date: 2026-02-04 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260204_add_unique_asset_property_name"
down_revision: str | None = "c6fd8148eb25"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add unique constraint on assets.property_name."""
    op.create_unique_constraint("uq_assets_property_name", "assets", ["property_name"])


def downgrade() -> None:
    """Remove unique constraint on assets.property_name."""
    op.drop_constraint("uq_assets_property_name", "assets", type_="unique")
