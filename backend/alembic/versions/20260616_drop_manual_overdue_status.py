"""drop manual overdue ledger status

Revision ID: 20260616_drop_manual_overdue_status
Revises: 20260615_drop_collection_module
Create Date: 2026-06-16
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260616_drop_manual_overdue_status"
down_revision: str | Sequence[str] | None = "20260615_drop_collection_module"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _table_exists(
    inspector: sa.engine.reflection.Inspector,
    table_name: str,
) -> bool:
    return inspector.has_table(table_name)


def _normalize_overdue_rows(table_name: str) -> None:
    bind = op.get_bind()
    table = sa.table(
        table_name,
        sa.column("payment_status", sa.String()),
        sa.column("paid_amount", sa.Numeric()),
    )
    bind.execute(
        table.update()
        .where(table.c.payment_status == "overdue")
        .values(
            payment_status=sa.case(
                (table.c.paid_amount > 0, "partial"),
                else_="unpaid",
            )
        )
    )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for table_name in ("contract_ledger_entries", "service_fee_ledgers"):
        if _table_exists(inspector, table_name):
            _normalize_overdue_rows(table_name)


def downgrade() -> None:
    raise RuntimeError("manual overdue ledger status was retired and is not recreated")
