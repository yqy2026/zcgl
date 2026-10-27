"""Create asset-operations v5 asset-unit source tables.

Revision ID: 20261023_asset_operations_v5_asset_units
Revises: 20260808_drop_unused_tables_fields
Create Date: 2026-10-23
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20261023_asset_operations_v5_asset_units"
down_revision: str | Sequence[str] | None = "20260808_drop_unused_tables_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "asset_units",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("unit_code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("owner_party_id", sa.String(), nullable=False),
        sa.Column("address", sa.String(length=500), nullable=False),
        sa.Column("usage_type", sa.String(length=100), nullable=False),
        sa.Column("acquisition_mode", sa.String(length=20), nullable=False),
        sa.Column(
            "is_operating", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column(
            "land_area",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            server_default="0",
        ),
        sa.Column("building_area", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("rentable_area", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("managed_from", sa.Date(), nullable=False),
        sa.Column("managed_to", sa.Date(), nullable=True),
        sa.Column("vacancy_reason", sa.String(length=30), nullable=True),
        sa.Column("expected_lease_start", sa.Date(), nullable=True),
        sa.Column(
            "predecessor_unit_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")
        ),
        sa.CheckConstraint(
            "acquisition_mode IN ('owned', 'leased', 'managed')",
            name="ck_asset_units_acquisition_mode",
        ),
        sa.CheckConstraint(
            "land_area >= 0", name="ck_asset_units_land_area_nonnegative"
        ),
        sa.CheckConstraint(
            "building_area >= 0", name="ck_asset_units_building_area_nonnegative"
        ),
        sa.CheckConstraint(
            "rentable_area >= 0 AND rentable_area <= building_area",
            name="ck_asset_units_rentable_area_valid",
        ),
        sa.CheckConstraint(
            "managed_to IS NULL OR managed_to >= managed_from",
            name="ck_asset_units_managed_range",
        ),
        sa.CheckConstraint(
            "vacancy_reason IS NULL OR vacancy_reason IN "
            "('renovation', 'marketing', 'repossession', "
            "'pending_contract', 'other')",
            name="ck_asset_units_vacancy_reason",
        ),
        sa.ForeignKeyConstraint(
            ["owner_party_id"],
            ["parties.id"],
            name="fk_asset_units_owner_party",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name="fk_asset_units_project"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_asset_units"),
        sa.UniqueConstraint("unit_code", name="uq_asset_units_unit_code"),
    )
    op.create_index("ix_asset_units_project_id", "asset_units", ["project_id"])
    op.create_index("ix_asset_units_owner_party_id", "asset_units", ["owner_party_id"])
    op.create_index("ix_asset_units_managed_from", "asset_units", ["managed_from"])

    op.create_table(
        "asset_unit_boundary_changes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("change_type", sa.String(length=20), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column(
            "source_unit_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "result_unit_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "area_check",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")
        ),
        sa.Column("idempotency_key", sa.String(length=100), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column(
            "result_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.CheckConstraint(
            "change_type IN ('split', 'merge')",
            name="ck_asset_unit_boundary_changes_type",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(source_unit_ids) = 'array' "
            "AND jsonb_array_length(source_unit_ids) >= 1",
            name="ck_asset_unit_boundary_changes_source_units",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(result_unit_ids) = 'array' "
            "AND jsonb_array_length(result_unit_ids) >= 1",
            name="ck_asset_unit_boundary_changes_result_units",
        ),
        sa.CheckConstraint(
            "(change_type = 'split' AND jsonb_array_length(result_unit_ids) >= 2) "
            "OR (change_type = 'merge' AND jsonb_array_length(source_unit_ids) >= 2)",
            name="ck_asset_unit_boundary_changes_shape",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(area_check) = 'object'",
            name="ck_asset_unit_boundary_changes_area_check",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="fk_asset_unit_changes_created_by"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_asset_unit_boundary_changes"),
        sa.UniqueConstraint(
            "created_by",
            "idempotency_key",
            name="uq_asset_unit_boundary_changes_actor_request",
        ),
    )
    op.create_index(
        "ix_asset_unit_boundary_changes_effective_date",
        "asset_unit_boundary_changes",
        ["effective_date"],
    )

    op.create_table(
        "asset_unit_boundary_sources",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("asset_unit_id", sa.String(length=36), nullable=False),
        sa.Column("boundary_change_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(
            ["asset_unit_id"],
            ["asset_units.id"],
            name="fk_asset_unit_boundary_sources_unit",
        ),
        sa.ForeignKeyConstraint(
            ["boundary_change_id"],
            ["asset_unit_boundary_changes.id"],
            name="fk_asset_unit_boundary_sources_change",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_asset_unit_boundary_sources"),
        sa.UniqueConstraint(
            "asset_unit_id",
            name="uq_asset_unit_boundary_sources_unit",
        ),
    )

    op.create_table(
        "property_certificate_asset_units",
        sa.Column("certificate_id", sa.String(), nullable=False),
        sa.Column("asset_unit_id", sa.String(length=36), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="ck_property_certificate_asset_units_effective_range",
        ),
        sa.ForeignKeyConstraint(
            ["asset_unit_id"],
            ["asset_units.id"],
            name="fk_property_certificate_asset_units_unit",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["certificate_id"],
            ["property_certificates.id"],
            name="fk_property_certificate_asset_units_certificate",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "certificate_id",
            "asset_unit_id",
            name="pk_property_certificate_asset_units",
        ),
    )


def downgrade() -> None:
    raise RuntimeError(
        "asset-operations v5 asset-unit schema is irreversible; "
        "roll forward with a corrective migration"
    )
