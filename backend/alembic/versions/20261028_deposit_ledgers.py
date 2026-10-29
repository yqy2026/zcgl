"""Add source-only deposit entries and append-only records.

Revision ID: 20261028_deposit_ledgers
Revises: 20261027_rent_ledgers
"""

import sqlalchemy as sa

from alembic import op

revision = "20261028_deposit_ledgers"
down_revision = "20261027_rent_ledgers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "deposit_ledger_entries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("contract_kind", sa.String(20), nullable=False),
        sa.Column("contract_id", sa.String(36), nullable=False),
        sa.Column("collector", sa.String(20), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.UniqueConstraint(
            "contract_kind", "contract_id", name="uq_deposit_ledger_entries_contract"
        ),
        sa.CheckConstraint(
            "contract_kind IN ('upstream','terminal')",
            name="ck_deposit_ledger_entries_kind",
        ),
        sa.CheckConstraint(
            "collector IN ('operator','owner')",
            name="ck_deposit_ledger_entries_collector",
        ),
        sa.CheckConstraint(
            "contract_kind <> 'upstream' OR collector = 'owner'",
            name="ck_deposit_ledger_entries_upstream_collector",
        ),
        sa.CheckConstraint("version >= 1", name="ck_deposit_ledger_entries_version"),
    )
    op.create_table(
        "deposit_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "deposit_entry_id",
            sa.String(36),
            sa.ForeignKey("deposit_ledger_entries.id"),
            nullable=False,
        ),
        sa.Column("record_type", sa.String(30), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("occurred_on", sa.Date(), nullable=False),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("attachments.id")),
        sa.Column(
            "offset_ledger_entry_id",
            sa.String(36),
            sa.ForeignKey("rent_ledger_entries.id"),
        ),
        sa.Column(
            "lifecycle_event_id",
            sa.String(36),
            sa.ForeignKey("contract_lifecycle_events.id"),
        ),
        sa.Column(
            "reverses_record_id", sa.String(36), sa.ForeignKey("deposit_records.id")
        ),
        sa.Column("reason", sa.Text()),
        sa.Column("created_by", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idempotency_key", sa.String(100), nullable=False, unique=True),
        sa.CheckConstraint(
            "record_type IN ('collect','refund','deduct','forfeit','owner_reported_collect','owner_reported_refund','pay','recover','reversal')",
            name="ck_deposit_records_type",
        ),
        sa.CheckConstraint("amount > 0", name="ck_deposit_records_amount"),
        sa.CheckConstraint(
            "(record_type = 'reversal' AND reverses_record_id IS NOT NULL AND reason IS NOT NULL AND length(trim(reason)) > 0) OR (record_type <> 'reversal' AND reverses_record_id IS NULL)",
            name="ck_deposit_records_reversal",
        ),
        sa.CheckConstraint(
            "record_type <> 'forfeit' OR (reason IS NOT NULL AND length(trim(reason)) > 0)",
            name="ck_deposit_records_forfeit_reason",
        ),
        sa.CheckConstraint(
            "(record_type = 'deduct' AND offset_ledger_entry_id IS NOT NULL) OR (record_type <> 'deduct' AND offset_ledger_entry_id IS NULL)",
            name="ck_deposit_records_offset",
        ),
        sa.CheckConstraint(
            "lifecycle_event_id IS NULL OR record_type = 'deduct'",
            name="ck_deposit_records_lifecycle",
        ),
    )
    op.create_index(
        "uq_deposit_records_reversal",
        "deposit_records",
        ["reverses_record_id"],
        unique=True,
        postgresql_where=sa.text("reverses_record_id IS NOT NULL"),
        sqlite_where=sa.text("reverses_record_id IS NOT NULL"),
    )
    op.create_index("ix_deposit_records_entry", "deposit_records", ["deposit_entry_id"])


def downgrade() -> None:
    op.drop_index("ix_deposit_records_entry", table_name="deposit_records")
    op.drop_index("uq_deposit_records_reversal", table_name="deposit_records")
    op.drop_table("deposit_records")
    op.drop_table("deposit_ledger_entries")
