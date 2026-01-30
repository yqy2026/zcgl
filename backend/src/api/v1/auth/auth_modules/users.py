"""
用户管理API路由

包含: 用户CRUD操作、密码管理、用户状态管理（锁定、激活、停用）
"""

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from .....core.exception_handler import (
    BaseBusinessError,
    bad_request,
    forbidden,
    internal_error,
    not_found,
)
from .....core.response_handler import APIResponse, PaginatedData, ResponseHandler

logger = logging.getLogger(__name__)

from .....crud.auth import AuditLogCRUD, UserCRUD
from .....database import get_db
from .....exceptions import BusinessLogicError
from .....middleware.auth import (
    get_current_active_user,
    require_admin,
    safe_role_compare,
)
from .....middleware.security_middleware import get_client_ip
from .....models.auth import UserRole
from .....schemas.auth import (
    AdminPasswordResetRequest,
    PasswordChangeRequest,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from .....schemas.auth import (
    UserQueryParams as UserQueryParamsSchema,
)
from .....services import AuthService

router = APIRouter(prefix="/users", tags=["用户管理"])


# ==================== User CRUD Endpoints ====================


@router.get(
    "", response_model=APIResponse[PaginatedData[UserResponse]], summary="获取用户列表"
)
@router.get(
    "/search",
    response_model=APIResponse[PaginatedData[UserResponse]],
    summary="搜索用户",
)
async def get_users(
    params: UserQueryParamsSchema = Depends(),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_admin),
) -> JSONResponse:
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

    return ResponseHandler.paginated(
        data=[UserResponse.model_validate(user) for user in users],
        page=params.page,
        page_size=params.page_size,
        total=total,
        message="获取用户列表成功",
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
        raise bad_request(str(e))


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
    if not safe_role_compare(current_user.role, UserRole.ADMIN) and (
        current_user.id != user_id
    ):
        raise forbidden("无权访问该用户信息")

    user = user_crud.get(db, user_id)
    if not user:
        raise not_found("用户不存在", resource_type="user", resource_id=user_id)

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
    if not safe_role_compare(current_user.role, UserRole.ADMIN) and (
        current_user.id != user_id
    ):
        raise forbidden("无权修改该用户信息")

    try:
        existing_user = user_crud.get(db, str(user_id))
        if not existing_user:
            raise not_found("用户不存在", resource_type="user", resource_id=user_id)
        user = user_crud.update(db, existing_user, user_data)
        return UserResponse.model_validate(user)
    except BusinessLogicError as e:
        raise bad_request(str(e))


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
    if not safe_role_compare(current_user.role, UserRole.ADMIN) and (
        current_user.id != user_id
    ):
        raise forbidden("无权修改该用户密码")

    user = user_crud.get(db, user_id)
    if not user:
        raise not_found("用户不存在", resource_type="user", resource_id=user_id)

    try:
        success = auth_service.change_password(
            user=user,
            current_password=password_data.current_password,
            new_password=password_data.new_password,
        )
        if success:
            return {"message": "密码修改成功"}
        else:
            raise internal_error("密码修改失败")
    except BusinessLogicError as e:
        raise bad_request(str(e))


def _deactivate_user(user_id: str, db: Session) -> dict[str, str]:
    user_crud = UserCRUD()

    user = user_crud.get(db, str(user_id))
    if user:
        success = user_crud.delete(db, str(user_id))
    else:
        success = False
    if not success:
        raise not_found("用户不存在", resource_type="user", resource_id=user_id)

    return {"message": "用户已停用"}


@router.post("/{user_id}/deactivate", summary="停用用户")
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
    return _deactivate_user(user_id=user_id, db=db)


@router.delete("/{user_id}", summary="删除用户")
async def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_admin),
) -> dict[str, str]:
    """
    删除用户（仅管理员）

    - 软删除用户
    - 撤销所有会话
    """
    return _deactivate_user(user_id=user_id, db=db)


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

    success = auth_service.activate_user(user_id)
    if not success:
        raise not_found("用户不存在", resource_type="user", resource_id=user_id)

    return {"message": "用户已激活"}


# ==================== User Account Management Endpoints ====================


@router.post("/{user_id}/lock", summary="锁定用户")
async def lock_user(
    user_id: str,
    request: Request,
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
            raise not_found("用户不存在", resource_type="user", resource_id=user_id)

        setattr(user, "is_locked", True)
        setattr(user, "updated_at", datetime.now(UTC))
        db.commit()
        db.refresh(user)

        # 记录审计日志
        audit_crud = AuditLogCRUD()
        audit_crud.create(
            db=db,
            user_id=current_user.id,
            action="user_locked",
            resource_type="user",
            resource_id=user_id,
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("user-agent", ""),
        )

        return {"success": True, "message": f"用户 {user.username} 已锁定"}
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        db.rollback()
        raise bad_request(str(e))


@router.post("/{user_id}/unlock", summary="解锁用户账户")
async def unlock_user_account(
    user_id: str,
    request: Request,
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
            raise not_found("用户不存在", resource_type="user", resource_id=user_id)

        setattr(user, "is_locked", False)
        setattr(user, "updated_at", datetime.now(UTC))
        db.commit()
        db.refresh(user)

        # 记录审计日志
        audit_crud = AuditLogCRUD()
        audit_crud.create(
            db=db,
            user_id=current_user.id,
            action="user_unlocked",
            resource_type="user",
            resource_id=user_id,
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("user-agent", ""),
        )

        return {"success": True, "message": f"用户 {user.username} 已解锁"}
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        db.rollback()
        raise bad_request(str(e))


@router.post("/{user_id}/reset-password", summary="重置用户密码")
async def reset_user_password(
    user_id: str,
    password_data: AdminPasswordResetRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_admin),
) -> dict[str, Any]:
    """
    重置用户密码（仅管理员）

    - 不需要验证当前密码
    - 适用于用户忘记密码等情况
    """
    try:
        reset_request = password_data

        user_crud = UserCRUD()
        auth_service = AuthService(db)

        user = user_crud.get(db, user_id)
        if not user:
            raise not_found("用户不存在", resource_type="user", resource_id=user_id)

        # 设置新密码
        setattr(
            user,
            "password_hash",
            auth_service.get_password_hash(reset_request.new_password),
        )
        setattr(user, "updated_at", datetime.now(UTC))
        db.commit()
        db.refresh(user)

        # 记录审计日志
        audit_crud = AuditLogCRUD()
        audit_crud.create(
            db=db,
            user_id=current_user.id,
            action="password_reset",
            resource_type="user",
            resource_id=user_id,
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("user-agent", ""),
        )

        return {
            "success": True,
            "message": f"用户 {user.username} 密码已重置",
            "user_id": user_id,
        }
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        db.rollback()
        raise bad_request(str(e))


@router.get(
    "/statistics/summary", response_model=dict[str, Any], summary="获取用户统计"
)
async def get_user_statistics(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_admin),
) -> dict[str, Any]:
    """
    获取用户相关统计数据（仅管理员）
    """
    try:
        from .....services.core.user_management_service import UserManagementService

        user_service = UserManagementService(db)
        stats = user_service.get_statistics()

        return {
            "success": True,
            "data": stats,
        }
    except Exception as e:
        raise internal_error(str(e))
