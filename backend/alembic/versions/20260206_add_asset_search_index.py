"""add_asset_search_index

Revision ID: 20260206_add_asset_search_index
Revises: 20260204_add_unique_asset_property_name
Create Date: 2026-02-06 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260206_add_asset_search_index"
down_revision: str | None = "20260204_add_unique_asset_property_name"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add asset_search_index table for blind index search."""
    op.create_table(
        "asset_search_index",
        sa.Column("asset_id", sa.String(), nullable=False),
        sa.Column("field_name", sa.String(length=50), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("key_version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["asset_id"], ["assets.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint(
            "asset_id", "field_name", "token_hash", "key_version"
        ),
    )
    op.create_index(
        "ix_asset_search_index_field_token_version",
        "asset_search_index",
        ["field_name", "token_hash", "key_version"],
        unique=False,
    )
    op.create_index(
        "ix_asset_search_index_asset_field",
        "asset_search_index",
        ["asset_id", "field_name"],
        unique=False,
    )


def downgrade() -> None:
    """Drop asset_search_index table."""
    op.drop_index(
        "ix_asset_search_index_asset_field", table_name="asset_search_index"
    )
    op.drop_index(
        "ix_asset_search_index_field_token_version", table_name="asset_search_index"
    )
    op.drop_table("asset_search_index")
