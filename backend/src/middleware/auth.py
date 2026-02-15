"""
认证中间件
"""

import logging
from typing import Any

import jwt
from fastapi import Cookie, Depends, Request
from jwt import PyJWTError as JWTError
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.environment import is_production
from ..core.exception_handler import bad_request, forbidden, unauthorized
from ..crud.auth import AuditLogCRUD
from ..database import get_async_db
from ..models.auth import User
from ..schemas.auth import TokenData
from ..schemas.rbac import PermissionCheckRequest
from ..security.cookie_manager import cookie_manager
from ..services import RBACService
from ..services.permission.rbac_service import (
    ADMIN_PERMISSION_ACTION,
    ADMIN_PERMISSION_RESOURCE,
)
from .token_blacklist_guard import TokenBlacklistGuard

logger = logging.getLogger(__name__)


_token_blacklist_guard = TokenBlacklistGuard(is_production=lambda: is_production())
_token_blacklist_circuit = _token_blacklist_guard.circuit


def _is_token_blacklisted(
    jti: str | None, user_id: str | None = None, session_id: str | None = None
) -> bool:
    """检查 token 是否在黑名单中（熔断/异常统一 fail-closed）。"""
    return _token_blacklist_guard.is_token_blacklisted(
        jti=jti,
        user_id=user_id,
        session_id=session_id,
    )


def _get_jwt_settings() -> tuple[str, str, str, str]:
    return (
        settings.SECRET_KEY,
        getattr(settings, "ALGORITHM", "HS256"),
        settings.JWT_AUDIENCE,
        settings.JWT_ISSUER,
    )


def _validate_jwt_token(token: str) -> TokenData:
    """
    共享的JWT验证逻辑

    Args:
        token: JWT token string

    Returns:
        TokenData: 解析并验证后的token数据

    Raises:
        HTTPException: 如果token无效或验证失败
    """
    credentials_exception = unauthorized("无效的认证凭据")

    try:
        secret_key, algorithm, audience, issuer = _get_jwt_settings()
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[algorithm],
            audience=audience,
            issuer=issuer,
        )

        user_id: str | None = payload.get("sub")
        username: str | None = payload.get("username")
        exp: int | None = payload.get("exp")
        iat: int | None = payload.get("iat")
        jti: str | None = payload.get("jti")  # JWT ID for token tracking

        # 验证必需字段
        if user_id is None or username is None:
            logger.warning(
                f"JWT token missing required fields: sub={user_id}, username={username}"
            )
            raise credentials_exception

        # 验证过期时间（虽然jwt.decode已经验证，但双重检查更安全）
        if exp is None:
            logger.warning("JWT token missing expiration time")
            raise credentials_exception

        # 验证签发时间
        if iat is None:
            logger.warning("JWT token missing issued at time")
            raise credentials_exception

        # 验证token是否在黑名单中（如果实现了token黑名单）
        if _is_token_blacklisted(jti=jti, user_id=user_id, session_id=None):
            logger.warning(f"JWT token {jti} is blacklisted")
            raise unauthorized("Token已失效")

        # 使用标准的TokenData Pydantic模型
        try:
            token_data = TokenData(
                sub=user_id,
                username=username,
                exp=payload.get("exp") if payload else None,
            )
        except Exception as e:
            # 如果TokenData验证失败，记录错误并抛出认证异常
            logger.error(f"TokenData validation failed: {e}")
            raise credentials_exception

    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        raise credentials_exception
    except Exception as e:
        logger.exception("Unexpected JWT validation error: %s", e)
        raise credentials_exception

    return token_data


async def get_current_user(
    auth_token: str | None = Cookie(None, alias=cookie_manager.cookie_name),
    db: AsyncSession = Depends(get_async_db),
) -> User:
    """
    Get current authenticated user from JWT token.

    Cookie-only authentication. Tokens are read from httpOnly cookies.
    """
    credentials_exception = unauthorized("无效的认证凭据")

    token = auth_token
    if token:
        logger.debug("Authenticating using httpOnly cookie")

    # No token found in cookie
    if not token:
        raise credentials_exception

    # 使用共享的JWT验证逻辑
    try:
        token_data = _validate_jwt_token(token)
    except Exception:
        raise credentials_exception

    # Get user from database
    user_stmt = select(User).where(User.id == token_data.sub)
    user = (await db.execute(user_stmt)).scalars().first()
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise unauthorized("用户账户已被禁用")

    if user.is_locked_now():
        raise unauthorized("用户账户已被锁定，请稍后再试")

    logger.debug(f"Successfully authenticated user {user.username}")
    return user


