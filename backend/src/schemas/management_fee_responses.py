"""Public management fee read contracts independent of ORM storage state."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict


class ManagementFeeLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str | None = None
    line_kind: Literal["current", "carried"]
    upstream_contract_id: str
    terminal_contract_id: str
    rent_ledger_entry_id: str
    asset_unit_ids: list[str]
    tenant_name_snapshot: str
    rent_period: str
    scheduled_rent: Decimal
    owner_received_amount: Decimal
    counted_record_ids: list[str]
    received_on: date | None
    fee_rate: Decimal
    fee_amount: Decimal
    deferred_amount: Decimal
    deferral_reason: str | None
    carried_from_statement_id: str | None
    processed: bool = True


ManagementFeeStatementStatus = Literal[
    "collecting", "pending_stamp", "confirmed", "superseded"
]


class ManagementFeeStatementResponse(BaseModel):
    id: str
    owner_party_id: str
    period: str
    statement_number: str
    version: int
    status: ManagementFeeStatementStatus
    deadline: date
    upstream_contract_ids: list[str]
    base_amount: Decimal
    fee_amount: Decimal
    stamped_document_id: str | None
    confirmed_at: datetime | None
    confirmed_by: str | None
    predecessor_statement_id: str | None
    successor_statement_id: str | None
    lines: list[ManagementFeeLineResponse]
    carried_waiting_hint: bool
    upstream_missing_entry_ids: list[str]
    upstream_missing_warning: str | None


class ManagementFeeListResponse(BaseModel):
    items: list[ManagementFeeStatementResponse]
    total: int
