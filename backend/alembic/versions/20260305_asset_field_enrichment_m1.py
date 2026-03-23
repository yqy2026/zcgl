"""asset field enrichment for M1: rename property_name, add classification and address sub-fields, review fields

Revision ID: 20260305_asset_field_enrichment_m1
Revises: 20260304_rename_asset_business_model_to_revenue_mode
Create Date: 2026-03-05 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260305_asset_field_enrichment_m1"
down_revision: str | None = "20260304_rename_asset_business_model_to_revenue_mode"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── 1. rename property_name → asset_name ─────────────────────────────────
    op.alter_column("assets", "property_name", new_column_name="asset_name")

    # ── 2. add new columns (all nullable initially) ───────────────────────────
    op.add_column("assets", sa.Column("asset_code", sa.String(50), nullable=True))
    op.add_column("assets", sa.Column("asset_form", sa.String(20), nullable=True))
    op.add_column("assets", sa.Column("spatial_level", sa.String(20), nullable=True))
    op.add_column("assets", sa.Column("business_usage", sa.String(20), nullable=True))
    op.add_column("assets", sa.Column("province_code", sa.String(20), nullable=True))
    op.add_column("assets", sa.Column("city_code", sa.String(20), nullable=True))
    op.add_column("assets", sa.Column("district_code", sa.String(20), nullable=True))
    op.add_column("assets", sa.Column("address_detail", sa.String(200), nullable=True))
    op.add_column(
        "assets",
        sa.Column("review_status", sa.String(20), nullable=False, server_default="draft"),
    )
    op.add_column("assets", sa.Column("review_by", sa.String(100), nullable=True))
    op.add_column("assets", sa.Column("reviewed_at", sa.DateTime, nullable=True))
    op.add_column("assets", sa.Column("review_reason", sa.Text, nullable=True))

    # ── 3. unique index on asset_code ─────────────────────────────────────────
    op.create_index("ix_assets_asset_code", "assets", ["asset_code"], unique=True)
    op.create_index("ix_assets_asset_form", "assets", ["asset_form"])

    # ── 4. backfill placeholder values for classification fields ──────────────
    op.execute(
        """
        UPDATE assets
        SET
            asset_form     = 'other',
            spatial_level  = 'building',
            business_usage = 'commercial'
        WHERE asset_form IS NULL
        """
    )


def downgrade() -> None:
    # 删除新加索引
    op.drop_index("ix_assets_asset_form", table_name="assets")
    op.drop_index("ix_assets_asset_code", table_name="assets")

    # 删除新加列
    for col in [
        "review_reason",
        "reviewed_at",
        "review_by",
        "review_status",
        "address_detail",
        "district_code",
        "city_code",
        "province_code",
        "business_usage",
        "spatial_level",
        "asset_form",
        "asset_code",
    ]:
        op.drop_column("assets", col)

    # rename back
    op.alter_column("assets", "asset_name", new_column_name="property_name")
