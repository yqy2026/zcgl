"""Source-only deposit writes and calculated query responses."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..core.exception_handler import BaseBusinessError


class DepositWritePayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="before")
    @classmethod
    def reject_derived_fields(cls, value: object) -> object:
        if isinstance(value, dict) and {
            "agreed_amount",
            "held_amount",
            "carried_in_amount",
            "carried_out_amount",
            "direction",
            "outstanding_amount",
            "status",
        }.intersection(value):
            raise BaseBusinessError(
                message="派生字段不可写入",
                code="DERIVED_FIELD_NOT_WRITABLE",
                status_code=422,
            )
        return value


class DepositRecordRequest(DepositWritePayload):
    record_type: Literal[
        "collect",
        "refund",
        "deduct",
        "forfeit",
        "owner_reported_collect",
        "owner_reported_refund",
        "pay",
        "recover",
    ]
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    occurred_on: date
    document_id: str | None = Field(None, min_length=1, max_length=36)
    offset_ledger_entry_id: str | None = Field(None, min_length=1, max_length=36)
    reason: str = ""
    expected_version: int = Field(ge=1)


class DepositReversalRequest(DepositWritePayload):
    reason: str = ""
    expected_version: int = Field(ge=1)


class DepositRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    deposit_entry_id: str
    record_type: str
    amount: Decimal
    occurred_on: date
    document_id: str | None = None
    offset_ledger_entry_id: str | None = None
    lifecycle_event_id: str | None = None
    reverses_record_id: str | None = None
    reason: str | None = None
    created_by: str
    created_at: datetime


class DepositRecordCommandResponse(DepositRecordResponse):
    version: int
    idempotent: bool = False


class DepositOffsetCandidate(BaseModel):
    id: str
    contract_id: str
    period_start: date
    period_end: date
    due_date: date
    remaining_amount: Decimal


class DepositEntryResponse(BaseModel):
    id: str
    contract_kind: Literal["upstream", "terminal"]
    contract_id: str
    collector: Literal["operator", "owner"]
    agreed_amount: Decimal
    held_amount: Decimal
    carried_in_amount: Decimal
    carried_out_amount: Decimal
    direction: Literal["receivable", "payable", "refundable", "recoverable", "none"]
    outstanding_amount: Decimal
    status: Literal[
        "receivable_uncollected",
        "payable_unpaid",
        "refundable_unreturned",
        "recoverable_unreceived",
        "settled",
    ]
    version: int
    ended: bool
    read_only: bool
    records: list[DepositRecordResponse] = Field(default_factory=list)
    offset_candidates: list[DepositOffsetCandidate] = Field(default_factory=list)


class DepositListResponse(BaseModel):
    items: list[DepositEntryResponse]
    total: int
    page: int
    page_size: int
