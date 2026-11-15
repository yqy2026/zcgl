"""Classify existing fee stamp attachments as archive versions.

Revision ID: 20261104_fee_stamp_archive
Revises: 20261103_contract_supplements
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261104_fee_stamp_archive"
down_revision: str | None = "20261103_contract_supplements"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    orphan_count = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT count(*) FROM attachments a WHERE a.owner_type = 'management_fee_statement' AND NOT EXISTS (SELECT 1 FROM management_fee_statements s WHERE s.id = a.owner_id)"
            )
        )
        .scalar_one()
    )
    if orphan_count:
        raise RuntimeError(
            f"Fee stamp archive migration blocked: {orphan_count} stamped attachments have missing statements"
        )
    op.execute(
        sa.text("""
        INSERT INTO archive_documents
            (id, document_type, target_type, target_id, attachment_id,
             document_version, replaces_document_id, uploaded_by, uploaded_at)
        SELECT md5('fee-stamp-archive:' || id)::uuid::text,
               'management_fee_statement', 'management_fee_statement', owner_id, id,
               row_number() OVER (PARTITION BY owner_id ORDER BY created_at, id),
               NULL, created_by, created_at
        FROM attachments WHERE owner_type = 'management_fee_statement'
    """)
    )
    # Rebuild the replacement chain in bind order so only the newest backfilled
    # version derives as current; links are added after the rows exist because
    # the per-row FK check cannot reference rows from the same INSERT.
    op.execute(
        sa.text("""
        UPDATE archive_documents backfilled
        SET replaces_document_id = previous.id
        FROM archive_documents previous
        WHERE backfilled.document_type = 'management_fee_statement'
          AND backfilled.target_type = 'management_fee_statement'
          AND previous.target_type = backfilled.target_type
          AND previous.target_id = backfilled.target_id
          AND previous.document_type = backfilled.document_type
          AND previous.document_version = backfilled.document_version - 1
          AND backfilled.document_version > 1
    """)
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM archive_documents WHERE document_type = 'management_fee_statement' AND target_type = 'management_fee_statement'"
        )
    )
