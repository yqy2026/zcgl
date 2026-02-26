"""phase2_step1_add_party_columns

Revision ID: 20260219_phase2_add_party_columns_step1
Revises: 20260221_backfill_expanded_policy_package_rules
Create Date: 2026-02-19 16:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260219_phase2_add_party_columns_step1"
down_revision: str | None = "20260221_backfill_expanded_policy_package_rules"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _column_exists(bind: sa.engine.Connection, table: str, column: str) -> bool:
    inspector = sa.inspect(bind)
    return any(col["name"] == column for col in inspector.get_columns(table))


def _index_exists(bind: sa.engine.Connection, table: str, index_name: str) -> bool:
    inspector = sa.inspect(bind)
    return any(idx["name"] == index_name for idx in inspector.get_indexes(table))


def _table_exists(bind: sa.engine.Connection, table: str) -> bool:
    inspector = sa.inspect(bind)
    return inspector.has_table(table)


def _ensure_index(
    bind: sa.engine.Connection,
    *,
    table: str,
    column: str,
    index_name: str,
) -> None:
    if not _table_exists(bind, table):
        return
    if not _column_exists(bind, table, column):
        return
    if _index_exists(bind, table, index_name):
        return
    op.create_index(index_name, table, [column], unique=False)


def upgrade() -> None:
    """Step 1: add party columns and history table (nullable for backfill)."""
    bind = op.get_bind()

    if not _column_exists(bind, "assets", "owner_party_id"):
        with op.batch_alter_table("assets") as batch_op:
            batch_op.add_column(sa.Column("owner_party_id", sa.String(), nullable=True))
            batch_op.create_foreign_key(
                "fk_assets_owner_party_id_parties",
                "parties",
                ["owner_party_id"],
                ["id"],
            )
            batch_op.create_index("ix_assets_owner_party_id", ["owner_party_id"], unique=False)

    if not _column_exists(bind, "assets", "manager_party_id"):
        with op.batch_alter_table("assets") as batch_op:
            batch_op.add_column(sa.Column("manager_party_id", sa.String(), nullable=True))
            batch_op.create_foreign_key(
                "fk_assets_manager_party_id_parties",
                "parties",
                ["manager_party_id"],
                ["id"],
            )
            batch_op.create_index(
                "ix_assets_manager_party_id",
                ["manager_party_id"],
                unique=False,
            )

    if not _column_exists(bind, "rent_contracts", "owner_party_id"):
        with op.batch_alter_table("rent_contracts") as batch_op:
            batch_op.add_column(sa.Column("owner_party_id", sa.String(), nullable=True))
            batch_op.create_foreign_key(
                "fk_rent_contracts_owner_party_id_parties",
                "parties",
                ["owner_party_id"],
                ["id"],
            )
            batch_op.create_index(
                "ix_rent_contracts_owner_party_id",
                ["owner_party_id"],
                unique=False,
            )

    if not _column_exists(bind, "rent_contracts", "manager_party_id"):
        with op.batch_alter_table("rent_contracts") as batch_op:
            batch_op.add_column(sa.Column("manager_party_id", sa.String(), nullable=True))
            batch_op.create_foreign_key(
                "fk_rent_contracts_manager_party_id_parties",
                "parties",
                ["manager_party_id"],
                ["id"],
            )
            batch_op.create_index(
                "ix_rent_contracts_manager_party_id",
                ["manager_party_id"],
                unique=False,
            )

    if not _column_exists(bind, "rent_contracts", "tenant_party_id"):
        with op.batch_alter_table("rent_contracts") as batch_op:
            batch_op.add_column(sa.Column("tenant_party_id", sa.String(), nullable=True))
            batch_op.create_foreign_key(
                "fk_rent_contracts_tenant_party_id_parties",
                "parties",
                ["tenant_party_id"],
                ["id"],
            )
            batch_op.create_index(
                "ix_rent_contracts_tenant_party_id",
                ["tenant_party_id"],
                unique=False,
            )

    if not _column_exists(bind, "rent_ledger", "owner_party_id"):
        with op.batch_alter_table("rent_ledger") as batch_op:
            batch_op.add_column(sa.Column("owner_party_id", sa.String(), nullable=True))
            batch_op.create_foreign_key(
                "fk_rent_ledger_owner_party_id_parties",
                "parties",
                ["owner_party_id"],
                ["id"],
            )
            batch_op.create_index(
                "ix_rent_ledger_owner_party_id",
                ["owner_party_id"],
                unique=False,
            )

    if not _column_exists(bind, "projects", "manager_party_id"):
        with op.batch_alter_table("projects") as batch_op:
            batch_op.add_column(sa.Column("manager_party_id", sa.String(), nullable=True))
            batch_op.create_foreign_key(
                "fk_projects_manager_party_id_parties",
                "parties",
                ["manager_party_id"],
                ["id"],
            )
            batch_op.create_index("ix_projects_manager_party_id", ["manager_party_id"], unique=False)

    if not _column_exists(bind, "roles", "party_id"):
        with op.batch_alter_table("roles") as batch_op:
            batch_op.add_column(sa.Column("party_id", sa.String(), nullable=True))
            batch_op.create_foreign_key(
                "fk_roles_party_id_parties",
                "parties",
                ["party_id"],
                ["id"],
            )
            batch_op.create_index("ix_roles_party_id", ["party_id"], unique=False)

    if not _table_exists(bind, "asset_management_history"):
        op.create_table(
            "asset_management_history",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("asset_id", sa.String(), nullable=False),
            sa.Column("manager_party_id", sa.String(), nullable=False),
            sa.Column("start_date", sa.Date(), nullable=True),
            sa.Column("end_date", sa.Date(), nullable=True),
            sa.Column("agreement", sa.String(length=500), nullable=True),
            sa.Column("change_reason", sa.String(length=500), nullable=True),
            sa.Column("changed_by", sa.String(length=100), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["manager_party_id"], ["parties.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    if _table_exists(bind, "asset_management_history"):
        if not _index_exists(
            bind, "asset_management_history", "ix_asset_management_history_asset_id"
        ):
            op.create_index(
                "ix_asset_management_history_asset_id",
                "asset_management_history",
                ["asset_id"],
                unique=False,
            )
        if not _index_exists(
            bind,
            "asset_management_history",
            "ix_asset_management_history_manager_party_id",
        ):
            op.create_index(
                "ix_asset_management_history_manager_party_id",
                "asset_management_history",
                ["manager_party_id"],
                unique=False,
            )

    _ensure_index(
        bind,
        table="assets",
        column="owner_party_id",
        index_name="ix_assets_owner_party_id",
    )
    _ensure_index(
        bind,
        table="assets",
        column="manager_party_id",
        index_name="ix_assets_manager_party_id",
    )
    _ensure_index(
        bind,
        table="rent_contracts",
        column="owner_party_id",
        index_name="ix_rent_contracts_owner_party_id",
    )
    _ensure_index(
        bind,
        table="rent_contracts",
        column="manager_party_id",
        index_name="ix_rent_contracts_manager_party_id",
    )
    _ensure_index(
        bind,
        table="rent_contracts",
        column="tenant_party_id",
        index_name="ix_rent_contracts_tenant_party_id",
    )
    _ensure_index(
        bind,
        table="rent_ledger",
        column="owner_party_id",
        index_name="ix_rent_ledger_owner_party_id",
    )
    _ensure_index(
        bind,
        table="projects",
        column="manager_party_id",
        index_name="ix_projects_manager_party_id",
    )
    _ensure_index(
        bind,
        table="roles",
        column="party_id",
        index_name="ix_roles_party_id",
    )


def downgrade() -> None:
    """Rollback Step 1 columns/table."""
    bind = op.get_bind()

    if _index_exists(
        bind, "asset_management_history", "ix_asset_management_history_manager_party_id"
    ):
        op.drop_index(
            "ix_asset_management_history_manager_party_id",
            table_name="asset_management_history",
        )
    if _index_exists(bind, "asset_management_history", "ix_asset_management_history_asset_id"):
        op.drop_index(
            "ix_asset_management_history_asset_id",
            table_name="asset_management_history",
        )
    if _table_exists(bind, "asset_management_history"):
        op.drop_table("asset_management_history")

    if _column_exists(bind, "roles", "party_id"):
        with op.batch_alter_table("roles") as batch_op:
            batch_op.drop_index("ix_roles_party_id")
            batch_op.drop_column("party_id")

    if _column_exists(bind, "projects", "manager_party_id"):
        with op.batch_alter_table("projects") as batch_op:
            batch_op.drop_index("ix_projects_manager_party_id")
            batch_op.drop_column("manager_party_id")

    if _column_exists(bind, "rent_ledger", "owner_party_id"):
        with op.batch_alter_table("rent_ledger") as batch_op:
            batch_op.drop_index("ix_rent_ledger_owner_party_id")
            batch_op.drop_column("owner_party_id")

    if _column_exists(bind, "rent_contracts", "tenant_party_id"):
        with op.batch_alter_table("rent_contracts") as batch_op:
            batch_op.drop_index("ix_rent_contracts_tenant_party_id")
            batch_op.drop_column("tenant_party_id")

    if _column_exists(bind, "rent_contracts", "manager_party_id"):
        with op.batch_alter_table("rent_contracts") as batch_op:
            batch_op.drop_index("ix_rent_contracts_manager_party_id")
            batch_op.drop_column("manager_party_id")

    if _column_exists(bind, "rent_contracts", "owner_party_id"):
        with op.batch_alter_table("rent_contracts") as batch_op:
            batch_op.drop_index("ix_rent_contracts_owner_party_id")
            batch_op.drop_column("owner_party_id")

    if _column_exists(bind, "assets", "manager_party_id"):
        with op.batch_alter_table("assets") as batch_op:
            batch_op.drop_index("ix_assets_manager_party_id")
            batch_op.drop_column("manager_party_id")

    if _column_exists(bind, "assets", "owner_party_id"):
        with op.batch_alter_table("assets") as batch_op:
            batch_op.drop_index("ix_assets_owner_party_id")
            batch_op.drop_column("owner_party_id")
