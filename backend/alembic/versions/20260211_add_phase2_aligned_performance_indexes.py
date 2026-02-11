"""add_phase2_aligned_performance_indexes

Revision ID: 20260211_add_phase2_aligned_performance_indexes
Revises: 20260209_add_asset_management_manager_indexes
Create Date: 2026-02-11 09:10:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260211_add_phase2_aligned_performance_indexes"
down_revision: str | None = "20260209_add_asset_management_manager_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


CREATE_INDEX_STATEMENTS: tuple[str, ...] = (
    # assets
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_assets_ownership_usage_active
    ON assets (ownership_id, usage_status)
    WHERE (data_status IS NULL OR data_status != '已删除')
    """,
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_assets_project_status
    ON assets (project_id, data_status)
    """,
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_assets_management_nature_active
    ON assets (management_entity, property_nature)
    WHERE (data_status IS NULL OR data_status != '已删除')
    """,
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_assets_active_created_at
    ON assets (created_at DESC)
    WHERE (data_status IS NULL OR data_status != '已删除')
    """,
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_assets_area_range_active
    ON assets (actual_property_area)
    WHERE (data_status IS NULL OR data_status != '已删除')
      AND actual_property_area IS NOT NULL
    """,
    # rent_contracts
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_rent_contracts_ownership_status_active
    ON rent_contracts (ownership_id, contract_status)
    WHERE (data_status IS NULL OR data_status != '已删除')
    """,
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_rent_contracts_status_end_date_active
    ON rent_contracts (contract_status, end_date)
    WHERE (data_status IS NULL OR data_status != '已删除')
    """,
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_rent_contracts_type_status_active
    ON rent_contracts (contract_type, contract_status)
    WHERE (data_status IS NULL OR data_status != '已删除')
    """,
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_rent_contracts_tenant_name_trgm_active
    ON rent_contracts USING gin (tenant_name gin_trgm_ops)
    WHERE (data_status IS NULL OR data_status != '已删除')
    """,
    # rent_ledger
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_rent_ledger_contract_year_month
    ON rent_ledger (contract_id, year_month)
    """,
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_rent_ledger_payment_status_due_date
    ON rent_ledger (payment_status, due_date)
    """,
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_rent_ledger_year_month
    ON rent_ledger (year_month)
    """,
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_rent_ledger_ownership_payment_status
    ON rent_ledger (ownership_id, payment_status)
    """,
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_rent_ledger_asset_year_month
    ON rent_ledger (asset_id, year_month)
    """,
    # ownerships / projects
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_ownerships_active_data_status
    ON ownerships (is_active, data_status)
    """,
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_ownerships_name_trgm
    ON ownerships USING gin (name gin_trgm_ops)
    """,
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_projects_status_created_at
    ON projects (project_status, created_at DESC)
    """,
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_projects_is_active_true
    ON projects (is_active)
    WHERE is_active IS TRUE
    """,
    # property certificate association table
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_property_cert_assets_asset_id_cert_id
    ON property_cert_assets (asset_id, certificate_id)
    """,
    # notifications
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_notifications_recipient_read_created
    ON notifications (recipient_id, is_read, created_at DESC)
    """,
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_notifications_type_created_at
    ON notifications (type, created_at DESC)
    """,
    # async_tasks
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_async_tasks_status_created_at
    ON async_tasks (status, created_at DESC)
    """,
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_async_tasks_user_status_created_at
    ON async_tasks (user_id, status, created_at DESC)
    """,
    # operation_logs
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_operation_logs_user_created_at
    ON operation_logs (user_id, created_at DESC)
    """,
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_operation_logs_module_created_at
    ON operation_logs (module, created_at DESC)
    """,
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_operation_logs_ip_address
    ON operation_logs (ip_address)
    """,
)


DROP_INDEX_STATEMENTS: tuple[str, ...] = (
    "DROP INDEX CONCURRENTLY IF EXISTS ix_operation_logs_ip_address",
    "DROP INDEX CONCURRENTLY IF EXISTS ix_operation_logs_module_created_at",
    "DROP INDEX CONCURRENTLY IF EXISTS ix_operation_logs_user_created_at",
    "DROP INDEX CONCURRENTLY IF EXISTS ix_async_tasks_user_status_created_at",
    "DROP INDEX CONCURRENTLY IF EXISTS ix_async_tasks_status_created_at",
    "DROP INDEX CONCURRENTLY IF EXISTS ix_notifications_type_created_at",
    "DROP INDEX CONCURRENTLY IF EXISTS ix_notifications_recipient_read_created",
    "DROP INDEX CONCURRENTLY IF EXISTS ix_property_cert_assets_asset_id_cert_id",
    "DROP INDEX CONCURRENTLY IF EXISTS ix_projects_is_active_true",
    "DROP INDEX CONCURRENTLY IF EXISTS ix_projects_status_created_at",
    "DROP INDEX CONCURRENTLY IF EXISTS ix_ownerships_name_trgm",
    "DROP INDEX CONCURRENTLY IF EXISTS ix_ownerships_active_data_status",
    "DROP INDEX CONCURRENTLY IF EXISTS ix_rent_ledger_asset_year_month",
    "DROP INDEX CONCURRENTLY IF EXISTS ix_rent_ledger_ownership_payment_status",
    "DROP INDEX CONCURRENTLY IF EXISTS ix_rent_ledger_year_month",
    "DROP INDEX CONCURRENTLY IF EXISTS ix_rent_ledger_payment_status_due_date",
    "DROP INDEX CONCURRENTLY IF EXISTS ix_rent_ledger_contract_year_month",
    "DROP INDEX CONCURRENTLY IF EXISTS ix_rent_contracts_tenant_name_trgm_active",
    "DROP INDEX CONCURRENTLY IF EXISTS ix_rent_contracts_type_status_active",
    "DROP INDEX CONCURRENTLY IF EXISTS ix_rent_contracts_status_end_date_active",
    "DROP INDEX CONCURRENTLY IF EXISTS ix_rent_contracts_ownership_status_active",
    "DROP INDEX CONCURRENTLY IF EXISTS ix_assets_area_range_active",
    "DROP INDEX CONCURRENTLY IF EXISTS ix_assets_active_created_at",
    "DROP INDEX CONCURRENTLY IF EXISTS ix_assets_management_nature_active",
    "DROP INDEX CONCURRENTLY IF EXISTS ix_assets_project_status",
    "DROP INDEX CONCURRENTLY IF EXISTS ix_assets_ownership_usage_active",
)


def _execute_concurrently(statement: str) -> None:
    with op.get_context().autocommit_block():
        op.execute(statement)


def upgrade() -> None:
    """Add phase-2 aligned performance indexes."""
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    for statement in CREATE_INDEX_STATEMENTS:
        _execute_concurrently(statement)


def downgrade() -> None:
    """Remove phase-2 aligned performance indexes."""
    for statement in DROP_INDEX_STATEMENTS:
        _execute_concurrently(statement)