async def get_current_user_from_cookie(
    auth_token: str | None = Cookie(None, alias=cookie_manager.cookie_name),
    db: AsyncSession = Depends(get_async_db),
) -> User:
    """
    Get current user from httpOnly cookie.

    Args:
        auth_token: JWT from httpOnly cookie (automatically sent by browser)
        db: Database session

    Returns:
        User: Authenticated user object

    Raises:
        unauthorized: If no valid token found or user is inactive/locked
    """
    token = auth_token
    if token:
        logger.debug("Authenticating using httpOnly cookie")

    # No token found in either cookie or header
    if not token:
        raise unauthorized("Not authenticated")

    # 使用共享的JWT验证逻辑
    try:
        token_data = _validate_jwt_token(token)
    except Exception:
        raise unauthorized("Invalid token")

    # Get user from database
    user_stmt = select(User).where(User.id == token_data.sub)
    user = (await db.execute(user_stmt)).scalars().first()
    if user is None:
        raise unauthorized("Invalid authentication credentials")

    # Check if user is active
    if not user.is_active:
        raise unauthorized("User account is disabled")

    # Check if user is locked
    if user.is_locked_now():
        raise unauthorized("User account is locked, please try again later")

    logger.debug(
        f"Successfully authenticated user {user.username} via cookie-based auth"
    )
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """获取当前活跃用户"""
    if not current_user.is_active:
        raise bad_request("用户账户未激活")
    return current_user


async def require_admin(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> User:
    """要求管理员权限"""
    rbac_service = RBACService(db)
    if not await rbac_service.is_admin(current_user.id):
        raise forbidden("需要管理员权限")
    return current_user


async def get_optional_current_user(
    auth_token: str | None = Cookie(None, alias=cookie_manager.cookie_name),
    db: AsyncSession = Depends(get_async_db),
) -> User | None:
    """获取可选的当前用户（用于可选认证的端点）"""
    resolved_token = auth_token

    if not resolved_token:
        return None

    try:
        token_data = _validate_jwt_token(resolved_token)
    except Exception:
        return None

    user_stmt = select(User).where(User.id == token_data.sub)
    user = (await db.execute(user_stmt)).scalars().first()
    if user and user.is_active and not user.is_locked_now():
        return user

    return None


class PermissionChecker:
    """权限检查器"""

    def __init__(self, required_permissions: list[str]):
        self.required_permissions = required_permissions

    async def __call__(
        self,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_async_db),
    ) -> User:
        """检查用户权限"""
        if not await self._has_permission(current_user, db):
            raise forbidden("权限不足")
        return current_user

    async def _has_permission(self, user: User, db: AsyncSession) -> bool:
        """检查用户是否有所需权限"""
        rbac_service = RBACService(db)
        for permission_code in self.required_permissions:
            if ":" in permission_code:
                resource, action = permission_code.split(":", 1)
            else:
                resource, action = "system", permission_code
            if (
                resource == ADMIN_PERMISSION_RESOURCE
                and action == ADMIN_PERMISSION_ACTION
            ):
                if await rbac_service.is_admin(user.id):
                    return True
                continue
            if await rbac_service.check_user_permission(user.id, resource, action):
                return True
        return False


def require_permissions(required_permissions: list[str]) -> PermissionChecker:
    """权限装饰器工厂函数"""
    return PermissionChecker(required_permissions)


class OrganizationPermissionChecker:
    """组织权限检查器"""

    def __init__(self, organization_id: str | None = None):
        self.organization_id = organization_id

    async def __call__(
        self,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_async_db),
    ) -> User:
        """检查用户是否有访问指定组织的权限"""
        if not await self._can_access_organization(current_user, db):
            raise forbidden("无权访问该组织的数据")
        return current_user

    async def _can_access_organization(self, user: User, db: AsyncSession) -> bool:
        """检查用户是否可以访问组织"""
        rbac_service = RBACService(db)
        if await rbac_service.is_admin(user.id):
            return True

        # 用户可以访问自己的默认组织
        if user.default_organization_id == self.organization_id:
            return True

        # 当未指定目标组织时，默认组织视为其组织访问范围
        if self.organization_id is None:
            return user.default_organization_id is not None

        return False


