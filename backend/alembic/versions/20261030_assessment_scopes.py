"""Create assessment-scope version tables for asset-operations v5 reporting.

Revision ID: 20261030_assessment_scopes
Revises: 20261029_fee_attachments
Create Date: 2026-10-30
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20261030_assessment_scopes"
down_revision: str | Sequence[str] | None = "20261029_fee_attachments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_RECEIPT_COMMAND_KINDS = (
    "'create_upstream', 'create_terminal', 'correct_rent_schedule', "
    "'create_manual_rent_entry', 'void_manual_rent_entry', 'terminate_terminal', "
    "'defer_management_fee_line', 'confirm_management_fee_statement', "
    "'supersede_management_fee_statement', 'commit_assessment_scope'"
)


def upgrade() -> None:
    op.create_table(
        "assessment_scope_versions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("operator_party_id", sa.String(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=True),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="draft"
        ),
        sa.Column("effective_from_period", sa.String(length=7), nullable=False),
        sa.Column("based_on_version_id", sa.String(length=36), nullable=True),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")
        ),
        sa.Column("activated_by", sa.String(), nullable=True),
        sa.Column("activated_at", sa.DateTime(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.CheckConstraint(
            "status IN ('draft', 'active', 'superseded')",
            name="ck_assessment_scope_versions_status",
        ),
        sa.CheckConstraint(
            "(status = 'draft' AND version_number IS NULL) "
            "OR (status <> 'draft' AND version_number >= 1)",
            name="ck_assessment_scope_versions_number",
        ),
        sa.ForeignKeyConstraint(
            ["operator_party_id"],
            ["parties.id"],
            name="fk_assessment_scope_versions_operator_party",
        ),
        sa.ForeignKeyConstraint(
            ["based_on_version_id"],
            ["assessment_scope_versions.id"],
            name="fk_assessment_scope_versions_based_on",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="fk_assessment_scope_versions_created_by"
        ),
        sa.ForeignKeyConstraint(
            ["activated_by"],
            ["users.id"],
            name="fk_assessment_scope_versions_activated_by",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_assessment_scope_versions"),
        sa.UniqueConstraint(
            "operator_party_id",
            "year",
            "version_number",
            name="uq_assessment_scope_versions_number",
        ),
    )
    op.create_index(
        "ix_assessment_scope_versions_operator",
        "assessment_scope_versions",
        ["operator_party_id", "year"],
    )
    op.create_index(
        "uq_assessment_scope_versions_active",
        "assessment_scope_versions",
        ["operator_party_id", "year"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )
    op.create_index(
        "uq_assessment_scope_versions_draft",
        "assessment_scope_versions",
        ["operator_party_id", "year"],
        unique=True,
        postgresql_where=sa.text("status = 'draft'"),
    )

    op.create_table(
        "assessment_scope_items",
        sa.Column("scope_version_id", sa.String(length=36), nullable=False),
        sa.Column("asset_unit_id", sa.String(length=36), nullable=False),
        sa.Column("included", sa.Boolean(), nullable=False),
        sa.Column("exclusion_reason", sa.Text(), nullable=True),
        sa.Column(
            "unit_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.CheckConstraint(
            "included = TRUE OR (exclusion_reason IS NOT NULL "
            "AND btrim(exclusion_reason) <> '')",
            name="ck_assessment_scope_items_exclusion_reason",
        ),
        sa.ForeignKeyConstraint(
            ["scope_version_id"],
            ["assessment_scope_versions.id"],
            name="fk_assessment_scope_items_version",
        ),
        sa.ForeignKeyConstraint(
            ["asset_unit_id"],
            ["asset_units.id"],
            name="fk_assessment_scope_items_asset_unit",
        ),
        sa.PrimaryKeyConstraint(
            "scope_version_id", "asset_unit_id", name="pk_assessment_scope_items"
        ),
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
        "Assessment-scope versions are append-only reporting evidence; "
        "roll forward with a corrective migration instead"
    )
