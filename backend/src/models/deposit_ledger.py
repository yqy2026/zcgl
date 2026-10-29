"""Deposit source entries and append-only external settlement facts."""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class DepositLedgerEntry(Base):
    __tablename__ = "deposit_ledger_entries"
    __table_args__ = (
        UniqueConstraint(
            "contract_kind", "contract_id", name="uq_deposit_ledger_entries_contract"
        ),
        CheckConstraint(
            "contract_kind IN ('upstream','terminal')",
            name="ck_deposit_ledger_entries_kind",
        ),
        CheckConstraint(
            "collector IN ('operator','owner')",
            name="ck_deposit_ledger_entries_collector",
        ),
        CheckConstraint(
            "contract_kind <> 'upstream' OR collector = 'owner'",
            name="ck_deposit_ledger_entries_upstream_collector",
        ),
        CheckConstraint("version >= 1", name="ck_deposit_ledger_entries_version"),
    )
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    contract_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    contract_id: Mapped[str] = mapped_column(String(36), nullable=False)
    collector: Mapped[str] = mapped_column(String(20), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    __mapper_args__ = {"version_id_col": version}


class DepositRecord(Base):
    __tablename__ = "deposit_records"
    __table_args__ = (
        CheckConstraint(
            "record_type IN ('collect','refund','deduct','forfeit','owner_reported_collect','owner_reported_refund','pay','recover','reversal')",
            name="ck_deposit_records_type",
        ),
        CheckConstraint("amount > 0", name="ck_deposit_records_amount"),
        CheckConstraint(
            "(record_type = 'reversal' AND reverses_record_id IS NOT NULL AND reason IS NOT NULL AND length(trim(reason)) > 0) OR (record_type <> 'reversal' AND reverses_record_id IS NULL)",
            name="ck_deposit_records_reversal",
        ),
        CheckConstraint(
            "record_type <> 'forfeit' OR (reason IS NOT NULL AND length(trim(reason)) > 0)",
            name="ck_deposit_records_forfeit_reason",
        ),
        CheckConstraint(
            "(record_type = 'deduct' AND offset_ledger_entry_id IS NOT NULL) OR (record_type <> 'deduct' AND offset_ledger_entry_id IS NULL)",
            name="ck_deposit_records_offset",
        ),
        CheckConstraint(
            "lifecycle_event_id IS NULL OR record_type = 'deduct'",
            name="ck_deposit_records_lifecycle",
        ),
        Index(
            "uq_deposit_records_reversal",
            "reverses_record_id",
            unique=True,
            postgresql_where=text("reverses_record_id IS NOT NULL"),
            sqlite_where=text("reverses_record_id IS NOT NULL"),
        ),
        Index("ix_deposit_records_entry", "deposit_entry_id"),
    )
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    deposit_entry_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("deposit_ledger_entries.id"), nullable=False
    )
    record_type: Mapped[str] = mapped_column(String(30), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    occurred_on: Mapped[date] = mapped_column(Date, nullable=False)
    document_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("attachments.id")
    )
    offset_ledger_entry_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("rent_ledger_entries.id")
    )
    lifecycle_event_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("contract_lifecycle_events.id")
    )
    reverses_record_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("deposit_records.id")
    )
    reason: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(
        String, ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True
    )
