"""
用户管理API路由

包含: 用户CRUD操作、密码管理、用户状态管理（锁定、激活、停用）
"""

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from ....crud.auth import AuditLogCRUD, UserCRUD
from ....database import get_db
from ....exceptions import BusinessLogicError
from ....middleware.auth import get_current_active_user, require_admin
from ....schemas.auth import (
    PasswordChangeRequest,
    UserCreate,
    UserListResponse,
    UserQueryParams as UserQueryParamsSchema,
    UserResponse,
    UserUpdate,
)
from ....services import AuthService

router = APIRouter(prefix="/users", tags=["用户管理"])


# ==================== User CRUD Endpoints ====================


@router.get("", response_model=UserListResponse, summary="获取用户列表")
@router.get("/search", response_model=UserListResponse, summary="搜索用户")
async def get_users(
    params: UserQueryParamsSchema = Depends(),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_admin),
) -> UserListResponse:
    """
    获取用户列表（仅管理员）

    - 支持分页
    - 支持按角色、状态、组织筛选
    - 支持关键词搜索
    """
    user_crud = UserCRUD()

    # 获取用户列表
    users, total = user_crud.get_multi_with_filters(
        db=db,
        skip=(params.page - 1) * params.page_size,
        limit=params.page_size,
        search=params.search,
        role=params.role,
        is_active=params.is_active,
        organization_id=params.organization_id,
    )

    total_pages = (total + params.page_size - 1) // params.page_size

    return UserListResponse(
        users=[UserResponse.model_validate(user) for user in users],
        total=total,
        page=params.page,
        page_size=params.page_size,
        total_pages=total_pages,
    )


@router.post("", response_model=UserResponse, summary="创建用户")
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_admin),
) -> UserResponse:
    """
    创建新用户（仅管理员）

    - 验证用户名和邮箱唯一性
    - 自动哈希密码
    """
    try:
        user_crud = UserCRUD()
        user = user_crud.create(db, user_data)
        return UserResponse.model_validate(user)
    except BusinessLogicError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{user_id}", response_model=UserResponse, summary="获取用户详情")
async def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
) -> UserResponse:
    """
    获取用户详情

    - 管理员可以查看所有用户
    - 普通用户只能查看自己的信息
    """
    user_crud = UserCRUD()

    # 权限检查
    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="无权访问该用户信息"
        )

    user = user_crud.get(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    return UserResponse.model_validate(user)


@router.put("/{user_id}", response_model=UserResponse, summary="更新用户")
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
) -> UserResponse:
    """
    更新用户信息

    - 管理员可以更新所有用户
    - 普通用户只能更新自己的基本信息
    - 密码更新需要当前密码验证
    """
    user_crud = UserCRUD()

    # 权限检查
    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="无权修改该用户信息"
        )

    try:
        existing_user = user_crud.get(db, str(user_id))
        if not existing_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在"
            )
        user = user_crud.update(db, existing_user, user_data)
        return UserResponse.model_validate(user)
    except BusinessLogicError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{user_id}/change-password", summary="修改密码")
async def change_password(
    user_id: str,
    password_data: PasswordChangeRequest,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
) -> dict[str, str]:
    """
    修改用户密码

    - 用户可以修改自己的密码
    - 管理员可以为任何用户修改密码
    - 需要验证当前密码
    """
    auth_service = AuthService(db)
    user_crud = UserCRUD()

    # 权限检查
    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="无权修改该用户密码"
        )

    user = user_crud.get(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    try:
        success = auth_service.change_password(  # type: ignore[no-untyped-call]
            user=user,
            current_password=password_data.current_password,
            new_password=password_data.new_password,
        )
        if success:
            return {"message": "密码修改成功"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="密码修改失败"
            )
    except BusinessLogicError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{user_id}/deactivate", summary="停用用户")
@router.delete("/{user_id}", summary="删除用户")
async def deactivate_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_admin),
) -> dict[str, str]:
    """
    停用用户（仅管理员）

    - 软删除用户
    - 撤销所有会话
    """
    user_crud = UserCRUD()

    user = user_crud.get(db, str(user_id))
    if user:
        success = user_crud.delete(db, str(user_id))
    else:
        success = False
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    return {"message": "用户已停用"}


