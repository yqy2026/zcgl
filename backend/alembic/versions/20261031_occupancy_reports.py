"""Create monthly occupancy-report chain table for asset-operations v5.

Revision ID: 20261031_occupancy_reports
Revises: 20261030_assessment_scopes
Create Date: 2026-10-31
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261031_occupancy_reports"
down_revision: str | Sequence[str] | None = "20261030_assessment_scopes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "monthly_occupancy_reports",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("operator_party_id", sa.String(), nullable=False),
        sa.Column("period", sa.String(length=7), nullable=False),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="draft"
        ),
        sa.Column("scope_version_id", sa.String(length=36), nullable=True),
        sa.Column("change_note", sa.Text(), nullable=True),
        sa.Column("project_count", sa.Integer(), nullable=True),
        sa.Column("operating_project_count", sa.Integer(), nullable=True),
        sa.Column("non_operating_project_count", sa.Integer(), nullable=True),
        sa.Column("unit_count", sa.Integer(), nullable=True),
        sa.Column("rented_unit_count", sa.Integer(), nullable=True),
        sa.Column("occupancy_rate", sa.Numeric(precision=19, scale=10), nullable=True),
        sa.Column("land_area", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("building_area", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("rentable_area", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("rented_area", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("submitted_by", sa.String(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("withdrawn_by", sa.String(), nullable=True),
        sa.Column("withdrawn_at", sa.DateTime(), nullable=True),
        sa.Column("withdraw_reason", sa.Text(), nullable=True),
        sa.Column("predecessor_report_id", sa.String(length=36), nullable=True),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.CheckConstraint(
            "status IN ('draft', 'submitted', 'withdrawn')",
            name="ck_monthly_occupancy_reports_status",
        ),
        sa.CheckConstraint(
            "period ~ '^[0-9]{4}-(0[1-9]|1[0-2])$'",
            name="ck_monthly_occupancy_reports_period_format",
        ),
        sa.CheckConstraint(
            "unit_count IS NULL OR unit_count >= 0",
            name="ck_monthly_occupancy_reports_unit_count",
        ),
        sa.CheckConstraint(
            "rented_unit_count IS NULL OR rented_unit_count >= 0",
            name="ck_monthly_occupancy_reports_rented_unit_count",
        ),
        sa.CheckConstraint(
            "land_area IS NULL OR land_area >= 0",
            name="ck_monthly_occupancy_reports_land_area",
        ),
        sa.CheckConstraint(
            "building_area IS NULL OR building_area >= 0",
            name="ck_monthly_occupancy_reports_building_area",
        ),
        sa.CheckConstraint(
            "rentable_area IS NULL OR rentable_area >= 0",
            name="ck_monthly_occupancy_reports_rentable_area",
        ),
        sa.CheckConstraint(
            "rented_area IS NULL OR rented_area >= 0",
            name="ck_monthly_occupancy_reports_rented_area",
        ),
        sa.ForeignKeyConstraint(
            ["operator_party_id"],
            ["parties.id"],
            name="fk_monthly_occupancy_reports_operator_party",
        ),
        sa.ForeignKeyConstraint(
            ["scope_version_id"],
            ["assessment_scope_versions.id"],
            name="fk_monthly_occupancy_reports_scope_version",
        ),
        sa.ForeignKeyConstraint(
            ["submitted_by"],
            ["users.id"],
            name="fk_monthly_occupancy_reports_submitted_by",
        ),
        sa.ForeignKeyConstraint(
            ["withdrawn_by"],
            ["users.id"],
            name="fk_monthly_occupancy_reports_withdrawn_by",
        ),
        sa.ForeignKeyConstraint(
            ["predecessor_report_id"],
            ["monthly_occupancy_reports.id"],
            name="fk_monthly_occupancy_reports_predecessor",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_monthly_occupancy_reports_created_by",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_monthly_occupancy_reports"),
    )
    op.create_index(
        "uq_monthly_occupancy_reports_active_chain",
        "monthly_occupancy_reports",
        ["operator_party_id", "period"],
        unique=True,
        postgresql_where=sa.text("status <> 'withdrawn'"),
    )
    op.create_index(
        "ix_monthly_occupancy_reports_operator_period",
        "monthly_occupancy_reports",
        ["operator_party_id", "period"],
    )


def downgrade() -> None:
    raise RuntimeError(
        "Monthly occupancy reports are append-only reporting evidence; "
        "roll forward with a corrective migration instead"
    )
