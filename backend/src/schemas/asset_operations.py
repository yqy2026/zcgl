"""Pydantic contracts for the asset-operations v5 vertical slice.

Write models contain source facts only. Status, occupancy, expiry and warning
fields exist exclusively on response projections.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

AcquisitionMode = Literal["owned", "leased", "managed"]
VacancyReason = Literal[
    "renovation",
    "marketing",
    "repossession",
    "pending_contract",
    "other",
]
UpstreamContractType = Literal["lease", "management_agreement"]
TerminalContractMode = Literal["sublease", "direct_lease"]
ContractKind = Literal["upstream", "terminal"]
PaymentCycle = Literal["monthly", "quarterly", "yearly", "custom"]
RentCollector = Literal["operator", "owner"]
ContractIntakeType = Literal[
    "upstream_lease",
    "management_agreement",
    "terminal",
]
LifecycleEventType = Literal["renewed", "terminated", "exited", "reversed"]
TerminationType = Literal["expiry", "early", "mutual"]
HandoverStatus = Literal["pending", "completed", "not_applicable"]
DepositSettlementStatus = Literal["pending", "settled", "not_applicable"]


class _StrictPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


def _ensure_unique_ids(values: list[str], *, field_name: str) -> list[str]:
    if len(values) != len(set(values)):
        raise ValueError(f"{field_name} 不得包含重复 ID")
    return values


class ContractWarning(_StrictPayload):
    code: str = Field(..., min_length=1, max_length=100)
    severity: Literal["info", "warning", "error"]
    message: str | None = Field(None, max_length=500)


class AssetUnitCreate(_StrictPayload):
    unit_code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=200)
    project_id: str = Field(..., min_length=1)
    owner_party_id: str = Field(..., min_length=1)
    address: str = Field(..., min_length=1, max_length=500)
    usage_type: str = Field(..., min_length=1, max_length=100)
    acquisition_mode: AcquisitionMode
    is_operating: bool = True
    land_area: Decimal = Field(
        default=Decimal("0"), ge=0, max_digits=12, decimal_places=2
    )
    building_area: Decimal = Field(..., ge=0, max_digits=12, decimal_places=2)
    rentable_area: Decimal = Field(..., ge=0, max_digits=12, decimal_places=2)
    managed_from: date
    managed_to: date | None = None
    vacancy_reason: VacancyReason | None = None
    expected_lease_start: date | None = None
    predecessor_unit_ids: list[str] = Field(default_factory=list)

    @field_validator("predecessor_unit_ids")
    @classmethod
    def validate_predecessor_ids(cls, values: list[str]) -> list[str]:
        return _ensure_unique_ids(values, field_name="predecessor_unit_ids")

    @model_validator(mode="after")
    def validate_ranges(self) -> Self:
        if self.rentable_area > self.building_area:
            raise ValueError("rentable_area 不得大于 building_area")
        if self.managed_to is not None and self.managed_to < self.managed_from:
            raise ValueError("managed_to 不得早于 managed_from")
        return self


class AssetUnitUpdate(_StrictPayload):
    expected_version: int = Field(..., ge=1)
    name: str | None = Field(None, min_length=1, max_length=200)
    project_id: str | None = Field(None, min_length=1)
    owner_party_id: str | None = Field(None, min_length=1)
    address: str | None = Field(None, min_length=1, max_length=500)
    usage_type: str | None = Field(None, min_length=1, max_length=100)
    acquisition_mode: AcquisitionMode | None = None
    is_operating: bool | None = None
    land_area: Decimal | None = Field(None, ge=0, max_digits=12, decimal_places=2)
    building_area: Decimal | None = Field(None, ge=0, max_digits=12, decimal_places=2)
    rentable_area: Decimal | None = Field(None, ge=0, max_digits=12, decimal_places=2)
    managed_from: date | None = None
    managed_to: date | None = None

    @model_validator(mode="after")
    def validate_partial_ranges(self) -> Self:
        if (
            self.building_area is not None
            and self.rentable_area is not None
            and self.rentable_area > self.building_area
        ):
            raise ValueError("rentable_area 不得大于 building_area")
        if (
            self.managed_from is not None
            and self.managed_to is not None
            and self.managed_to < self.managed_from
        ):
            raise ValueError("managed_to 不得早于 managed_from")
        return self


class AssetUnitVacancyNoteUpdate(_StrictPayload):
    expected_version: int = Field(..., ge=1)
    vacancy_reason: VacancyReason | None = None
    expected_lease_start: date | None = None


class AssetUnitResponse(AssetUnitCreate):
    id: str
    version: int
    created_at: datetime
    updated_at: datetime
    rental_status: Literal["rented", "vacant", "non_rentable"]
    rented_area: Decimal = Field(..., ge=0)
    occupancy_rate: Decimal = Field(..., ge=0, le=1)
    warnings: list[ContractWarning] = Field(default_factory=list)

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
        str_strip_whitespace=True,
    )


class AssetUnitSplitPartInput(_StrictPayload):
    unit_code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=200)
    land_area: Decimal = Field(
        default=Decimal("0"), ge=0, max_digits=12, decimal_places=2
    )
    building_area: Decimal = Field(..., ge=0, max_digits=12, decimal_places=2)
    rentable_area: Decimal = Field(..., ge=0, max_digits=12, decimal_places=2)

    @model_validator(mode="after")
    def validate_area(self) -> Self:
        if self.rentable_area > self.building_area:
            raise ValueError("rentable_area 不得大于 building_area")
        return self


class AssetUnitSplitPreviewRequest(_StrictPayload):
    effective_date: date
    parts: list[AssetUnitSplitPartInput] = Field(..., min_length=2)

    @model_validator(mode="after")
    def validate_unique_codes(self) -> Self:
        codes = [part.unit_code for part in self.parts]
        if len(codes) != len(set(codes)):
            raise ValueError("parts.unit_code 不得重复")
        return self


class AssetUnitSplitProposal(_StrictPayload):
    change_type: Literal["split"] = "split"
    source_unit_id: str = Field(..., min_length=1)
    effective_date: date
    parts: list[AssetUnitSplitPartInput] = Field(..., min_length=2)

    @model_validator(mode="after")
    def validate_unique_codes(self) -> Self:
        codes = [part.unit_code for part in self.parts]
        if len(codes) != len(set(codes)):
            raise ValueError("parts.unit_code 不得重复")
        return self


class AssetUnitBoundaryImpact(_StrictPayload):
    source_units_stop_on: date
    result_units_start_on: date
    unit_count_delta: int


class AssetUnitBoundaryPreviewResponse(_StrictPayload):
    change_type: Literal["split", "merge"]
    source_unit_ids: list[str]
    results: list[AssetUnitSplitPartInput]
    area_check: dict[str, dict[str, str]]
    impact: AssetUnitBoundaryImpact
    warnings: list[ContractWarning] = Field(default_factory=list)
    versions: dict[str, int]
    preview_token: str = Field(..., min_length=1)
    expires_at: datetime


class AssetUnitSplitCommitRequest(_StrictPayload):
    preview_token: str = Field(..., min_length=1, max_length=512)
    reason: str = Field(..., min_length=1, max_length=500)
    expected_version: int = Field(..., ge=1)


class AssetUnitMergeResultInput(_StrictPayload):
    unit_code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=200)


class AssetUnitMergePreviewRequest(_StrictPayload):
    source_unit_ids: list[str] = Field(..., min_length=2)
    effective_date: date
    result: AssetUnitMergeResultInput

    @field_validator("source_unit_ids")
    @classmethod
    def validate_source_unit_ids(cls, values: list[str]) -> list[str]:
        unique_values = _ensure_unique_ids(values, field_name="source_unit_ids")
        if any(value.strip() == "" for value in unique_values):
            raise ValueError("source_unit_ids 不得包含空 ID")
        return sorted(unique_values)


class AssetUnitMergeProposal(AssetUnitMergePreviewRequest):
    change_type: Literal["merge"] = "merge"


class AssetUnitMergeCommitRequest(_StrictPayload):
    preview_token: str = Field(..., min_length=1, max_length=512)
    reason: str = Field(..., min_length=1, max_length=500)
    expected_versions: dict[str, Annotated[int, Field(ge=1)]] = Field(
        ...,
        min_length=2,
    )

    @field_validator("expected_versions")
    @classmethod
    def validate_expected_version_ids(
        cls,
        values: dict[str, int],
    ) -> dict[str, int]:
        if any(unit_id.strip() == "" for unit_id in values):
            raise ValueError("expected_versions 不得包含空 ID")
        return dict(sorted(values.items()))


class AssetUnitBoundaryCommitResponse(_StrictPayload):
    boundary_change_id: str
    change_type: Literal["split", "merge"]
    source_unit_ids: list[str]
    result_unit_ids: list[str]
    effective_date: date
    committed_at: datetime
    idempotent: bool = False


class ContractRentScheduleInput(_StrictPayload):
    stage_start: date
    stage_end: date
    base_monthly_rent: Decimal = Field(..., ge=0, max_digits=14, decimal_places=2)
    increase_rate: Decimal = Field(default=Decimal("0"), ge=0, le=1)
    free_rent_months: Decimal = Field(
        default=Decimal("0"), ge=0, max_digits=8, decimal_places=2
    )
    discount_amount: Decimal = Field(
        default=Decimal("0"), ge=0, max_digits=14, decimal_places=2
    )
    actual_monthly_rent: Decimal = Field(..., ge=0, max_digits=14, decimal_places=2)
    payment_cycle: PaymentCycle
    due_day: int = Field(..., ge=1, le=31)

    @model_validator(mode="after")
    def validate_stage_range(self) -> Self:
        if self.stage_end < self.stage_start:
            raise ValueError("stage_end 不得早于 stage_start")
        return self


class UpstreamContractCreate(_StrictPayload):
    contract_number: str = Field(..., min_length=1, max_length=100)
    contract_type: UpstreamContractType
    name: str = Field(..., min_length=1, max_length=200)
    owner_party_id: str = Field(..., min_length=1)
    operator_party_id: str = Field(..., min_length=1)
    start_date: date
    end_date: date
    payment_cycle: PaymentCycle | None = None
    payment_day: int | None = Field(None, ge=1, le=31)
    management_fee_rate: Decimal | None = Field(None, ge=0, le=1)
    deposit_amount: Decimal = Field(default=Decimal("0"), ge=0)
    oa_reference: str | None = Field(None, max_length=100)
    renewed_from_id: str | None = Field(None, min_length=1)
    scan_document_id: str = Field(..., min_length=1)
    asset_unit_ids: list[str] = Field(..., min_length=1)
    rent_schedules: list[ContractRentScheduleInput] = Field(default_factory=list)

    @field_validator("asset_unit_ids")
    @classmethod
    def validate_asset_unit_ids(cls, values: list[str]) -> list[str]:
        return _ensure_unique_ids(values, field_name="asset_unit_ids")

    @model_validator(mode="after")
    def validate_terms(self) -> Self:
        if self.end_date < self.start_date:
            raise ValueError("end_date 不得早于 start_date")
        if self.contract_type == "lease":
            if self.payment_cycle is None:
                raise ValueError("lease 必须提供 payment_cycle")
            if self.management_fee_rate is not None:
                raise ValueError("lease 不得提供 management_fee_rate")
        else:
            if self.management_fee_rate is None:
                raise ValueError("management_agreement 必须提供 management_fee_rate")
            if self.payment_cycle is not None or self.payment_day is not None:
                raise ValueError(
                    "management_agreement 不得提供 payment_cycle 或 payment_day"
                )
        return self


class UpstreamContractUpdate(_StrictPayload):
    expected_version: int = Field(..., ge=1)
    name: str | None = Field(None, min_length=1, max_length=200)
    end_date: date | None = None
    payment_cycle: PaymentCycle | None = None
    payment_day: int | None = Field(None, ge=1, le=31)
    management_fee_rate: Decimal | None = Field(None, ge=0, le=1)
    deposit_amount: Decimal | None = Field(None, ge=0)
    oa_reference: str | None = Field(None, max_length=100)


class UpstreamContractConfirmRequest(_StrictPayload):
    """Human-confirmed upstream terms; session owns type, scan, and renewal."""

    contract_number: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    owner_party_id: str = Field(..., min_length=1)
    operator_party_id: str = Field(..., min_length=1)
    start_date: date
    end_date: date
    payment_cycle: PaymentCycle | None = None
    payment_day: int | None = Field(None, ge=1, le=31)
    management_fee_rate: Decimal | None = Field(None, ge=0, le=1)
    deposit_amount: Decimal = Field(default=Decimal("0"), ge=0)
    oa_reference: str | None = Field(None, max_length=100)
    asset_unit_ids: list[str] = Field(..., min_length=1)
    rent_schedules: list[ContractRentScheduleInput] = Field(default_factory=list)

    @field_validator("asset_unit_ids")
    @classmethod
    def validate_asset_unit_ids(cls, values: list[str]) -> list[str]:
        return _ensure_unique_ids(values, field_name="asset_unit_ids")

    @model_validator(mode="after")
    def validate_period(self) -> Self:
        if self.end_date < self.start_date:
            raise ValueError("end_date 不得早于 start_date")
        return self


class UpstreamContractResponse(UpstreamContractCreate):
    id: str
    version: int
    created_at: datetime
    updated_at: datetime
    status: Literal[
        "scheduled",
        "active",
        "expiring",
        "expired_pending_action",
        "exited",
        "historical",
    ]
    warnings: list[ContractWarning] = Field(default_factory=list)
    idempotent: bool = False

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
        str_strip_whitespace=True,
    )


class TerminalContractCreate(_StrictPayload):
    contract_number: str = Field(..., min_length=1, max_length=100)
    contract_mode: TerminalContractMode
    tenant_party_id: str = Field(..., min_length=1)
    lessor_party_id: str = Field(..., min_length=1)
    upstream_contract_id: str | None = Field(None, min_length=1)
    start_date: date
    end_date: date
    deposit_months: Decimal | None = Field(None, ge=0)
    deposit_amount: Decimal = Field(default=Decimal("0"), ge=0)
    rent_collector: RentCollector
    renewed_from_id: str | None = Field(None, min_length=1)
    scan_document_id: str = Field(..., min_length=1)
    asset_unit_ids: list[str] = Field(..., min_length=1)
    rent_schedules: list[ContractRentScheduleInput] = Field(default_factory=list)

    @field_validator("asset_unit_ids")
    @classmethod
    def validate_asset_unit_ids(cls, values: list[str]) -> list[str]:
        return _ensure_unique_ids(values, field_name="asset_unit_ids")

    @model_validator(mode="after")
    def validate_terms(self) -> Self:
        if self.end_date < self.start_date:
            raise ValueError("end_date 不得早于 start_date")
        expected_collector = "operator" if self.contract_mode == "sublease" else "owner"
        if self.rent_collector != expected_collector:
            raise ValueError(
                f"rent_collector 与 contract_mode 不一致，应为 {expected_collector}"
            )
        return self


class TerminalContractUpdate(_StrictPayload):
    expected_version: int = Field(..., ge=1)
    upstream_contract_id: str | None = Field(None, min_length=1)
    end_date: date | None = None
    deposit_months: Decimal | None = Field(None, ge=0)
    deposit_amount: Decimal | None = Field(None, ge=0)


class TerminalContractConfirmRequest(_StrictPayload):
    """Human-confirmed terminal terms; session owns scan and renewal."""

    contract_number: str = Field(..., min_length=1, max_length=100)
    contract_mode: TerminalContractMode
    tenant_party_id: str = Field(..., min_length=1)
    lessor_party_id: str = Field(..., min_length=1)
    upstream_contract_id: str | None = Field(None, min_length=1)
    start_date: date
    end_date: date
    deposit_months: Decimal | None = Field(None, ge=0)
    deposit_amount: Decimal = Field(default=Decimal("0"), ge=0)
    rent_collector: RentCollector
    asset_unit_ids: list[str] = Field(..., min_length=1)
    rent_schedules: list[ContractRentScheduleInput] = Field(default_factory=list)

    @field_validator("asset_unit_ids")
    @classmethod
    def validate_asset_unit_ids(cls, values: list[str]) -> list[str]:
        return _ensure_unique_ids(values, field_name="asset_unit_ids")

    @model_validator(mode="after")
    def validate_terms(self) -> Self:
        if self.end_date < self.start_date:
            raise ValueError("end_date 不得早于 start_date")
        expected_collector = "operator" if self.contract_mode == "sublease" else "owner"
        if self.rent_collector != expected_collector:
            raise ValueError(
                f"rent_collector 与 contract_mode 不一致，应为 {expected_collector}"
            )
        return self


class TerminalContractResponse(TerminalContractCreate):
    id: str
    version: int
    created_at: datetime
    updated_at: datetime
    status: Literal["scheduled", "active", "expiring", "ended", "historical"]
    warnings: list[ContractWarning] = Field(default_factory=list)
    idempotent: bool = False

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
        str_strip_whitespace=True,
    )


class ContractCoverageItem(_StrictPayload):
    """One temporal coverage row on a contract detail."""

    asset_unit_id: str
    effective_from: date
    effective_to: date | None = None


class RentScheduleItem(_StrictPayload):
    """One confirmed rent stage on a contract detail."""

    id: str
    stage_start: date
    stage_end: date
    base_monthly_rent: Decimal
    increase_rate: Decimal
    free_rent_months: Decimal
    discount_amount: Decimal
    actual_monthly_rent: Decimal
    payment_cycle: PaymentCycle
    due_day: int


class RenewalChainItem(_StrictPayload):
    """One predecessor/current/successor node of a renewal chain."""

    contract_id: str
    contract_number: str
    start_date: date
    end_date: date
    relation: Literal["predecessor", "current", "successor"]


class LifecycleEventItem(_StrictPayload):
    """One replayed lifecycle fact on a contract detail."""

    id: str
    event_type: LifecycleEventType
    effective_date: date
    successor_contract_id: str | None = None
    reversed_event_id: str | None = None
    reason: str | None = None
    created_by: str
    created_at: datetime


class UpstreamContractListResponse(_StrictPayload):
    """One page of upstream contract rows with derived status."""

    items: list[UpstreamContractDetail]
    total: int


class TerminalContractListResponse(_StrictPayload):
    """One page of terminal contract rows with derived status and warnings."""

    items: list[TerminalContractDetail]
    total: int


class AssetUnitDetail(AssetUnitResponse):
    """Unit facts plus the live terminal contracts covering it."""

    terminal_contract_ids: list[str] = Field(default_factory=list)


class AssetUnitListResponse(_StrictPayload):
    """One page of asset-unit rows with derived rental facts."""

    items: list[AssetUnitDetail]
    total: int


class UpstreamContractDetail(UpstreamContractResponse):
    """Contract terms plus replayed aggregates for the detail read."""

    idempotent: bool = False
    asset_unit_ids: list[str] = Field(default_factory=list)
    # Read projection narrows the write-input list into confirmed schedule rows.
    rent_schedules: list[RentScheduleItem] = Field(default_factory=list)  # type: ignore[assignment]
    coverages: list[ContractCoverageItem] = Field(default_factory=list)
    renewal_chain: list[RenewalChainItem] = Field(default_factory=list)
    terminal_contract_ids: list[str] = Field(default_factory=list)
    lifecycle_events: list[LifecycleEventItem] = Field(default_factory=list)


class TerminalContractDetail(TerminalContractResponse):
    """Contract terms plus replayed aggregates for the detail read."""

    idempotent: bool = False
    asset_unit_ids: list[str] = Field(default_factory=list)
    # Read projection narrows the write-input list into confirmed schedule rows.
    rent_schedules: list[RentScheduleItem] = Field(default_factory=list)  # type: ignore[assignment]
    coverages: list[ContractCoverageItem] = Field(default_factory=list)
    renewal_chain: list[RenewalChainItem] = Field(default_factory=list)
    lifecycle_events: list[LifecycleEventItem] = Field(default_factory=list)


class ContractIntakeSessionResponse(_StrictPayload):
    id: str
    document_id: str
    contract_type: ContractIntakeType
    status: Literal[
        "uploaded",
        "extracting",
        "ready_for_review",
        "confirming",
        "confirmed",
        "cancelling",
        "cancelled",
        "failed",
    ]
    candidate_fields: dict[str, object] = Field(default_factory=dict)
    warnings: list[ContractWarning] = Field(default_factory=list)
    expires_at: datetime


class ContractLifecycleEventCreate(_StrictPayload):
    contract_kind: ContractKind
    contract_id: str = Field(..., min_length=1)
    event_type: LifecycleEventType
    effective_date: date
    termination_type: TerminationType | None = None
    handover_status: HandoverStatus | None = None
    deposit_settlement_status: DepositSettlementStatus | None = None
    successor_contract_id: str | None = Field(None, min_length=1)
    reversed_event_id: str | None = Field(None, min_length=1)
    reason: str | None = Field(None, max_length=500)
    created_by: str = Field(..., min_length=1)
    idempotency_key: str = Field(..., min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_event_shape(self) -> Self:
        if self.event_type == "terminated" and self.contract_kind != "terminal":
            raise ValueError("terminated 仅适用于 terminal 合同")
        if self.event_type == "exited" and self.contract_kind != "upstream":
            raise ValueError("exited 仅适用于 upstream 合同")
        if self.event_type == "renewed":
            if self.successor_contract_id is None:
                raise ValueError("renewed 必须提供 successor_contract_id")
            if self.successor_contract_id == self.contract_id:
                raise ValueError("successor_contract_id 不得等于 contract_id")
        elif self.successor_contract_id is not None:
            raise ValueError("非 renewed 事件不得提供 successor_contract_id")
        if self.event_type == "reversed":
            if self.reversed_event_id is None:
                raise ValueError("reversed 必须提供 reversed_event_id")
        elif self.reversed_event_id is not None:
            raise ValueError("非 reversed 事件不得提供 reversed_event_id")
        if self.event_type != "renewed" and (
            self.reason is None or self.reason.strip() == ""
        ):
            raise ValueError("终止、退出或撤销必须提供 reason")
        return self


class TerminalContractTerminationProposal(_StrictPayload):
    """Human-reviewed facts bound into a terminal termination preview."""

    effective_date: date
    termination_type: TerminationType
    handover_status: HandoverStatus
    deposit_settlement_status: DepositSettlementStatus
    reason: str = Field(..., min_length=1, max_length=500)


class TerminalContractTerminationReversalProposal(_StrictPayload):
    """Point at one termination event of this contract and void it."""

    target_event_id: str = Field(..., min_length=1, max_length=36)
    effective_date: date
    reason: str = Field(..., min_length=1, max_length=500)


class UpstreamContractExitProposal(_StrictPayload):
    """Human-reviewed facts bound into an upstream exit preview."""

    effective_date: date
    reason: str = Field(..., min_length=1, max_length=500)


class UpstreamContractExitReversalProposal(_StrictPayload):
    """Point at one exit event of this contract and void it."""

    target_event_id: str = Field(..., min_length=1, max_length=36)
    effective_date: date
    reason: str = Field(..., min_length=1, max_length=500)


class UpstreamContractRenewalRequest(_StrictPayload):
    """Signed successor facts; parties, type and units come from the old one."""

    contract_number: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    start_date: date
    end_date: date
    payment_cycle: PaymentCycle | None = None
    payment_day: int | None = Field(None, ge=1, le=31)
    management_fee_rate: Decimal | None = Field(None, ge=0, le=1)
    deposit_amount: Decimal = Field(default=Decimal("0"), ge=0)
    oa_reference: str | None = Field(None, max_length=100)
    scan_document_id: str = Field(..., min_length=1)
    scan_owner_id: str = Field(..., min_length=1)
    rent_schedules: list[ContractRentScheduleInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_terms(self) -> Self:
        if self.end_date < self.start_date:
            raise ValueError("end_date 不得早于 start_date")
        return self


class TerminalContractRenewalRequest(_StrictPayload):
    """Signed successor facts; parties, mode and units come from the old one."""

    contract_number: str = Field(..., min_length=1, max_length=100)
    upstream_contract_id: str | None = Field(None, min_length=1)
    start_date: date
    end_date: date
    deposit_months: Decimal | None = Field(None, ge=0)
    deposit_amount: Decimal = Field(default=Decimal("0"), ge=0)
    scan_document_id: str = Field(..., min_length=1)
    scan_owner_id: str = Field(..., min_length=1)
    rent_schedules: list[ContractRentScheduleInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_terms(self) -> Self:
        if self.end_date < self.start_date:
            raise ValueError("end_date 不得早于 start_date")
        return self


class ContractLifecycleEventResponse(_StrictPayload):
    id: str
    contract_kind: ContractKind
    contract_id: str
    event_type: LifecycleEventType
    effective_date: date
    termination_type: TerminationType | None = None
    handover_status: HandoverStatus | None = None
    deposit_settlement_status: DepositSettlementStatus | None = None
    successor_contract_id: str | None = None
    reversed_event_id: str | None = None
    reason: str | None = None
    created_by: str
    created_at: datetime
    idempotency_key: str
    idempotent: bool = False

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
        str_strip_whitespace=True,
    )


class TerminalContractTerminationCoverageImpact(_StrictPayload):
    """One covered unit's coverage end before and after a termination."""

    asset_unit_id: str
    effective_from: date
    current_effective_to: date | None = None
    new_effective_to: date


