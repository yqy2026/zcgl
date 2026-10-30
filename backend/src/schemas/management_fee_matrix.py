"""Annual whole-owner management fee ledger read models."""

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class ManagementFeeMonthView(BaseModel):
    month: int
    statement_id: str | None = None
    status: Literal["collecting", "pending_stamp", "confirmed", "upcoming", "missing"]
    fee_amount: Decimal | None = None


class ManagementFeeOwnerRow(BaseModel):
    owner_party_id: str
    owner_name: str
    months: list[ManagementFeeMonthView]
    total_confirmed_amount: Decimal


class ManagementFeeMatrixView(BaseModel):
    ledger_type: Literal["management_fee"] = "management_fee"
    year: int
    current_month: int
    rows: list[ManagementFeeOwnerRow]
    total_confirmed_amount: Decimal
