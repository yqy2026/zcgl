"""m2 contract ledger entries table

Revision ID: 20260306_m2_contract_ledger_entries
Revises: 20260306_m2_contract_lifecycle_core
Create Date: 2026-03-06 18:41:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260306_m2_contract_ledger_entries"
down_revision: str | None = "20260306_m2_contract_lifecycle_core"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "contract_ledger_entries",
        sa.Column("entry_id", sa.String(), nullable=False),
        sa.Column("contract_id", sa.String(), nullable=False),
        sa.Column("year_month", sa.String(length=7), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("amount_due", sa.DECIMAL(15, 2), nullable=False),
        sa.Column("currency_code", sa.String(length=10), nullable=False),
        sa.Column(
            "is_tax_included",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("tax_rate", sa.DECIMAL(5, 4), nullable=True),
        sa.Column(
            "payment_status",
            sa.String(length=20),
            nullable=False,
            server_default="unpaid",
        ),
        sa.Column(
            "paid_amount",
            sa.DECIMAL(15, 2),
            nullable=False,
            server_default="0",
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["contract_id"],
            ["contracts.contract_id"],
            name="fk_contract_ledger_entry_contract",
        ),
        sa.PrimaryKeyConstraint("entry_id"),
        sa.UniqueConstraint(
            "contract_id",
            "year_month",
            name="uq_contract_ledger_entry_month",
        ),
    )
    op.create_index(
        "ix_contract_ledger_entries_contract_id",
        "contract_ledger_entries",
        ["contract_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_contract_ledger_entries_contract_id",
        table_name="contract_ledger_entries",
    )
    op.drop_table("contract_ledger_entries")
