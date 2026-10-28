"""Source-only rent commands and their durable acknowledgements."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..core.exception_handler import BaseBusinessError
from .asset_operations import ContractRentScheduleInput


class RentWritePayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="before")
    @classmethod
    def reject_derived_fields(cls, value: object) -> object:
        if isinstance(value, dict) and {
            "status",
            "effective_paid_amount",
            "remaining_amount",
        }.intersection(value):
            raise BaseBusinessError(
                message="派生字段不可写入",
                code="DERIVED_FIELD_NOT_WRITABLE",
                status_code=422,
            )
        return value


class RentPaymentRequest(RentWritePayload):
    record_type: Literal[
        "payment", "receipt", "owner_reported_receipt", "deposit_offset"
    ]
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    occurred_on: date
    document_id: str | None = Field(None, max_length=36)
    expected_version: int = Field(ge=1)


class RentReversalRequest(RentWritePayload):
    reason: str = ""
    expected_version: int = Field(ge=1)


class ManualRentEntryRequest(RentWritePayload):
    contract_kind: Literal["upstream", "terminal"]
    contract_id: str = Field(min_length=1, max_length=36)
    origin: Literal["manual", "clawback"]
    period_start: date | None = None
    period_end: date | None = None
    due_date: date | None = None
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    basis_note: str = ""


class VoidRentEntryRequest(RentReversalRequest):
    pass


class RentEntryCommandResponse(BaseModel):
    entry_id: str
    version: int
    idempotent: bool = False


class RentRecordCommandResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    ledger_entry_id: str
    record_type: str
    amount: Decimal
    occurred_on: date
    reverses_record_id: str | None = None
    reason: str | None = None
    version: int
    idempotent: bool = False


class RentScheduleCorrectionProposal(RentWritePayload):
    rent_schedules: list[ContractRentScheduleInput]
    reason: str = ""


class RentScheduleCorrectionCommit(RentWritePayload):
    preview_token: str = Field(min_length=1)
    expected_version: int = Field(ge=1)


class RentScheduleCorrectionPreview(BaseModel):
    contract_id: str
    contract_version: int
    rent_schedules: list[ContractRentScheduleInput]
    impact: dict[str, object]
    preview_token: str
    expires_at: datetime


class RentScheduleCorrectionResponse(BaseModel):
    contract_id: str
    version: int
    impact: dict[str, object]
    idempotent: bool = False
