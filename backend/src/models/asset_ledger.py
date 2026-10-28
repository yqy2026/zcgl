"""Rent obligations and append-only external payment facts for asset operations."""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class RentLedgerEntry(Base):
    __tablename__ = "rent_ledger_entries"
    __table_args__ = (
        CheckConstraint(
            "entry_type IN ('upstream_payable','terminal_receivable','owner_receipt_expected')",
            name="ck_rent_ledger_entries_type",
        ),
        CheckConstraint(
            "(contract_kind = 'upstream' AND entry_type = 'upstream_payable') OR (contract_kind = 'terminal' AND entry_type IN ('terminal_receivable','owner_receipt_expected'))",
            name="ck_rent_ledger_entries_contract_type",
        ),
        CheckConstraint(
            "due_amount > 0 AND period_end >= period_start",
            name="ck_rent_ledger_entries_amount_period",
        ),
        CheckConstraint(
            "origin IN ('generated','manual','clawback')",
            name="ck_rent_ledger_entries_origin",
        ),
        CheckConstraint(
            "origin = 'generated' OR (basis_note IS NOT NULL AND length(trim(basis_note)) > 0)",
            name="ck_rent_ledger_entries_basis",
        ),
        CheckConstraint("currency = 'CNY'", name="ck_rent_ledger_entries_currency"),
        Index(
            "uq_rent_ledger_entries_generated_period",
            "contract_kind",
            "contract_id",
            "entry_type",
            "period_start",
            unique=True,
            postgresql_where=text("origin = 'generated'"),
            sqlite_where=text("origin = 'generated'"),
        ),
        Index("ix_rent_ledger_entries_contract", "contract_kind", "contract_id"),
    )
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    entry_type: Mapped[str] = mapped_column(String(30), nullable=False)
    contract_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    contract_id: Mapped[str] = mapped_column(String(36), nullable=False)
    period: Mapped[str] = mapped_column(String(7), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="CNY")
    origin: Mapped[str] = mapped_column(String(20), nullable=False, default="generated")
    basis_note: Mapped[str | None] = mapped_column(Text)
    locked_source: Mapped[dict[str, object]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict
    )
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    void_correlation_id: Mapped[str | None] = mapped_column(String(100))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    __mapper_args__ = {"version_id_col": version}


class RentPaymentRecord(Base):
    __tablename__ = "rent_payment_records"
    __table_args__ = (
        CheckConstraint(
            "record_type IN ('payment','receipt','owner_reported_receipt','deposit_offset','reversal')",
            name="ck_rent_payment_records_type",
        ),
        CheckConstraint("amount > 0", name="ck_rent_payment_records_amount"),
        CheckConstraint(
            "(record_type = 'reversal' AND reverses_record_id IS NOT NULL AND reason IS NOT NULL AND length(trim(reason)) > 0) OR (record_type <> 'reversal' AND reverses_record_id IS NULL)",
            name="ck_rent_payment_records_reversal",
        ),
        CheckConstraint(
            "(record_type = 'deposit_offset' AND paired_deposit_record_id IS NOT NULL) OR (record_type <> 'deposit_offset' AND paired_deposit_record_id IS NULL)",
            name="ck_rent_payment_records_pair",
        ),
        Index(
            "uq_rent_payment_records_reversal",
            "reverses_record_id",
            unique=True,
            postgresql_where=text("reverses_record_id IS NOT NULL"),
            sqlite_where=text("reverses_record_id IS NOT NULL"),
        ),
        Index("ix_rent_payment_records_entry", "ledger_entry_id"),
    )
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    ledger_entry_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("rent_ledger_entries.id"), nullable=False
    )
    record_type: Mapped[str] = mapped_column(String(30), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    occurred_on: Mapped[date] = mapped_column(Date, nullable=False)
    document_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("attachments.id")
    )
    paired_deposit_record_id: Mapped[str | None] = mapped_column(String(36))
    reverses_record_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("rent_payment_records.id")
    )
    reason: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(
        String, ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True
    )
