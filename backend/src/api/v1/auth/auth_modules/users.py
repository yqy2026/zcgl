"""
用户管理API路由

包含: 用户CRUD操作、密码管理、用户状态管理（锁定、激活、停用）
"""

import logging
from importlib import import_module
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
from .....middleware.auth import (
    AuthzContext,
    get_current_active_user,
    require_authz,
)
from .....middleware.security_middleware import get_client_ip
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
from .....security.permissions import require_any_role
from .....services.core.audit_service import AuditService
from .....services.core.password_service import PasswordService
from .....services.core.session_service import AsyncSessionService
from .....services.core.user_management_service import AsyncUserManagementService
from .....services.factory import ServiceFactory, get_service_factory
from .....services.permission.rbac_service import RBACService

router = APIRouter(prefix="/users", tags=["用户管理"])

_get_factory = get_service_factory()
UserCRUD = getattr(import_module("src.crud.auth"), "UserCRUD")
_USER_CREATE_UNSCOPED_PARTY_ID = "__unscoped__:user:create"
_SYSTEM_MANAGEMENT_ROLE_CODES = ["admin", "system_admin", "perm_admin"]


def _normalize_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if normalized == "":
        return None
    return normalized


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


async def _resolve_user_create_resource_context(request: Request) -> dict[str, str]:
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    if not isinstance(payload, dict):
        payload = {}

    organization_id = _normalize_optional_str(payload.get("default_organization_id"))
    scoped_party_id = (
        organization_id
        if organization_id is not None
        else _USER_CREATE_UNSCOPED_PARTY_ID
    )
    return _build_party_scope_context(
        scoped_party_id=scoped_party_id,
        organization_id=organization_id,
    )


class AuditLogCRUD:
    """兼容测试桩的审计日志适配器。"""

    def __init__(self, db: AsyncSession):
        self._audit_service = AuditService(db)

    async def create_async(self, **kwargs: Any) -> Any:
        payload = dict(kwargs)
        user_id = str(payload.pop("user_id", "unknown"))
        action = str(payload.pop("action", "unknown_action"))
        return await self._audit_service.create_audit_log(
            user_id=user_id,
            action=action,
            **payload,
        )


async def _create_audit_log(db: AsyncSession, **kwargs: Any) -> Any:
    """审计日志创建辅助函数。"""
    audit_logger = AuditLogCRUD(db)
    return await audit_logger.create_async(**kwargs)


def _build_legacy_user_service(db: AsyncSession) -> AsyncUserManagementService:
    password_service = PasswordService()
    session_service = AsyncSessionService(db)
    rbac_service = RBACService(db)
    return AsyncUserManagementService(
        db,
        password_service=password_service,
        session_service=session_service,
        rbac_service=rbac_service,
    )


async def _build_user_response(
    user: Any,
    *,
    factory: ServiceFactory | None = None,
    rbac_service: RBACService | None = None,
) -> UserResponse:
    if factory is not None and isinstance(factory, ServiceFactory):
        resolved_rbac = factory.rbac
    elif rbac_service is not None:
        resolved_rbac = rbac_service
    else:
        raise ValueError("必须提供 factory 或 rbac_service")

    role_summary = await resolved_rbac.get_user_role_summary(str(user.id))
    base = UserResponse.model_validate(user)
    return base.model_copy(
        update={
            "role_id": role_summary["primary_role_id"],
            "roles": role_summary["roles"],
            "role_ids": role_summary["role_ids"],
            "is_admin": role_summary["is_admin"],
        }
    )


async def _require_user_read_or_self_authz(
    request: Request,
    current_user: Any = Depends(get_current_active_user),
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
        deny_as_not_found=True,
    )
    return await checker(request=request, current_user=current_user, db=db)


