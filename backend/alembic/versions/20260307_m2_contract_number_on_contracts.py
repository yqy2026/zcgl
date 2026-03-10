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


def upgrade() -> None:
    op.add_column(
        "contracts",
        sa.Column("contract_number", sa.String(length=100), nullable=False, comment="合同编号"),
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
