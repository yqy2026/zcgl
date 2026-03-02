"""phase4_set_party_columns_not_null

Revision ID: 20260301_phase4_set_party_columns_not_null
Revises: 20260224_backfill_ownership_occupancy_policy_rules
Create Date: 2026-03-01 09:00:00.000000
"""

from __future__ import annotations

import os
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260301_phase4_set_party_columns_not_null"
down_revision: str | None = "20260224_backfill_ownership_occupancy_policy_rules"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_MANDATORY_COLUMNS: tuple[tuple[str, str], ...] = (
    ("assets", "owner_party_id"),
    ("assets", "manager_party_id"),
    ("rent_contracts", "owner_party_id"),
    ("rent_contracts", "manager_party_id"),
    ("rent_ledger", "owner_party_id"),
    ("projects", "manager_party_id"),
)

_TENANT_DECISION_ENV = "PHASE4_TENANT_NOT_NULL_DECISION"


def _decision() -> str:
    decision = (os.getenv(_TENANT_DECISION_ENV) or "").strip().upper()
    if decision not in {"A", "B"}:
        raise RuntimeError(
            f"{_TENANT_DECISION_ENV} must be A or B before running migration "
            "(A=SET NOT NULL, B=skip tenant_party_id hardening)."
        )
    return decision


def _column_meta(
    inspector: sa.engine.reflection.Inspector,
    table_name: str,
    column_name: str,
) -> dict[str, object] | None:
    if not inspector.has_table(table_name):
        return None
    for column in inspector.get_columns(table_name):
        if str(column.get("name")) == column_name:
            return column
    return None


def _assert_no_null_values(
    connection: sa.engine.Connection,
    table_name: str,
    column_name: str,
) -> None:
    count_sql = sa.text(
        f"SELECT COUNT(*) FROM {table_name} WHERE {column_name} IS NULL OR {column_name} = ''"
    )
    null_count = int(connection.execute(count_sql).scalar() or 0)
    if null_count > 0:
        raise RuntimeError(
            f"Cannot set NOT NULL: {table_name}.{column_name} has {null_count} null/empty rows"
        )


def _set_not_null_if_needed(
    inspector: sa.engine.reflection.Inspector,
    connection: sa.engine.Connection,
    table_name: str,
    column_name: str,
) -> None:
    column = _column_meta(inspector, table_name, column_name)
    if column is None:
        return
    if not bool(column.get("nullable", True)):
        return

    _assert_no_null_values(connection, table_name, column_name)
    op.alter_column(
        table_name,
        column_name,
        existing_type=sa.String(),
        nullable=False,
    )


def upgrade() -> None:
    """Harden primary party columns to NOT NULL for Phase 4 Step 3."""
    tenant_decision = _decision()
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    for table_name, column_name in _MANDATORY_COLUMNS:
        _set_not_null_if_needed(inspector, connection, table_name, column_name)

    if tenant_decision == "A":
        _set_not_null_if_needed(
            inspector,
            connection,
            "rent_contracts",
            "tenant_party_id",
        )


def downgrade() -> None:
    """Relax NOT NULL constraints (best effort rollback)."""
    inspector = sa.inspect(op.get_bind())

    for table_name, column_name in _MANDATORY_COLUMNS:
        column = _column_meta(inspector, table_name, column_name)
        if column is None:
            continue
        if bool(column.get("nullable", True)):
            continue
        op.alter_column(
            table_name,
            column_name,
            existing_type=sa.String(),
            nullable=True,
        )

    tenant_column = _column_meta(inspector, "rent_contracts", "tenant_party_id")
    if tenant_column is not None and not bool(tenant_column.get("nullable", True)):
        op.alter_column(
            "rent_contracts",
            "tenant_party_id",
            existing_type=sa.String(),
            nullable=True,
        )