async def _require_user_update_or_self_authz(
    request: Request,
    current_user: Any = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> AuthzContext:
    target_user_id = str(request.path_params.get("user_id") or "").strip()
    current_user_id = str(getattr(current_user, "id", "")).strip()
    if target_user_id != "" and target_user_id == current_user_id:
        return AuthzContext(
            current_user=current_user,
            action="update",
            resource_type="user",
            resource_id=target_user_id,
            resource_context={},
            allowed=True,
            reason_code="self_access_bypass",
        )

    checker = require_authz(
        action="update",
        resource_type="user",
        resource_id="{user_id}",
    )
    return await checker(request=request, current_user=current_user, db=db)


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
    factory: ServiceFactory = Depends(_get_factory),
    current_user: UserResponse = Depends(
        require_any_role(_SYSTEM_MANAGEMENT_ROLE_CODES)
    ),
    _authz_ctx: AuthzContext = Depends(
        require_authz(action="read", resource_type="user")
    ),
) -> JSONResponse:
    """
    获取用户列表（仅管理员）

    - 支持分页
    - 支持按角色、状态、组织筛选
    - 支持关键词搜索

    **Party 隔离策略**：User 表本身无 party_id，用户通过 user_party_bindings 关联
    Party。本接口为超管专属全局视图（require_admin 门控），不按 party 隔离。
    若未来需要「主体级管理员」查看子集，须在 service 层扩展 party_filter 参数，
    当前暂不实现（无该角色需求），但设计意图须保持明确：普通用户不得访问本接口。
    """

    if isinstance(factory, ServiceFactory):
        user_service = factory.user_management
        users, total = await user_service.get_users_with_filters(
            skip=(params.page - 1) * params.page_size,
            limit=params.page_size,
            search=params.search,
            role_id=params.role_id,
            is_active=params.is_active,
            organization_id=params.organization_id,
        )
        items = [await _build_user_response(user, factory=factory) for user in users]
    else:
        user_repo = UserCRUD()
        users, total = await user_repo.get_multi_with_filters_async(
            db=db,
            skip=(params.page - 1) * params.page_size,
            limit=params.page_size,
            search=params.search,
            role_id=params.role_id,
            is_active=params.is_active,
            organization_id=params.organization_id,
        )
        legacy_rbac_service = RBACService(db)
        items = [
            await _build_user_response(user, rbac_service=legacy_rbac_service)
            for user in users
        ]

    return ResponseHandler.paginated(
        data=items,
        page=params.page,
        page_size=params.page_size,
        total=total,
        message="获取用户列表成功",
    )


@router.post("", response_model=UserResponse, summary="创建用户")
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_async_db),
    factory: ServiceFactory = Depends(_get_factory),
    current_user: UserResponse = Depends(
        require_any_role(_SYSTEM_MANAGEMENT_ROLE_CODES)
    ),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="create",
            resource_type="user",
            resource_context=_resolve_user_create_resource_context,
        )
    ),
) -> UserResponse:
    """
    创建新用户（仅管理员）

    - 验证用户名和邮箱唯一性
    - 自动哈希密码
    """

    try:
        if isinstance(factory, ServiceFactory):
            user_service = factory.user_management
            user = await user_service.create_user(
                user_data, assigned_by=str(current_user.id)
            )
            return await _build_user_response(user, factory=factory)

        legacy_user_service = _build_legacy_user_service(db)
        user = await legacy_user_service.create_user(
            user_data, assigned_by=str(current_user.id)
        )
        legacy_rbac_service = RBACService(db)
        return await _build_user_response(user, rbac_service=legacy_rbac_service)
    except BusinessLogicError as e:
        raise bad_request(str(e))


@router.get("/{user_id}", response_model=UserResponse, summary="获取用户详情")
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_async_db),
    factory: ServiceFactory = Depends(_get_factory),
    current_user: UserResponse = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(_require_user_read_or_self_authz),
) -> UserResponse:
    """
    获取用户详情

    - 管理员可以查看所有用户
    - 普通用户只能查看自己的信息
    """

    if isinstance(factory, ServiceFactory):
        rbac_service = factory.rbac
    else:
        rbac_service = RBACService(db)

    if not await rbac_service.is_admin(current_user.id) and current_user.id != user_id:
        raise forbidden("无权访问该用户信息")

    if isinstance(factory, ServiceFactory):
        user_service = factory.user_management
        user = await user_service.get_user_by_id(user_id)
    else:
        user_repo = UserCRUD()
        user = await user_repo.get_async(db, user_id)

    if not user:
        raise not_found("用户不存在", resource_type="user", resource_id=user_id)

    if isinstance(factory, ServiceFactory):
        return await _build_user_response(user, factory=factory)
    return await _build_user_response(user, rbac_service=rbac_service)