def require_organization_access(
    organization_id: str | None = None,
) -> OrganizationPermissionChecker:
    """组织权限装饰器工厂函数"""
    return OrganizationPermissionChecker(organization_id)


class AuditLogger:
    """审计日志记录器"""

    def __init__(self, action: str, resource_type: str | None = None):
        self.action = action
        self.resource_type = resource_type

    async def __call__(
        self,
        request: Request,
        current_user: User | None = Depends(get_optional_current_user),
        db: AsyncSession = Depends(get_async_db),
    ) -> User | None:
        """记录审计日志"""
        if not current_user:
            return current_user

        try:
            from ..middleware.security_middleware import get_client_ip

            ip_address = get_client_ip(request)
            user_agent = request.headers.get("user-agent", "")
            request_params = str(request.query_params) if request.query_params else None

            await self.log_action(
                db=db,
                user=current_user,
                api_endpoint=request.url.path,
                http_method=request.method,
                request_params=request_params,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        except Exception as e:
            logger.warning(f"审计日志记录失败: {e}")
        return current_user

    async def log_action(
        self,
        db: AsyncSession,
        user: User,
        resource_id: str | None = None,
        resource_name: str | None = None,
        api_endpoint: str | None = None,
        http_method: str | None = None,
        request_params: str | None = None,
        request_body: str | None = None,
        response_status: int | None = None,
        response_message: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        session_id: str | None = None,
    ) -> None:
        audit_crud = AuditLogCRUD()
        await audit_crud.create_async(
            db=db,
            user_id=user.id,
            action=self.action,
            resource_type=self.resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            api_endpoint=api_endpoint,
            http_method=http_method,
            request_params=request_params,
            request_body=request_body,
            response_status=response_status,
            response_message=response_message,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id,
        )


def audit_action(action: str, resource_type: str | None = None) -> AuditLogger:
    """审计装饰器工厂函数"""
    return AuditLogger(action, resource_type)


# 安全配置
class SecurityConfig:
    """安全配置"""

    # 密码策略
    MIN_PASSWORD_LENGTH = settings.MIN_PASSWORD_LENGTH
    MAX_FAILED_ATTEMPTS = settings.MAX_FAILED_ATTEMPTS
    LOCKOUT_DURATION_MINUTES = settings.LOCKOUT_DURATION

    # JWT配置
    ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
    REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS

    # 会话配置
    MAX_CONCURRENT_SESSIONS = settings.MAX_CONCURRENT_SESSIONS
    SESSION_EXPIRE_DAYS = settings.SESSION_EXPIRE_DAYS

    # 审计配置
    AUDIT_LOG_RETENTION_DAYS = settings.AUDIT_LOG_RETENTION_DAYS

    @classmethod
    def get_password_policy(cls) -> dict[str, Any]:
        """获取密码策略"""
        return {
            "min_length": cls.MIN_PASSWORD_LENGTH,
            "max_failed_attempts": cls.MAX_FAILED_ATTEMPTS,
            "lockout_duration_minutes": cls.LOCKOUT_DURATION_MINUTES,
            "require_uppercase": True,
            "require_lowercase": True,
            "require_digits": True,
            "require_special_chars": True,
        }

    @classmethod
    def get_token_config(cls) -> dict[str, Any]:
        """获取令牌配置"""
        return {
            "access_token_expire_minutes": cls.ACCESS_TOKEN_EXPIRE_MINUTES,
            "refresh_token_expire_days": cls.REFRESH_TOKEN_EXPIRE_DAYS,
            "algorithm": getattr(settings, "ALGORITHM", "HS256"),
            "max_concurrent_sessions": cls.MAX_CONCURRENT_SESSIONS,
            "session_expire_days": cls.SESSION_EXPIRE_DAYS,
        }


# ==================== RBAC权限检查器 ====================


class RBACPermissionChecker:
    """RBAC权限检查器"""

    def __init__(self, resource: str, action: str, resource_id: str | None = None):
        self.resource = resource
        self.action = action
        self.resource_id = resource_id

    async def __call__(
        self,
        current_user: User | None = Depends(get_current_user),
        db: AsyncSession = Depends(get_async_db),
    ) -> User | None:
        """检查用户权限"""

        # 如果没有用户（未认证），抛出认证异常
        if current_user is None:
            raise unauthorized("需要认证")

        rbac_service = RBACService(db)
        if await rbac_service.is_admin(current_user.id):
            return current_user

        # 使用RBAC服务检查权限
        permission_request = PermissionCheckRequest(
            resource=self.resource,
            action=self.action,
            resource_id=self.resource_id,
            context=None,
        )

        permission_result = await rbac_service.check_permission(
            current_user.id, permission_request
        )

        if not permission_result.has_permission:
            raise forbidden(f"权限不足，需要 {self.resource}:{self.action} 权限")

        return current_user


def require_permission(
    resource: str, action: str, resource_id: str | None = None
) -> RBACPermissionChecker:
    """RBAC权限装饰器工厂函数"""
    return RBACPermissionChecker(resource, action, resource_id)


class ResourcePermissionChecker:
    """资源权限检查器"""

    def __init__(self, resource_type: str, required_level: str = "read"):
        self.resource_type = resource_type
        self.required_level = required_level

    async def __call__(
        self,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_async_db),
        resource_id: str | None = None,
    ) -> User:
        """检查用户资源权限"""
        rbac_service = RBACService(db)
        if await rbac_service.is_admin(current_user.id):
            return current_user

        # 检查是否有对应的资源权限
        from ..models.rbac import ResourcePermission

        stmt = select(ResourcePermission).where(
            and_(
                ResourcePermission.user_id == current_user.id,
                ResourcePermission.resource_type == self.resource_type,
                ResourcePermission.resource_id == resource_id,
                ResourcePermission.is_active,
            )
        )
        resource_permission = (await db.execute(stmt)).scalars().first()

        if not resource_permission:
            raise forbidden(f"无权访问此{self.resource_type}资源")

        # 检查权限级别
        level_actions = {
            "read": ["read"],
            "write": ["read", "write"],
            "delete": ["read", "write", "delete"],
            "admin": ["read", "write", "delete", "admin"],
        }

        # 简化处理：假设当前操作对应required_level
        if self.required_level not in level_actions:
            raise forbidden(f"无效的权限级别: {self.required_level}")

        return current_user


