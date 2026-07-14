"""payment voucher attachments

Revision ID: 20260713_payment_voucher_attachments
Revises: 20260713_payment_flow_lifecycle_audit
Create Date: 2026-07-13
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260713_payment_voucher_attachments"
down_revision: str | Sequence[str] | None = "20260713_payment_flow_lifecycle_audit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _create_attachments_table() -> None:
    op.create_table(
        "attachments",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("owner_type", sa.String(length=40), nullable=False),
        sa.Column("owner_id", sa.String(), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_type", sa.String(length=10), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("file_hash", sa.String(length=64), nullable=True),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("created_by", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "owner_type IN ('asset', 'contract', 'property_certificate', 'payment_flow')",
            name="ck_attachment_owner_type",
        ),
        sa.CheckConstraint(
            "file_type IN ('pdf', 'jpg', 'jpeg', 'png')",
            name="ck_attachment_file_type",
        ),
        sa.CheckConstraint(
            "file_size >= 0 AND file_size <= 20971520",
            name="ck_attachment_file_size",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key", name="uq_attachments_storage_key"),
    )
    op.create_index(
        "ix_attachments_owner",
        "attachments",
        ["owner_type", "owner_id"],
    )
    op.create_index(
        "ix_attachments_file_hash",
        "attachments",
        ["file_hash"],
    )


def upgrade() -> None:
    _create_attachments_table()


def downgrade() -> None:
    raise RuntimeError("payment voucher attachments migration is not downgraded")
