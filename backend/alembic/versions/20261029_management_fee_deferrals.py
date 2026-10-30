"""Store explicit management fee deferral decisions.

Revision ID: 20261029_fee_deferrals
Revises: 20261029_management_fees
"""

import sqlalchemy as sa

from alembic import op

revision = "20261029_fee_deferrals"
down_revision = "20261029_management_fees"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "management_fee_deferrals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "statement_id",
            sa.String(36),
            sa.ForeignKey("management_fee_statements.id"),
            nullable=False,
        ),
        sa.Column(
            "rent_ledger_entry_id",
            sa.String(36),
            sa.ForeignKey("rent_ledger_entries.id"),
            nullable=False,
        ),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "statement_id",
            "rent_ledger_entry_id",
            name="uq_management_fee_deferrals_statement_entry",
        ),
        sa.CheckConstraint(
            "length(trim(reason)) > 0", name="ck_management_fee_deferrals_reason"
        ),
    )


def downgrade() -> None:
    raise RuntimeError(
        "Management fee deferrals are append-only; use a corrective migration"
    )
