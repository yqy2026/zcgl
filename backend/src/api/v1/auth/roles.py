"""
角色管理API路由
支持角色CRUD、权限分配、用户关联等完整功能
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.exception_handler import (
    BaseBusinessError,
    bad_request,
    internal_error,
    not_found,
)
from ....core.response_handler import APIResponse, PaginatedData, ResponseHandler
from ....crud.rbac import permission_crud, role_crud
from ....database import get_async_db
from ....middleware.auth import get_current_active_user, require_admin
from ....models.auth import User
from ....schemas.rbac import (
    PermissionResponse,
    RoleCreate,
    RoleResponse,
    RoleUpdate,
)
from ....services.rbac import rbac_service

router = APIRouter(tags=["角色管理"])

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
    organization_id: str | None = None
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
    organization_id: str | None = Query(None, description="组织ID"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> JSONResponse:
    """
    获取角色列表，支持分页和筛选

    - **page**: 页码，从1开始
    - **limit**: 每页数量，最多100
    - **search**: 按名称、显示名称或描述搜索
    - **category**: 按角色类别筛选
    - **is_active**: 按激活状态筛选
    - **organization_id**: 按组织筛选
    """

    try:
        skip = (page - 1) * page_size

        roles, total = await role_crud.get_multi_with_filters(
            db=db,
            skip=skip,
            limit=page_size,
            search=search,
            category=category,
            is_active=is_active,
            organization_id=organization_id,
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
) -> RoleDetailResponse:
    """
    创建新角色（仅管理员）

    - **name**: 角色名称（必填，唯一）
    - **display_name**: 显示名称（必填）
    - **description**: 描述（可选）
    - **level**: 角色级别（可选，默认1）
    """

    try:
        new_role = await rbac_service.create_role(
            db=db,
            obj_in=role_data,
            created_by=str(current_user.id),
        )

        return RoleDetailResponse.model_validate(new_role)
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise bad_request(str(e))


@router.get("/{role_id}", response_model=RoleDetailResponse, summary="获取角色详情")
async def get_role(
    role_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> RoleDetailResponse:
    """获取角色详情及其关联的权限和用户"""
    try:
        role = await role_crud.get(db, id=role_id)

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
) -> RoleDetailResponse:
    """
    更新角色信息（仅管理员）

    - 系统角色无法修改
    - 只能修改非系统内置的角色
    """

    try:
        updated_role = await rbac_service.update_role(
            db=db,
            role_id=role_id,
            obj_in=role_data,
            updated_by=str(current_user.id),
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
) -> None:
    """
    删除角色（仅管理员）

    - 系统角色无法删除
    - 如果角色正在被用户使用，无法删除
    """

    try:
        success = await rbac_service.delete_role(
            db=db, role_id=role_id, deleted_by=str(current_user.id)
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
) -> dict[str, Any]:
    """获取系统中所有可用权限，按资源分组"""
    try:
        permissions: list[Any] = await permission_crud.get_multi(
            db, skip=0, limit=10000
        )

        grouped: dict[str, list[PermissionResponse]] = {}
        for perm in permissions:
            resource = perm.resource
            if resource not in grouped:
                grouped[resource] = []
            grouped[resource].append(PermissionResponse.model_validate(perm))

        return {
            "success": True,
            "data": grouped,
            "total": len(permissions),
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
) -> dict[str, Any]:
    """
    为角色分配权限

    - 替换角色的所有权限为新的权限列表
    """

    try:
        await rbac_service.update_role_permissions(
            db=db,
            role_id=role_id,
            permission_ids=request.permission_ids,
            updated_by=str(current_user.id),
        )

        role = await role_crud.get(db, id=role_id)

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
) -> JSONResponse:
    """获取拥有某个角色的所有用户"""
    try:
        role = await role_crud.get(db, id=role_id)

        if not role:
            raise not_found("角色不存在", resource_type="role", resource_id=role_id)

        from ....crud.auth import UserCRUD

        user_crud = UserCRUD()
        skip = (page - 1) * page_size
        users, total = await user_crud.get_users_by_role(
            db, role_id, skip, page_size
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
) -> dict[str, Any]:
    """获取角色相关的统计数据"""
    try:
        by_category = await role_crud.count_by_category(db)
        counts = await role_crud.count_by_flags(db)

        return {
            "success": True,
            "data": {
                "total_roles": counts["total"],
                "active_roles": counts["active"],
                "system_roles": counts["system"],
                "custom_roles": counts["custom"],
                "by_category": by_category,
            },
        }
    except Exception as e:
        raise internal_error(str(e))
