"""contract_group_nullable_rule_drop_versions

Revision ID: 20260611_contract_group_nullable_rule_drop_versions
Revises: 20260603_drop_generic_contacts
Create Date: 2026-06-11 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260611_contract_group_nullable_rule_drop_versions"
down_revision: str | None = "20260603_drop_generic_contacts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "contract_groups",
        "settlement_rule",
        existing_type=sa.JSON(),
        nullable=True,
    )
    op.drop_column("contract_groups", "predecessor_group_id")
    op.drop_column("contract_groups", "version")
    op.drop_column("contracts", "version")


def downgrade() -> None:
    op.add_column(
        "contracts",
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "contract_groups",
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "contract_groups",
        sa.Column("predecessor_group_id", sa.String(), nullable=True),
    )
    op.create_foreign_key(
        "fk_cg_predecessor",
        "contract_groups",
        "contract_groups",
        ["predecessor_group_id"],
        ["contract_group_id"],
    )

    contract_groups = sa.table(
        "contract_groups",
        sa.column("settlement_rule", sa.JSON),
    )
    op.execute(
        contract_groups.update()
        .where(contract_groups.c.settlement_rule.is_(None))
        .values(settlement_rule={})
    )
    op.alter_column(
        "contract_groups",
        "settlement_rule",
        existing_type=sa.JSON(),
        nullable=False,
    )
    op.alter_column("contracts", "version", server_default=None)
    op.alter_column("contract_groups", "version", server_default=None)
