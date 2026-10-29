"""Bind termination settlement proposals to durable command receipts.

Revision ID: 20261028_termination_receipts
Revises: 20261028_deposit_ledgers
"""

from alembic import op

revision = "20261028_termination_receipts"
down_revision = "20261028_deposit_ledgers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_asset_contract_write_receipts_command_kind",
        "asset_contract_write_receipts",
        type_="check",
    )
    op.create_check_constraint(
        "ck_asset_contract_write_receipts_command_kind",
        "asset_contract_write_receipts",
        "command_kind IN ('create_upstream', 'create_terminal', 'correct_rent_schedule', 'create_manual_rent_entry', 'void_manual_rent_entry', 'terminate_terminal')",
    )


def downgrade() -> None:
    raise RuntimeError(
        "Termination receipts are append-only; use a corrective migration"
    )
