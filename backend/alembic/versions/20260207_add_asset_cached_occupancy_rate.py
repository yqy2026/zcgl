"""add generated cached_occupancy_rate column for asset sorting/filtering

Revision ID: 20260207_add_asset_cached_occupancy_rate
Revises: 20260207_drop_legacy_dynamic_permission_tables
Create Date: 2026-02-07 18:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260207_add_asset_cached_occupancy_rate"
down_revision: str | None = "20260207_drop_legacy_dynamic_permission_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ASSET_TABLE = "assets"
OCCUPANCY_COLUMN = "cached_occupancy_rate"
OCCUPANCY_INDEX = "ix_assets_cached_occupancy_rate_active"

OCCUPANCY_EXPRESSION = (
    "CASE "
    "WHEN include_in_occupancy_rate = false THEN 0 "
    "WHEN COALESCE(rentable_area, 0) = 0 THEN 0 "
    "ELSE ROUND((COALESCE(rented_area, 0) / NULLIF(rentable_area, 0)) * 100, 2) "
    "END"
)


def _column_exists(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _index_exists(table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    if not _column_exists(ASSET_TABLE, OCCUPANCY_COLUMN):
        op.execute(
            sa.text(
                f"""
                ALTER TABLE {ASSET_TABLE}
                ADD COLUMN {OCCUPANCY_COLUMN} NUMERIC(7,2)
                GENERATED ALWAYS AS ({OCCUPANCY_EXPRESSION}) STORED
                """
            )
        )

    if not _index_exists(ASSET_TABLE, OCCUPANCY_INDEX):
        op.execute(
            sa.text(
                f"""
                CREATE INDEX {OCCUPANCY_INDEX}
                ON {ASSET_TABLE} ({OCCUPANCY_COLUMN})
                WHERE data_status <> '已删除'
                """
            )
        )


def downgrade() -> None:
    if _index_exists(ASSET_TABLE, OCCUPANCY_INDEX):
        op.drop_index(OCCUPANCY_INDEX, table_name=ASSET_TABLE)

    if _column_exists(ASSET_TABLE, OCCUPANCY_COLUMN):
        op.execute(sa.text(f"ALTER TABLE {ASSET_TABLE} DROP COLUMN {OCCUPANCY_COLUMN}"))
