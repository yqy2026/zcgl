"""add contract party name snapshots

Revision ID: 20260620_contract_party_name_snapshots
Revises: 20260620_derive_ledger_payment_status
Create Date: 2026-06-20
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260620_contract_party_name_snapshots"
down_revision: str | Sequence[str] | None = "20260620_derive_ledger_payment_status"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _table_has_column(
    inspector: sa.engine.reflection.Inspector,
    table_name: str,
    column_name: str,
) -> bool:
    if not inspector.has_table(table_name):
        return False
    return any(
        column["name"] == column_name for column in inspector.get_columns(table_name)
    )


def _add_snapshot_columns(inspector: sa.engine.reflection.Inspector) -> None:
    if not inspector.has_table("contracts"):
        return
    if not _table_has_column(inspector, "contracts", "lessor_name_snapshot"):
        op.add_column(
            "contracts",
            sa.Column(
                "lessor_name_snapshot",
                sa.String(length=200),
                nullable=True,
                comment="Lessor/entrusting party name snapshot captured at finalization.",
            ),
        )
    if not _table_has_column(inspector, "contracts", "lessee_name_snapshot"):
        op.add_column(
            "contracts",
            sa.Column(
                "lessee_name_snapshot",
                sa.String(length=200),
                nullable=True,
                comment="Lessee/entrusted party name snapshot captured at finalization.",
            ),
        )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    _add_snapshot_columns(inspector)
    inspector = sa.inspect(bind)
    if not (
        inspector.has_table("contracts")
        and inspector.has_table("parties")
        and _table_has_column(inspector, "contracts", "lessor_name_snapshot")
        and _table_has_column(inspector, "contracts", "lessee_name_snapshot")
    ):
        return

    bind.execute(
        sa.text(
            """
            UPDATE contracts AS c
            SET lessor_name_snapshot = p.name
            FROM parties AS p
            WHERE c.lessor_party_id = p.id
              AND c.lessor_name_snapshot IS NULL
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE contracts AS c
            SET lessee_name_snapshot = p.name
            FROM parties AS p
            WHERE c.lessee_party_id = p.id
              AND c.lessee_name_snapshot IS NULL
            """
        )
    )

    if inspector.has_table("lease_contract_details") and _table_has_column(
        inspector, "lease_contract_details", "tenant_name"
    ):
        bind.execute(
            sa.text(
                """
                UPDATE lease_contract_details AS lcd
                SET tenant_name = c.lessee_name_snapshot
                FROM contracts AS c
                WHERE lcd.contract_id = c.contract_id
                  AND c.lessee_name_snapshot IS NOT NULL
                """
            )
        )


def downgrade() -> None:
    raise RuntimeError("contract party name snapshots are not downgraded")
