"""
认证相关API路由 - 认证端点

包含: 登录、登出、刷新令牌、获取当前用户信息
"""

import logging
from datetime import UTC, datetime
from importlib import import_module
from json import JSONDecodeError, loads
from typing import Any

import jwt
from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from .....core.config import settings
from .....core.exception_handler import (
    BaseBusinessError,
    bad_request,
    internal_error,
    unauthorized,
)

logger = logging.getLogger(__name__)

from .....database import get_async_db
from .....exceptions import BusinessLogicError
from .....middleware.auth import get_current_active_user
from .....middleware.security_middleware import get_client_ip
from .....models.auth import User
from .....schemas.auth import (
    CookieAuthResponse,
    CookieRefreshResponse,
    LoginRequest,
    PermissionSchema,
    UserResponse,
)
from .....security.cookie_manager import cookie_manager
from .....services.core.audit_service import AuditService
from .....services.core.authentication_service import AsyncAuthenticationService
from .....services.core.password_service import PasswordService
from .....services.core.session_service import AsyncSessionService
from .....services.core.user_management_service import AsyncUserManagementService
from .....services.factory import ServiceFactory, get_service_factory
from .....services.permission.rbac_service import RBACService

router = APIRouter(tags=["认证管理"])

_get_factory = get_service_factory()
UserCRUD = getattr(import_module("src.crud.auth"), "UserCRUD")


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


def _resolve_persistent_login(device_info: Any) -> bool:
    """Resolve remember-login preference from persisted session device_info.

    Backward compatibility:
    Sessions created before remember-me rollout don't include the `remember` field.
    Missing/unknown values are treated as legacy persistent sessions.
    """

    def _to_bool(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "1", "yes", "on"}:
                return True
            if normalized in {"false", "0", "no", "off"}:
                return False
            return True
        return True

    # Legacy sessions without structured device_info should keep persistent cookies.
    if device_info is None:
        return True

    if isinstance(device_info, dict):
        if "remember" not in device_info:
            return True
        remember_value = device_info.get("remember")
        return _to_bool(remember_value)

    if isinstance(device_info, str):
        try:
            parsed = loads(device_info)
        except JSONDecodeError:
            return True
        if isinstance(parsed, dict):
            if "remember" not in parsed:
                return True
            remember_value = parsed.get("remember")
            return _to_bool(remember_value)
        return True

    return True


def _build_legacy_services(
    db: AsyncSession,
) -> tuple[
    AsyncAuthenticationService,
    AsyncSessionService,
    AsyncUserManagementService,
    RBACService,
]:
    password_service = PasswordService()
    session_service = AsyncSessionService(db)
    rbac_service = RBACService(db)
    user_service = AsyncUserManagementService(
        db,
        password_service=password_service,
        session_service=session_service,
        rbac_service=rbac_service,
    )
    auth_service = AsyncAuthenticationService(
        db,
        password_service=password_service,
        user_service=user_service,
        session_service=session_service,
    )
    return auth_service, session_service, user_service, rbac_service


