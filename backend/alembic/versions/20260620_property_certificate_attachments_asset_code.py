"""property certificate attachments and asset code hardening

Revision ID: 20260620_property_certificate_attachments_asset_code
Revises: 20260620_party_rejected_review_status
Create Date: 2026-06-20
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260620_property_certificate_attachments_asset_code"
down_revision: str | Sequence[str] | None = "20260620_party_rejected_review_status"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _table_has_column(
    inspector: sa.engine.reflection.Inspector,
    table_name: str,
    column_name: str,
) -> bool:
    if not inspector.has_table(table_name):
        return False
    return any(
        column["name"] == column_name for column in inspector.get_columns(table_name)
    )


def _column_nullable(
    inspector: sa.engine.reflection.Inspector,
    table_name: str,
    column_name: str,
) -> bool:
    if not inspector.has_table(table_name):
        return False
    for column in inspector.get_columns(table_name):
        if column["name"] == column_name:
            return bool(column.get("nullable", True))
    return False


def _index_exists(
    inspector: sa.engine.reflection.Inspector,
    table_name: str,
    index_name: str,
) -> bool:
    if not inspector.has_table(table_name):
        return False
    return any(
        index["name"] == index_name for index in inspector.get_indexes(table_name)
    )


def _create_attachment_table(inspector: sa.engine.reflection.Inspector) -> None:
    if inspector.has_table("property_certificate_attachments"):
        return
    op.create_table(
        "property_certificate_attachments",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "certificate_id",
            sa.String(),
            sa.ForeignKey("property_certificates.id", ondelete="CASCADE"),
            nullable=False,
            comment="Property certificate ID.",
        ),
        sa.Column(
            "file_name",
            sa.String(length=255),
            nullable=False,
            comment="Original or display file name.",
        ),
        sa.Column(
            "storage_key",
            sa.String(length=500),
            nullable=False,
            comment="Stable attachment storage key.",
        ),
        sa.Column("content_type", sa.String(length=100), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_property_certificate_attachments_certificate_id",
        "property_certificate_attachments",
        ["certificate_id"],
    )
    op.create_index(
        "ix_property_certificate_attachments_storage_key",
        "property_certificate_attachments",
        ["storage_key"],
    )


def _ensure_attachment_indexes(inspector: sa.engine.reflection.Inspector) -> None:
    if not inspector.has_table("property_certificate_attachments"):
        return
    if not _index_exists(
        inspector,
        "property_certificate_attachments",
        "ix_property_certificate_attachments_certificate_id",
    ):
        op.create_index(
            "ix_property_certificate_attachments_certificate_id",
            "property_certificate_attachments",
            ["certificate_id"],
        )
    if not _index_exists(
        inspector,
        "property_certificate_attachments",
        "ix_property_certificate_attachments_storage_key",
    ):
        op.create_index(
            "ix_property_certificate_attachments_storage_key",
            "property_certificate_attachments",
            ["storage_key"],
        )


def _backfill_asset_codes() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            WITH numbered_assets AS (
                SELECT
                    id,
                    ROW_NUMBER() OVER (ORDER BY id) AS sequence_number
                FROM assets
                WHERE asset_code IS NULL OR BTRIM(asset_code) = ''
            )
            UPDATE assets AS a
            SET asset_code = 'AST-LEGACY-' || LPAD(
                numbered_assets.sequence_number::text,
                6,
                '0'
            )
            FROM numbered_assets
            WHERE a.id = numbered_assets.id
            """
        )
    )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    _create_attachment_table(inspector)
    inspector = sa.inspect(bind)
    _ensure_attachment_indexes(inspector)

    if _table_has_column(inspector, "assets", "asset_code"):
        _backfill_asset_codes()
        inspector = sa.inspect(bind)
        if _column_nullable(inspector, "assets", "asset_code"):
            op.alter_column(
                "assets",
                "asset_code",
                existing_type=sa.String(length=50),
                nullable=False,
            )


def downgrade() -> None:
    raise RuntimeError(
        "property certificate attachments and asset_code hardening are not downgraded"
    )
