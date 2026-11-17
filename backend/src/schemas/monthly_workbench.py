"""Public contracts for the monthly workbench overview (本月).

Derived, stateless aggregation over the single source of truth
(upstream contracts → asset units → terminal contracts + ledgers).
Nothing here persists; every section is recomputed from live facts.
"""

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict


class WorkbenchMoneyTask(BaseModel):
    """One pending payment / collection line (contract × period)."""

    model_config = ConfigDict(from_attributes=True)

    contract_kind: Literal["upstream", "terminal"]
    contract_id: str
    contract_number: str
    contract_name: str
    counterparty_name: str
    unit_label: str | None = None
    period: str
    ledger_entry_id: str
    due_amount: Decimal
    paid_amount: Decimal
    remaining_amount: Decimal
    due_date: date
    days_overdue: int
    status: Literal["overdue", "partial", "unpaid", "upcoming"]
    record_type_hint: Literal["payment", "receipt"]


class WorkbenchMoneyCard(BaseModel):
    """A deadline task card: pending lines plus the folded done count."""

    period: str
    subtitle: str
    pending_count: int
    pending_amount: Decimal
    done_count: int
    done_amount: Decimal
    items: list[WorkbenchMoneyTask]


class WorkbenchManagementFeeItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    owner_party_id: str
    owner_party_name: str
    statement_id: str | None
    statement_number: str | None
    status: Literal["collecting", "pending_stamp", "confirmed", "missing"]
    base_amount: Decimal | None
    fee_amount: Decimal | None
    received_line_count: int
    line_count: int


class WorkbenchManagementFeeCard(BaseModel):
    period: str
    items: list[WorkbenchManagementFeeItem]


class WorkbenchOccupancyReportCard(BaseModel):
    operator_party_id: str
    period: str
    status: Literal["draft", "submitted", "missing_scope"]
    unavailable_reason: str | None = None
    unit_count: int | None = None
    rented_unit_count: int | None = None
    occupancy_rate: Decimal | None = None
    rate_delta: Decimal | None = None
    gate_reasons: list[str] = []
    can_submit: bool = False


class WorkbenchExpiredUpstreamItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    contract_id: str
    contract_number: str
    name: str
    contract_type: Literal["lease", "management_agreement"]
    end_date: date
    days_past: int
    unit_count: int
    active_terminal_count: int
    has_pending_renewal: bool


class WorkbenchExpiringUpstreamItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    contract_id: str
    contract_number: str
    name: str
    contract_type: Literal["lease", "management_agreement"]
    owner_party_name: str
    end_date: date
    days_left: int
    overrun_terminal_count: int


class WorkbenchArchiveGapItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_type: str
    label: str
    missing: int


class WorkbenchDepositItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    deposit_id: str
    contract_kind: Literal["upstream", "terminal"]
    contract_id: str
    contract_number: str
    counterparty_name: str
    collector: Literal["operator", "owner"]
    status: Literal[
        "receivable_uncollected",
        "payable_unpaid",
        "refundable_unreturned",
        "recoverable_unreceived",
        "settled",
    ]
    direction: Literal["receivable", "payable", "refundable", "recoverable", "none"]
    agreed_amount: Decimal
    held_amount: Decimal
    outstanding_amount: Decimal


class WorkbenchPendingScopeUnit(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    asset_unit_id: str
    unit_code: str
    unit_name: str
    reason: Literal["new_takeover", "boundary_uncertain"]


class WorkbenchProgress(BaseModel):
    total: int
    done: int


class MonthlyWorkbenchView(BaseModel):
    month: str
    today: date
    days_left_in_month: int
    progress: WorkbenchProgress
    rent_payments: WorkbenchMoneyCard
    rent_collections: WorkbenchMoneyCard
    management_fees: WorkbenchManagementFeeCard
    occupancy_report: WorkbenchOccupancyReportCard
    expired_upstream: list[WorkbenchExpiredUpstreamItem]
    expiring_upstream: list[WorkbenchExpiringUpstreamItem]
    archive_gaps: list[WorkbenchArchiveGapItem]
    unlinked_unit_count: int
    deposits_pending: list[WorkbenchDepositItem]
    pending_scope_units: list[WorkbenchPendingScopeUnit]