@router.post("/login", response_model=CookieAuthResponse, summary="用户登录")
async def login(
    request: Request,
    credentials: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_async_db),
    factory: ServiceFactory = Depends(_get_factory),
) -> dict[str, Any]:
    """
    用户登录接口

    - 支持用户名或手机号登录
    - 返回JWT访问令牌和刷新令牌
    - 记录登录审计日志
    """

    using_factory = isinstance(factory, ServiceFactory)
    if using_factory:
        auth_service = factory.authentication
        session_service = factory.session
        rbac_service = factory.rbac
        audit_db = factory.db
    else:
        auth_service, session_service, _, rbac_service = (
            _build_legacy_services(db)
        )
        audit_db = db

    client_ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "unknown")
    persistent_login = credentials.remember is True

    try:
        user = await auth_service.authenticate_user(
            credentials.identifier, credentials.password
        )
        if not user:
            user_repo = UserCRUD()
            existing_user = await user_repo.find_active_by_identifier_async(
                db, credentials.identifier
            )
            if existing_user is None:
                existing_user = await user_repo.find_by_identifier_async(
                    db, credentials.identifier
                )
            if existing_user:
                await _create_audit_log(
                    audit_db,
                    user_id=str(existing_user.id) if existing_user else "unknown",
                    action="user_login_failed",
                    resource_type="authentication",
                    ip_address=client_ip,
                    user_agent=user_agent,
                )

            raise unauthorized("账号或密码错误")

        device_info: dict[str, Any] = {
            "user_agent": user_agent,
            "ip_address": client_ip,
            "device_id": str(user.id),
            "remember": persistent_login,
        }
        tokens = auth_service.create_tokens(user, device_info)

        cookie_manager.set_auth_cookie(
            response, tokens.access_token, persistent=persistent_login
        )
        cookie_manager.set_refresh_cookie(
            response, tokens.refresh_token, persistent=persistent_login
        )
        cookie_manager.set_csrf_cookie(
            response,
            cookie_manager.create_csrf_token(),
            persistent=persistent_login,
        )

        await session_service.create_user_session(
            user_id=str(user.id),
            refresh_token=tokens.refresh_token,
            device_info=device_info,
            ip_address=client_ip,
            user_agent=user_agent,
            session_id=getattr(tokens, "session_id", None),
        )

        await _create_audit_log(
            audit_db,
            user_id=str(user.id),
            action="user_login",
            resource_type="authentication",
            api_endpoint="/api/auth/login",
            http_method="POST",
            response_status=200,
            ip_address=client_ip,
            user_agent=user_agent,
        )

        role_summary: dict[str, Any] = {
            "roles": [],
            "role_ids": [],
            "primary_role_id": None,
            "primary_role_name": None,
            "is_admin": False,
        }
        try:
            role_summary = await rbac_service.get_user_role_summary(str(user.id))
        except Exception as e:
            logger.warning(f"Failed to fetch role summary for user {user.id}: {e}")

        try:
            permission_summary = await rbac_service.get_user_permissions_summary(
                str(user.id)
            )
            permission_map: dict[tuple[str, str], PermissionSchema] = {}
            for perm in permission_summary.permissions:
                resource = str(perm.resource)
                action = str(perm.action)
                key = (resource, action)
                description = getattr(perm, "description", None)

                existing = permission_map.get(key)
                if existing is None:
                    permission_map[key] = PermissionSchema(
                        resource=resource,
                        action=action,
                        description=description,
                    )
                    continue

                # 若已存在记录缺少描述，而当前记录存在描述，则补齐描述
                if existing.description in (None, "") and description not in (None, ""):
                    permission_map[key] = PermissionSchema(
                        resource=resource,
                        action=action,
                        description=description,
                    )

            permissions_list = list(permission_map.values())
        except Exception as e:
            logger.warning(f"Failed to fetch permissions for user {user.id}: {e}")
            permissions_list = []

        return {
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "phone": getattr(user, "phone", "") or "",
                "full_name": user.full_name,
                "role_id": role_summary["primary_role_id"],
                "role_name": role_summary["primary_role_name"],
                "roles": role_summary["roles"],
                "role_ids": role_summary["role_ids"],
                "is_admin": role_summary["is_admin"],
                "is_active": bool(user.is_active)
                if hasattr(user.is_active, "__int__")
                else user.is_active,
                "is_locked": bool(getattr(user, "is_locked", False))
                if hasattr(getattr(user, "is_locked", False), "__int__")
                else getattr(user, "is_locked", False),
                "last_login_at": getattr(user, "last_login_at", None),
                "default_organization_id": getattr(
                    user, "default_organization_id", None
                ),
                "created_at": getattr(user, "created_at", None) or datetime.now(UTC),
                "updated_at": getattr(user, "updated_at", None) or datetime.now(UTC),
            },
            "permissions": [
                {
                    "resource": p.resource,
                    "action": p.action,
                    "description": p.description,
                }
                for p in permissions_list
            ],
            "message": "登录成功",
            "auth_mode": "cookie",
        }

    except BusinessLogicError as e:
        raise bad_request(str(e))
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        logger.error(f"Authentication error: {str(e)}", exc_info=True)

        raise internal_error("登录服务暂时不可用，请稍后重试")


@router.post("/logout", summary="用户登出")
async def logout(
    request: Request,
    response: Response,
    current_user: UserResponse = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
    factory: ServiceFactory = Depends(_get_factory),
) -> dict[str, Any]:
    """
    用户登出接口

    - 撤销当前会话
    - 将当前JWT令牌加入黑名单
    - 清除客户端令牌（包括 httpOnly cookie）
    - 记录登出审计日志
    """

    if isinstance(factory, ServiceFactory):
        session_service = factory.session
        audit_db = factory.db
    else:
        session_service = AsyncSessionService(db)
        audit_db = db

    client_ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "unknown")

    cookie_manager.clear_auth_cookie(response)
    cookie_manager.clear_refresh_cookie(response)
    cookie_manager.clear_csrf_cookie(response)

    cookie_header = request.headers.get("cookie", "")
    token = cookie_manager.get_token_from_cookie(
        cookie_header, cookie_name=cookie_manager.cookie_name
    )

    if token:
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[getattr(settings, "ALGORITHM", "HS256")],
                audience=settings.JWT_AUDIENCE,
                issuer=settings.JWT_ISSUER,
                options={"verify_exp": False},
            )
            jti = payload.get("jti")
            exp = payload.get("exp")

            if jti and exp:
                from .....security.token_blacklist import blacklist_manager

                blacklist_manager.add_token(jti, exp)
        except Exception as e:
            logger.warning(f"Failed to blacklist token during logout: {e}")

    revoked_count = await session_service.revoke_all_user_sessions(current_user.id)

    await _create_audit_log(
        audit_db,
        user_id=current_user.id,
        action="user_logout",
        resource_type="authentication",
        api_endpoint="/api/v1/auth/logout",
        http_method="POST",
        response_status=200,
        response_message=f"已撤销 {revoked_count} 个会话",
        ip_address=client_ip,
        user_agent=user_agent,
    )

    return {"message": "登出成功", "revoked_sessions": revoked_count}


