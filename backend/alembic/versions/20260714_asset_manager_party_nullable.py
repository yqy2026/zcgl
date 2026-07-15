"""allow unprojected assets to have no derived manager party

Revision ID: 20260714_asset_manager_party_nullable
Revises: 20260713_payment_voucher_download_permission
Create Date: 2026-07-14
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260714_asset_manager_party_nullable"
down_revision: str | Sequence[str] | None = (
    "20260713_payment_voucher_download_permission"
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "assets",
        "manager_party_id",
        existing_type=sa.String(),
        nullable=True,
    )


def downgrade() -> None:
    raise RuntimeError(
        "cannot restore assets.manager_party_id NOT NULL after allowing "
        "unprojected assets without a manager party"
    )
