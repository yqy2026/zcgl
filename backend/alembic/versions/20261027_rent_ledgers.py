"""Persist rent obligations and append-only payment records.

Revision ID: 20261027_rent_ledgers
Revises: 20261027_business_change_events
Create Date: 2026-10-27
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20261027_rent_ledgers"
down_revision = "20261027_business_change_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "contract_rent_schedules",
        sa.Column("superseded_at", sa.DateTime(timezone=True)),
    )
    op.add_column(
        "contract_rent_schedules",
        sa.Column("superseded_correlation_id", sa.String(100)),
    )
    op.drop_constraint(
        "uq_contract_rent_schedules_target_stage",
        "contract_rent_schedules",
        type_="unique",
    )
    op.create_index(
        "uq_contract_rent_schedules_active_stage",
        "contract_rent_schedules",
        ["contract_kind", "contract_id", "stage_start"],
        unique=True,
        postgresql_where=sa.text("superseded_at IS NULL"),
    )
    op.drop_constraint(
        "ck_asset_contract_write_receipts_command_kind",
        "asset_contract_write_receipts",
        type_="check",
    )
    op.create_check_constraint(
        "ck_asset_contract_write_receipts_command_kind",
        "asset_contract_write_receipts",
        "command_kind IN ('create_upstream', 'create_terminal', 'correct_rent_schedule', 'create_manual_rent_entry', 'void_manual_rent_entry')",
    )
    op.create_table(
        "rent_ledger_entries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("entry_type", sa.String(30), nullable=False),
        sa.Column("contract_kind", sa.String(20), nullable=False),
        sa.Column("contract_id", sa.String(36), nullable=False),
        sa.Column("period", sa.String(7), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("due_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("origin", sa.String(20), nullable=False),
        sa.Column("basis_note", sa.Text()),
        sa.Column("locked_source", postgresql.JSONB(), nullable=False),
        sa.Column("voided_at", sa.DateTime(timezone=True)),
        sa.Column("void_correlation_id", sa.String(100)),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "entry_type IN ('upstream_payable','terminal_receivable','owner_receipt_expected')",
            name="ck_rent_ledger_entries_type",
        ),
        sa.CheckConstraint(
            "(contract_kind = 'upstream' AND entry_type = 'upstream_payable') OR (contract_kind = 'terminal' AND entry_type IN ('terminal_receivable','owner_receipt_expected'))",
            name="ck_rent_ledger_entries_contract_type",
        ),
        sa.CheckConstraint(
            "due_amount > 0 AND period_end >= period_start",
            name="ck_rent_ledger_entries_amount_period",
        ),
        sa.CheckConstraint(
            "origin IN ('generated','manual','clawback')",
            name="ck_rent_ledger_entries_origin",
        ),
        sa.CheckConstraint(
            "origin = 'generated' OR (basis_note IS NOT NULL AND length(trim(basis_note)) > 0)",
            name="ck_rent_ledger_entries_basis",
        ),
        sa.CheckConstraint("currency = 'CNY'", name="ck_rent_ledger_entries_currency"),
    )
    op.create_index(
        "uq_rent_ledger_entries_generated_period",
        "rent_ledger_entries",
        ["contract_kind", "contract_id", "entry_type", "period_start"],
        unique=True,
        postgresql_where=sa.text("origin = 'generated'"),
    )
    op.create_index(
        "ix_rent_ledger_entries_contract",
        "rent_ledger_entries",
        ["contract_kind", "contract_id"],
    )
    op.create_table(
        "rent_payment_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "ledger_entry_id",
            sa.String(36),
            sa.ForeignKey("rent_ledger_entries.id"),
            nullable=False,
        ),
        sa.Column("record_type", sa.String(30), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("occurred_on", sa.Date(), nullable=False),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("attachments.id")),
        sa.Column("paired_deposit_record_id", sa.String(36)),
        sa.Column(
            "reverses_record_id",
            sa.String(36),
            sa.ForeignKey("rent_payment_records.id"),
        ),
        sa.Column("reason", sa.Text()),
        sa.Column("created_by", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idempotency_key", sa.String(100), nullable=False, unique=True),
        sa.CheckConstraint(
            "record_type IN ('payment','receipt','owner_reported_receipt','deposit_offset','reversal')",
            name="ck_rent_payment_records_type",
        ),
        sa.CheckConstraint("amount > 0", name="ck_rent_payment_records_amount"),
        sa.CheckConstraint(
            "(record_type = 'reversal' AND reverses_record_id IS NOT NULL AND reason IS NOT NULL AND length(trim(reason)) > 0) OR (record_type <> 'reversal' AND reverses_record_id IS NULL)",
            name="ck_rent_payment_records_reversal",
        ),
        sa.CheckConstraint(
            "(record_type = 'deposit_offset' AND paired_deposit_record_id IS NOT NULL) OR (record_type <> 'deposit_offset' AND paired_deposit_record_id IS NULL)",
            name="ck_rent_payment_records_pair",
        ),
    )
    op.create_index(
        "uq_rent_payment_records_reversal",
        "rent_payment_records",
        ["reverses_record_id"],
        unique=True,
        postgresql_where=sa.text("reverses_record_id IS NOT NULL"),
    )
    op.create_index(
        "ix_rent_payment_records_entry", "rent_payment_records", ["ledger_entry_id"]
    )


def downgrade() -> None:
    raise RuntimeError("Rent ledger history is append-only; use a corrective migration")
