"""
合同关系技术聚合 Pydantic Schemas（REQ-RNT-001 M2）

对应数据模型：docs/features/requirements-appendix-fields.md §3.3–§3.7
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError

from ..models.contract_group import (
    ContractDirection,
    ContractLifecycleStatus,
    GroupRelationType,
    LedgerFollowUpStatus,
    LedgerView,
    OperationalPaymentFlowStatus,
    OperationalPaymentFlowType,
    PaymentAllocationTargetType,
    RevenueMode,
)

# ===================== Settlement Rule =====================

_VALID_PAYMENT_CYCLES = {"月付", "季付", "半年付", "年付"}


class SettlementRuleSchema(BaseModel):
    """结算规则 JSON 结构 — 五个必填键"""

    version: str = Field(..., min_length=1, description="规则版本标识")
    cycle: str = Field(..., description="结算周期：月付/季付/半年付/年付")
    settlement_mode: str = Field(..., min_length=1, description="结算模式描述")
    amount_rule: dict[str, Any] = Field(..., description="金额规则对象")
    payment_rule: dict[str, Any] = Field(..., description="支付规则对象")

    @model_validator(mode="after")
    def validate_cycle(self) -> "SettlementRuleSchema":
        if self.cycle not in _VALID_PAYMENT_CYCLES:
            raise PydanticCustomError(
                "invalid_payment_cycle",
                f"结算周期必须为 {sorted(_VALID_PAYMENT_CYCLES)} 之一，当前值：{self.cycle}",
                {},
            )
        return self


# ===================== ContractGroup =====================


class ContractGroupCreate(BaseModel):
    """创建合同组入参"""

    project_id: str = Field(..., min_length=1, description="所属项目 ID")
    revenue_mode: RevenueMode = Field(..., description="经营模式：lease / agency")
    operator_party_id: str = Field(..., min_length=1, description="运营方主体 ID")
    owner_party_id: str = Field(..., min_length=1, description="产权方主体 ID")
    effective_from: date = Field(..., description="合同组有效开始日期")
    effective_to: date | None = Field(None, description="合同组有效结束日期（可空）")
    settlement_rule: SettlementRuleSchema | None = Field(None, description="结算规则")
    revenue_attribution_rule: dict[str, Any] | None = Field(
        None, description="收益归属规则"
    )
    revenue_share_rule: dict[str, Any] | None = Field(None, description="收益分成规则")
    risk_tags: list[str] | None = Field(None, description="风险标签列表")
    asset_ids: list[str] = Field(default_factory=list, description="关联资产 ID 列表")

    @model_validator(mode="after")
    def validate_date_range(self) -> "ContractGroupCreate":
        if self.effective_to is not None and self.effective_to <= self.effective_from:
            raise PydanticCustomError(
                "invalid_date_range",
                "合同组结束日期必须晚于开始日期",
                {},
            )
        return self


class ContractGroupUpdate(BaseModel):
    """更新合同组入参（均可选）"""

    effective_to: date | None = Field(None, description="合同组有效结束日期")
    settlement_rule: SettlementRuleSchema | None = Field(None, description="结算规则")
    revenue_attribution_rule: dict[str, Any] | None = Field(None)
    revenue_share_rule: dict[str, Any] | None = Field(None)
    risk_tags: list[str] | None = Field(None)
    asset_ids: list[str] | None = Field(
        None, description="替换资产关联，None 表示不修改"
    )


class ContractGroupListItem(BaseModel):
    """合同组列表出参（精简）"""

    contract_group_id: str
    project_id: str | None = None
    project_name: str | None = None
    group_code: str
    revenue_mode: RevenueMode
    contract_role_counts: dict[str, int] = Field(default_factory=dict)
    operator_party_id: str
    owner_party_id: str
    effective_from: date
    effective_to: date | None
    derived_status: str
    data_status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ContractGroupDetail(ContractGroupListItem):
    """合同组详情出参（含派生字段及合同摘要列表）"""

    settlement_rule: dict[str, Any] | None
    revenue_attribution_rule: dict[str, Any] | None
    revenue_share_rule: dict[str, Any] | None
    risk_tags: list[str] | None
    upstream_contract_ids: list[str] = Field(default_factory=list)
    downstream_contract_ids: list[str] = Field(default_factory=list)
    contracts: list["ContractSummary"] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# ===================== Contract Detail Schemas =====================


class LeaseDetailCreate(BaseModel):
    """租赁合同明细 — 创建入参"""

    total_deposit: Decimal = Field(Decimal("0"), ge=0, description="押金总额")
    rent_amount: Decimal = Field(..., ge=0, description="合同级租金汇总")
    monthly_rent_base: Decimal | None = Field(None, ge=0, description="月租基数")
    payment_cycle: str = Field("月付", description="付款周期：月付/季付/半年付/年付")
    payment_terms: str | None = Field(None, description="付款条款说明")
    tenant_name: str | None = Field(None, max_length=200)
    tenant_contact: str | None = Field(None, max_length=100)
    tenant_phone: str | None = Field(None, max_length=20)
    tenant_address: str | None = Field(None, max_length=500)
    tenant_usage: str | None = Field(None, max_length=500)
    owner_name: str | None = Field(None, max_length=200)
    owner_contact: str | None = Field(None, max_length=100)
    owner_phone: str | None = Field(None, max_length=20)

    @model_validator(mode="after")
    def validate_payment_cycle(self) -> "LeaseDetailCreate":
        if self.payment_cycle not in _VALID_PAYMENT_CYCLES:
            raise PydanticCustomError(
                "invalid_payment_cycle",
                f"付款周期必须为 {sorted(_VALID_PAYMENT_CYCLES)} 之一",
                {},
            )
        return self


class LeaseDetailResponse(LeaseDetailCreate):
    """租赁合同明细 — 出参"""

    lease_detail_id: str
    contract_id: str
    rent_amount_excl_tax: Decimal | None = Field(None, description="不含税金额（派生）")

    model_config = ConfigDict(from_attributes=True)


class AgencyDetailCreate(BaseModel):
    """代理协议明细 — 创建入参"""

    service_fee_ratio: Decimal = Field(
        ..., ge=Decimal("0"), le=Decimal("1"), description="服务费比例，如 0.05 = 5%"
    )
    fee_calculation_base: str = Field(
        "actual_received", description="计费基数：actual_received / due_amount"
    )
    agency_scope: str | None = Field(None, description="代理范围说明")

    @model_validator(mode="after")
    def validate_fee_base(self) -> "AgencyDetailCreate":
        valid = {"actual_received", "due_amount"}
        if self.fee_calculation_base not in valid:
            raise PydanticCustomError(
                "invalid_fee_calculation_base",
                f"计费基数必须为 {sorted(valid)} 之一",
                {},
            )
        return self


class AgencyDetailResponse(AgencyDetailCreate):
    """代理协议明细 — 出参"""

    agency_detail_id: str
    contract_id: str

    model_config = ConfigDict(from_attributes=True)


# ===================== Contract =====================


class ContractRentTermCreate(BaseModel):
    """创建租金条款入参。"""

    sort_order: int = Field(..., ge=1)
    start_date: date
    end_date: date
    monthly_rent: Decimal = Field(..., ge=0)
    management_fee: Decimal = Field(Decimal("0"), ge=0)
    other_fees: Decimal = Field(Decimal("0"), ge=0)
    notes: str | None = None

    @model_validator(mode="after")
    def validate_date_range(self) -> "ContractRentTermCreate":
        if self.end_date < self.start_date:
            raise PydanticCustomError(
                "invalid_rent_term_date_range",
                "租金条款结束日期不得早于开始日期",
                {},
            )
        return self


class ContractCreate(BaseModel):
    """创建合同入参"""

    contract_group_id: str = Field(..., min_length=1, description="所属合同组 ID")
    contract_number: str = Field(
        ..., min_length=1, max_length=100, description="合同编号"
    )
    contract_direction: ContractDirection = Field(..., description="合同方向")
    group_relation_type: GroupRelationType = Field(..., description="合同角色")
    lessor_party_id: str = Field(..., min_length=1, description="出租方/委托方主体 ID")
    lessee_party_id: str = Field(..., min_length=1, description="承租方/受托方主体 ID")
    sign_date: date | None = Field(None, description="签订日期（草稿可空）")
    effective_from: date = Field(..., description="合同生效日期")
    effective_to: date | None = Field(None, description="合同到期日期（可空）")
    currency_code: str = Field("CNY", max_length=10)
    tax_rate: Decimal | None = Field(None, ge=0, le=1)
    is_tax_included: bool = Field(True)
    contract_notes: str | None = Field(None)
    source_session_id: str | None = Field(None, max_length=100)
    asset_ids: list[str] = Field(default_factory=list, description="关联资产 ID 列表")
    lease_detail: LeaseDetailCreate | None = Field(None, description="租赁合同明细")
    agency_detail: AgencyDetailCreate | None = Field(None, description="代理协议明细")
    rent_terms: list[ContractRentTermCreate] = Field(
        default_factory=list,
        description="初始租金条款，与合同在同一事务内落库",
    )

    @model_validator(mode="after")
    def validate_date_range(self) -> "ContractCreate":
        if self.effective_to is not None and self.effective_to <= self.effective_from:
            raise PydanticCustomError(
                "invalid_date_range",
                "合同结束日期必须晚于开始日期",
                {},
            )
        return self


# 同 session 场景下 ORM 对象可能携带枚举 name 字符串（如 'LESSEE'），
# 响应 schema 的枚举为中文值（'承租'）。创建后立即序列化详情会命中
# identity map 缓存对象，需要归一化（见 2026-08-09 验收 5.1）。
_ENUM_NAME_TO_VALUE: dict[str, str] = {
    "LESSEE": "承租",
    "LESSOR": "出租",
    "UPSTREAM": "上游",
    "DOWNSTREAM": "下游",
    "ENTRUSTED": "委托",
    "DIRECT_LEASE": "直租",
    "DRAFT": "草稿",
    "ACTIVE": "生效",
    "TERMINATED": "已终止",
}


def _coerce_enum_name(value: Any) -> Any:
    """枚举 name 字符串归一化为 .value；枚举对象与原值直接透传。"""
    if isinstance(value, str):
        return _ENUM_NAME_TO_VALUE.get(value, value)
    return value


class ContractSummary(BaseModel):
    """合同组内合同摘要"""

    contract_id: str
    contract_number: str
    contract_direction: ContractDirection
    group_relation_type: GroupRelationType
    lessor_party_id: str
    lessee_party_id: str
    lessor_name_snapshot: str | None = None
    lessee_name_snapshot: str | None = None
    effective_from: date
    effective_to: date | None
    status: ContractLifecycleStatus

    model_config = ConfigDict(from_attributes=True)

    @field_validator(
        "contract_direction", "group_relation_type", "status", mode="before"
    )
    @classmethod
    def coerce_enum_names(cls, v: Any) -> Any:
        return _coerce_enum_name(v)


class ContractDetail(BaseModel):
    """合同详情出参"""

    contract_id: str
    contract_group_id: str
    project_id: str | None = None
    contract_number: str
    contract_direction: ContractDirection
    group_relation_type: GroupRelationType
    lessor_party_id: str
    lessee_party_id: str
    lessor_name_snapshot: str | None = None
    lessee_name_snapshot: str | None = None
    sign_date: date | None
    effective_from: date
    effective_to: date | None
    currency_code: str
    tax_rate: Decimal | None
    is_tax_included: bool
    status: ContractLifecycleStatus
    contract_notes: str | None
    data_status: str
    created_at: datetime
    updated_at: datetime
    lease_detail: LeaseDetailResponse | None = None
    agency_detail: AgencyDetailResponse | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator(
        "contract_direction", "group_relation_type", "status", mode="before"
    )
    @classmethod
    def coerce_enum_names(cls, v: Any) -> Any:
        return _coerce_enum_name(v)


class ContractScanDocumentCreate(BaseModel):
    """合同盖章扫描件元数据入参。"""

    storage_key: str = Field(..., min_length=1, max_length=300)
    original_filename: str = Field(..., min_length=1, max_length=255)
    content_type: str | None = Field(None, max_length=100)
    file_size: int | None = Field(None, ge=0)
    checksum_sha256: str | None = Field(None, min_length=64, max_length=64)


class ContractScanDocumentResponse(ContractScanDocumentCreate):
    """合同盖章扫描件出参。"""

    document_id: str
    data_status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ContractScanDocumentReplaceRequest(BaseModel):
    """整体替换同合同号所有记录的扫描件关联。"""

    documents: list[ContractScanDocumentCreate] = Field(..., min_length=1)


class ContractLifecycleAction(BaseModel):
    """合同生命周期操作入参。"""

    reason: str | None = Field(None, description="驳回 / 终止 / 作废原因")
    related_entry_id: str | None = Field(None, description="关联单号")


class ContractCorrectionStartRequest(BaseModel):
    """发起纠错草稿入参。"""

    reason: str = Field(..., min_length=1, description="纠错原因")


class AuditLogResponse(BaseModel):
    """审计日志出参。"""

    log_id: str
    contract_id: str
    action: str
    old_status: str | None
    new_status: str | None
    reason: str | None
    operator_id: str | None
    operator_name: str | None
    related_entry_id: str | None
    context: dict[str, Any] | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ContractRentTermUpdate(BaseModel):
    """更新租金条款入参。"""

    sort_order: int | None = Field(None, ge=1)
    start_date: date | None = None
    end_date: date | None = None
    monthly_rent: Decimal | None = Field(None, ge=0)
    management_fee: Decimal | None = Field(None, ge=0)
    other_fees: Decimal | None = Field(None, ge=0)
    notes: str | None = None

    @model_validator(mode="after")
    def validate_date_range(self) -> "ContractRentTermUpdate":
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.end_date < self.start_date
        ):
            raise PydanticCustomError(
                "invalid_rent_term_date_range",
                "租金条款结束日期不得早于开始日期",
                {},
            )
        return self


class ContractRentTermResponse(BaseModel):
    """租金条款出参。"""

    rent_term_id: str
    contract_id: str
    sort_order: int
    start_date: date
    end_date: date
    monthly_rent: Decimal
    management_fee: Decimal
    other_fees: Decimal
    total_monthly_amount: Decimal | None
    notes: str | None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ContractLedgerEntryResponse(BaseModel):
    """合同台账条目出参。"""

    entry_id: str
    contract_id: str
    year_month: str
    due_date: date
    amount_due: Decimal
    ledger_views: list[LedgerView]
    flow_occurred_on_dates: list[date] = Field(default_factory=list)
    currency_code: str
    is_tax_included: bool
    tax_rate: Decimal | None
    payment_status: str
    paid_amount: Decimal
    follow_up_status: LedgerFollowUpStatus | None = None
    next_follow_up_date: date | None = None
    follow_up_note: str | None = None
    attributed_project_id: str | None = None
    attributed_owner_party_id: str | None = None
    attributed_operator_party_id: str | None = None
    attributed_asset_ids: list[str] | None = None
    notes: str | None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class LedgerAggregateQueryParams(BaseModel):
    """跨合同台账聚合查询参数。"""

    ledger_view: (
        Literal[
            "terminal_collection",
            "operator_income",
            "operator_cost",
        ]
        | None
    ) = Field(None, description="经营台账视图")
    project_id: str | None = Field(None, min_length=1, description="项目 ID")
    asset_id: str | None = Field(None, min_length=1, description="资产 ID")
    party_id: str | None = Field(None, min_length=1, description="主体 ID")
    contract_id: str | None = Field(None, min_length=1, description="合同 ID")
    year_month_start: str | None = Field(
        None,
        pattern=r"^\d{4}-\d{2}$",
        description="开始账期，格式 YYYY-MM",
    )
    year_month_end: str | None = Field(
        None,
        pattern=r"^\d{4}-\d{2}$",
        description="结束账期，格式 YYYY-MM",
    )
    flow_occurred_on_start: date | None = Field(
        None,
        description="收付流水发生日期开始",
    )
    flow_occurred_on_end: date | None = Field(
        None,
        description="收付流水发生日期结束",
    )
    payment_status: (
        Literal[
            "unpaid",
            "paid",
            "partial",
            "voided",
        ]
        | None
    ) = Field(None, description="支付状态")
    include_voided: bool = Field(False, description="是否包含作废条目")
    offset: int = Field(0, ge=0, description="分页偏移")
    limit: int = Field(20, ge=1, le=200, description="每页条数")

    @model_validator(mode="after")
    def validate_filters(self) -> "LedgerAggregateQueryParams":
        if not any(
            [
                self.project_id is not None,
                self.asset_id is not None,
                self.party_id is not None,
                self.contract_id is not None,
                self.year_month_start is not None,
                self.flow_occurred_on_start is not None,
                self.flow_occurred_on_end is not None,
            ]
        ):
            raise PydanticCustomError(
                "missing_ledger_filters",
                "project_id、asset_id、party_id、contract_id、year_month_start、flow_occurred_on_start 至少需要一个筛选条件",
                {},
            )
        if (
            self.year_month_start is not None
            and self.year_month_end is not None
            and self.year_month_start > self.year_month_end
        ):
            raise PydanticCustomError(
                "invalid_year_month_range",
                "开始账期不能晚于结束账期",
                {},
            )
        if (
            self.flow_occurred_on_start is not None
            and self.flow_occurred_on_end is not None
            and self.flow_occurred_on_start > self.flow_occurred_on_end
        ):
            raise PydanticCustomError(
                "invalid_flow_occurred_on_range",
                "flow occurred start date cannot be after end date",
                {},
            )
        return self


class ContractLedgerListResponse(BaseModel):
    """合同台账分页出参。"""

    items: list[ContractLedgerEntryResponse]
    total: int
    offset: int
    limit: int


class LedgerExportQueryParams(LedgerAggregateQueryParams):
    """台账导出查询参数。"""

    export_format: Literal["csv", "excel"] = Field(
        "excel",
        description="导出格式",
    )


class LedgerFollowUpUpdateRequest(BaseModel):
    """Update lightweight terminal-collection follow-up fields."""

    model_config = ConfigDict(extra="forbid")

    follow_up_status: LedgerFollowUpStatus | None = None
    next_follow_up_date: date | None = None
    follow_up_note: str | None = Field(None, max_length=500)


class LedgerRecalculateSkippedEntry(BaseModel):
    """重算时跳过的台账条目。"""

    entry_id: str
    year_month: str
    payment_status: str
    reason: str


class LedgerRecalculateResponse(BaseModel):
    """台账重算结果摘要。"""

    created: int = Field(..., ge=0)
    updated: int = Field(..., ge=0)
    voided: int = Field(..., ge=0)
    skipped_entries: list[LedgerRecalculateSkippedEntry] = Field(default_factory=list)


class OperationalPaymentFlowCreate(BaseModel):
    """Request body for creating an operational payment flow."""

    flow_type: OperationalPaymentFlowType
    occurred_on: date
    amount: Decimal = Field(..., gt=0)
    counterparty_id: str | None = None
    voucher_attachment_ids: list[str] | None = None
    notes: str | None = None


class OperationalPaymentFlowResponse(BaseModel):
    """Response payload for an operational payment flow."""

    flow_id: str
    flow_type: OperationalPaymentFlowType
    occurred_on: date
    amount: Decimal
    registered_by: str
    counterparty_id: str | None = None
    voucher_attachment_ids: list[str] | None = None
    notes: str | None = None
    status: OperationalPaymentFlowStatus
    corrected_from_flow_id: str | None = None
    status_changed_by: str | None = None
    status_changed_at: datetime | None = None
    status_change_reason: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class PaymentVoucherAttachmentResponse(BaseModel):
    """Downloadable voucher metadata exposed with a payment flow."""

    id: str
    file_name: str
    file_type: str
    file_size: int

    model_config = ConfigDict(from_attributes=True)


class PaymentVoucherDownloadAuditResponse(BaseModel):
    """Scoped evidence for one voucher download attempt."""

    log_id: str
    user_id: str
    flow_id: str
    attachment_id: str
    file_name: str | None = None
    downloaded_at: datetime
    result: Literal["success", "not_found"]


class PaymentAllocationCreate(BaseModel):
    """Request row for allocating one payment flow to a ledger period."""

    target_type: PaymentAllocationTargetType
    target_id: str = Field(..., min_length=1)
    year_month: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    amount: Decimal = Field(..., gt=0)


class PaymentAllocationSaveRequest(BaseModel):
    """Request body for replacing allocations for one flow."""

    allocations: list[PaymentAllocationCreate] = Field(..., min_length=1)


class PaymentFlowLifecycleActionRequest(BaseModel):
    """Reason required for a payment-flow terminal action."""

    reason: str = Field(..., min_length=1, max_length=500)


class PaymentFlowCorrectionRequest(PaymentFlowLifecycleActionRequest):
    """Atomic replacement payload for one active payment flow."""

    replacement: OperationalPaymentFlowCreate
    allocations: list[PaymentAllocationCreate] = Field(..., min_length=1)


class PaymentAllocationResponse(BaseModel):
    """Response payload for a payment allocation."""

    allocation_id: str
    flow_id: str
    target_type: PaymentAllocationTargetType
    target_id: str
    year_month: str
    amount: Decimal
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class OperationalPaymentFlowDetailResponse(OperationalPaymentFlowResponse):
    """Payment flow with allocations and authorized voucher metadata."""

    allocations: list[PaymentAllocationResponse] = Field(default_factory=list)
    voucher_attachments: list[PaymentVoucherAttachmentResponse] = Field(
        default_factory=list
    )


class ServiceFeeLedgerResponse(BaseModel):
    """Response payload for a monthly service-fee ledger entry."""

    service_fee_entry_id: str
    contract_group_id: str
    agency_contract_id: str
    agency_agreement_contract_id: str
    source_ledger_ids: list[str]
    year_month: str
    amount_due: Decimal
    paid_amount: Decimal
    payment_status: str
    currency_code: str
    service_fee_ratio: Decimal
    calculation_base_amount: Decimal
    attributed_project_id: str | None = None
    attributed_owner_party_id: str | None = None
    attributed_operator_party_id: str | None = None
    attributed_asset_ids: list[str] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ServiceFeeGenerateRequest(BaseModel):
    """Request body for generating monthly service-fee ledger entries."""

    contract_group_id: str = Field(..., min_length=1)


class ServiceFeeSourceReconcileRequest(BaseModel):
    """Explicit operator confirmation for adopting the current source facts."""

    reason: str = Field(..., min_length=1, max_length=500)


class ServiceFeeGenerateResponse(BaseModel):
    """Result summary for monthly service-fee generation."""

    created: int = Field(..., ge=0)
    updated: int = Field(..., ge=0)
    voided: int = Field(..., ge=0)
    source_mismatches: int = Field(..., ge=0)


class LedgerCompensationFailure(BaseModel):
    """台账补偿失败项。"""

    contract_id: str
    error: str


class LedgerCompensationResponse(BaseModel):
    """台账补偿结果摘要。"""

    contracts_scanned: int = Field(..., ge=0)
    contracts_repaired: int = Field(..., ge=0)
    rent_entries_created: int = Field(..., ge=0)
    rent_entries_voided: int = Field(..., ge=0)
    failures: list[LedgerCompensationFailure] = Field(default_factory=list)
    timestamp: str


# 解决 ContractGroupDetail 中 ContractSummary 的前向引用
ContractGroupDetail.model_rebuild()
