"""add_unique_asset_property_name

Revision ID: 20260204_add_unique_asset_property_name
Revises: c6fd8148eb25
Create Date: 2026-02-04 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260204_add_unique_asset_property_name"
down_revision: str | None = "c6fd8148eb25"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _ensure_alembic_version_capacity() -> None:
    """Ensure alembic_version.version_num can store long revision ids."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "alembic_version" not in inspector.get_table_names():
        return

    columns = {column["name"]: column for column in inspector.get_columns("alembic_version")}
    version_column = columns.get("version_num")
    if version_column is None:
        return

    current_length = getattr(version_column["type"], "length", None)
    if current_length is None or current_length >= 64:
        return

    op.alter_column(
        "alembic_version",
        "version_num",
        existing_type=sa.String(length=current_length),
        type_=sa.String(length=64),
        nullable=False,
    )


def upgrade() -> None:
    """Add unique constraint on assets.property_name."""
    _ensure_alembic_version_capacity()
    op.create_unique_constraint("uq_assets_property_name", "assets", ["property_name"])


def downgrade() -> None:
    """Remove unique constraint on assets.property_name."""
    op.drop_constraint("uq_assets_property_name", "assets", type_="unique")
