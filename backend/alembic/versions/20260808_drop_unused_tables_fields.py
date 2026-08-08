"""drop_unused_tables_fields

Revision ID: 20260808_drop_unused_tables_fields
Revises: 20260806_user_party_scope_batch_commit_receipts
Create Date: 2026-08-08 09:00:00.000000

Drops the never-written tables and dead columns identified by the
2026-08-04 unused-db-fields audit (docs/issues/2026-08-04-unused-db-fields-audit.md):
- 4 tables with no business writes: asset_documents, party_role_defs,
  party_role_bindings, asset_management_history
- 5 groups of dead columns on live tables: audit_logs.user_organization,
  abac_role_policies.priority_override/params_override,
  certificate_party_relations.share_ratio, assets.asset_form/spatial_level/
  business_usage, project_assets.bind_reason/unbind_reason
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260808_drop_unused_tables_fields"
down_revision: str | None = "20260806_user_party_scope_batch_commit_receipts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_DROPPED_TABLES: tuple[str, ...] = (
    "asset_documents",
    "party_role_bindings",
    "party_role_defs",
    "asset_management_history",
)

_DROPPED_COLUMNS: tuple[tuple[str, str], ...] = (
    ("audit_logs", "user_organization"),
    ("abac_role_policies", "priority_override"),
    ("abac_role_policies", "params_override"),
    ("certificate_party_relations", "share_ratio"),
    ("assets", "asset_form"),
    ("assets", "spatial_level"),
    ("assets", "business_usage"),
    ("project_assets", "bind_reason"),
    ("project_assets", "unbind_reason"),
)


def _column_exists(
    inspector: sa.engine.reflection.Inspector,
    table_name: str,
    column_name: str,
) -> bool:
    if not inspector.has_table(table_name):
        return False
    return any(
        str(column.get("name")) == column_name
        for column in inspector.get_columns(table_name)
    )


def upgrade() -> None:
    """Drop the unused tables and dead columns with idempotent guards."""
    inspector = sa.inspect(op.get_bind())

    for table_name in _DROPPED_TABLES:
        if inspector.has_table(table_name):
            op.drop_table(table_name)

    # Re-inspect after table drops so stale inspectors don't mask columns.
    inspector = sa.inspect(op.get_bind())
    for table_name, column_name in _DROPPED_COLUMNS:
        if not _column_exists(inspector, table_name, column_name):
            continue
        op.drop_column(table_name, column_name)


def downgrade() -> None:
    """This cleanup is irreversible: dropped tables carried no data, and the
    dead columns were never read. Refuse to recreate dead schema."""
    raise RuntimeError(
        "drop_unused_tables_fields is irreversible: tables were empty and "
        "columns were dead. Do not restore them."
    )
