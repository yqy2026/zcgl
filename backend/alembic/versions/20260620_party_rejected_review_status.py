"""rename party reversed review status to rejected

Revision ID: 20260620_party_rejected_review_status
Revises: 20260620_contract_party_name_snapshots
Create Date: 2026-06-20
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260620_party_rejected_review_status"
down_revision: str | Sequence[str] | None = "20260620_contract_party_name_snapshots"
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


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not _table_has_column(inspector, "parties", "review_status"):
        return
    bind.execute(
        sa.text(
            """
            UPDATE parties
            SET review_status = 'rejected'
            WHERE review_status = 'reversed'
            """
        )
    )


def downgrade() -> None:
    raise RuntimeError("party rejected review status is not downgraded")