class TerminalContractTerminationPreviewResponse(_StrictPayload):
    """Impact confirmation for one terminal termination, bound to a token."""

    contract_id: str
    contract_number: str
    contract_version: int
    effective_date: date
    last_valid_day: date
    coverage_impact: list[TerminalContractTerminationCoverageImpact]
    warnings: list[str] = Field(default_factory=list)
    proposal: TerminalContractTerminationProposal
    preview_token: str = Field(..., min_length=1)
    expires_at: datetime


class TerminalContractTerminationCommitRequest(_StrictPayload):
    """Consume one termination preview token under the shown version."""

    preview_token: str = Field(..., min_length=1, max_length=512)
    expected_version: int = Field(..., ge=1)


class UpstreamContractExitCoverageImpact(_StrictPayload):
    """One covered unit's upstream coverage end before and after an exit."""

    asset_unit_id: str
    effective_from: date
    current_effective_to: date | None = None
    new_effective_to: date


class UpstreamContractExitPreviewResponse(_StrictPayload):
    """Impact confirmation for one upstream exit, bound to a token."""

    contract_id: str
    contract_number: str
    contract_version: int
    deposit_amount: Decimal
    effective_date: date
    last_valid_day: date
    coverage_impact: list[UpstreamContractExitCoverageImpact]
    warnings: list[str] = Field(default_factory=list)
    proposal: UpstreamContractExitProposal
    preview_token: str = Field(..., min_length=1)
    expires_at: datetime


