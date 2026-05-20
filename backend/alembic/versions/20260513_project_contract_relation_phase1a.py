"""project contract relation phase1a: add project id to contract groups

Revision ID: 20260513_project_contract_relation_phase1a
Revises: 20260408_phase3_role_redefinition
Create Date: 2026-05-13 11:40:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260513_project_contract_relation_phase1a"
down_revision: str | None = "20260408_phase3_role_redefinition"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "contract_groups",
        sa.Column(
            "project_id",
            sa.String(),
            nullable=True,
            comment="所属项目 ID；Phase 1a 存量回填前允许为空",
        ),
    )
    op.create_index(
        "ix_contract_groups_project_id",
        "contract_groups",
        ["project_id"],
    )
    op.create_foreign_key(
        "fk_contract_groups_project_id",
        "contract_groups",
        "projects",
        ["project_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_contract_groups_project_id",
        "contract_groups",
        type_="foreignkey",
    )
    op.drop_index("ix_contract_groups_project_id", table_name="contract_groups")
    op.drop_column("contract_groups", "project_id")