def require_resource_permission(
    resource_type: str, required_level: str = "read"
) -> ResourcePermissionChecker:
    """资源权限装饰器工厂函数"""
    return ResourcePermissionChecker(resource_type, required_level)


class RoleBasedAccessChecker:
    """基于角色的访问检查器"""

    def __init__(self, required_roles: list[str]):
        self.required_roles = required_roles

    async def __call__(
        self,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_async_db),
    ) -> User:
        """检查用户角色"""
        rbac_service = RBACService(db)
        if await rbac_service.is_admin(current_user.id):
            return current_user

        # 获取用户角色
        user_roles = await rbac_service.get_user_roles(current_user.id)

        user_role_names = [role.name for role in user_roles]

        # 检查是否有所需角色
        if not any(role_name in self.required_roles for role_name in user_role_names):
            raise forbidden(f"需要以下角色之一: {', '.join(self.required_roles)}")

        return current_user


def require_roles(required_roles: list[str]) -> RoleBasedAccessChecker:
    """角色权限装饰器工厂函数"""
    return RoleBasedAccessChecker(required_roles)


async def can_edit_contract(user: User, db: AsyncSession, contract_id: str) -> bool:
    """
    检查用户是否可以编辑合同

    规则:
    - 管理员可以编辑任何合同
    - 其他角色需要通过RBAC服务检查特定权限
    """
    rbac_service = RBACService(db)
    if await rbac_service.is_admin(user.id):
        return True

    # 使用RBAC服务进行细粒度权限检查
    try:
        permission_request = PermissionCheckRequest(
            resource="rent_contract",
            action="edit",
            resource_id=contract_id,
            context=None,
        )

        result = await rbac_service.check_permission(user.id, permission_request)
        return bool(result.has_permission)
    except Exception:
        # 如果RBAC检查失败，默认拒绝权限（安全优先）
        return False


async def get_user_rbac_permissions(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """获取用户RBAC权限信息"""
    rbac_service = RBACService(db)
    permissions_summary = await rbac_service.get_user_permissions_summary(
        current_user.id
    )
    is_admin = await rbac_service.is_admin(current_user.id)

    return {
        "is_admin": is_admin,
        "roles": [role.name for role in permissions_summary.roles],
        "permissions": (
            ["all"]
            if is_admin
            else dict(permissions_summary.effective_permissions.items())
        ),
    }
