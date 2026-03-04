"""rename asset business_model column to revenue_mode

Revision ID: 20260304_rename_asset_business_model_to_revenue_mode
Revises: 20260224_backfill_ownership_occupancy_policy_rules
Create Date: 2026-03-04 16:00:00.000000

"""

from collections.abc import Sequence

from sqlalchemy import inspect

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260304_rename_asset_business_model_to_revenue_mode"
down_revision: str | None = "20260224_backfill_ownership_occupancy_policy_rules"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE_NAME = "assets"
_OLD_COLUMN = "business_model"
_NEW_COLUMN = "revenue_mode"


def _get_asset_columns() -> set[str] | None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table(_TABLE_NAME):
        return None
    return {str(column["name"]) for column in inspector.get_columns(_TABLE_NAME)}


def upgrade() -> None:
    columns = _get_asset_columns()
    if columns is None:
        return

    if _OLD_COLUMN in columns and _NEW_COLUMN not in columns:
        op.alter_column(_TABLE_NAME, _OLD_COLUMN, new_column_name=_NEW_COLUMN)
        return

    if _NEW_COLUMN in columns and _OLD_COLUMN not in columns:
        return

    columns_text = ", ".join(sorted(columns))
    raise RuntimeError(
        f"Unexpected column state for {_TABLE_NAME}: {columns_text}. "
        f"Expected exactly one of '{_OLD_COLUMN}' or '{_NEW_COLUMN}'."
    )


def downgrade() -> None:
    columns = _get_asset_columns()
    if columns is None:
        return

    if _NEW_COLUMN in columns and _OLD_COLUMN not in columns:
        op.alter_column(_TABLE_NAME, _NEW_COLUMN, new_column_name=_OLD_COLUMN)
        return

    if _OLD_COLUMN in columns and _NEW_COLUMN not in columns:
        return

    columns_text = ", ".join(sorted(columns))
    raise RuntimeError(
        f"Unexpected column state for {_TABLE_NAME}: {columns_text}. "
        f"Expected exactly one of '{_OLD_COLUMN}' or '{_NEW_COLUMN}'."
    )
