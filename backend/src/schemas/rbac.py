"""
RBAC相关的Pydantic模式
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict


# Permission相关模式
class PermissionBase(BaseModel):
    name: str = Field(..., description="权限名称")
    display_name: str = Field(..., description="显示名称")
    description: Optional[str] = Field(None, description="权限描述")
    resource: str = Field(..., description="资源类型")
    action: str = Field(..., description="操作类型")
    max_level: Optional[int] = Field(None, description="最大级别")
    conditions: Optional[Dict[str, Any]] = Field(None, description="权限条件")


class PermissionCreate(PermissionBase):
    is_system_permission: bool = Field(False, description="是否系统权限")
    requires_approval: bool = Field(False, description="是否需要审批")


class PermissionUpdate(BaseModel):
    display_name: Optional[str] = Field(None, description="显示名称")
    description: Optional[str] = Field(None, description="权限描述")
    max_level: Optional[int] = Field(None, description="最大级别")
    conditions: Optional[Dict[str, Any]] = Field(None, description="权限条件")
    requires_approval: bool = Field(False, description="是否需要审批")
    is_active: bool = Field(True, description="是否激活")


class PermissionResponse(PermissionBase):
    id: str
    is_system_permission: bool
    requires_approval: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]

    model_config = ConfigDict(
        from_attributes = True
    )
# Role相关模式
class RoleBase(BaseModel):
    name: str = Field(..., description="角色名称")
    display_name: str = Field(..., description="显示名称")
    description: Optional[str] = Field(None, description="角色描述")
    level: int = Field(1, description="角色级别")
    category: Optional[str] = Field(None, description="角色类别")
    scope: str = Field("global", description="权限范围")
    scope_id: Optional[str] = Field(None, description="范围ID")


class RoleCreate(RoleBase):
    is_system_role: bool = Field(False, description="是否系统角色")
    organization_id: Optional[str] = Field(None, description="所属组织ID")
    permission_ids: Optional[List[str]] = Field([], description="权限ID列表")


class RoleUpdate(BaseModel):
    display_name: Optional[str] = Field(None, description="显示名称")
    description: Optional[str] = Field(None, description="角色描述")
    level: Optional[int] = Field(None, description="角色级别")
    category: Optional[str] = Field(None, description="角色类别")
    scope: Optional[str] = Field(None, description="权限范围")
    scope_id: Optional[str] = Field(None, description="范围ID")
    is_active: bool = Field(True, description="是否激活")
    permission_ids: Optional[List[str]] = Field(None, description="权限ID列表")


class RoleResponse(RoleBase):
    id: str
    is_system_role: bool
    is_active: bool
    organization_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]
    updated_by: Optional[str]
    permissions: List[PermissionResponse] = []

    model_config = ConfigDict(
        from_attributes = True
    )
# UserRoleAssignment相关模式
class UserRoleAssignmentCreate(BaseModel):
    user_id: str = Field(..., description="用户ID")
    role_id: str = Field(..., description="角色ID")
    expires_at: Optional[datetime] = Field(None, description="过期时间")
    reason: Optional[str] = Field(None, description="分配原因")
    notes: Optional[str] = Field(None, description="备注")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")


class UserRoleAssignmentUpdate(BaseModel):
    expires_at: Optional[datetime] = Field(None, description="过期时间")
    is_active: bool = Field(True, description="是否激活")
    reason: Optional[str] = Field(None, description="分配原因")
    notes: Optional[str] = Field(None, description="备注")


class UserRoleAssignmentResponse(BaseModel):
    id: str
    user_id: str
    role_id: str
    assigned_by: Optional[str]
    assigned_at: datetime
    expires_at: Optional[datetime]
    is_active: bool
    reason: Optional[str]
    notes: Optional[str]
    context: Optional[Dict[str, Any]]
    user: Optional[Dict[str, Any]]
    role: Optional[RoleResponse]

    model_config = ConfigDict(
        from_attributes = True
    )
# ResourcePermission相关模式
class ResourcePermissionCreate(BaseModel):
    resource_type: str = Field(..., description="资源类型")
    resource_id: str = Field(..., description="资源ID")
    user_id: Optional[str] = Field(None, description="用户ID")
    role_id: Optional[str] = Field(None, description="角色ID")
    permission_id: Optional[str] = Field(None, description="权限ID")
    permission_level: str = Field("read", description="权限级别")
    expires_at: Optional[datetime] = Field(None, description="过期时间")
    reason: Optional[str] = Field(None, description="授权原因")
    conditions: Optional[Dict[str, Any]] = Field(None, description="权限条件")


class ResourcePermissionUpdate(BaseModel):
    permission_level: str = Field("read", description="权限级别")
    expires_at: Optional[datetime] = Field(None, description="过期时间")
    is_active: bool = Field(True, description="是否激活")
    conditions: Optional[Dict[str, Any]] = Field(None, description="权限条件")


class ResourcePermissionResponse(BaseModel):
    id: str
    resource_type: str
    resource_id: str
    user_id: Optional[str]
    role_id: Optional[str]
    permission_id: Optional[str]
    permission_level: str
    granted_at: datetime
    expires_at: Optional[datetime]
    is_active: bool
    granted_by: Optional[str]
    reason: Optional[str]
    conditions: Optional[Dict[str, Any]]

    model_config = ConfigDict(
        from_attributes = True
    )
# 权限检查相关模式
class PermissionCheckRequest(BaseModel):
    resource: str = Field(..., description="资源类型")
    action: str = Field(..., description="操作类型")
    resource_id: Optional[str] = Field(None, description="资源ID")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")


class PermissionCheckResponse(BaseModel):
    has_permission: bool = Field(..., description="是否有权限")
    granted_by: List[str] = Field(default=[], description="授权来源(角色/权限)")
    conditions: Optional[Dict[str, Any]] = Field(None, description="权限条件")
    reason: Optional[str] = Field(None, description="拒绝原因")


# 批量权限检查
class BatchPermissionCheckRequest(BaseModel):
    checks: List[PermissionCheckRequest] = Field(..., description="权限检查列表")


class BatchPermissionCheckResponse(BaseModel):
    results: List[PermissionCheckResponse] = Field(..., description="检查结果列表")


# 查询参数模式
class RoleQueryParams(BaseModel):
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")
    search: Optional[str] = Field(None, description="搜索关键词")
    category: Optional[str] = Field(None, description="角色类别")
    is_active: Optional[bool] = Field(None, description="是否激活")
    organization_id: Optional[str] = Field(None, description="组织ID")
    scope: Optional[str] = Field(None, description="权限范围")


class PermissionQueryParams(BaseModel):
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")
    search: Optional[str] = Field(None, description="搜索关键词")
    resource: Optional[str] = Field(None, description="资源类型")
    action: Optional[str] = Field(None, description="操作类型")
    is_system_permission: Optional[bool] = Field(None, description="是否系统权限")


class UserRoleAssignmentQueryParams(BaseModel):
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")
    user_id: Optional[str] = Field(None, description="用户ID")
    role_id: Optional[str] = Field(None, description="角色ID")
    is_active: Optional[bool] = Field(None, description="是否激活")


# 统计信息模式
class PermissionStatisticsResponse(BaseModel):
    total_permissions: int
    total_roles: int
    total_assignments: int
    active_users: int
    roles_by_category: Dict[str, int]
    permissions_by_resource: Dict[str, int]


# 用户权限汇总模式
class UserPermissionSummary(BaseModel):
    user_id: str
    username: str
    roles: List[RoleResponse]
    permissions: List[PermissionResponse]
    resource_permissions: List[ResourcePermissionResponse]
    effective_permissions: Dict[str, List[str]]  # resource -> actions