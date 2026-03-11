"""m2 add contract_number back to contracts

Revision ID: 20260307_m2_contract_number_on_contracts
Revises: 20260307_m2_collection_records_contract_fk
Create Date: 2026-03-07 09:08:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260307_m2_contract_number_on_contracts"
down_revision: str | None = "20260307_m2_collection_records_contract_fk"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


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
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _column_exists(inspector, "contracts", "contract_number"):
        op.add_column(
            "contracts",
            sa.Column(
                "contract_number",
                sa.String(length=100),
                nullable=True,
                comment="合同编号",
            ),
        )

    op.execute(
        sa.text(
            """
            UPDATE contracts AS c
            SET contract_number = legacy.contract_number
            FROM rent_contracts AS legacy
            WHERE c.contract_id = legacy.id
              AND (c.contract_number IS NULL OR c.contract_number = '')
              AND legacy.contract_number IS NOT NULL
              AND legacy.contract_number <> ''
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE contracts
            SET contract_number = 'AUTO-' || contract_id
            WHERE contract_number IS NULL OR contract_number = ''
            """
        )
    )
    op.alter_column(
        "contracts",
        "contract_number",
        existing_type=sa.String(length=100),
        nullable=False,
    )
    op.create_index(
        "ix_contracts_contract_number",
        "contracts",
        ["contract_number"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_contracts_contract_number", table_name="contracts")
    op.drop_column("contracts", "contract_number")