@router.put("/{user_id}", response_model=UserResponse, summary="更新用户")
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_async_db),
    factory: ServiceFactory = Depends(_get_factory),
    current_user: UserResponse = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(_require_user_update_or_self_authz),
) -> UserResponse:
    """
    更新用户信息

    - 管理员可以更新所有用户
    - 普通用户只能更新自己的基本信息
    - 密码更新需要当前密码验证
    """

    if isinstance(factory, ServiceFactory):
        rbac_service = factory.rbac
    else:
        rbac_service = RBACService(db)

    if not await rbac_service.is_admin(current_user.id) and current_user.id != user_id:
        raise forbidden("无权修改该用户信息")

    try:
        if isinstance(factory, ServiceFactory):
            user_service = factory.user_management
            existing_user = await user_service.get_user_by_id(str(user_id))
        else:
            user_service = _build_legacy_user_service(db)
            user_repo = UserCRUD()
            existing_user = await user_repo.get_async(db, str(user_id))

        if not existing_user:
            raise not_found("用户不存在", resource_type="user", resource_id=user_id)
        user = await user_service.update_user(
            user_id, user_data, assigned_by=str(current_user.id)
        )
        if not user:
            raise not_found("用户不存在", resource_type="user", resource_id=user_id)
        if isinstance(factory, ServiceFactory):
            return await _build_user_response(user, factory=factory)
        return await _build_user_response(user, rbac_service=rbac_service)
    except BusinessLogicError as e:
        raise bad_request(str(e))


@router.post("/{user_id}/change-password", summary="修改密码")
async def change_password(
    user_id: str,
    password_data: PasswordChangeRequest,
    db: AsyncSession = Depends(get_async_db),
    factory: ServiceFactory = Depends(_get_factory),
    current_user: UserResponse = Depends(get_current_active_user),
) -> dict[str, str]:
    """
    修改用户密码

    - 用户可以修改自己的密码
    - 管理员可以为任何用户修改密码
    - 需要验证当前密码
    """

    if isinstance(factory, ServiceFactory):
        user_service = factory.user_management
        rbac_service = factory.rbac
    else:
        user_service = _build_legacy_user_service(db)
        rbac_service = RBACService(db)

    if not await rbac_service.is_admin(current_user.id) and current_user.id != user_id:
        raise forbidden("无权修改该用户密码")

    if isinstance(factory, ServiceFactory):
        user = await user_service.get_user_by_id(user_id)
    else:
        user_repo = UserCRUD()
        user = await user_repo.get_async(db, user_id)

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


async def _deactivate_user(
    user_id: str,
    *,
    db: AsyncSession,
    factory: ServiceFactory,
) -> dict[str, str]:
    if isinstance(factory, ServiceFactory):
        user_service = factory.user_management
        user = await user_service.get_user_by_id(str(user_id))
        if user:
            success = await user_service.deactivate_user(str(user_id))
        else:
            success = False
    else:
        user_repo = UserCRUD()
        user = await user_repo.get_async(db, str(user_id))
        success = await user_repo.delete_async(db, str(user_id)) if user else False

    if not success:
        raise not_found("用户不存在", resource_type="user", resource_id=user_id)

    return {"message": "用户已停用"}


@router.post("/{user_id}/deactivate", summary="停用用户")
async def deactivate_user(
    user_id: str,
    db: AsyncSession = Depends(get_async_db),
    factory: ServiceFactory = Depends(_get_factory),
    current_user: UserResponse = Depends(
        require_any_role(_SYSTEM_MANAGEMENT_ROLE_CODES)
    ),
    _authz_ctx: AuthzContext = Depends(
        require_authz(action="update", resource_type="user", resource_id="{user_id}")
    ),
) -> dict[str, str]:
    """
    停用用户（仅管理员）

    - 软删除用户
    - 撤销所有会话
    """

    return await _deactivate_user(user_id=user_id, db=db, factory=factory)


@router.delete("/{user_id}", summary="删除用户")
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_async_db),
    factory: ServiceFactory = Depends(_get_factory),
    current_user: UserResponse = Depends(
        require_any_role(_SYSTEM_MANAGEMENT_ROLE_CODES)
    ),
    _authz_ctx: AuthzContext = Depends(
        require_authz(action="delete", resource_type="user", resource_id="{user_id}")
    ),
) -> dict[str, str]:
    """
    删除用户（仅管理员）

    - 软删除用户
    - 撤销所有会话
    """

    return await _deactivate_user(user_id=user_id, db=db, factory=factory)


