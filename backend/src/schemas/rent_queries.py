"""Read projections for the rent ledger; amounts and status are never writable."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class RentRecordView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    ledger_entry_id: str
    record_type: str
    amount: Decimal
    occurred_on: date
    document_id: str | None = None
    reverses_record_id: str | None = None
    paired_deposit_record_id: str | None = None
    reason: str | None = None
    created_by: str
    created_at: datetime


class RentEntryView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    entry_type: str
    contract_kind: str
    contract_id: str
    period: str
    period_start: date
    period_end: date
    due_date: date
    due_amount: Decimal
    currency: str
    origin: str
    basis_note: str | None = None
    locked_source: dict[str, object]
    voided_at: datetime | None = None
    version: int
    effective_paid_amount: Decimal
    remaining_amount: Decimal
    status: str
    warnings: list[str] = Field(default_factory=list)
    records: list[RentRecordView] = Field(default_factory=list)


class RentMonthView(BaseModel):
    month: int
    entries: list[RentEntryView] = Field(default_factory=list)
    due_amount: Decimal = Decimal("0")
    paid_amount: Decimal = Decimal("0")
    remaining_amount: Decimal = Decimal("0")
    label: str | None = None


class RentContractRow(BaseModel):
    contract_kind: str
    contract_id: str
    contract_number: str
    contract_name: str
    months: list[RentMonthView]
    warnings: list[str] = Field(default_factory=list)
    total_due_amount: Decimal
    total_paid_amount: Decimal
    total_remaining_amount: Decimal


class RentMatrixView(BaseModel):
    ledger_type: str
    year: int
    current_month: int
    rows: list[RentContractRow]
    total_due_amount: Decimal
    total_paid_amount: Decimal
    total_remaining_amount: Decimal
