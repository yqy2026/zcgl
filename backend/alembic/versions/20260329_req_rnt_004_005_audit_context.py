"""req rnt 004 005 audit context

Revision ID: 20260329_req_rnt_004_005_audit_context
Revises: 20260324_req_rnt_006_service_fee_ledger_m3
Create Date: 2026-03-29 19:20:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260329_req_rnt_004_005_audit_context"
down_revision: str | None = "20260324_req_rnt_006_service_fee_ledger_m3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("contract_audit_logs")}

    if "context" not in columns:
        op.add_column(
            "contract_audit_logs",
            sa.Column(
                "context",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
                comment="结构化审计上下文（联审范围、差异分类、纠错链路等）",
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("contract_audit_logs")}
    if "context" in columns:
        op.drop_column("contract_audit_logs", "context")
