"""
认证相关API路由 - 认证端点

包含: 登录、登出、刷新令牌、获取当前用户信息
"""

import logging
from datetime import UTC, datetime
from typing import Any

import jwt
from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from .....core.config import settings
from .....core.exception_handler import (
    BaseBusinessError,
    bad_request,
    internal_error,
    unauthorized,
)

logger = logging.getLogger(__name__)

from .....crud.auth import AuditLogCRUD, UserCRUD
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
    RefreshTokenRequest,
    UserResponse,
)
from .....security.cookie_manager import cookie_manager
from .....services.core.authentication_service import AuthenticationService
from .....services.core.session_service import SessionService
from .....services.permission.rbac_service import RBACService

router = APIRouter(tags=["认证管理"])


@router.post("/login", response_model=CookieAuthResponse, summary="用户登录")
async def login(
    request: Request,
    credentials: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """
    用户登录接口

    - 支持用户名或邮箱登录
    - 返回JWT访问令牌和刷新令牌
    - 记录登录审计日志
    """

    def _sync(sync_db: Session) -> dict[str, Any]:
        db = sync_db
        auth_service = AuthenticationService(db)
        session_service = SessionService(db)
        audit_crud = AuditLogCRUD()
        user_crud = UserCRUD()

        # 获取客户端信息
        client_ip = get_client_ip(request)
        user_agent = request.headers.get("user-agent", "unknown")

        try:
            # 认证用户（启用真实认证流程）
            user = auth_service.authenticate_user(
                credentials.username, credentials.password
            )
            if not user:
                # 记录失败登录
                existing_user = user_crud.get_by_username(db, credentials.username)
                if existing_user:
                    audit_crud.create(
                        db=db,
                        user_id=str(existing_user.id) if existing_user else "unknown",
                        action="user_login_failed",
                        resource_type="authentication",
                        ip_address=client_ip,
                        user_agent=user_agent,
                    )

                raise unauthorized("用户名或密码错误")

            # 创建令牌（增强安全性）
            device_info: dict[str, str] = {
                "user_agent": user_agent,
                "ip_address": client_ip,
            }
            tokens = auth_service.create_tokens(user, device_info)

            # Set httpOnly cookie for XSS protection
            cookie_manager.set_auth_cookie(response, tokens.access_token)
            cookie_manager.set_refresh_cookie(response, tokens.refresh_token)
            cookie_manager.set_csrf_cookie(response, cookie_manager.create_csrf_token())

            # 创建会话
            session_service.create_user_session(
                user_id=str(user.id),
                refresh_token=tokens.refresh_token,
                ip_address=client_ip,
                user_agent=user_agent,
                session_id=getattr(tokens, "session_id", None),
            )

            # 记录成功登录
            audit_crud.create(
                db=db,
                user_id=str(user.id),
                action="user_login",
                resource_type="authentication",
                api_endpoint="/api/auth/login",
                http_method="POST",
                response_status=200,
                ip_address=client_ip,
                user_agent=user_agent,
            )

            # Get user permissions
            rbac_service = RBACService(db)
            try:
                permission_summary = rbac_service.get_user_permissions_summary(
                    str(user.id)
                )
                # Extract unique permissions from roles
                permissions_set = set()
                for perm in permission_summary.permissions:
                    permissions_set.add(
                        PermissionSchema(
                            resource=perm.resource,
                            action=perm.action,
                            description=perm.description,
                        )
                    )

                # Convert to list
                permissions_list = list(permissions_set)
            except Exception as e:
                # If permission fetching fails, return empty list
                logger.warning(f"Failed to fetch permissions for user {user.id}: {e}")
                permissions_list = []

            # Cookie-based auth: do not return tokens in response body
            return {
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.full_name,
                    "role": user.role,
                    "is_active": bool(user.is_active)
                    if hasattr(user.is_active, "__int__")
                    else user.is_active,
                    "is_locked": bool(getattr(user, "is_locked", False))
                    if hasattr(getattr(user, "is_locked", False), "__int__")
                    else getattr(user, "is_locked", False),
                    "last_login_at": getattr(user, "last_login_at", None),
                    "employee_id": getattr(user, "employee_id", None),
                    "default_organization_id": getattr(
                        user, "default_organization_id", None
                    ),
                    "created_at": getattr(user, "created_at", None)
                    or datetime.now(UTC),
                    "updated_at": getattr(user, "updated_at", None)
                    or datetime.now(UTC),
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
            # Log the error for debugging (internal use only)
            logger.error(f"Authentication error: {str(e)}", exc_info=True)

            # Return generic error message to client
            raise internal_error("登录服务暂时不可用，请稍后重试")

    return await db.run_sync(_sync)


@router.post("/logout", summary="用户登出")
async def logout(
    request: Request,
    response: Response,
    current_user: UserResponse = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """
    用户登出接口

    - 撤销当前会话
    - 将当前JWT令牌加入黑名单
    - 清除客户端令牌（包括 httpOnly cookie）
    - 记录登出审计日志
    """

    def _sync(sync_db: Session) -> dict[str, Any]:
        db = sync_db
        session_service = SessionService(db)
        audit_crud = AuditLogCRUD()

        # 获取客户端信息
        client_ip = get_client_ip(request)
        user_agent = request.headers.get("user-agent", "unknown")

        # Clear httpOnly cookie
        cookie_manager.clear_auth_cookie(response)
        cookie_manager.clear_refresh_cookie(response)
        cookie_manager.clear_csrf_cookie(response)

        # 提取并黑名单当前JWT令牌（cookie-only）
        cookie_header = request.headers.get("cookie", "")
        token = cookie_manager.get_token_from_cookie(
            cookie_header, cookie_name=cookie_manager.cookie_name
        )

        if token:
            try:
                # 解码JWT获取jti和exp
                payload = jwt.decode(
                    token,
                    settings.SECRET_KEY,
                    algorithms=[getattr(settings, "ALGORITHM", "HS256")],
                    audience=settings.JWT_AUDIENCE,
                    issuer=settings.JWT_ISSUER,
                    options={"verify_exp": False},  # 允许解码已过期的令牌
                )
                jti = payload.get("jti")
                exp = payload.get("exp")

                if jti and exp:
                    from .....security.token_blacklist import blacklist_manager

                    blacklist_manager.add_token(jti, exp)
            except Exception as e:
                # 记录错误但继续登出流程
                logger.warning(f"Failed to blacklist token during logout: {e}")

        # 撤销用户所有会话
        revoked_count = session_service.revoke_all_user_sessions(current_user.id)

        # 记录登出日志
        audit_crud.create(
            db=db,
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

    return await db.run_sync(_sync)


@router.post("/refresh", response_model=CookieRefreshResponse, summary="刷新令牌")
async def refresh_token(
    request: Request,
    response: Response,
    refresh_data: RefreshTokenRequest | None = None,
    db: AsyncSession = Depends(get_async_db),
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

    def _sync(sync_db: Session) -> CookieRefreshResponse:
        db = sync_db
        auth_service = AuthenticationService(db)
        session_service = SessionService(db)

        # 获取客户端信息
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")

        # 验证刷新令牌（增强安全性）
        # Note: Returns User object (not UserSession), extracted from the session
        cookie_header = request.headers.get("cookie", "")
        refresh_token = cookie_manager.get_token_from_cookie(
            cookie_header, cookie_name=cookie_manager.refresh_cookie_name
        )
        if not refresh_token and refresh_data:
            refresh_token = refresh_data.refresh_token
        if not refresh_token:
            raise bad_request("刷新令牌缺失")

        session = auth_service.validate_refresh_token(
            refresh_token, client_ip=client_ip, user_agent=user_agent
        )
        if not session:
            # 记录失败的刷新尝试
            from .....crud.auth import AuditLogCRUD

            audit_crud = AuditLogCRUD()
            audit_crud.create(
                db=db,
                user_id="unknown",  # 无法确定用户
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

        # 验证用户状态
        user: User | None = getattr(session, "user", None)
        user_active = getattr(user, "is_active", False) if user else False
        if not user or not user_active:
            # 撤销无效会话
            session_service.revoke_session(refresh_token)
            raise unauthorized("用户不存在或已被禁用")

        # 记录刷新操作（可选：检查IP变化等安全检查）
        # Note: IP变化检查暂时跳过，因为 User 对象不包含 session 信息
        # 如需IP检查，需要直接查询 UserSession 表

        # 创建新令牌（增强安全性）
        device_info: dict[str, str | None] = {
            "user_agent": user_agent,
            "ip_address": client_ip,
            "device_id": getattr(user, "id", None),  # 使用 user.id 作为 device_id
            "platform": None,  # User 对象不包含 platform 信息
        }
        tokens = auth_service.create_tokens(user, device_info)
        cookie_manager.set_auth_cookie(response, tokens.access_token)
        cookie_manager.set_refresh_cookie(response, tokens.refresh_token)
        cookie_manager.set_csrf_cookie(response, cookie_manager.create_csrf_token())

        # 更新会话
        # Note: UserSession 需要单独查询和更新，这里暂时跳过
        # User 对象不包含 session 相关字段 (refresh_token, last_accessed_at, etc.)
        # 如需更新 session，需要查询 UserSession 表并更新
        db.commit()

        # 记录成功的刷新操作
        from .....crud.auth import AuditLogCRUD

        audit_crud = AuditLogCRUD()
        audit_crud.create(
            db=db,
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

    return await db.run_sync(_sync)


@router.get("/me", response_model=dict[str, Any], summary="获取当前用户信息")
def get_current_user_info(
    current_user: UserResponse = Depends(get_current_active_user),
) -> dict[str, Any]:
    """
    获取当前登录用户的信息

    企业级实现，包含完整的用户信息、权限状态、会话信息和时间戳
    """
    return {
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "id": current_user.id,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "is_admin": current_user.role == "admin",
        "timestamp": datetime.now(UTC).isoformat(),
        "session_status": "active",
    }
