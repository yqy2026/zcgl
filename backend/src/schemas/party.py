"""Pydantic schemas for Party-Role domain APIs."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..models.party import PartyReviewStatus, PartyType
from ..models.user_party_binding import RelationType

PartyBusinessRole = Literal["owner", "operator", "terminal_tenant"]
PartyLifecycleOperation = Literal["deactivate", "reactivate"]
PartyIdentifierType = Literal[
    "unified_social_credit_code",
    "legal_registration_number",
    "foreign_registration_number",
    "national_id",
    "passport",
]


class PartyCreate(BaseModel):
    """Party create payload."""

    model_config = ConfigDict(extra="forbid")

    party_type: PartyType = Field(..., description="主体类型")
    name: str = Field(..., min_length=1, max_length=200, description="主体名称")
    identifier_type: PartyIdentifierType | None = Field(
        None, description="正式标识类型"
    )
    identifier_value: str | None = Field(
        None, min_length=1, max_length=500, description="正式标识值"
    )
    external_ref: str | None = Field(None, max_length=200, description="外部引用")
    metadata: dict[str, Any] | None = Field(default=None, description="扩展元数据")

    @model_validator(mode="after")
    def validate_identifier_pair(self) -> "PartyCreate":
        if (self.identifier_type is None) != (self.identifier_value is None):
            raise ValueError("identifier_type 与 identifier_value 必须同时提供")
        return self


class PartyUpdate(BaseModel):
    """Party update payload."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(None, min_length=1, max_length=200, description="主体名称")
    identifier_type: PartyIdentifierType | None = Field(
        None, description="正式标识类型"
    )
    identifier_value: str | None = Field(
        None, min_length=1, max_length=500, description="正式标识值"
    )
    external_ref: str | None = Field(None, max_length=200, description="外部引用")
    metadata: dict[str, Any] | None = Field(default=None, description="扩展元数据")

    @model_validator(mode="after")
    def validate_identifier_pair(self) -> "PartyUpdate":
        identifier_fields = {"identifier_type", "identifier_value"}
        supplied_fields = identifier_fields.intersection(self.model_fields_set)
        if len(supplied_fields) not in {0, 2}:
            raise ValueError("identifier_type 与 identifier_value 必须同时提供")
        if len(supplied_fields) == 2 and (
            (self.identifier_type is None) != (self.identifier_value is None)
        ):
            raise ValueError(
                "identifier_type 与 identifier_value 必须同时为空或同时有值"
            )
        return self


class PartyResponse(BaseModel):
    """Party response."""

    id: str
    business_roles: list[PartyBusinessRole] = Field(default_factory=list)
    party_type: PartyType
    name: str
    code: str
    identifier_type: PartyIdentifierType | None = None
    identifier_display: str | None = None
    external_ref: str | None = None
    status: str
    metadata: dict[str, Any] | None = Field(
        default=None,
        validation_alias="metadata_json",
        description="扩展元数据",
    )
    review_status: PartyReviewStatus | None = None
    review_by: str | None = None
    reviewed_at: datetime | None = None
    review_reason: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class PartyLifecyclePreviewRequest(BaseModel):
    """Requested Party activation-state transition."""

    operation: PartyLifecycleOperation

    model_config = ConfigDict(extra="forbid")


class PartyLifecycleState(BaseModel):
    """Party availability state before or after a lifecycle action."""

    party_id: str
    status: str
    review_status: str
    available_for_new_references: bool


class PartyLifecycleImpact(BaseModel):
    """References and effective scopes affected by a Party state change."""

    represented_organization_count: int = Field(..., ge=0)
    potentially_affected_organization_count: int = Field(..., ge=0)
    current_user_binding_count: int = Field(..., ge=0)
    affected_user_count: int = Field(..., ge=0)
    user_scope_change_count: int = Field(..., ge=0)
    asset_reference_count: int = Field(..., ge=0)
    project_reference_count: int = Field(..., ge=0)
    contract_group_reference_count: int = Field(..., ge=0)
    contract_reference_count: int = Field(..., ge=0)


class PartyLifecyclePreviewResponse(BaseModel):
    party_id: str
    operation: PartyLifecycleOperation
    before_state: PartyLifecycleState
    after_state: PartyLifecycleState
    impact: PartyLifecycleImpact
    preview_token: str
    expires_at: datetime


class PartyLifecycleCommitRequest(BaseModel):
    preview_token: str = Field(..., min_length=1, max_length=512)
    reason: str = Field(..., min_length=1, max_length=500)
    idempotency_key: str = Field(..., min_length=1, max_length=128)

    @field_validator("preview_token", "reason", "idempotency_key")
    @classmethod
    def reject_blank_value(cls, value: str) -> str:
        normalized = value.strip()
        if normalized == "":
            raise ValueError("value must not be blank")
        return normalized

    model_config = ConfigDict(extra="forbid")


class PartyLifecycleCommitResponse(BaseModel):
    party: PartyResponse
    operation: PartyLifecycleOperation
    before_state: PartyLifecycleState
    after_state: PartyLifecycleState
    impact: PartyLifecycleImpact
    committed_at: datetime
    idempotent: bool = False


class PartyReviewRejectRequest(BaseModel):
    """Party review reject payload."""

    reason: str = Field(..., min_length=1, max_length=500, description="驳回原因")


class PartyImportRequest(BaseModel):
    """Batch import payload for initializing party master data."""

    items: list[PartyCreate] = Field(..., min_length=1, description="待导入主体列表")


class PartyImportResultItem(BaseModel):
    """Single import row result."""

    index: int = Field(..., ge=0)
    status: str = Field(..., description="created/error")
    party_id: str | None = None
    message: str | None = None


