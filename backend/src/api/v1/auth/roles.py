"""
角色管理API路由
支持角色CRUD、权限分配、用户关联等完整功能
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.exception_handler import (
    BaseBusinessError,
    bad_request,
    forbidden,
    internal_error,
    not_found,
)
from ....core.response_handler import APIResponse, PaginatedData, ResponseHandler
from ....database import get_async_db
from ....middleware.auth import (
    AuthzContext,
    get_current_active_user,
    require_admin,
    require_authz,
)
from ....models.auth import User
from ....schemas.rbac import (
    PermissionCheckRequest,
    PermissionCheckResponse,
    PermissionGrantCreate,  # DEPRECATED
    PermissionGrantResponse,  # DEPRECATED
    PermissionGrantUpdate,  # DEPRECATED
    PermissionResponse,
    RoleCreate,
    RoleResponse,
    RoleUpdate,
    UserPermissionSummary,
    UserRoleAssignmentCreate,
    UserRoleAssignmentResponse,
)
from ....services import RBACService
from ....utils.str import normalize_optional_str

router = APIRouter(tags=["角色管理"])
_ROLE_CREATE_UNSCOPED_PARTY_ID = "__unscoped__:role:create"


def _build_party_scope_context(
    *,
    scoped_party_id: str,
    organization_id: str | None = None,
) -> dict[str, str]:
    context: dict[str, str] = {
        "party_id": scoped_party_id,
        "owner_party_id": scoped_party_id,
        "manager_party_id": scoped_party_id,
    }
    if organization_id is not None:
        context["organization_id"] = organization_id
    return context


async def _resolve_role_create_resource_context(request: Request) -> dict[str, str]:
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    if not isinstance(payload, dict):
        payload = {}

    party_id = normalize_optional_str(payload.get("party_id"))
    organization_id = normalize_optional_str(payload.get("organization_id"))
    scoped_party_id = party_id or organization_id or _ROLE_CREATE_UNSCOPED_PARTY_ID
    return _build_party_scope_context(
        scoped_party_id=scoped_party_id,
        organization_id=organization_id,
    )


async def _resolve_user_assignment_resource_id(request: Request) -> str | None:
    try:
        payload = await request.json()
    except Exception:
        return None

    if not isinstance(payload, dict):
        return None
    return normalize_optional_str(payload.get("user_id"))


# ==================== Schema定义 ====================


class RoleListResponse(BaseModel):
    """角色列表响应"""

    items: list[RoleResponse]
    total: int
    page: int
    page_size: int
    pages: int


class RoleDetailResponse(BaseModel):
    """角色详情响应"""

    id: str
    name: str
    display_name: str
    description: str | None = None
    level: int
    category: str | None = None
    is_system_role: bool
    is_active: bool
    party_id: str | None = None
    organization_id: str | None = None  # DEPRECATED alias
    scope: str
    permissions: list[PermissionResponse] = []
    user_count: int = 0
    created_at: datetime
    updated_at: datetime
    created_by: str | None = None
    updated_by: str | None = None

    model_config = ConfigDict(from_attributes=True)


class RolePermissionUpdateRequest(BaseModel):
    """更新角色权限请求"""

    permission_ids: list[str] = Field(..., description="权限ID列表")


class RoleUserListResponse(BaseModel):
    """角色用户列表响应"""

    users: list[dict[str, Any]]
    total: int


class UserPermissionCheckRequest(BaseModel):
    """用户权限检查请求"""

    user_id: str = Field(..., description="用户ID")
    resource: str = Field(..., description="资源类型")
    action: str = Field(..., description="操作类型")
    resource_id: str | None = Field(None, description="资源ID")
    context: dict[str, Any] | None = Field(None, description="上下文")


async def _require_user_read_or_self_authz(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> AuthzContext:
    target_user_id = str(request.path_params.get("user_id") or "").strip()
    current_user_id = str(getattr(current_user, "id", "")).strip()
    if target_user_id != "" and target_user_id == current_user_id:
        return AuthzContext(
            current_user=current_user,
            action="read",
            resource_type="user",
            resource_id=target_user_id,
            resource_context={},
            allowed=True,
            reason_code="self_access_bypass",
        )

    checker = require_authz(
        action="read",
        resource_type="user",
        resource_id="{user_id}",
    )
    return await checker(request=request, current_user=current_user, db=db)


# ==================== 角色CRUD端点 ====================


@router.get(
    "", response_model=APIResponse[PaginatedData[RoleResponse]], summary="获取角色列表"
)
async def get_roles(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: str | None = Query(None, description="搜索关键词"),
    category: str | None = Query(None, description="角色类别"),
    is_active: bool | None = Query(None, description="是否激活"),
    party_id: str | None = Query(None, description="主体ID"),
    organization_id: str | None = Query(None, description="组织ID（DEPRECATED）"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(action="read", resource_type="role")
    ),
) -> JSONResponse:
    """
    获取角色列表，支持分页和筛选

    - **page**: 页码，从1开始
    - **limit**: 每页数量，最多100
    - **search**: 按名称、显示名称或描述搜索
    - **category**: 按角色类别筛选
    - **is_active**: 按激活状态筛选
    - **party_id**: 按主体筛选
    - **organization_id**: 按组织筛选（DEPRECATED）
    """

    try:
        skip = (page - 1) * page_size
        rbac_service = RBACService(db)
        roles, total = await rbac_service.get_roles(
            skip=skip,
            limit=page_size,
            search=search,
            category=category,
            is_active=is_active,
            party_id=party_id,
            organization_id=organization_id,  # DEPRECATED alias
            current_user_id=str(current_user.id),
        )

        return ResponseHandler.paginated(
            data=[RoleResponse.model_validate(role) for role in roles],
            page=page,
            page_size=page_size,
            total=total,
            message="获取角色列表成功",
        )
    except Exception as e:
        raise internal_error(str(e))


@router.post(
    "",
    response_model=RoleDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建角色",
)
async def create_role(
    role_data: RoleCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="create",
            resource_type="role",
            resource_context=_resolve_role_create_resource_context,
        )
    ),
) -> RoleDetailResponse:
    """
    创建新角色（仅管理员）

    - **name**: 角色名称（必填，唯一）
    - **display_name**: 显示名称（必填）
    - **description**: 描述（可选）
    - **level**: 角色级别（可选，默认1）
    """

    try:
        rbac_service = RBACService(db)
        new_role = await rbac_service.create_role(
            role_data=role_data,
            created_by=str(current_user.id),
        )

        return RoleDetailResponse.model_validate(new_role)
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise bad_request(str(e))


@router.post(
    "/permission-check",
    response_model=PermissionCheckResponse,
    summary="统一权限检查",
)
async def check_user_permission(
    check_data: UserPermissionCheckRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin),
    _authz_ctx: AuthzContext = Depends(
        require_authz(action="read", resource_type="role")
    ),
) -> PermissionCheckResponse:
    """统一权限检查入口（管理员调试与审计使用）"""
    try:
        rbac_service = RBACService(db)
        request = PermissionCheckRequest(
            resource=check_data.resource,
            action=check_data.action,
            resource_id=check_data.resource_id,
            context=check_data.context,
        )
        return await rbac_service.check_permission(check_data.user_id, request)
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise bad_request(str(e))


@router.post(
    "/assignments",
    response_model=UserRoleAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="为用户分配角色",
)
async def assign_role_to_user(
    assignment_data: UserRoleAssignmentCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="update",
            resource_type="user",
            resource_id=_resolve_user_assignment_resource_id,
        )
    ),
) -> UserRoleAssignmentResponse:
    """创建用户-角色分配记录"""
    try:
        rbac_service = RBACService(db)
        assignment = await rbac_service.assign_role_to_user(
            assignment_data=assignment_data,
            assigned_by=str(current_user.id),
        )
        return UserRoleAssignmentResponse.model_validate(assignment)
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise bad_request(str(e))


@router.get(
    "/users/{user_id}/roles",
    response_model=list[RoleResponse],
    summary="获取用户角色列表",
)
async def get_user_roles(
    user_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(_require_user_read_or_self_authz),
) -> list[RoleResponse]:
    """获取指定用户的角色列表（本人或管理员）"""
    try:
        rbac_service = RBACService(db)
        if current_user.id != user_id and not await rbac_service.is_admin(
            current_user.id
        ):
            raise forbidden("无权查看该用户角色")

        roles = await rbac_service.get_user_roles(user_id)
        return [RoleResponse.model_validate(role) for role in roles]
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise bad_request(str(e))


@router.delete(
    "/users/{user_id}/roles/{role_id}",
    response_model=dict[str, Any],
    summary="撤销用户角色",
)
async def revoke_user_role(
    user_id: str,
    role_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin),
    _authz_ctx: AuthzContext = Depends(
        require_authz(action="delete", resource_type="user", resource_id="{user_id}")
    ),
) -> dict[str, Any]:
    """撤销用户角色分配"""
    try:
        rbac_service = RBACService(db)
        success = await rbac_service.revoke_role_from_user(
            user_id=user_id,
            role_id=role_id,
            revoked_by=str(current_user.id),
        )
        if not success:
            raise not_found(
                "用户角色分配不存在",
                resource_type="user_role_assignment",
                resource_id=f"{user_id}:{role_id}",
            )
        return {"success": True, "message": "角色撤销成功"}
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise bad_request(str(e))


@router.get(
    "/users/{user_id}/permissions/summary",
    response_model=UserPermissionSummary,
    summary="获取用户权限汇总",
)
async def get_user_permissions_summary(
    user_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(_require_user_read_or_self_authz),
) -> UserPermissionSummary:
    """获取用户权限汇总（本人或管理员）"""
    try:
        rbac_service = RBACService(db)
        if current_user.id != user_id and not await rbac_service.is_admin(
            current_user.id
        ):
            raise forbidden("无权查看该用户权限汇总")
        return await rbac_service.get_user_permissions_summary(user_id)
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise bad_request(str(e))


@router.post(
    "/permission-grants",
    response_model=PermissionGrantResponse,  # DEPRECATED
    status_code=status.HTTP_201_CREATED,
    summary="创建统一授权记录",
)
async def create_permission_grant(
    grant_data: PermissionGrantCreate,  # DEPRECATED
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="create",
            resource_type="role",
            resource_context=_resolve_role_create_resource_context,
        )
    ),
) -> PermissionGrantResponse:  # DEPRECATED
    """创建统一授权记录（静态RBAC之外的动态/临时授权都落在此表）"""
    try:
        rbac_service = RBACService(db)
        grant = await rbac_service.grant_permission_to_user(
            user_id=grant_data.user_id,
            permission_id=grant_data.permission_id,
            grant_type=grant_data.grant_type,
            granted_by=str(current_user.id),
            effect=grant_data.effect,
            scope=grant_data.scope,
            scope_id=grant_data.scope_id,
            conditions=grant_data.conditions,
            starts_at=grant_data.starts_at,
            expires_at=grant_data.expires_at,
            priority=grant_data.priority,
            source_type=grant_data.source_type,
            source_id=grant_data.source_id,
            reason=grant_data.reason,
        )
        return PermissionGrantResponse.model_validate(grant)  # DEPRECATED
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise bad_request(str(e))


@router.get(
    "/permission-grants",
    response_model=APIResponse[PaginatedData[PermissionGrantResponse]],  # DEPRECATED
    summary="分页获取统一授权记录",
)
async def get_permission_grants(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    user_id: str | None = Query(None, description="用户ID"),
    permission_id: str | None = Query(None, description="权限ID"),
    grant_type: str | None = Query(None, description="授权类型"),
    effect: str | None = Query(None, description="allow/deny"),
    scope: str | None = Query(None, description="作用域"),
    is_active: bool | None = Query(None, description="是否激活"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin),
    _authz_ctx: AuthzContext = Depends(
        require_authz(action="read", resource_type="role")
    ),
) -> JSONResponse:
    """分页查询统一授权记录"""
    try:
        rbac_service = RBACService(db)
        skip = (page - 1) * page_size
        grants, total = await rbac_service.list_permission_grants(
            skip=skip,
            limit=page_size,
            user_id=user_id,
            permission_id=permission_id,
            grant_type=grant_type,
            effect=effect,
            scope=scope,
            is_active=is_active,
        )

        return ResponseHandler.paginated(
            data=[
                PermissionGrantResponse.model_validate(grant) for grant in grants
            ],  # DEPRECATED
            page=page,
            page_size=page_size,
            total=total,
            message="获取统一授权列表成功",
        )
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(str(e))


@router.get(
    "/permission-grants/{grant_id}",
    response_model=PermissionGrantResponse,  # DEPRECATED
    summary="获取统一授权记录详情",
)
async def get_permission_grant(
    grant_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="role",
            resource_id="{grant_id}",
            deny_as_not_found=True,
        )
    ),
) -> PermissionGrantResponse:  # DEPRECATED
    """获取指定统一授权记录详情"""
    try:
        rbac_service = RBACService(db)
        grant = await rbac_service.get_permission_grant(grant_id)
        if not grant:
            raise not_found(
                "统一授权记录不存在",
                resource_type="permission_grant",
                resource_id=grant_id,
            )
        return PermissionGrantResponse.model_validate(grant)  # DEPRECATED
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(str(e))


@router.patch(
    "/permission-grants/{grant_id}",
    response_model=PermissionGrantResponse,  # DEPRECATED
    summary="更新统一授权记录",
)
async def update_permission_grant(
    grant_id: str,
    grant_data: PermissionGrantUpdate,  # DEPRECATED
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="update",
            resource_type="role",
            resource_id="{grant_id}",
        )
    ),
) -> PermissionGrantResponse:  # DEPRECATED
    """更新统一授权记录"""
    try:
        rbac_service = RBACService(db)
        grant = await rbac_service.update_permission_grant(
            grant_id=grant_id,
            grant_data=grant_data,
            updated_by=str(current_user.id),
        )
        return PermissionGrantResponse.model_validate(grant)  # DEPRECATED
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise bad_request(str(e))


@router.delete(
    "/permission-grants/{grant_id}",
    response_model=dict[str, Any],
    summary="撤销统一授权记录",
)
async def revoke_permission_grant(
    grant_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="delete",
            resource_type="role",
            resource_id="{grant_id}",
        )
    ),
) -> dict[str, Any]:
    """撤销统一授权记录"""
    try:
        rbac_service = RBACService(db)
        success = await rbac_service.revoke_permission_grant(
            grant_id=grant_id,
            revoked_by=str(current_user.id),
        )
        if not success:
            raise not_found(
                "统一授权记录不存在",
                resource_type="permission_grant",
                resource_id=grant_id,
            )
        return {"success": True, "message": "统一授权已撤销", "grant_id": grant_id}
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise bad_request(str(e))


@router.get("/{role_id}", response_model=RoleDetailResponse, summary="获取角色详情")
async def get_role(
    role_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="role",
            resource_id="{role_id}",
            deny_as_not_found=True,
        )
    ),
) -> RoleDetailResponse:
    """获取角色详情及其关联的权限和用户"""
    try:
        rbac_service = RBACService(db)
        role = await rbac_service.get_role(
            role_id,
            current_user_id=str(current_user.id),
        )

        if not role:
            raise not_found("角色不存在", resource_type="role", resource_id=role_id)

        return RoleDetailResponse.model_validate(role)
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(str(e))


@router.put("/{role_id}", response_model=RoleDetailResponse, summary="更新角色")
async def update_role(
    role_id: str,
    role_data: RoleUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin),
    _authz_ctx: AuthzContext = Depends(
        require_authz(action="update", resource_type="role", resource_id="{role_id}")
    ),
) -> RoleDetailResponse:
    """
    更新角色信息（仅管理员）

    - 系统角色无法修改
    - 只能修改非系统内置的角色
    """

    try:
        rbac_service = RBACService(db)
        updated_role = await rbac_service.update_role(
            role_id=role_id,
            role_data=role_data,
            updated_by=str(current_user.id),
            current_user_id=str(current_user.id),
        )

        return RoleDetailResponse.model_validate(updated_role)
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise bad_request(str(e))


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除角色")
async def delete_role(
    role_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin),
    _authz_ctx: AuthzContext = Depends(
        require_authz(action="delete", resource_type="role", resource_id="{role_id}")
    ),
) -> None:
    """
    删除角色（仅管理员）

    - 系统角色无法删除
    - 如果角色正在被用户使用，无法删除
    """

    try:
        rbac_service = RBACService(db)
        success = await rbac_service.delete_role(
            role_id=role_id,
            deleted_by=str(current_user.id),
            current_user_id=str(current_user.id),
        )

        if not success:
            raise not_found("角色不存在", resource_type="role", resource_id=role_id)
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise bad_request(str(e))

    # ==================== 权限管理端点 ====================

    return None


@router.get("/permissions/list", response_model=dict[str, Any], summary="获取所有权限")
async def get_all_permissions(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(action="read", resource_type="role")
    ),
) -> dict[str, Any]:
    """获取系统中所有可用权限，按资源分组"""
    try:
        rbac_service = RBACService(db)
        grouped_permissions, total = await rbac_service.get_all_permissions_grouped(
            limit=10000
        )
        grouped = {
            resource: [
                PermissionResponse.model_validate(permission)
                for permission in permissions
            ]
            for resource, permissions in grouped_permissions.items()
        }

        return {
            "success": True,
            "data": grouped,
            "total": total,
        }
    except Exception as e:
        raise internal_error(str(e))


@router.put(
    "/{role_id}/permissions", response_model=dict[str, Any], summary="设置角色权限"
)
async def set_role_permissions(
    role_id: str,
    request: RolePermissionUpdateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin),
    _authz_ctx: AuthzContext = Depends(
        require_authz(action="update", resource_type="role", resource_id="{role_id}")
    ),
) -> dict[str, Any]:
    """
    为角色分配权限

    - 替换角色的所有权限为新的权限列表
    """

    try:
        rbac_service = RBACService(db)
        await rbac_service.update_role_permissions(
            role_id=role_id,
            permission_ids=request.permission_ids,
            updated_by=str(current_user.id),
            current_user_id=str(current_user.id),
        )

        role = await rbac_service.get_role(
            role_id,
            current_user_id=str(current_user.id),
        )

        return {
            "success": True,
            "message": "权限更新成功",
            "data": {
                "role_id": role_id,
                "permission_count": len(role.permissions) if role else 0,
            },
        }
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise bad_request(str(e))

    # ==================== 角色用户关联端点 ====================


@router.get(
    "/{role_id}/users",
    response_model=APIResponse[PaginatedData[dict[str, Any]]],
    summary="获取角色的用户列表",
)
async def get_role_users(
    role_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(action="read", resource_type="role", resource_id="{role_id}")
    ),
) -> JSONResponse:
    """获取拥有某个角色的所有用户"""
    try:
        rbac_service = RBACService(db)
        skip = (page - 1) * page_size
        users, total = await rbac_service.get_role_users(
            role_id,
            skip=skip,
            limit=page_size,
            current_user_id=str(current_user.id),
        )

        return ResponseHandler.paginated(
            data=[
                {"id": u.id, "username": u.username, "email": u.email} for u in users
            ],
            page=page,
            page_size=page_size,
            total=total,
            message="获取角色用户列表成功",
        )
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(str(e))


# ==================== 统计端点 ====================


@router.get(
    "/statistics/summary", response_model=dict[str, Any], summary="获取角色统计信息"
)
async def get_role_statistics(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(action="read", resource_type="role")
    ),
) -> dict[str, Any]:
    """获取角色相关的统计数据"""
    try:
        rbac_service = RBACService(db)
        stats = await rbac_service.get_role_statistics()

        return {
            "success": True,
            "data": stats,
        }
    except Exception as e:
        raise internal_error(str(e))
