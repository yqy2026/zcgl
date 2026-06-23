"""add frozen attribution columns to ledgers

Revision ID: 20260618_ledger_frozen_attribution
Revises: 20260616_drop_manual_overdue_status
Create Date: 2026-06-18
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260618_ledger_frozen_attribution"
down_revision: str | Sequence[str] | None = "20260616_drop_manual_overdue_status"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ATTRIBUTION_COLUMNS = (
    "attributed_project_id",
    "attributed_owner_party_id",
    "attributed_operator_party_id",
    "attributed_asset_ids",
)
ATTRIBUTION_FOREIGN_KEYS = (
    ("attributed_project_id", "projects", "id"),
    ("attributed_owner_party_id", "parties", "id"),
    ("attributed_operator_party_id", "parties", "id"),
)


def _table_exists(
    inspector: sa.engine.reflection.Inspector,
    table_name: str,
) -> bool:
    return inspector.has_table(table_name)


def _table_has_column(
    inspector: sa.engine.reflection.Inspector,
    table_name: str,
    column_name: str,
) -> bool:
    return any(
        column["name"] == column_name for column in inspector.get_columns(table_name)
    )


def _index_exists(
    inspector: sa.engine.reflection.Inspector,
    table_name: str,
    index_name: str,
) -> bool:
    return any(
        index.get("name") == index_name for index in inspector.get_indexes(table_name)
    )


def _foreign_key_exists(
    inspector: sa.engine.reflection.Inspector,
    table_name: str,
    constraint_name: str,
) -> bool:
    return any(
        fk.get("name") == constraint_name
        for fk in inspector.get_foreign_keys(table_name)
    )


def _foreign_key_name(table_name: str, column_name: str) -> str:
    return f"fk_{table_name}_{column_name}"


def _add_attribution_columns(
    inspector: sa.engine.reflection.Inspector,
    table_name: str,
) -> None:
    if not _table_exists(inspector, table_name):
        return

    if not _table_has_column(inspector, table_name, "attributed_project_id"):
        op.add_column(
            table_name,
            sa.Column("attributed_project_id", sa.String(), nullable=True),
        )
    if not _table_has_column(inspector, table_name, "attributed_owner_party_id"):
        op.add_column(
            table_name,
            sa.Column("attributed_owner_party_id", sa.String(), nullable=True),
        )
    if not _table_has_column(inspector, table_name, "attributed_operator_party_id"):
        op.add_column(
            table_name,
            sa.Column("attributed_operator_party_id", sa.String(), nullable=True),
        )
    if not _table_has_column(inspector, table_name, "attributed_asset_ids"):
        op.add_column(
            table_name,
            sa.Column("attributed_asset_ids", postgresql.JSONB(), nullable=True),
        )

    index_columns = (
        "attributed_project_id",
        "attributed_owner_party_id",
        "attributed_operator_party_id",
    )
    for column_name in index_columns:
        index_name = f"ix_{table_name}_{column_name}"
        if not _index_exists(inspector, table_name, index_name):
            op.create_index(index_name, table_name, [column_name], unique=False)

    for column_name, referred_table, referred_column in ATTRIBUTION_FOREIGN_KEYS:
        constraint_name = _foreign_key_name(table_name, column_name)
        if not _foreign_key_exists(inspector, table_name, constraint_name):
            op.create_foreign_key(
                constraint_name,
                table_name,
                referred_table,
                [column_name],
                [referred_column],
            )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    _add_attribution_columns(inspector, "contract_ledger_entries")
    _add_attribution_columns(inspector, "service_fee_ledgers")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for table_name in ("service_fee_ledgers", "contract_ledger_entries"):
        if not _table_exists(inspector, table_name):
            continue
        for column_name in (
            "attributed_operator_party_id",
            "attributed_owner_party_id",
            "attributed_project_id",
        ):
            constraint_name = _foreign_key_name(table_name, column_name)
            if _foreign_key_exists(inspector, table_name, constraint_name):
                op.drop_constraint(
                    constraint_name,
                    table_name,
                    type_="foreignkey",
                )
            index_name = f"ix_{table_name}_{column_name}"
            if _index_exists(inspector, table_name, index_name):
                op.drop_index(index_name, table_name=table_name)
        for column_name in reversed(ATTRIBUTION_COLUMNS):
            if _table_has_column(inspector, table_name, column_name):
                op.drop_column(table_name, column_name)
