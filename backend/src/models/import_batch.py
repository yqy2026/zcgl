"""Import batch facts for the three-sheet workbook import (asset-ops v5 V4)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    literal_column,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base

_JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


def _utcnow() -> datetime:
    return datetime.now(UTC)


class ImportBatch(Base):
    """One uploaded workbook: validation state, proposal hash and commit audit."""

    __tablename__ = "import_batches"
    __table_args__ = (
        CheckConstraint("mode IN ('create', 'update')", name="ck_import_batches_mode"),
        CheckConstraint(
            "status IN ('uploaded', 'validating', 'invalid', 'ready', "
            "'committed', 'reverted')",
            name="ck_import_batches_status",
        ),
        CheckConstraint(
            "row_count >= 0 AND valid_count >= 0 AND error_count >= 0 "
            "AND warning_count >= 0",
            name="ck_import_batches_counts_nonnegative",
        ),
        CheckConstraint(
            "status <> 'committed' "
            "OR (committed_at IS NOT NULL AND committed_by IS NOT NULL)",
            name="ck_import_batches_commit_audit",
        ),
        CheckConstraint(
            "status <> 'reverted' "
            "OR (reverted_at IS NOT NULL AND reverted_by IS NOT NULL "
            "AND revert_reason IS NOT NULL)",
            name="ck_import_batches_revert_audit",
        ),
        Index(
            "uq_import_batches_commit_idempotency",
            "committed_by",
            "idempotency_key",
            unique=True,
            postgresql_where=literal_column("idempotency_key IS NOT NULL"),
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    mode: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="uploaded")
    file_document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("attachments.id", ondelete="RESTRICT"),
        nullable=False,
    )
    template_version: Mapped[str] = mapped_column(String(20), nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    valid_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    warning_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    proposal_hash: Mapped[str | None] = mapped_column(String(64))
    committed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    committed_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    reverted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reverted_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    revert_reason: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[str | None] = mapped_column(String(100))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )


class ImportBatchChange(Base):
    """Per-field diff rows: old/new values, severity and selection state."""

    __tablename__ = "import_batch_changes"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('change', 'warning', 'error')",
            name="ck_import_batch_changes_severity",
        ),
        CheckConstraint(
            "target_type IN ('asset_unit', 'upstream_contract', 'terminal_contract')",
            name="ck_import_batch_changes_target_type",
        ),
        CheckConstraint("row_number >= 0", name="ck_import_batch_changes_row_positive"),
        UniqueConstraint(
            "batch_id",
            "row_number",
            "target_key",
            "field_name",
            name="uq_import_batch_changes_row_field",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    batch_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("import_batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sheet_name: Mapped[str] = mapped_column(String(20), nullable=False)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    target_type: Mapped[str] = mapped_column(String(20), nullable=False)
    target_key: Mapped[str] = mapped_column(String(200), nullable=False)
    field_name: Mapped[str] = mapped_column(String(50), nullable=False)
    old_value: Mapped[dict[str, object] | None] = mapped_column(_JSON_TYPE)
    new_value: Mapped[dict[str, object] | None] = mapped_column(_JSON_TYPE)
    selected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    severity: Mapped[str] = mapped_column(String(10), nullable=False, default="change")
    effect_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
