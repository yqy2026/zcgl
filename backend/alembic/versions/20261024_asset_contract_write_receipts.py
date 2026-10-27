"""add idempotent receipts for asset-contract writes

Revision ID: 20261024_asset_contract_write_receipts
Revises: 20261024_asset_operations_v5_permissions
Create Date: 2026-10-24
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20261024_asset_contract_write_receipts"
down_revision: str | Sequence[str] | None = "20261024_asset_operations_v5_permissions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "asset_contract_write_receipts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("actor_id", sa.String(), nullable=False),
        sa.Column("command_kind", sa.String(length=30), nullable=False),
        sa.Column("idempotency_key", sa.String(length=100), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column(
            "result_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")
        ),
        sa.CheckConstraint(
            "command_kind IN ('create_upstream', 'create_terminal')",
            name="ck_asset_contract_write_receipts_command_kind",
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["users.id"],
            name="fk_asset_contract_write_receipts_actor",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_asset_contract_write_receipts"),
        sa.UniqueConstraint(
            "actor_id",
            "idempotency_key",
            name="uq_asset_contract_write_receipts_actor_request",
        ),
    )
    op.create_index(
        "ix_asset_contract_write_receipts_created_at",
        "asset_contract_write_receipts",
        ["created_at"],
    )


def downgrade() -> None:
    raise RuntimeError(
        "asset-contract write receipts are irreversible; "
        "roll forward with a corrective migration"
    )
