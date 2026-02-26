from typing import Any

"""
RBAC相关的Pydantic模式
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# Permission相关模式
class PermissionBase(BaseModel):
    name: str = Field(..., description="权限名称")
    display_name: str = Field(..., description="显示名称")
    description: str | None = Field(None, description="权限描述")
    resource: str = Field(..., description="资源类型")
    action: str = Field(..., description="操作类型")
    max_level: int | None = Field(None, description="最大级别")
    conditions: dict[str, Any] | None = Field(None, description="权限条件")


class PermissionCreate(PermissionBase):
    is_system_permission: bool = Field(False, description="是否系统权限")
    requires_approval: bool = Field(False, description="是否需要审批")


class PermissionUpdate(BaseModel):
    display_name: str | None = Field(None, description="显示名称")
    description: str | None = Field(None, description="权限描述")
    max_level: int | None = Field(None, description="最大级别")
    conditions: dict[str, Any] | None = Field(None, description="权限条件")
    requires_approval: bool = Field(False, description="是否需要审批")
    is_active: bool = Field(True, description="是否激活")


class PermissionResponse(PermissionBase):
    id: str
    is_system_permission: bool
    requires_approval: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: str | None

    model_config = ConfigDict(from_attributes=True)


# Role相关模式
class RoleBase(BaseModel):
    name: str = Field(..., description="角色名称")
    display_name: str = Field(..., description="显示名称")
    description: str | None = Field(None, description="角色描述")
    level: int = Field(1, description="角色级别")
    category: str | None = Field(None, description="角色类别")
    scope: str = Field("global", description="权限范围")
    scope_id: str | None = Field(None, description="范围ID")


class RoleCreate(RoleBase):
    is_system_role: bool = Field(False, description="是否系统角色")
    organization_id: str | None = Field(None, description="所属组织ID（DEPRECATED）")
    party_id: str | None = Field(None, description="所属主体ID")
    permission_ids: list[str] = Field(default_factory=list, description="权限ID列表")


class RoleUpdate(BaseModel):
    display_name: str | None = Field(None, description="显示名称")
    description: str | None = Field(None, description="角色描述")
    level: int | None = Field(None, description="角色级别")
    category: str | None = Field(None, description="角色类别")
    scope: str | None = Field(None, description="权限范围")
    scope_id: str | None = Field(None, description="范围ID")
    party_id: str | None = Field(None, description="所属主体ID")
    is_active: bool = Field(True, description="是否激活")
    permission_ids: list[str] | None = Field(None, description="权限ID列表")


class RoleResponse(RoleBase):
    id: str
    is_system_role: bool
    is_active: bool
    organization_id: str | None
    party_id: str | None
    created_at: datetime
    updated_at: datetime
    created_by: str | None
    updated_by: str | None
    permissions: list[PermissionResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# UserRoleAssignment相关模式
class UserRoleAssignmentCreate(BaseModel):
    user_id: str = Field(..., description="用户ID")
    role_id: str = Field(..., description="角色ID")
    expires_at: datetime | None = Field(None, description="过期时间")
    reason: str | None = Field(None, description="分配原因")
    notes: str | None = Field(None, description="备注")
    context: dict[str, Any] | None = Field(None, description="上下文信息")


class UserRoleAssignmentUpdate(BaseModel):
    expires_at: datetime | None = Field(None, description="过期时间")
    is_active: bool = Field(True, description="是否激活")
    reason: str | None = Field(None, description="分配原因")
    notes: str | None = Field(None, description="备注")


class UserRoleAssignmentResponse(BaseModel):
    id: str
    user_id: str
    role_id: str
    assigned_by: str | None
    assigned_at: datetime
    expires_at: datetime | None
    is_active: bool
    reason: str | None
    notes: str | None
    context: dict[str, Any] | None
    user: dict[str, Any] | None
    role: RoleResponse | None

    model_config = ConfigDict(from_attributes=True)


# ResourcePermission相关模式
class ResourcePermissionCreate(BaseModel):
    resource_type: str = Field(..., description="资源类型")
    resource_id: str = Field(..., description="资源ID")
    user_id: str | None = Field(None, description="用户ID")
    role_id: str | None = Field(None, description="角色ID")
    permission_id: str | None = Field(None, description="权限ID")
    permission_level: str = Field("read", description="权限级别")
    expires_at: datetime | None = Field(None, description="过期时间")
    reason: str | None = Field(None, description="授权原因")
    conditions: dict[str, Any] | None = Field(None, description="权限条件")


class ResourcePermissionUpdate(BaseModel):
    permission_level: str = Field("read", description="权限级别")
    expires_at: datetime | None = Field(None, description="过期时间")
    is_active: bool = Field(True, description="是否激活")
    conditions: dict[str, Any] | None = Field(None, description="权限条件")


class ResourcePermissionResponse(BaseModel):
    id: str
    resource_type: str
    resource_id: str
    user_id: str | None
    role_id: str | None
    permission_id: str | None
    permission_level: str
    granted_at: datetime
    expires_at: datetime | None
    is_active: bool
    granted_by: str | None
    reason: str | None
    conditions: dict[str, Any] | None

    model_config = ConfigDict(from_attributes=True)


class PermissionGrantCreate(BaseModel):
    user_id: str = Field(..., description="用户ID")
    permission_id: str = Field(..., description="权限ID")
    grant_type: str = Field("direct", description="授权类型")
    effect: str = Field("allow", description="效果 allow/deny")
    scope: str = Field("global", description="作用域类型")
    scope_id: str | None = Field(None, description="作用域ID")
    conditions: dict[str, Any] | None = Field(None, description="授权条件")
    starts_at: datetime | None = Field(None, description="生效时间")
    expires_at: datetime | None = Field(None, description="过期时间")
    priority: int = Field(100, description="优先级")
    source_type: str | None = Field(None, description="来源类型")
    source_id: str | None = Field(None, description="来源ID")
    reason: str | None = Field(None, description="授权原因")


class PermissionGrantUpdate(BaseModel):
    effect: str | None = Field(None, description="效果 allow/deny")
    scope: str | None = Field(None, description="作用域类型")
    scope_id: str | None = Field(None, description="作用域ID")
    conditions: dict[str, Any] | None = Field(None, description="授权条件")
    starts_at: datetime | None = Field(None, description="生效时间")
    expires_at: datetime | None = Field(None, description="过期时间")
    priority: int | None = Field(None, description="优先级")
    is_active: bool | None = Field(None, description="是否激活")
    reason: str | None = Field(None, description="授权原因")


class PermissionGrantResponse(BaseModel):
    id: str
    user_id: str
    permission_id: str
    grant_type: str
    effect: str
    scope: str
    scope_id: str | None
    conditions: dict[str, Any] | None
    starts_at: datetime | None
    expires_at: datetime | None
    priority: int
    is_active: bool
    source_type: str | None
    source_id: str | None
    granted_by: str | None
    reason: str | None
    created_at: datetime
    updated_at: datetime
    revoked_at: datetime | None
    revoked_by: str | None

    model_config = ConfigDict(from_attributes=True)


# 权限检查相关模式
class PermissionCheckRequest(BaseModel):
    resource: str = Field(..., description="资源类型")
    action: str = Field(..., description="操作类型")
    resource_id: str | None = Field(None, description="资源ID")
    context: dict[str, Any] | None = Field(None, description="上下文信息")


class PermissionCheckResponse(BaseModel):
    has_permission: bool = Field(..., description="是否有权限")
    granted_by: list[str] = Field(
        default_factory=list, description="授权来源(角色/权限)"
    )
    conditions: dict[str, Any] | None = Field(None, description="权限条件")
    reason: str | None = Field(None, description="拒绝原因")


# 批量权限检查
class BatchPermissionCheckRequest(BaseModel):
    checks: list[PermissionCheckRequest] = Field(..., description="权限检查列表")


class BatchPermissionCheckResponse(BaseModel):
    results: list[PermissionCheckResponse] = Field(..., description="检查结果列表")


# 查询参数模式
class RoleQueryParams(BaseModel):
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")
    search: str | None = Field(None, description="搜索关键词")
    category: str | None = Field(None, description="角色类别")
    is_active: bool | None = Field(None, description="是否激活")
    organization_id: str | None = Field(None, description="组织ID（DEPRECATED）")
    party_id: str | None = Field(None, description="主体ID")
    scope: str | None = Field(None, description="权限范围")


class PermissionQueryParams(BaseModel):
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")
    search: str | None = Field(None, description="搜索关键词")
    resource: str | None = Field(None, description="资源类型")
    action: str | None = Field(None, description="操作类型")
    is_system_permission: bool | None = Field(None, description="是否系统权限")


class UserRoleAssignmentQueryParams(BaseModel):
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")
    user_id: str | None = Field(None, description="用户ID")
    role_id: str | None = Field(None, description="角色ID")
    is_active: bool | None = Field(None, description="是否激活")


# 统计信息模式
class PermissionStatisticsResponse(BaseModel):
    total_permissions: int
    total_roles: int
    total_assignments: int
    active_users: int
    roles_by_category: dict[str, int]
    permissions_by_resource: dict[str, int]


# 用户权限汇总模式
class UserPermissionSummary(BaseModel):
    user_id: str
    username: str
    roles: list[RoleResponse]
    permissions: list[PermissionResponse]
    resource_permissions: list[ResourcePermissionResponse]
    effective_permissions: dict[str, list[str]]  # resource -> actions
