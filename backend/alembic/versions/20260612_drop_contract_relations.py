"""drop contract_relations table

Revision ID: 20260612_drop_contract_relations
Revises: 20260611_drop_approval_domain
Create Date: 2026-06-12
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260612_drop_contract_relations"
down_revision: str | Sequence[str] | None = "20260611_drop_approval_domain"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "contracts",
        sa.Column("correction_source_contract_id", sa.String(length=50), nullable=True),
    )
    op.create_index(
        "ix_contracts_correction_source_contract_id",
        "contracts",
        ["correction_source_contract_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_contracts_correction_source_contract_id_contracts",
        "contracts",
        "contracts",
        ["correction_source_contract_id"],
        ["contract_id"],
    )
    op.drop_table("contract_relations")


def downgrade() -> None:
    raise RuntimeError("contract_relations was retired from MVP and is not recreated")
