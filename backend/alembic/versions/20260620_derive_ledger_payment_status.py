"""derive ledger payment status from paid amount

Revision ID: 20260620_derive_ledger_payment_status
Revises: 20260620_contract_number_project_scan_documents
Create Date: 2026-06-20
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260620_derive_ledger_payment_status"
down_revision: str | Sequence[str] | None = (
    "20260620_contract_number_project_scan_documents"
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_columns(
    inspector: sa.engine.reflection.Inspector,
    table_name: str,
    required_columns: set[str],
) -> bool:
    if not inspector.has_table(table_name):
        return False
    existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
    return required_columns.issubset(existing_columns)


def _normalize_table(table_name: str, id_column: str) -> None:
    bind = op.get_bind()
    table = sa.table(
        table_name,
        sa.column(id_column, sa.String()),
        sa.column("payment_status", sa.String()),
        sa.column("amount_due", sa.Numeric()),
        sa.column("paid_amount", sa.Numeric()),
    )
    bind.execute(
        table.update()
        .where(table.c.payment_status != "voided")
        .values(
            payment_status=sa.case(
                (table.c.paid_amount <= 0, "unpaid"),
                (table.c.paid_amount < table.c.amount_due, "partial"),
                else_="paid",
            )
        )
    )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    required_columns = {"payment_status", "amount_due", "paid_amount"}

    if _has_columns(inspector, "contract_ledger_entries", required_columns):
        _normalize_table("contract_ledger_entries", "entry_id")
    if _has_columns(inspector, "service_fee_ledgers", required_columns):
        _normalize_table("service_fee_ledgers", "service_fee_entry_id")


def downgrade() -> None:
    raise RuntimeError("derived ledger payment status is not downgraded")
