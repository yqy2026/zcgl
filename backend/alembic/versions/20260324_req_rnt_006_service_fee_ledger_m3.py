"""req rnt 006 m3 service fee ledger

Revision ID: 20260324_req_rnt_006_service_fee_ledger_m3
Revises: 20260312_party_soft_delete_review_log
Create Date: 2026-03-24 11:40:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260324_req_rnt_006_service_fee_ledger_m3"
down_revision: str | None = "20260312_party_soft_delete_review_log"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("service_fee_ledgers"):
        op.create_table(
            "service_fee_ledgers",
            sa.Column("service_fee_entry_id", sa.String(), nullable=False),
            sa.Column("contract_group_id", sa.String(), nullable=False),
            sa.Column("agency_contract_id", sa.String(), nullable=False),
            sa.Column("source_ledger_id", sa.String(), nullable=False),
            sa.Column("year_month", sa.String(length=7), nullable=False),
            sa.Column("amount_due", sa.DECIMAL(15, 2), nullable=False),
            sa.Column("paid_amount", sa.DECIMAL(15, 2), nullable=False, server_default="0"),
            sa.Column("payment_status", sa.String(length=20), nullable=False, server_default="unpaid"),
            sa.Column("currency_code", sa.String(length=10), nullable=False, server_default="CNY"),
            sa.Column("service_fee_ratio", sa.DECIMAL(5, 4), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["contract_group_id"],
                ["contract_groups.contract_group_id"],
                name="fk_service_fee_ledger_group",
            ),
            sa.ForeignKeyConstraint(
                ["agency_contract_id"],
                ["contracts.contract_id"],
                name="fk_service_fee_ledger_contract",
            ),
            sa.ForeignKeyConstraint(
                ["source_ledger_id"],
                ["contract_ledger_entries.entry_id"],
                name="fk_service_fee_ledger_source",
            ),
            sa.PrimaryKeyConstraint("service_fee_entry_id"),
            sa.UniqueConstraint(
                "source_ledger_id",
                name="uq_service_fee_ledger_source",
            ),
        )

    existing_indexes = {
        index.get("name")
        for index in inspector.get_indexes("service_fee_ledgers")
    }
    if "ix_service_fee_ledgers_contract_group_id" not in existing_indexes:
        op.create_index(
            "ix_service_fee_ledgers_contract_group_id",
            "service_fee_ledgers",
            ["contract_group_id"],
            unique=False,
        )


def downgrade() -> None:
    op.drop_index(
        "ix_service_fee_ledgers_contract_group_id",
        table_name="service_fee_ledgers",
    )
    op.drop_table("service_fee_ledgers")
