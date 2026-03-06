"""
合同组体系 Pydantic Schemas（REQ-RNT-001 M2）

对应数据模型：docs/features/requirements-appendix-fields.md §3.3–§3.7
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_core import PydanticCustomError

from ..models.contract_group import (
    ContractDirection,
    ContractLifecycleStatus,
    ContractRelationType,
    ContractReviewStatus,
    GroupRelationType,
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

    revenue_mode: RevenueMode = Field(..., description="经营模式：lease / agency")
    operator_party_id: str = Field(..., min_length=1, description="运营方主体 ID")
    owner_party_id: str = Field(..., min_length=1, description="产权方主体 ID")
    effective_from: date = Field(..., description="合同组有效开始日期")
    effective_to: date | None = Field(None, description="合同组有效结束日期（可空）")
    settlement_rule: SettlementRuleSchema = Field(..., description="结算规则（五键必填）")
    revenue_attribution_rule: dict[str, Any] | None = Field(None, description="收益归属规则")
    revenue_share_rule: dict[str, Any] | None = Field(None, description="收益分成规则")
    risk_tags: list[str] | None = Field(None, description="风险标签列表")
    predecessor_group_id: str | None = Field(None, description="前驱合同组 ID（续签用）")
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
    asset_ids: list[str] | None = Field(None, description="替换资产关联，None 表示不修改")


class ContractGroupListItem(BaseModel):
    """合同组列表出参（精简）"""

    contract_group_id: str
    group_code: str
    revenue_mode: RevenueMode
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

    settlement_rule: dict[str, Any]
    revenue_attribution_rule: dict[str, Any] | None
    revenue_share_rule: dict[str, Any] | None
    risk_tags: list[str] | None
    predecessor_group_id: str | None
    version: int
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


class ContractCreate(BaseModel):
    """创建合同入参"""

    contract_group_id: str = Field(..., min_length=1, description="所属合同组 ID")
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
    status: ContractLifecycleStatus = Field(ContractLifecycleStatus.DRAFT)
    review_status: ContractReviewStatus = Field(ContractReviewStatus.DRAFT)
    contract_notes: str | None = Field(None)
    source_session_id: str | None = Field(None, max_length=100)
    asset_ids: list[str] = Field(default_factory=list, description="关联资产 ID 列表")
    lease_detail: LeaseDetailCreate | None = Field(None, description="租赁合同明细")
    agency_detail: AgencyDetailCreate | None = Field(None, description="代理协议明细")

    @model_validator(mode="after")
    def validate_date_range(self) -> "ContractCreate":
        if self.effective_to is not None and self.effective_to <= self.effective_from:
            raise PydanticCustomError(
                "invalid_date_range",
                "合同结束日期必须晚于开始日期",
                {},
            )
        return self


class ContractSummary(BaseModel):
    """合同组内合同摘要"""

    contract_id: str
    contract_direction: ContractDirection
    group_relation_type: GroupRelationType
    lessor_party_id: str
    lessee_party_id: str
    effective_from: date
    effective_to: date | None
    status: ContractLifecycleStatus
    review_status: ContractReviewStatus

    model_config = ConfigDict(from_attributes=True)


class ContractDetail(BaseModel):
    """合同详情出参"""

    contract_id: str
    contract_group_id: str
    contract_direction: ContractDirection
    group_relation_type: GroupRelationType
    lessor_party_id: str
    lessee_party_id: str
    sign_date: date | None
    effective_from: date
    effective_to: date | None
    currency_code: str
    tax_rate: Decimal | None
    is_tax_included: bool
    status: ContractLifecycleStatus
    review_status: ContractReviewStatus
    review_by: str | None
    reviewed_at: datetime | None
    review_reason: str | None
    contract_notes: str | None
    data_status: str
    version: int
    created_at: datetime
    updated_at: datetime
    lease_detail: LeaseDetailResponse | None = None
    agency_detail: AgencyDetailResponse | None = None

    model_config = ConfigDict(from_attributes=True)


class ContractRelationCreate(BaseModel):
    """创建合同关系入参"""

    parent_contract_id: str = Field(..., min_length=1)
    child_contract_id: str = Field(..., min_length=1)
    relation_type: ContractRelationType = Field(...)

    @model_validator(mode="after")
    def validate_no_self_relation(self) -> "ContractRelationCreate":
        if self.parent_contract_id == self.child_contract_id:
            raise PydanticCustomError(
                "self_relation",
                "parent_contract_id 和 child_contract_id 不能相同",
                {},
            )
        return self


# 解决 ContractGroupDetail 中 ContractSummary 的前向引用
ContractGroupDetail.model_rebuild()