class PartyImportResponse(BaseModel):
    """Batch import result summary."""

    created_count: int = Field(..., ge=0)
    error_count: int = Field(..., ge=0)
    items: list[PartyImportResultItem]


class PartyReviewLogResponse(BaseModel):
    """Party review/change log response."""

    id: str
    party_id: str
    action: str
    from_status: str
    to_status: str
    operator: str | None = None
    reason: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PartyContactCreate(BaseModel):
    """Create contact payload."""

    party_id: str | None = Field(None, description="主体ID")
    contact_name: str = Field(
        ..., min_length=1, max_length=100, description="联系人姓名"
    )
    contact_phone: str | None = Field(None, max_length=50, description="联系电话")
    contact_email: str | None = Field(None, max_length=255, description="联系邮箱")
    position: str | None = Field(None, max_length=100, description="职位")
    is_primary: bool = Field(default=False, description="是否主联系人")
    notes: str | None = Field(None, description="备注")


class PartyContactUpdate(BaseModel):
    """Update contact payload."""

    contact_name: str | None = Field(
        None, min_length=1, max_length=100, description="联系人姓名"
    )
    contact_phone: str | None = Field(None, max_length=50, description="联系电话")
    contact_email: str | None = Field(None, max_length=255, description="联系邮箱")
    position: str | None = Field(None, max_length=100, description="职位")
    is_primary: bool | None = Field(None, description="是否主联系人")
    notes: str | None = Field(None, description="备注")


class PartyContactResponse(BaseModel):
    """Contact response."""

    id: str
    party_id: str
    contact_name: str
    contact_phone: str | None
    contact_email: str | None
    position: str | None
    is_primary: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomerRiskTagResponse(BaseModel):
    """Customer risk tag item with source metadata."""

    tag: str = Field(..., min_length=1, description="风险标签")
    source: Literal["manual", "rule"] = Field(..., description="标签来源")
    updated_at: datetime | None = Field(None, description="标签最近更新时间")


class CustomerContractSummaryResponse(BaseModel):
    """Historical customer contract summary."""

    contract_id: str = Field(..., description="合同ID")
    contract_number: str = Field(..., description="合同编号")
    group_code: str = Field(..., description="合同组编号")
    revenue_mode: str = Field(..., description="经营模式")
    group_relation_type: str = Field(..., description="组内合同角色")
    status: str = Field(..., description="合同状态")
    effective_from: datetime | None = Field(None, description="生效开始")
    effective_to: datetime | None = Field(None, description="生效结束")


class CustomerProfileResponse(BaseModel):
    """Data-scope customer profile view."""

    customer_party_id: str = Field(..., description="客户主体ID")
    customer_name: str = Field(..., description="客户名称")
    customer_type: str = Field(..., description="客户类型 internal/external")
    subject_nature: str = Field(..., description="主体性质 enterprise/individual")
    binding_type: str = Field(..., description="数据范围绑定类型 owner/manager/all")
    contract_role: str = Field(..., description="客户合同角色")
    contact_name: str | None = Field(None, description="联系人")
    contact_phone: str | None = Field(None, description="联系电话")
    identifier_type: str | None = Field(None, description="统一标识类型")
    identifier_display: str | None = Field(None, description="脱敏后的正式标识")
    address: str | None = Field(None, description="地址")
    status: str = Field(..., description="客户状态")
    historical_contract_count: int = Field(..., ge=0, description="历史签约数")
    risk_tags: list[str] = Field(default_factory=list, description="风险标签汇总")
    risk_tag_items: list[CustomerRiskTagResponse] = Field(
        default_factory=list,
        description="带来源信息的风险标签",
    )
    payment_term_preference: str | None = Field(None, description="账期偏好")
    contracts: list[CustomerContractSummaryResponse] = Field(
        default_factory=list,
        description="历史合同列表",
    )


class UserPartyBindingCreate(BaseModel):
    """Create user-party binding payload."""

    user_id: str = Field(..., description="用户ID")
    party_id: str = Field(..., description="主体ID")
    relation_type: RelationType = Field(..., description="关系类型")
    valid_from: datetime | None = Field(None, description="生效时间")
    valid_to: datetime | None = Field(None, description="失效时间")


class UserPartyBindingUpsert(BaseModel):
    """Create/update user-party binding payload without user_id."""

    party_id: str = Field(..., description="主体ID")
    relation_type: RelationType = Field(..., description="关系类型")
    valid_from: datetime | None = Field(None, description="生效时间")
    valid_to: datetime | None = Field(None, description="失效时间")


class UserPartyBindingUpdate(BaseModel):
    """Update user-party binding payload."""

    party_id: str | None = Field(None, description="主体ID")
    relation_type: RelationType | None = Field(None, description="关系类型")
    valid_from: datetime | None = Field(None, description="生效时间")
    valid_to: datetime | None = Field(None, description="失效时间")


class UserPartyBindingResponse(BaseModel):
    """User-party binding response."""

    id: str
    user_id: str
    party_id: str
    relation_type: RelationType
    valid_from: datetime
    valid_to: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


__all__ = [
    "PartyCreate",
    "PartyUpdate",
    "PartyResponse",
    "PartyImportRequest",
    "PartyImportResponse",
    "PartyImportResultItem",
    "PartyReviewLogResponse",
    "PartyReviewRejectRequest",
    "PartyContactCreate",
    "PartyContactUpdate",
    "PartyContactResponse",
    "CustomerRiskTagResponse",
    "CustomerContractSummaryResponse",
    "CustomerProfileResponse",
    "UserPartyBindingCreate",
    "UserPartyBindingUpsert",
    "UserPartyBindingUpdate",
    "UserPartyBindingResponse",
]
