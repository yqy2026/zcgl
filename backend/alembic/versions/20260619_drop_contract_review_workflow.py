"""drop contract review workflow residue

Revision ID: 20260619_drop_contract_review_workflow
Revises: 20260619_drop_project_review_fields
Create Date: 2026-06-19
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260619_drop_contract_review_workflow"
down_revision: str | Sequence[str] | None = "20260619_drop_project_review_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CONTRACT_REVIEW_COLUMNS = (
    "review_status",
    "review_by",
    "reviewed_at",
    "review_reason",
)
AUDIT_REVIEW_COLUMNS = (
    "review_status_old",
    "review_status_new",
)


def _table_has_column(
    inspector: sa.engine.reflection.Inspector,
    table_name: str,
    column_name: str,
) -> bool:
    return any(
        column["name"] == column_name for column in inspector.get_columns(table_name)
    )


def _drop_columns_if_present(
    inspector: sa.engine.reflection.Inspector,
    table_name: str,
    column_names: tuple[str, ...],
) -> None:
    if not inspector.has_table(table_name):
        return
    for column_name in column_names:
        if _table_has_column(inspector, table_name, column_name):
            op.drop_column(table_name, column_name)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("contracts") and _table_has_column(
        inspector,
        "contracts",
        "status",
    ):
        bind.execute(
            sa.text(
                """
                UPDATE contracts
                SET status = CASE
                    WHEN status = 'PENDING_REVIEW' THEN 'ACTIVE'
                    WHEN status = 'EXPIRED' THEN 'ACTIVE'
                    ELSE status
                END
                """
            )
        )
        old_status_type = postgresql.ENUM(
            name="contractlifecyclestatus",
            create_type=False,
        )
        new_status_type = postgresql.ENUM(
            "DRAFT",
            "ACTIVE",
            "TERMINATED",
            name="contractlifecyclestatus_new",
        )
        new_status_type.create(bind, checkfirst=True)
        op.alter_column("contracts", "status", server_default=None)
        with op.batch_alter_table("contracts") as batch_op:
            batch_op.alter_column(
                "status",
                existing_type=old_status_type,
                type_=new_status_type,
                postgresql_using="status::text::contractlifecyclestatus_new",
            )
        op.alter_column("contracts", "status", server_default=sa.text("'DRAFT'"))
        old_status_type.drop(bind, checkfirst=True)
        bind.execute(
            sa.text(
                "ALTER TYPE contractlifecyclestatus_new RENAME TO contractlifecyclestatus"
            )
        )

    _drop_columns_if_present(inspector, "contracts", CONTRACT_REVIEW_COLUMNS)
    _drop_columns_if_present(inspector, "contract_audit_logs", AUDIT_REVIEW_COLUMNS)

    bind.execute(sa.text("DROP TYPE IF EXISTS contractreviewstatus"))


def downgrade() -> None:
    raise RuntimeError("contract review workflow was retired and is not recreated")
