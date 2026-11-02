"""Add occupancy-report line snapshots and reporting receipt command kinds.

Revision ID: 20261031_report_lines_receipts
Revises: 20261031_occupancy_reports
Create Date: 2026-10-31
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20261031_report_lines_receipts"
down_revision: str | Sequence[str] | None = "20261031_occupancy_reports"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_RECEIPT_COMMAND_KINDS = (
    "'create_upstream', 'create_terminal', 'correct_rent_schedule', "
    "'create_manual_rent_entry', 'void_manual_rent_entry', 'terminate_terminal', "
    "'defer_management_fee_line', 'confirm_management_fee_statement', "
    "'supersede_management_fee_statement', 'commit_assessment_scope', "
    "'submit_occupancy_report', 'withdraw_occupancy_report'"
)


def upgrade() -> None:
    op.create_table(
        "monthly_occupancy_report_lines",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("report_id", sa.String(length=36), nullable=False),
        sa.Column("asset_unit_id", sa.String(length=36), nullable=False),
        sa.Column("owner_name_snapshot", sa.String(length=200), nullable=False),
        sa.Column("usage_type_snapshot", sa.String(length=100), nullable=False),
        sa.Column("project_name_snapshot", sa.String(length=200), nullable=False),
        sa.Column("address_snapshot", sa.String(length=500), nullable=False),
        sa.Column("land_area", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("building_area", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("rentable_area", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("rented_area", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column(
            "unit_count", sa.Integer(), nullable=False, server_default="1"
        ),
        sa.Column("rented_unit_count", sa.Integer(), nullable=False),
        sa.Column("rental_status", sa.String(length=20), nullable=False),
        sa.Column(
            "terminal_contract_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.CheckConstraint(
            "rental_status IN ('rented', 'vacant', 'non_rentable')",
            name="ck_monthly_occupancy_report_lines_rental_status",
        ),
        sa.CheckConstraint(
            "unit_count = 1",
            name="ck_monthly_occupancy_report_lines_unit_count",
        ),
        sa.CheckConstraint(
            "rented_unit_count IN (0, 1)",
            name="ck_monthly_occupancy_report_lines_rented_unit_count",
        ),
        sa.CheckConstraint(
            "land_area >= 0 AND building_area >= 0 AND rentable_area >= 0 "
            "AND rented_area >= 0",
            name="ck_monthly_occupancy_report_lines_areas_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["report_id"],
            ["monthly_occupancy_reports.id"],
            name="fk_monthly_occupancy_report_lines_report",
        ),
        sa.ForeignKeyConstraint(
            ["asset_unit_id"],
            ["asset_units.id"],
            name="fk_monthly_occupancy_report_lines_asset_unit",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_monthly_occupancy_report_lines"),
        sa.UniqueConstraint(
            "report_id",
            "asset_unit_id",
            name="uq_monthly_occupancy_report_lines_report_unit",
        ),
    )
    op.create_index(
        "ix_monthly_occupancy_report_lines_report",
        "monthly_occupancy_report_lines",
        ["report_id"],
    )

    op.drop_constraint(
        "ck_asset_contract_write_receipts_command_kind",
        "asset_contract_write_receipts",
        type_="check",
    )
    op.create_check_constraint(
        "ck_asset_contract_write_receipts_command_kind",
        "asset_contract_write_receipts",
        f"command_kind IN ({_RECEIPT_COMMAND_KINDS})",
    )


def downgrade() -> None:
    raise RuntimeError(
        "Occupancy-report line snapshots are immutable reporting evidence; "
        "roll forward with a corrective migration instead"
    )
