"""Pydantic schemas for Party-Role domain APIs."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ..models.party import PartyType
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


class PartyUpdate(BaseModel):
    """Party update payload."""

    party_type: PartyType | None = Field(None, description="主体类型")
    name: str | None = Field(None, min_length=1, max_length=200, description="主体名称")
    code: str | None = Field(None, min_length=1, max_length=100, description="主体编码")
    external_ref: str | None = Field(None, max_length=200, description="外部引用")
    status: str | None = Field(None, max_length=50, description="状态")
    metadata: dict[str, Any] | None = Field(
        default=None,
        validation_alias="metadata_json",
        description="扩展元数据",
    )


class PartyResponse(PartyBase):
    """Party response."""

    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


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
    contact_name: str = Field(..., min_length=1, max_length=100, description="联系人姓名")
    contact_phone: str | None = Field(None, max_length=50, description="联系电话")
    contact_email: str | None = Field(None, max_length=255, description="联系邮箱")
    position: str | None = Field(None, max_length=100, description="职位")
    is_primary: bool = Field(default=False, description="是否主联系人")
    notes: str | None = Field(None, description="备注")


class PartyContactUpdate(BaseModel):
    """Update contact payload."""

    contact_name: str | None = Field(None, min_length=1, max_length=100, description="联系人姓名")
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


class UserPartyBindingCreate(BaseModel):
    """Create user-party binding payload."""

    user_id: str = Field(..., description="用户ID")
    party_id: str = Field(..., description="主体ID")
    relation_type: RelationType = Field(..., description="关系类型")
    is_primary: bool = Field(default=False, description="是否主关系")
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
    "PartyHierarchyCreate",
    "PartyHierarchyResponse",
    "PartyContactCreate",
    "PartyContactUpdate",
    "PartyContactResponse",
    "UserPartyBindingCreate",
    "UserPartyBindingResponse",
]
