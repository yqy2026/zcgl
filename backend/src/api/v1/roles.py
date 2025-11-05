"""
角色管理API路由
支持角色CRUD、权限分配、用户关联等完整功能
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...crud.rbac import PermissionCRUD, RoleCRUD
from ...database import get_db
from ...middleware.auth import get_current_active_user, require_admin
from ...models.auth import User
from ...models.rbac import Role
from ...schemas.rbac import (
    PermissionResponse,
    RoleCreate,
    RoleResponse,
    RoleUpdate,
)

router = APIRouter(tags=["角色管理"])

# ==================== Schema定义 ====================


class RoleListResponse(BaseModel):
    """角色列表响应"""

    items: list[RoleResponse]
    total: int
    page: int
    limit: int
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


class RolePermissionUpdateRequest(BaseModel):
    """更新角色权限请求"""

    permission_ids: list[str] = Field(..., description="权限ID列表")


class RoleUserListResponse(BaseModel):
    """角色用户列表响应"""

    users: list[dict]
    total: int


# ==================== 角色CRUD端点 ====================


@router.get("", response_model=RoleListResponse, summary="获取角色列表")
async def get_roles(
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    search: str | None = Query(None, description="搜索关键词"),
    category: str | None = Query(None, description="角色类别"),
    is_active: bool | None = Query(None, description="是否激活"),
    organization_id: str | None = Query(None, description="组织ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
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
        role_crud = RoleCRUD()
        skip = (page - 1) * limit

        roles, total = role_crud.get_multi(
            db=db,
            skip=skip,
            limit=limit,
            search=search,
            category=category,
            is_active=is_active,
            organization_id=organization_id,
        )

        pages = (total + limit - 1) // limit

        return RoleListResponse(
            items=[RoleResponse.from_orm(role) for role in roles],
            total=total,
            page=page,
            limit=limit,
            pages=pages,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.post(
    "",
    response_model=RoleDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建角色",
)
async def create_role(
    role_data: RoleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    创建新角色（仅管理员）

    - **name**: 角色名称（必填，唯一）
    - **display_name**: 显示名称（必填）
    - **description**: 描述（可选）
    - **level**: 角色级别（可选，默认1）
    """
    try:
        role_crud = RoleCRUD()

        # 检查角色名称唯一性
        existing = role_crud.get_by_name(db, role_data.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"角色名称 '{role_data.name}' 已存在",
            )

        new_role = role_crud.create(
            db=db,
            obj_in=role_data,
            created_by=current_user.id,
        )

        return RoleDetailResponse.from_orm(new_role)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{role_id}", response_model=RoleDetailResponse, summary="获取角色详情")
async def get_role(
    role_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取角色详情及其关联的权限和用户"""
    try:
        role_crud = RoleCRUD()
        role = role_crud.get(db, role_id)

        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="角色不存在"
            )

        return RoleDetailResponse.from_orm(role)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.put("/{role_id}", response_model=RoleDetailResponse, summary="更新角色")
async def update_role(
    role_id: str,
    role_data: RoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    更新角色信息（仅管理员）

    - 系统角色无法修改
    - 只能修改非系统内置的角色
    """
    try:
        role_crud = RoleCRUD()
        role = role_crud.get(db, role_id)

        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="角色不存在"
            )

        if role.is_system_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="系统内置角色无法修改"
            )

        updated_role = role_crud.update(
            db=db,
            db_obj=role,
            obj_in=role_data,
            updated_by=current_user.id,
        )

        return RoleDetailResponse.from_orm(updated_role)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除角色")
async def delete_role(
    role_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    删除角色（仅管理员）

    - 系统角色无法删除
    - 如果角色正在被用户使用，无法删除
    """
    try:
        role_crud = RoleCRUD()
        role = role_crud.get(db, role_id)

        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="角色不存在"
            )

        success = role_crud.delete(db, role_id, current_user.id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="无法删除角色"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ==================== 权限管理端点 ====================


@router.get("/permissions/list", response_model=dict, summary="获取所有权限")
async def get_all_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取系统中所有可用权限，按资源分组"""
    try:
        permission_crud = PermissionCRUD()
        permissions, _ = permission_crud.get_multi(db, skip=0, limit=10000)

        # 按资源类型分组
        grouped = {}
        for perm in permissions:
            resource = perm.resource
            if resource not in grouped:
                grouped[resource] = []
            grouped[resource].append(PermissionResponse.from_orm(perm))

        return {
            "success": True,
            "data": grouped,
            "total": len(permissions),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.put("/{role_id}/permissions", response_model=dict, summary="设置角色权限")
async def set_role_permissions(
    role_id: str,
    request: RolePermissionUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    为角色分配权限

    - 替换角色的所有权限为新的权限列表
    """
    try:
        role_crud = RoleCRUD()
        permission_crud = PermissionCRUD()

        role = role_crud.get(db, role_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="角色不存在"
            )

        if role.is_system_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="系统角色权限无法修改"
            )

        # 清除现有权限
        role.permissions.clear()

        # 添加新权限
        for perm_id in request.permission_ids:
            perm = permission_crud.get(db, perm_id)
            if perm:
                role.permissions.append(perm)

        role.updated_by = current_user.id
        role.updated_at = datetime.now()
        db.commit()
        db.refresh(role)

        return {
            "success": True,
            "message": "权限更新成功",
            "data": {
                "role_id": role_id,
                "permission_count": len(role.permissions),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ==================== 角色用户关联端点 ====================


@router.get(
    "/{role_id}/users",
    response_model=RoleUserListResponse,
    summary="获取角色的用户列表",
)
async def get_role_users(
    role_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取拥有某个角色的所有用户"""
    try:
        role_crud = RoleCRUD()
        role = role_crud.get(db, role_id)

        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="角色不存在"
            )

        from ...crud.auth import UserCRUD

        user_crud = UserCRUD()

        # 获取拥有此角色的用户
        skip = (page - 1) * limit
        users, total = user_crud.get_users_by_role(db, role_id, skip, limit)

        return RoleUserListResponse(
            users=[
                {"id": u.id, "username": u.username, "email": u.email} for u in users
            ],
            total=total,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


# ==================== 统计端点 ====================


@router.get("/statistics/summary", response_model=dict, summary="获取角色统计信息")
async def get_role_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取角色相关的统计数据"""
    try:
        role_crud = RoleCRUD()

        total_roles = role_crud.count(db)
        by_category = role_crud.count_by_category(db)

        return {
            "success": True,
            "data": {
                "total_roles": total_roles,
                "active_roles": db.query(Role).filter(Role.is_active).count(),
                "system_roles": db.query(Role).filter(Role.is_system_role).count(),
                "custom_roles": db.query(Role).filter(not Role.is_system_role).count(),
                "by_category": by_category,
            },
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
