"""Pydantic schemas for Party-Role domain APIs."""

from datetime import datetime
from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from ..models.party import PartyReviewStatus, PartyType
from ..models.user_party_binding import RelationType


class PartyBase(BaseModel):
    """Shared Party fields."""

    party_type: PartyType = Field(..., description="主体类型")
    name: str = Field(..., min_length=1, max_length=200, description="主体名称")
    code: str = Field(..., min_length=1, max_length=100, description="主体编码")
    external_ref: str | None = Field(None, max_length=200, description="外部引用")
    status: str = Field(default="active", max_length=50, description="状态")
    metadata: dict[str, Any] | None = Field(
        default=None,
        validation_alias="metadata_json",
        description="扩展元数据",
    )


class PartyCreate(PartyBase):
    """Party create payload."""

    metadata: dict[str, Any] | None = Field(
        default=None,
        validation_alias=AliasChoices("metadata", "metadata_json"),
        description="扩展元数据",
    )


class PartyUpdate(BaseModel):
    """Party update payload."""

    party_type: PartyType | None = Field(None, description="主体类型")
    name: str | None = Field(None, min_length=1, max_length=200, description="主体名称")
    code: str | None = Field(None, min_length=1, max_length=100, description="主体编码")
    external_ref: str | None = Field(None, max_length=200, description="外部引用")
    status: str | None = Field(None, max_length=50, description="状态")
    metadata: dict[str, Any] | None = Field(
        default=None,
        validation_alias=AliasChoices("metadata", "metadata_json"),
        description="扩展元数据",
    )


class PartyResponse(PartyBase):
    """Party response."""

    id: str
    review_status: PartyReviewStatus | None = None
    review_by: str | None = None
    reviewed_at: datetime | None = None
    review_reason: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


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


class PartyHierarchyCreate(BaseModel):
    """Create hierarchy relation payload."""

    child_party_id: str = Field(..., description="子主体ID")


class PartyHierarchyResponse(BaseModel):
    """Hierarchy relation response."""

    id: str
    parent_party_id: str
    child_party_id: str
    created_at: datetime
    updated_at: datetime

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
    """Perspective-scoped customer profile view."""

    customer_party_id: str = Field(..., description="客户主体ID")
    customer_name: str = Field(..., description="客户名称")
    customer_type: str = Field(..., description="客户类型 internal/external")
    subject_nature: str = Field(..., description="主体性质 enterprise/individual")
    perspective_type: str = Field(..., description="当前视角 owner/manager")
    contract_role: str = Field(..., description="当前视角下的客户合同角色")
    contact_name: str | None = Field(None, description="联系人")
    contact_phone: str | None = Field(None, description="联系电话")
    identifier_type: str | None = Field(None, description="统一标识类型")
    unified_identifier: str | None = Field(None, description="统一标识")
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
    is_primary: bool = Field(default=False, description="是否主关系")
    valid_from: datetime | None = Field(None, description="生效时间")
    valid_to: datetime | None = Field(None, description="失效时间")


class UserPartyBindingUpsert(BaseModel):
    """Create/update user-party binding payload without user_id."""

    party_id: str = Field(..., description="主体ID")
    relation_type: RelationType = Field(..., description="关系类型")
    is_primary: bool = Field(default=False, description="是否主关系")
    valid_from: datetime | None = Field(None, description="生效时间")
    valid_to: datetime | None = Field(None, description="失效时间")


class UserPartyBindingUpdate(BaseModel):
    """Update user-party binding payload."""

    party_id: str | None = Field(None, description="主体ID")
    relation_type: RelationType | None = Field(None, description="关系类型")
    is_primary: bool | None = Field(None, description="是否主关系")
    valid_from: datetime | None = Field(None, description="生效时间")
    valid_to: datetime | None = Field(None, description="失效时间")


class UserPartyBindingResponse(BaseModel):
    """User-party binding response."""

    id: str
    user_id: str
    party_id: str
    relation_type: RelationType
    is_primary: bool
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
    "PartyHierarchyCreate",
    "PartyHierarchyResponse",
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
