"""drop retired collection workflow module

Revision ID: 20260615_drop_collection_module
Revises: 20260612_drop_contract_relations
Create Date: 2026-06-15
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260615_drop_collection_module"
down_revision: str | Sequence[str] | None = "20260612_drop_contract_relations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

COLLECTION_RESOURCE = "collection"


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


def _delete_collection_runtime_permissions(
    inspector: sa.engine.reflection.Inspector,
) -> None:
    bind = op.get_bind()
    permission_table = None
    collection_permission_ids = None

    if _table_exists(inspector, "permissions"):
        permission_table = sa.table(
            "permissions",
            sa.column("id", sa.String()),
            sa.column("resource", sa.String()),
        )
        collection_permission_ids = sa.select(permission_table.c.id).where(
            permission_table.c.resource == COLLECTION_RESOURCE
        )

    if _table_exists(inspector, "abac_policy_rules"):
        rule_table = sa.table(
            "abac_policy_rules",
            sa.column("resource_type", sa.String()),
        )
        bind.execute(
            rule_table.delete().where(rule_table.c.resource_type == COLLECTION_RESOURCE)
        )

    if _table_exists(inspector, "resource_permissions"):
        columns = [sa.column("resource_type", sa.String())]
        conditions = []
        if _table_has_column(inspector, "resource_permissions", "permission_id"):
            columns.append(sa.column("permission_id", sa.String()))
        resource_permission_table = sa.table(
            "resource_permissions",
            *columns,
        )
        conditions.append(
            resource_permission_table.c.resource_type == COLLECTION_RESOURCE
        )
        if collection_permission_ids is not None and hasattr(
            resource_permission_table.c, "permission_id"
        ):
            conditions.append(
                resource_permission_table.c.permission_id.in_(collection_permission_ids)
            )
        bind.execute(resource_permission_table.delete().where(sa.or_(*conditions)))

    if permission_table is None or collection_permission_ids is None:
        return

    if _table_exists(inspector, "role_permissions"):
        role_permission_table = sa.table(
            "role_permissions",
            sa.column("permission_id", sa.String()),
        )
        bind.execute(
            role_permission_table.delete().where(
                role_permission_table.c.permission_id.in_(collection_permission_ids)
            )
        )

    if _table_exists(inspector, "permission_grants"):
        permission_grant_table = sa.table(
            "permission_grants",
            sa.column("permission_id", sa.String()),
        )
        bind.execute(
            permission_grant_table.delete().where(
                permission_grant_table.c.permission_id.in_(collection_permission_ids)
            )
        )

    bind.execute(
        permission_table.delete().where(
            permission_table.c.resource == COLLECTION_RESOURCE
        )
    )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    _delete_collection_runtime_permissions(inspector)

    if _table_exists(inspector, "collection_records"):
        op.drop_table("collection_records")

    if bind.dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS collectionmethod")
        op.execute("DROP TYPE IF EXISTS collectionstatus")


def downgrade() -> None:
    raise RuntimeError("collection workflow was retired from MVP and is not recreated")
