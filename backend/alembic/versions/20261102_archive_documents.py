"""Add archive file versions and classify existing certificate attachments.

Revision ID: 20261102_archive_documents
Revises: 20261102_report_full_scope_snapshot
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261102_archive_documents"
down_revision: str | None = "20261102_report_full_scope_snapshot"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    orphan_count = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT count(*) FROM attachments a WHERE a.owner_type = 'property_certificate' AND NOT EXISTS (SELECT 1 FROM property_certificates c WHERE c.id = a.owner_id)"
            )
        )
        .scalar_one()
    )
    if orphan_count:
        raise RuntimeError(
            f"Archive migration blocked: {orphan_count} certificate attachments have missing owners"
        )
    op.create_table(
        "archive_documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("document_type", sa.String(40), nullable=False),
        sa.Column("target_type", sa.String(40), nullable=False),
        sa.Column("target_id", sa.String(), nullable=False),
        sa.Column(
            "attachment_id",
            sa.String(),
            sa.ForeignKey("attachments.id", ondelete="RESTRICT"),
            nullable=False,
            unique=True,
        ),
        sa.Column("document_version", sa.Integer(), nullable=False),
        sa.Column("replaces_document_id", sa.String(36), unique=True),
        sa.Column("uploaded_by", sa.String(100), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "document_version >= 1", name="ck_archive_documents_version"
        ),
        sa.CheckConstraint(
            "replaces_document_id IS NULL OR replaces_document_id <> id",
            name="ck_archive_documents_no_self_replacement",
        ),
        sa.CheckConstraint(
            "document_type IN ('property_certificate', 'upstream_contract', 'supplement', 'terminal_contract', 'handover', 'management_fee_statement', 'payment_voucher')",
            name="ck_archive_documents_type",
        ),
        sa.UniqueConstraint(
            "target_type",
            "target_id",
            "document_type",
            "document_version",
            name="uq_archive_documents_target_version",
        ),
        sa.UniqueConstraint(
            "id",
            "target_type",
            "target_id",
            "document_type",
            name="uq_archive_documents_replacement_target",
        ),
        sa.ForeignKeyConstraint(
            ["replaces_document_id", "target_type", "target_id", "document_type"],
            [
                "archive_documents.id",
                "archive_documents.target_type",
                "archive_documents.target_id",
                "archive_documents.document_type",
            ],
            ondelete="RESTRICT",
            name="fk_archive_documents_replacement_target",
        ),
    )
    op.execute(
        sa.text("""
        INSERT INTO archive_documents
            (id, document_type, target_type, target_id, attachment_id,
             document_version, replaces_document_id, uploaded_by, uploaded_at)
        SELECT md5('certificate-archive:' || id)::uuid::text,
               'property_certificate', 'property_certificate', owner_id, id,
               row_number() OVER (PARTITION BY owner_id ORDER BY created_at, id),
               NULL, created_by, created_at
        FROM attachments WHERE owner_type = 'property_certificate'
    """)
    )


def downgrade() -> None:
    op.drop_table("archive_documents")