@router.post("/refresh", response_model=CookieRefreshResponse, summary="刷新令牌")
async def refresh_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_async_db),
    factory: ServiceFactory = Depends(_get_factory),
) -> CookieRefreshResponse:
    """
    刷新访问令牌接口

    - 使用刷新令牌刷新会话（不在响应体返回Token）
    - 自动延长会话有效期
    - 增强安全性：记录刷新操作、检查IP变化等

    Note:
        authentication_service.validate_refresh_token() returns UserSession, so we
        extract the User from the session relationship.
    """

    if isinstance(factory, ServiceFactory):
        auth_service = factory.authentication
        session_service = factory.session
        audit_db = factory.db
    else:
        auth_service, session_service, _, _ = _build_legacy_services(db)
        audit_db = db

    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    cookie_header = request.headers.get("cookie", "")
    refresh_token = cookie_manager.get_token_from_cookie(
        cookie_header, cookie_name=cookie_manager.refresh_cookie_name
    )
    if not refresh_token:
        raise bad_request("刷新令牌缺失")

    session = await auth_service.validate_refresh_token(
        refresh_token, client_ip=client_ip, user_agent=user_agent
    )
    if not session:
        await _create_audit_log(
            audit_db,
            user_id="unknown",
            action="token_refresh_failed",
            resource_type="authentication",
            api_endpoint="/api/v1/auth/refresh",
            http_method="POST",
            response_status=401,
            response_message="无效的刷新令牌",
            ip_address=client_ip,
            user_agent=user_agent,
        )
        raise unauthorized("无效的刷新令牌")

    user: User | None = getattr(session, "user", None)
    user_active = getattr(user, "is_active", False) if user else False
    if not user or not user_active:
        await session_service.revoke_session(refresh_token)
        raise unauthorized("用户不存在或已被禁用")

    device_info: dict[str, str | None] = {
        "user_agent": user_agent,
        "ip_address": client_ip,
        "device_id": getattr(user, "id", None),
        "platform": None,
    }
    tokens = auth_service.create_tokens(user, device_info)
    persistent_login = _resolve_persistent_login(getattr(session, "device_info", None))
    cookie_manager.set_auth_cookie(
        response, tokens.access_token, persistent=persistent_login
    )
    cookie_manager.set_refresh_cookie(
        response, tokens.refresh_token, persistent=persistent_login
    )
    cookie_manager.set_csrf_cookie(
        response,
        cookie_manager.create_csrf_token(),
        persistent=persistent_login,
    )

    await _create_audit_log(
        audit_db,
        user_id=str(getattr(user, "id", "unknown")),
        action="token_refresh_success",
        resource_type="authentication",
        api_endpoint="/api/v1/auth/refresh",
        http_method="POST",
        response_status=200,
        response_message="令牌刷新成功",
        ip_address=client_ip,
        user_agent=user_agent,
    )

    return CookieRefreshResponse(message="令牌刷新成功", auth_mode="cookie")


@router.get("/me", response_model=dict[str, Any], summary="获取当前用户信息")
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
    factory: ServiceFactory = Depends(_get_factory),
) -> dict[str, Any]:
    """
    获取当前登录用户的信息

    企业级实现，包含完整的用户信息、权限状态、会话信息和时间戳
    """
    if isinstance(factory, ServiceFactory):
        rbac_service = factory.rbac
    else:
        rbac_service = RBACService(db)
    role_summary = await rbac_service.get_user_role_summary(str(current_user.id))

    return {
        "username": current_user.username,
        "email": current_user.email,
        "phone": getattr(current_user, "phone", "") or "",
        "full_name": current_user.full_name,
        "id": current_user.id,
        "is_active": current_user.is_active,
        "role_id": role_summary["primary_role_id"],
        "role_name": role_summary["primary_role_name"],
        "roles": role_summary["roles"],
        "role_ids": role_summary["role_ids"],
        "is_admin": role_summary["is_admin"],
        "default_organization_id": current_user.default_organization_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "session_status": "active",
    }
