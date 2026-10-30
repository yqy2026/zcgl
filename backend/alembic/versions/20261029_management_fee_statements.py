"""Add management fee statement identities and confirmation snapshots.

Revision ID: 20261029_management_fees
Revises: 20261028_termination_receipts
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "20261029_management_fees"
down_revision = "20261028_termination_receipts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "management_fee_statements",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "owner_party_id", sa.String(36), sa.ForeignKey("parties.id"), nullable=False
        ),
        sa.Column("period", sa.String(7), nullable=False),
        sa.Column("statement_number", sa.String(100), nullable=False, unique=True),
        sa.Column(
            "upstream_contract_ids",
            sa.JSON(none_as_null=True).with_variant(
                JSONB(none_as_null=True), "postgresql"
            ),
        ),
        sa.Column("base_amount", sa.Numeric(14, 2)),
        sa.Column("fee_amount", sa.Numeric(14, 2)),
        sa.Column("status", sa.String(20)),
        sa.Column(
            "stamped_document_id", sa.String(36), sa.ForeignKey("attachments.id")
        ),
        sa.Column("confirmed_at", sa.DateTime(timezone=True)),
        sa.Column("confirmed_by", sa.String(), sa.ForeignKey("users.id")),
        sa.Column(
            "predecessor_statement_id",
            sa.String(36),
            sa.ForeignKey("management_fee_statements.id"),
            unique=True,
        ),
        sa.Column(
            "successor_statement_id",
            sa.String(36),
            sa.ForeignKey("management_fee_statements.id"),
            unique=True,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "status IS NULL OR status IN ('confirmed','superseded')",
            name="ck_management_fee_statements_status",
        ),
        sa.CheckConstraint(
            "(status IS NULL AND base_amount IS NULL AND fee_amount IS NULL "
            "AND upstream_contract_ids IS NULL AND confirmed_at IS NULL AND confirmed_by IS NULL) "
            "OR (status IS NOT NULL AND base_amount IS NOT NULL AND fee_amount IS NOT NULL "
            "AND upstream_contract_ids IS NOT NULL AND stamped_document_id IS NOT NULL "
            "AND confirmed_at IS NOT NULL AND confirmed_by IS NOT NULL)",
            name="ck_management_fee_statements_snapshot",
        ),
        sa.CheckConstraint(
            "base_amount >= 0 AND fee_amount >= 0",
            name="ck_management_fee_statements_amounts",
        ),
        sa.CheckConstraint("version >= 1", name="ck_management_fee_statements_version"),
        sa.CheckConstraint(
            "id <> predecessor_statement_id AND id <> successor_statement_id",
            name="ck_management_fee_statements_no_self_link",
        ),
        sa.CheckConstraint(
            "length(period) = 7 AND substr(period, 5, 1) = '-' "
            "AND substr(period, 6, 2) IN ('01','02','03','04','05','06','07','08','09','10','11','12') "
            "AND substr(period, 1, 4) > '0000' "
            "AND substr(period, 1, 1) BETWEEN '0' AND '9' "
            "AND substr(period, 2, 1) BETWEEN '0' AND '9' "
            "AND substr(period, 3, 1) BETWEEN '0' AND '9' "
            "AND substr(period, 4, 1) BETWEEN '0' AND '9'",
            name="ck_management_fee_statements_period",
        ),
    )
    op.create_index(
        "uq_management_fee_statements_owner_period",
        "management_fee_statements",
        ["owner_party_id", "period"],
        unique=True,
        postgresql_where=sa.text("status IS NULL OR status <> 'superseded'"),
        sqlite_where=sa.text("status IS NULL OR status <> 'superseded'"),
    )
    op.create_table(
        "management_fee_statement_lines",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "statement_id",
            sa.String(36),
            sa.ForeignKey("management_fee_statements.id"),
            nullable=False,
        ),
        sa.Column("line_kind", sa.String(20), nullable=False),
        sa.Column(
            "upstream_contract_id",
            sa.String(36),
            sa.ForeignKey("upstream_contracts.id"),
            nullable=False,
        ),
        sa.Column(
            "terminal_contract_id",
            sa.String(36),
            sa.ForeignKey("terminal_contracts.id"),
            nullable=False,
        ),
        sa.Column(
            "rent_ledger_entry_id",
            sa.String(36),
            sa.ForeignKey("rent_ledger_entries.id"),
            nullable=False,
        ),
        sa.Column(
            "asset_unit_ids",
            sa.JSON().with_variant(JSONB, "postgresql"),
            nullable=False,
        ),
        sa.Column("tenant_name_snapshot", sa.String(200), nullable=False),
        sa.Column("rent_period", sa.String(7), nullable=False),
        sa.Column("scheduled_rent", sa.Numeric(14, 2), nullable=False),
        sa.Column("owner_received_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column(
            "counted_record_ids",
            sa.JSON().with_variant(JSONB, "postgresql"),
            nullable=False,
        ),
        sa.Column("received_on", sa.Date()),
        sa.Column("fee_rate", sa.Numeric(9, 6), nullable=False),
        sa.Column("fee_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("deferred_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("deferral_reason", sa.Text()),
        sa.Column(
            "carried_from_statement_id",
            sa.String(36),
            sa.ForeignKey("management_fee_statements.id"),
        ),
        sa.UniqueConstraint(
            "statement_id",
            "rent_ledger_entry_id",
            name="uq_management_fee_lines_statement_entry",
        ),
        sa.CheckConstraint(
            "line_kind IN ('current','carried')", name="ck_management_fee_lines_kind"
        ),
        sa.CheckConstraint(
            "scheduled_rent >= 0 AND owner_received_amount >= 0 AND fee_amount >= 0 AND deferred_amount >= 0",
            name="ck_management_fee_lines_amounts",
        ),
        sa.CheckConstraint(
            "fee_rate >= 0 AND fee_rate <= 1", name="ck_management_fee_lines_rate"
        ),
        sa.CheckConstraint(
            "deferred_amount = 0 OR (deferral_reason IS NOT NULL AND length(trim(deferral_reason)) > 0)",
            name="ck_management_fee_lines_deferral_reason",
        ),
        sa.CheckConstraint(
            "line_kind = 'carried' OR carried_from_statement_id IS NULL",
            name="ck_management_fee_lines_carried_source",
        ),
        sa.CheckConstraint(
            "length(rent_period) = 7 AND substr(rent_period, 5, 1) = '-' "
            "AND substr(rent_period, 6, 2) IN ('01','02','03','04','05','06','07','08','09','10','11','12') "
            "AND substr(rent_period, 1, 4) > '0000' "
            "AND substr(rent_period, 1, 1) BETWEEN '0' AND '9' "
            "AND substr(rent_period, 2, 1) BETWEEN '0' AND '9' "
            "AND substr(rent_period, 3, 1) BETWEEN '0' AND '9' "
            "AND substr(rent_period, 4, 1) BETWEEN '0' AND '9'",
            name="ck_management_fee_lines_period",
        ),
    )
    op.drop_constraint(
        "ck_asset_contract_write_receipts_command_kind",
        "asset_contract_write_receipts",
        type_="check",
    )
    op.alter_column(
        "asset_contract_write_receipts",
        "command_kind",
        existing_type=sa.String(30),
        type_=sa.String(64),
        existing_nullable=False,
    )
    op.create_check_constraint(
        "ck_asset_contract_write_receipts_command_kind",
        "asset_contract_write_receipts",
        "command_kind IN ('create_upstream', 'create_terminal', 'correct_rent_schedule', 'create_manual_rent_entry', 'void_manual_rent_entry', 'terminate_terminal', 'defer_management_fee_line', 'confirm_management_fee_statement', 'supersede_management_fee_statement')",
    )


def downgrade() -> None:
    raise RuntimeError(
        "Management fee confirmation snapshots are append-only; use a corrective migration"
    )
