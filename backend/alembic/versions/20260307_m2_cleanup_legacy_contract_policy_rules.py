"""m2 cleanup legacy contract policy rules

Revision ID: 20260307_m2_cleanup_legacy_contract_policy_rules
Revises: 20260307_m2_contract_number_on_contracts
Create Date: 2026-03-07 15:16:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260307_m2_cleanup_legacy_contract_policy_rules"
down_revision: str | None = "20260307_m2_contract_number_on_contracts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LEGACY_CONTRACT_RESOURCE_TYPE = "_".join(("rent", "contract"))


def upgrade() -> None:
    rule_table = sa.table(
        "abac_policy_rules",
        sa.column("resource_type", sa.String()),
    )
    bind = op.get_bind()
    bind.execute(
        rule_table.delete().where(
            rule_table.c.resource_type == LEGACY_CONTRACT_RESOURCE_TYPE
        )
    )


def downgrade() -> None:
    # Deleted legacy ABAC rules are intentionally not recreated.
    return None
