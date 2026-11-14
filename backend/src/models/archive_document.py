"""Append-only business classification and version links to stored files."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class ArchiveDocument(Base):
    __tablename__ = "archive_documents"
    __table_args__ = (
        CheckConstraint("document_version >= 1", name="ck_archive_documents_version"),
        CheckConstraint(
            "replaces_document_id IS NULL OR replaces_document_id <> id",
            name="ck_archive_documents_no_self_replacement",
        ),
        CheckConstraint(
            "document_type IN ('property_certificate', 'upstream_contract', 'supplement', 'terminal_contract', 'handover', 'management_fee_statement', 'payment_voucher')",
            name="ck_archive_documents_type",
        ),
        UniqueConstraint(
            "target_type",
            "target_id",
            "document_type",
            "document_version",
            name="uq_archive_documents_target_version",
        ),
        UniqueConstraint(
            "id",
            "target_type",
            "target_id",
            "document_type",
            name="uq_archive_documents_replacement_target",
        ),
        ForeignKeyConstraint(
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
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    document_type: Mapped[str] = mapped_column(String(40), nullable=False)
    target_type: Mapped[str] = mapped_column(String(40), nullable=False)
    target_id: Mapped[str] = mapped_column(String, nullable=False)
    attachment_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("attachments.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    document_version: Mapped[int] = mapped_column(Integer, nullable=False)
    replaces_document_id: Mapped[str | None] = mapped_column(String(36), unique=True)
    uploaded_by: Mapped[str] = mapped_column(String(100), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