@router.post("/{user_id}/activate", summary="激活用户")
async def activate_user(
    user_id: str,
    db: AsyncSession = Depends(get_async_db),
    factory: ServiceFactory = Depends(_get_factory),
    current_user: UserResponse = Depends(
        require_any_role(_SYSTEM_MANAGEMENT_ROLE_CODES)
    ),
    _authz_ctx: AuthzContext = Depends(
        require_authz(action="update", resource_type="user", resource_id="{user_id}")
    ),
) -> dict[str, str]:
    """
    激活用户（仅管理员）

    - 激活被停用的用户
    - 解除账户锁定
    """

    if isinstance(factory, ServiceFactory):
        user_service = factory.user_management
    else:
        user_service = _build_legacy_user_service(db)

    success = await user_service.activate_user(user_id)
    if not success:
        raise not_found("用户不存在", resource_type="user", resource_id=user_id)

    return {"message": "用户已激活"}


@router.post("/{user_id}/lock", summary="锁定用户")
async def lock_user(
    user_id: str,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    factory: ServiceFactory = Depends(_get_factory),
    current_user: UserResponse = Depends(
        require_any_role(_SYSTEM_MANAGEMENT_ROLE_CODES)
    ),
    _authz_ctx: AuthzContext = Depends(
        require_authz(action="update", resource_type="user", resource_id="{user_id}")
    ),
) -> dict[str, Any]:
    """
    锁定用户账户（仅管理员）

    锁定后用户无法登录
    """

    try:
        if isinstance(factory, ServiceFactory):
            user_service = factory.user_management
            audit_db = factory.db
        else:
            user_service = _build_legacy_user_service(db)
            audit_db = db

        user = await user_service.lock_user(user_id)

        if not user:
            raise not_found("用户不存在", resource_type="user", resource_id=user_id)

        await _create_audit_log(
            audit_db,
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
    factory: ServiceFactory = Depends(_get_factory),
    current_user: UserResponse = Depends(
        require_any_role(_SYSTEM_MANAGEMENT_ROLE_CODES)
    ),
    _authz_ctx: AuthzContext = Depends(
        require_authz(action="update", resource_type="user", resource_id="{user_id}")
    ),
) -> dict[str, Any]:
    """
    解锁用户账户（仅管理员）

    解锁后用户恢复正常登录

    Note: This is the POST version (more RESTful, has audit logging).
    The GET version at line 661 has been removed to avoid duplicate endpoints.
    """

    try:
        if isinstance(factory, ServiceFactory):
            user_service = factory.user_management
            audit_db = factory.db
        else:
            user_service = _build_legacy_user_service(db)
            audit_db = db

        user = await user_service.unlock_user_with_result(user_id)

        if not user:
            raise not_found("用户不存在", resource_type="user", resource_id=user_id)

        await _create_audit_log(
            audit_db,
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
    factory: ServiceFactory = Depends(_get_factory),
    current_user: UserResponse = Depends(
        require_any_role(_SYSTEM_MANAGEMENT_ROLE_CODES)
    ),
    _authz_ctx: AuthzContext = Depends(
        require_authz(action="update", resource_type="user", resource_id="{user_id}")
    ),
) -> dict[str, Any]:
    """
    重置用户密码（仅管理员）

    - 不需要验证当前密码
    - 适用于用户忘记密码等情况
    """

    try:
        reset_request = password_data

        if isinstance(factory, ServiceFactory):
            user_service = factory.user_management
            audit_db = factory.db
        else:
            user_service = _build_legacy_user_service(db)
            audit_db = db

        user = await user_service.admin_reset_password(
            user_id=user_id,
            new_password=reset_request.new_password,
        )
        if not user:
            raise not_found("用户不存在", resource_type="user", resource_id=user_id)

        await _create_audit_log(
            audit_db,
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
    factory: ServiceFactory = Depends(_get_factory),
    current_user: UserResponse = Depends(
        require_any_role(_SYSTEM_MANAGEMENT_ROLE_CODES)
    ),
    _authz_ctx: AuthzContext = Depends(
        require_authz(action="read", resource_type="user")
    ),
) -> dict[str, Any]:
    """
    获取用户相关统计数据（仅管理员）
    """

    try:
        if isinstance(factory, ServiceFactory):
            user_service = factory.user_management
        else:
            user_service = _build_legacy_user_service(db)
        stats = await user_service.get_statistics()

        return {
            "success": True,
            "data": stats,
        }
    except Exception as e:
        raise internal_error(str(e))
