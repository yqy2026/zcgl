"""remove asset contract snapshot fields

Revision ID: 4f9b3b2d6e91
Revises: 20260206_add_asset_fields_and_system_admin_permission
Create Date: 2026-02-07 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4f9b3b2d6e91"
down_revision: str | None = "20260206_add_asset_fields_and_system_admin_permission"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns(table_name)}
    return column_name in columns


def upgrade() -> None:
    columns_to_drop = [
        "tenant_name",
        "lease_contract_number",
        "contract_start_date",
        "contract_end_date",
        "monthly_rent",
        "deposit",
    ]

    with op.batch_alter_table("assets") as batch_op:
        for column_name in columns_to_drop:
            if _column_exists("assets", column_name):
                batch_op.drop_column(column_name)


def downgrade() -> None:
    with op.batch_alter_table("assets") as batch_op:
        if not _column_exists("assets", "tenant_name"):
            batch_op.add_column(sa.Column("tenant_name", sa.String(length=200), nullable=True, comment="租户名称"))
        if not _column_exists("assets", "lease_contract_number"):
            batch_op.add_column(
                sa.Column("lease_contract_number", sa.String(length=100), nullable=True, comment="租赁合同编号")
            )
        if not _column_exists("assets", "contract_start_date"):
            batch_op.add_column(sa.Column("contract_start_date", sa.Date(), nullable=True, comment="合同开始日期"))
        if not _column_exists("assets", "contract_end_date"):
            batch_op.add_column(sa.Column("contract_end_date", sa.Date(), nullable=True, comment="合同结束日期"))
        if not _column_exists("assets", "monthly_rent"):
            batch_op.add_column(sa.Column("monthly_rent", sa.DECIMAL(15, 2), nullable=True, comment="月租金（元）"))
        if not _column_exists("assets", "deposit"):
            batch_op.add_column(sa.Column("deposit", sa.DECIMAL(15, 2), nullable=True, comment="押金（元）"))
