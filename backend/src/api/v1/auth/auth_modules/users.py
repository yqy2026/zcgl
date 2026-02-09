"""
用户管理API路由

包含: 用户CRUD操作、密码管理、用户状态管理（锁定、激活、停用）
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from .....core.exception_handler import (
    BaseBusinessError,
    bad_request,
    forbidden,
    internal_error,
    not_found,
)
from .....core.response_handler import APIResponse, PaginatedData, ResponseHandler

logger = logging.getLogger(__name__)

from .....database import get_async_db
from .....exceptions import BusinessLogicError
from .....middleware.auth import get_current_active_user, require_admin
from .....middleware.security_middleware import get_client_ip
from .....models.auth import User
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
from .....services.core.audit_service import AuditService
from .....services.core.user_management_service import AsyncUserManagementService
from .....services.permission.rbac_service import RBACService

router = APIRouter(prefix="/users", tags=["用户管理"])


class UserCRUD:
    """兼容适配：将历史 UserCRUD 接口委托至用户服务层。"""

    async def get_multi_with_filters_async(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
        role_id: str | None = None,
        is_active: bool | None = None,
        organization_id: str | None = None,
    ) -> tuple[list[User], int]:
        user_service = AsyncUserManagementService(db)
        return await user_service.get_users_with_filters(
            skip=skip,
            limit=limit,
            search=search,
            role_id=role_id,
            is_active=is_active,
            organization_id=organization_id,
        )

    async def get_async(self, db: AsyncSession, user_id: str) -> User | None:
        user_service = AsyncUserManagementService(db)
        return await user_service.get_user_by_id(user_id)

    async def delete_async(self, db: AsyncSession, user_id: str) -> bool:
        user_service = AsyncUserManagementService(db)
        return await user_service.deactivate_user(user_id)


class AuditLogCRUD:
    """兼容适配：将历史 AuditLogCRUD 接口委托至审计服务层。"""

    async def create_async(self, db: AsyncSession, **kwargs: Any) -> Any:
        audit_service = AuditService(db)
        payload = dict(kwargs)
        user_id = str(payload.pop("user_id", "unknown"))
        action = str(payload.pop("action", "unknown_action"))
        return await audit_service.create_audit_log(
            user_id=user_id,
            action=action,
            **payload,
        )


async def _build_user_response(user: Any, db: AsyncSession) -> UserResponse:
    rbac_service = RBACService(db)
    role_summary = await rbac_service.get_user_role_summary(str(user.id))
    base = UserResponse.model_validate(user)
    return base.model_copy(
        update={
            "role_id": role_summary["primary_role_id"],
            "role_name": role_summary["primary_role_name"],
            "roles": role_summary["roles"],
            "role_ids": role_summary["role_ids"],
            "is_admin": role_summary["is_admin"],
        }
    )


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
    db: AsyncSession = Depends(get_async_db),
    current_user: UserResponse = Depends(require_admin),
) -> JSONResponse:
    """
    获取用户列表（仅管理员）

    - 支持分页
    - 支持按角色、状态、组织筛选
    - 支持关键词搜索
    """

    user_repository = UserCRUD()

    users, total = await user_repository.get_multi_with_filters_async(
        db=db,
        skip=(params.page - 1) * params.page_size,
        limit=params.page_size,
        search=params.search,
        role_id=params.role_id,
        is_active=params.is_active,
        organization_id=params.organization_id,
    )

    return ResponseHandler.paginated(
        data=[await _build_user_response(user, db) for user in users],
        page=params.page,
        page_size=params.page_size,
        total=total,
        message="获取用户列表成功",
    )


@router.post("", response_model=UserResponse, summary="创建用户")
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserResponse = Depends(require_admin),
) -> UserResponse:
    """
    创建新用户（仅管理员）

    - 验证用户名和邮箱唯一性
    - 自动哈希密码
    """

    try:
        user_service = AsyncUserManagementService(db)
        user = await user_service.create_user(user_data, assigned_by=str(current_user.id))
        return await _build_user_response(user, db)
    except BusinessLogicError as e:
        raise bad_request(str(e))


@router.get("/{user_id}", response_model=UserResponse, summary="获取用户详情")
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserResponse = Depends(get_current_active_user),
) -> UserResponse:
    """
    获取用户详情

    - 管理员可以查看所有用户
    - 普通用户只能查看自己的信息
    """

    user_repository = UserCRUD()

    rbac_service = RBACService(db)
    if not await rbac_service.is_admin(current_user.id) and current_user.id != user_id:
        raise forbidden("无权访问该用户信息")

    user = await user_repository.get_async(db, user_id)
    if not user:
        raise not_found("用户不存在", resource_type="user", resource_id=user_id)

    return await _build_user_response(user, db)


@router.put("/{user_id}", response_model=UserResponse, summary="更新用户")
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserResponse = Depends(get_current_active_user),
) -> UserResponse:
    """
    更新用户信息

    - 管理员可以更新所有用户
    - 普通用户只能更新自己的基本信息
    - 密码更新需要当前密码验证
    """

    user_repository = UserCRUD()

    rbac_service = RBACService(db)
    if not await rbac_service.is_admin(current_user.id) and current_user.id != user_id:
        raise forbidden("无权修改该用户信息")

    try:
        existing_user = await user_repository.get_async(db, str(user_id))
        if not existing_user:
            raise not_found("用户不存在", resource_type="user", resource_id=user_id)
        user_service = AsyncUserManagementService(db)
        user = await user_service.update_user(
            user_id, user_data, assigned_by=str(current_user.id)
        )
        if not user:
            raise not_found("用户不存在", resource_type="user", resource_id=user_id)
        return await _build_user_response(user, db)
    except BusinessLogicError as e:
        raise bad_request(str(e))


@router.post("/{user_id}/change-password", summary="修改密码")
async def change_password(
    user_id: str,
    password_data: PasswordChangeRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserResponse = Depends(get_current_active_user),
) -> dict[str, str]:
    """
    修改用户密码

    - 用户可以修改自己的密码
    - 管理员可以为任何用户修改密码
    - 需要验证当前密码
    """

    user_service = AsyncUserManagementService(db)
    user_repository = UserCRUD()

    rbac_service = RBACService(db)
    if not await rbac_service.is_admin(current_user.id) and current_user.id != user_id:
        raise forbidden("无权修改该用户密码")

    user = await user_repository.get_async(db, user_id)
    if not user:
        raise not_found("用户不存在", resource_type="user", resource_id=user_id)

    try:
        success = await user_service.change_password(
            user=user,
            current_password=password_data.current_password,
            new_password=password_data.new_password,
        )
        if success:
            return {"message": "密码修改成功"}
        raise internal_error("密码修改失败")
    except BusinessLogicError as e:
        raise bad_request(str(e))


async def _deactivate_user(user_id: str, db: AsyncSession) -> dict[str, str]:
    user_repository = UserCRUD()

    user = await user_repository.get_async(db, str(user_id))
    if user:
        success = await user_repository.delete_async(db, str(user_id))
    else:
        success = False
    if not success:
        raise not_found("用户不存在", resource_type="user", resource_id=user_id)

    return {"message": "用户已停用"}


@router.post("/{user_id}/deactivate", summary="停用用户")
async def deactivate_user(
    user_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserResponse = Depends(require_admin),
) -> dict[str, str]:
    """
    停用用户（仅管理员）

    - 软删除用户
    - 撤销所有会话
    """

    return await _deactivate_user(user_id=user_id, db=db)


@router.delete("/{user_id}", summary="删除用户")
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserResponse = Depends(require_admin),
) -> dict[str, str]:
    """
    删除用户（仅管理员）

    - 软删除用户
    - 撤销所有会话
    """

    return await _deactivate_user(user_id=user_id, db=db)


@router.post("/{user_id}/activate", summary="激活用户")
async def activate_user(
    user_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserResponse = Depends(require_admin),
) -> dict[str, str]:
    """
    激活用户（仅管理员）

    - 激活被停用的用户
    - 解除账户锁定
    """

    user_service = AsyncUserManagementService(db)

    success = await user_service.activate_user(user_id)
    if not success:
        raise not_found("用户不存在", resource_type="user", resource_id=user_id)

    return {"message": "用户已激活"}


@router.post("/{user_id}/lock", summary="锁定用户")
async def lock_user(
    user_id: str,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserResponse = Depends(require_admin),
) -> dict[str, Any]:
    """
    锁定用户账户（仅管理员）

    锁定后用户无法登录
    """

    try:
        user_service = AsyncUserManagementService(db)
        user = await user_service.lock_user(user_id)

        if not user:
            raise not_found("用户不存在", resource_type="user", resource_id=user_id)

        audit_logger = AuditLogCRUD()
        await audit_logger.create_async(
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
        raise bad_request(str(e))


@router.post("/{user_id}/unlock", summary="解锁用户账户")
async def unlock_user_account(
    user_id: str,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserResponse = Depends(require_admin),
) -> dict[str, Any]:
    """
    解锁用户账户（仅管理员）

    解锁后用户恢复正常登录

    Note: This is the POST version (more RESTful, has audit logging).
    The GET version at line 661 has been removed to avoid duplicate endpoints.
    """

    try:
        user_service = AsyncUserManagementService(db)
        user = await user_service.unlock_user_with_result(user_id)

        if not user:
            raise not_found("用户不存在", resource_type="user", resource_id=user_id)

        audit_logger = AuditLogCRUD()
        await audit_logger.create_async(
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
        raise bad_request(str(e))


@router.post("/{user_id}/reset-password", summary="重置用户密码")
async def reset_user_password(
    user_id: str,
    password_data: AdminPasswordResetRequest,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserResponse = Depends(require_admin),
) -> dict[str, Any]:
    """
    重置用户密码（仅管理员）

    - 不需要验证当前密码
    - 适用于用户忘记密码等情况
    """

    try:
        reset_request = password_data

        user_service = AsyncUserManagementService(db)
        user = await user_service.admin_reset_password(
            user_id=user_id,
            new_password=reset_request.new_password,
        )
        if not user:
            raise not_found("用户不存在", resource_type="user", resource_id=user_id)

        audit_logger = AuditLogCRUD()
        await audit_logger.create_async(
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
        raise bad_request(str(e))


@router.get(
    "/statistics/summary", response_model=dict[str, Any], summary="获取用户统计"
)
async def get_user_statistics(
    db: AsyncSession = Depends(get_async_db),
    current_user: UserResponse = Depends(require_admin),
) -> dict[str, Any]:
    """
    获取用户相关统计数据（仅管理员）
    """

    try:
        user_service = AsyncUserManagementService(db)
        stats = await user_service.get_statistics()

        return {
            "success": True,
            "data": stats,
        }
    except Exception as e:
        raise internal_error(str(e))