@router.post("/{user_id}/activate", summary="激活用户")
async def activate_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_admin),
) -> dict[str, str]:
    """
    激活用户（仅管理员）

    - 激活被停用的用户
    - 解除账户锁定
    """
    auth_service = AuthService(db)

    success = auth_service.activate_user(user_id)  # type: ignore[no-untyped-call]
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    return {"message": "用户已激活"}


# ==================== User Account Management Endpoints ====================


@router.post("/{user_id}/lock", summary="锁定用户")
async def lock_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_admin),
) -> dict[str, Any]:
    """
    锁定用户账户（仅管理员）

    锁定后用户无法登录
    """
    try:
        user_crud = UserCRUD()
        user = user_crud.get(db, user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在"
            )

        setattr(user, "is_locked", True)
        setattr(user, "updated_at", datetime.now(UTC))
        db.commit()
        db.refresh(user)

        # 记录审计日志
        audit_crud = AuditLogCRUD()
        audit_crud.create(
            db=db,
            user_id=user_id,
            action="user_locked",
            resource_type="user",
            resource_id=user_id,
            ip_address="system",
            user_agent="admin_action",
        )

        return {"success": True, "message": f"用户 {user.username} 已锁定"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{user_id}/unlock", summary="解锁用户账户")
async def unlock_user_account(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_admin),
) -> dict[str, Any]:
    """
    解锁用户账户（仅管理员）

    解锁后用户恢复正常登录

    Note: This is the POST version (more RESTful, has audit logging).
    The GET version at line 661 has been removed to avoid duplicate endpoints.
    """
    try:
        user_crud = UserCRUD()
        user = user_crud.get(db, user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在"
            )

        setattr(user, "is_locked", False)
        setattr(user, "updated_at", datetime.now(UTC))
        db.commit()
        db.refresh(user)

        # 记录审计日志
        audit_crud = AuditLogCRUD()
        audit_crud.create(
            db=db,
            user_id=user_id,
            action="user_unlocked",
            resource_type="user",
            resource_id=user_id,
            ip_address="system",
            user_agent="admin_action",
        )

        return {"success": True, "message": f"用户 {user.username} 已解锁"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{user_id}/reset-password", summary="重置用户密码")
async def reset_user_password(
    user_id: str,
    password_data: dict[str, Any],
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_admin),
) -> dict[str, Any]:
    """
    重置用户密码（仅管理员）

    - 不需要验证当前密码
    - 适用于用户忘记密码等情况
    """
    from pydantic import BaseModel

    class PasswordResetRequest(BaseModel):
        new_password: str
        reason: str | None = None

    try:
        # 解析请求体
        import json

        if isinstance(password_data, str):
            password_data = json.loads(password_data)

        reset_request = PasswordResetRequest(**password_data)

        user_crud = UserCRUD()
        auth_service = AuthService(db)

        user = user_crud.get(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在"
            )

        # 设置新密码
        setattr(
            user,
            "hashed_password",
            auth_service.get_password_hash(reset_request.new_password),  # type: ignore[no-untyped-call]
        )
        setattr(user, "updated_at", datetime.now(UTC))
        db.commit()
        db.refresh(user)

        # 记录审计日志
        audit_crud = AuditLogCRUD()
        audit_crud.create(
            db=db,
            user_id=user_id,
            action="password_reset",
            resource_type="user",
            resource_id=user_id,
            ip_address="system",
            user_agent="admin_action",
        )

        return {
            "success": True,
            "message": f"用户 {user.username} 密码已重置",
            "user_id": user_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/statistics/summary", response_model=dict[str, Any], summary="获取用户统计")
async def get_user_statistics(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_admin),
) -> dict[str, Any]:
    """
    获取用户相关统计数据（仅管理员）
    """
    try:
        from sqlalchemy import func

        from ....models.auth import User

        total_users = db.query(func.count(User.id)).scalar()
        active_users = db.query(func.count(User.id)).filter(User.is_active).scalar()
        locked_users = db.query(func.count(User.id)).filter(User.is_locked).scalar()
        inactive_users = (
            db.query(func.count(User.id)).filter(User.is_active.is_(False)).scalar()
        )

        return {
            "success": True,
            "data": {
                "total_users": total_users,
                "active_users": active_users,
                "locked_users": locked_users,
                "inactive_users": inactive_users,
                "online_users": 0,  # 可根据会话表计算
            },
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