class UpstreamContractExitCommitRequest(_StrictPayload):
    """Consume one exit preview token under the shown version."""

    preview_token: str = Field(..., min_length=1, max_length=512)
    expected_version: int = Field(..., ge=1)


__all__ = [
    "AssetUnitBoundaryCommitResponse",
    "AssetUnitBoundaryImpact",
    "AssetUnitBoundaryPreviewResponse",
    "AssetUnitCreate",
    "AssetUnitMergeCommitRequest",
    "AssetUnitMergePreviewRequest",
    "AssetUnitMergeProposal",
    "AssetUnitMergeResultInput",
    "AssetUnitResponse",
    "AssetUnitDetail",
    "AssetUnitListResponse",
    "AssetUnitSplitPartInput",
    "AssetUnitSplitCommitRequest",
    "AssetUnitSplitPreviewRequest",
    "AssetUnitSplitProposal",
    "AssetUnitUpdate",
    "AssetUnitVacancyNoteUpdate",
    "ContractLifecycleEventCreate",
    "ContractLifecycleEventResponse",
    "ContractIntakeSessionResponse",
    "ContractIntakeType",
    "ContractRentScheduleInput",
    "ContractWarning",
    "TerminalContractCreate",
    "TerminalContractConfirmRequest",
    "TerminalContractTerminationCommitRequest",
    "TerminalContractTerminationCoverageImpact",
    "TerminalContractTerminationPreviewResponse",
    "TerminalContractTerminationReversalProposal",
    "TerminalContractResponse",
    "TerminalContractTerminationProposal",
    "TerminalContractUpdate",
    "UpstreamContractCreate",
    "UpstreamContractConfirmRequest",
    "UpstreamContractExitCommitRequest",
    "UpstreamContractExitCoverageImpact",
    "UpstreamContractExitPreviewResponse",
    "UpstreamContractExitProposal",
    "UpstreamContractExitReversalProposal",
    "UpstreamContractRenewalRequest",
    "TerminalContractRenewalRequest",
    "UpstreamContractDetail",
    "TerminalContractDetail",
    "UpstreamContractListResponse",
    "TerminalContractListResponse",
    "ContractCoverageItem",
    "RentScheduleItem",
    "RenewalChainItem",
    "LifecycleEventItem",
    "UpstreamContractResponse",
    "UpstreamContractUpdate",
]
