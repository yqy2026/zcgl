"""Source-only management fee command payloads and durable responses."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ManagementFeeDeferralRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    rent_ledger_entry_id: str = Field(min_length=1, max_length=36)
    reason: str = ""
    expected_version: int = Field(ge=1)


class ManagementFeeCommandResponse(BaseModel):
    statement_id: str
    version: int
    idempotent: bool = False


class ManagementFeeConfirmationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    expected_version: int = Field(ge=1)


class ManagementFeeSuccessorRequest(ManagementFeeConfirmationRequest):
    reason: str = ""


class ManagementFeeSuccessorResponse(ManagementFeeCommandResponse):
    successor_statement_id: str


class ManagementFeeStampRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    document_id: str = Field(min_length=1, max_length=36)
    expected_version: int = Field(ge=1)


class ManagementFeeStampResponse(ManagementFeeCommandResponse):
    document_id: str
    fee_amount: Decimal


class ManagementFeeOwnerReceiptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    rent_ledger_entry_id: str = Field(min_length=1, max_length=36)
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    occurred_on: date
    document_id: str | None = Field(None, max_length=36)
    expected_version: int = Field(ge=1)
