"""
动态权限相关的 Pydantic schemas
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PermissionTypeEnum(str, Enum):
    """权限类型枚举"""

    ROLE_BASED = "role_based"
    USER_SPECIFIC = "user_specific"
    TEMPORARY = "temporary"
    CONDITIONAL = "conditional"
    TEMPLATE_BASED = "template_based"


class PermissionScopeEnum(str, Enum):
    """权限范围枚举"""

    GLOBAL = "global"
    ORGANIZATION = "organization"
    PROJECT = "project"
    ASSET = "asset"
    CUSTOM = "custom"


class RequestStatusEnum(str, Enum):
    """申请状态枚举"""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


# ==================== DynamicPermission ====================


class DynamicPermissionBase(BaseModel):
    """动态权限基础Schema"""

    permission_id: str = Field(..., description="权限ID")
    permission_type: PermissionTypeEnum = Field(..., description="权限类型")
    scope: PermissionScopeEnum = Field(..., description="权限范围")
    scope_id: str | None = Field(None, description="范围ID")
    conditions: dict[str, Any] | None = Field(None, description="权限条件")
    expires_at: datetime | None = Field(None, description="过期时间")


class DynamicPermissionCreate(DynamicPermissionBase):
    """创建动态权限Schema"""

    user_id: str = Field(..., description="用户ID")


class DynamicPermissionUpdate(BaseModel):
    """更新动态权限Schema"""

    conditions: dict[str, Any] | None = Field(None, description="权限条件")
    expires_at: datetime | None = Field(None, description="过期时间")
    is_active: bool | None = Field(None, description="是否激活")


class DynamicPermissionResponse(DynamicPermissionBase):
    """动态权限响应Schema"""

    id: str
    user_id: str
    assigned_by: str
    assigned_at: datetime
    revoked_by: str | None = None
    revoked_at: datetime | None = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


# ==================== TemporaryPermission ====================


class TemporaryPermissionBase(BaseModel):
    """临时权限基础Schema"""

    permission_id: str = Field(..., description="权限ID")
    scope: PermissionScopeEnum = Field(..., description="权限范围")
    scope_id: str | None = Field(None, description="范围ID")
    expires_at: datetime = Field(..., description="过期时间（必填）")


class TemporaryPermissionCreate(TemporaryPermissionBase):
    """创建临时权限Schema"""

    user_id: str = Field(..., description="用户ID")


class TemporaryPermissionResponse(TemporaryPermissionBase):
    """临时权限响应Schema"""

    id: str
    user_id: str
    assigned_by: str
    assigned_at: datetime
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


# ==================== ConditionalPermission ====================


class ConditionalPermissionBase(BaseModel):
    """条件权限基础Schema"""

    permission_id: str = Field(..., description="权限ID")
    scope: PermissionScopeEnum = Field(..., description="权限范围")
    scope_id: str | None = Field(None, description="范围ID")
    conditions: dict[str, Any] = Field(..., description="权限条件（必填）")


class ConditionalPermissionCreate(ConditionalPermissionBase):
    """创建条件权限Schema"""

    user_id: str = Field(..., description="用户ID")


class ConditionalPermissionResponse(ConditionalPermissionBase):
    """条件权限响应Schema"""

    id: str
    user_id: str
    assigned_by: str
    assigned_at: datetime
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


# ==================== PermissionTemplate ====================


class PermissionTemplateBase(BaseModel):
    """权限模板基础Schema"""

    name: str = Field(..., description="模板名称")
    description: str | None = Field(None, description="模板描述")
    permission_ids: list[str] = Field(..., description="权限ID列表")
    scope: PermissionScopeEnum = Field(..., description="默认权限范围")
    conditions: dict[str, Any] | None = Field(None, description="默认权限条件")


class PermissionTemplateCreate(PermissionTemplateBase):
    """创建权限模板Schema"""

    pass


class PermissionTemplateUpdate(BaseModel):
    """更新权限模板Schema"""

    name: str | None = Field(None, description="模板名称")
    description: str | None = Field(None, description="模板描述")
    permission_ids: list[str] | None = Field(None, description="权限ID列表")
    scope: PermissionScopeEnum | None = Field(None, description="默认权限范围")
    conditions: dict[str, Any] | None = Field(None, description="默认权限条件")
    is_active: bool | None = Field(None, description="是否激活")


class PermissionTemplateResponse(PermissionTemplateBase):
    """权限模板响应Schema"""

    id: str
    created_by: str
    created_at: datetime
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


# ==================== PermissionRequest ====================


class PermissionRequestBase(BaseModel):
    """权限申请基础Schema"""

    permission_ids: list[str] = Field(..., description="申请的权限ID列表")
    scope: PermissionScopeEnum = Field(..., description="申请范围")
    scope_id: str | None = Field(None, description="范围ID")
    reason: str = Field(..., description="申请理由")
    requested_duration_hours: int | None = Field(None, description="申请期限（小时）")
    requested_conditions: dict[str, Any] | None = Field(None, description="申请条件")


class PermissionRequestCreate(PermissionRequestBase):
    """创建权限申请Schema"""

    pass


class PermissionRequestUpdate(BaseModel):
    """更新权限申请Schema（审批）"""

    status: RequestStatusEnum = Field(..., description="审批状态")
    approval_comment: str | None = Field(None, description="审批意见")


class PermissionRequestResponse(PermissionRequestBase):
    """权限申请响应Schema"""

    id: str
    user_id: str
    status: RequestStatusEnum
    approved_by: str | None = None
    approved_at: datetime | None = None
    approval_comment: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==================== PermissionDelegation ====================


class PermissionDelegationBase(BaseModel):
    """权限委托基础Schema"""

    delegatee_id: str = Field(..., description="被委托人ID")
    permission_ids: list[str] = Field(..., description="委托的权限ID列表")
    scope: PermissionScopeEnum = Field(..., description="委托范围")
    scope_id: str | None = Field(None, description="范围ID")
    starts_at: datetime | None = Field(None, description="委托开始时间")
    ends_at: datetime = Field(..., description="委托结束时间")
    conditions: dict[str, Any] | None = Field(None, description="委托条件")
    reason: str | None = Field(None, description="委托原因")


class PermissionDelegationCreate(PermissionDelegationBase):
    """创建权限委托Schema"""

    pass


class PermissionDelegationResponse(PermissionDelegationBase):
    """权限委托响应Schema"""

    id: str
    delegator_id: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==================== DynamicPermissionAudit ====================


class DynamicPermissionAuditResponse(BaseModel):
    """动态权限审计日志响应Schema"""

    id: str
    user_id: str
    permission_id: str
    action: str = Field(
        ...,
        description="操作类型: ASSIGN, REVOKE, ASSIGN_TEMPORARY, ASSIGN_CONDITIONAL",
    )
    permission_type: str
    scope: str
    scope_id: str | None = None
    assigned_by: str
    reason: str | None = None
    conditions: dict[str, Any] | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==================== 列表响应 ====================


class DynamicPermissionListResponse(BaseModel):
    """动态权限列表响应"""

    items: list[DynamicPermissionResponse]
    total: int
    page: int
    page_size: int
    pages: int


class TemporaryPermissionListResponse(BaseModel):
    """临时权限列表响应"""

    items: list[TemporaryPermissionResponse]
    total: int
    page: int
    page_size: int
    pages: int


class PermissionRequestListResponse(BaseModel):
    """权限申请列表响应"""

    items: list[PermissionRequestResponse]
    total: int
    page: int
    page_size: int
    pages: int


class PermissionDelegationListResponse(BaseModel):
    """权限委托列表响应"""

    items: list[PermissionDelegationResponse]
    total: int
    page: int
    page_size: int
    pages: int
