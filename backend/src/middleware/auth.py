"""
认证中间件
"""

import logging
import sys
from collections import deque
from time import time
from typing import Any

import jwt
from fastapi import Cookie, Depends, Request
from jwt import PyJWTError as JWTError
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from ..constants.security_constants import (
    TOKEN_BLACKLIST_DEGRADE_THRESHOLD,
    TOKEN_BLACKLIST_DEGRADE_WINDOW_SECONDS,
    TOKEN_BLACKLIST_ERROR_THRESHOLD,
    TOKEN_BLACKLIST_ERROR_WINDOW_SECONDS,
)
from ..core.circuit_breaker import CircuitBreaker
from ..core.config import settings
from ..core.environment import is_production
from ..core.exception_handler import bad_request, forbidden, unauthorized
from ..database import get_async_db
from ..models.auth import User, UserRole
from ..schemas.auth import TokenData
from ..schemas.rbac import PermissionCheckRequest
from ..security.cookie_manager import cookie_manager
from ..security.logging_security import security_monitor
from ..services import RBACService

logger = logging.getLogger(__name__)


_token_blacklist_degrade_events: deque[float] = deque(maxlen=100)
_token_blacklist_error_events: deque[float] = deque(maxlen=100)
_last_degrade_alert_ts = 0.0
_last_error_alert_ts = 0.0


def _trim_recent_events(events: deque[float], window_seconds: int, now: float) -> int:
    while events and now - events[0] > window_seconds:
        events.popleft()
    return len(events)


def _record_token_blacklist_degraded(
    reason: str, jti: str | None, user_id: str | None
) -> None:
    global _last_degrade_alert_ts
    now = time()
    _token_blacklist_degrade_events.append(now)
    recent = _trim_recent_events(
        _token_blacklist_degrade_events, TOKEN_BLACKLIST_DEGRADE_WINDOW_SECONDS, now
    )

    security_monitor.record_metric("token_blacklist.degraded", 1)
    security_monitor.record_event(
        "token_blacklist_degraded",
        reason=reason,
        jti=jti,
        user_id=user_id,
        recent_count=recent,
        window_seconds=TOKEN_BLACKLIST_DEGRADE_WINDOW_SECONDS,
    )
    if is_production():
        security_monitor.record_audit(
            "token_blacklist_degraded",
            reason=reason,
            jti=jti,
            user_id=user_id,
        )

    if (
        recent >= TOKEN_BLACKLIST_DEGRADE_THRESHOLD
        and now - _last_degrade_alert_ts >= TOKEN_BLACKLIST_DEGRADE_WINDOW_SECONDS
    ):
        _last_degrade_alert_ts = now
        logger.warning("Token blacklist degraded frequently in the last window.")
        security_monitor.record_event(
            "token_blacklist_degraded_frequent",
            count=recent,
            window_seconds=TOKEN_BLACKLIST_DEGRADE_WINDOW_SECONDS,
        )


def _record_token_blacklist_error(
    error: Exception, jti: str | None, user_id: str | None
) -> None:
    global _last_error_alert_ts
    now = time()
    _token_blacklist_error_events.append(now)
    recent = _trim_recent_events(
        _token_blacklist_error_events, TOKEN_BLACKLIST_ERROR_WINDOW_SECONDS, now
    )

    security_monitor.record_metric("token_blacklist.error", 1)
    security_monitor.record_event(
        "token_blacklist_error",
        error=str(error),
        jti=jti,
        user_id=user_id,
        recent_count=recent,
        window_seconds=TOKEN_BLACKLIST_ERROR_WINDOW_SECONDS,
    )

    if (
        recent >= TOKEN_BLACKLIST_ERROR_THRESHOLD
        and now - _last_error_alert_ts >= TOKEN_BLACKLIST_ERROR_WINDOW_SECONDS
    ):
        _last_error_alert_ts = now
        logger.warning("Token blacklist errors are frequent in the last window.")
        security_monitor.record_event(
            "token_blacklist_error_frequent",
            count=recent,
            window_seconds=TOKEN_BLACKLIST_ERROR_WINDOW_SECONDS,
        )


def _is_token_blacklisted(
    jti: str | None, user_id: str | None = None, session_id: str | None = None
) -> bool:
    """
    检查token是否在黑名单中
    未来可以扩展为Redis缓存或数据库表
    """
    if not settings.TOKEN_BLACKLIST_ENABLED:
        return False

    if jti is None and user_id is None and session_id is None:
        return False

    if not _token_blacklist_circuit.allow_request():
        logger.error(
            "Token blacklist check degraded. Enforcing fail-closed in production."
        )
        _record_token_blacklist_degraded("circuit_open", jti, user_id)
        return is_production()

    try:
        from ..security.token_blacklist import blacklist_manager

        result = blacklist_manager.is_blacklisted(jti=jti, user_id=user_id)
        _token_blacklist_circuit.record_success()
        return result
    except ImportError:
        logger.debug(f"Token blacklist not implemented, allowing token {jti}")
        _record_token_blacklist_degraded("not_implemented", jti, user_id)
        _token_blacklist_circuit.record_success()
        return False
    except Exception as e:
        _token_blacklist_circuit.record_failure()
        logger.warning(f"Error checking token blacklist: {e}")
        _record_token_blacklist_error(e, jti, user_id)
        return is_production()


_token_blacklist_circuit = CircuitBreaker(max_failures=5, cooldown=60)


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
        role: str | None = payload.get("role")
        exp: int | None = payload.get("exp")
        iat: int | None = payload.get("iat")
        jti: str | None = payload.get("jti")  # JWT ID for token tracking

        # 验证必需字段
        if user_id is None or username is None or role is None:
            logger.warning(
                f"JWT token missing required fields: sub={user_id}, username={username}, role={role}"
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

        # Handle both string and enum role types
        role_enum = role
        if isinstance(role, str):
            try:
                role_enum = UserRole(role)
            except ValueError:
                logger.warning(f"Invalid role value '{role}', defaulting to USER")
                role_enum = UserRole.USER  # Default fallback
        elif isinstance(role, UserRole):
            # Already an enum, use as-is
            pass
        else:
            # Unknown type, default to USER
            logger.warning(
                f"Unknown role type '{type(role)}' with value '{role}', defaulting to USER"
            )
            role_enum = UserRole.USER

        # 使用标准的TokenData Pydantic模型
        try:
            token_data = TokenData(
                sub=user_id,
                username=username,
                role=role_enum,
                exp=payload.get("exp") if payload else None,
            )
        except Exception as e:
            # 如果TokenData验证失败，记录错误并抛出认证异常
            logger.error(f"TokenData validation failed: {e}")
            raise credentials_exception

    except JWTError as e:
        sys.stderr.write(f"DEBUG: [_validate_jwt_token] JWTError: {e}\n")
        logger.warning(f"JWT decode error: {e}")
        raise credentials_exception
    except Exception as e:
        sys.stderr.write(f"DEBUG: [_validate_jwt_token] Unexpected error: {e}\n")
        raise credentials_exception

    return token_data


def safe_role_compare(role_value: Any, target_role: Any) -> bool:
    """安全地比较角色值，支持字符串和枚举类型"""
    if isinstance(role_value, str):
        return bool(role_value == target_role.value)
    return bool(role_value == target_role)


async def get_current_user(
    request: Request,
    auth_token: str | None = Cookie(None, alias=cookie_manager.cookie_name),
    db: AsyncSession = Depends(get_async_db),
) -> User:
    """
    Get current authenticated user from JWT token.

    Cookie-only authentication. Tokens are read from httpOnly cookies.
    Also supports Authorization header for API access/testing.
    """
    credentials_exception = unauthorized("无效的认证凭据")

    token = auth_token
    if token:
        logger.debug("Authenticating using httpOnly cookie")

    # No token found in cookie, try header
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            logger.debug("Authenticating using Authorization header")

    # No token found in either cookie or header
    if not token:
        raise credentials_exception

    # 使用共享的JWT验证逻辑
    try:
        token_data = _validate_jwt_token(token)
    except Exception:
        raise credentials_exception

    # Get user from database
    user = await db.run_sync(
        lambda sync_db: sync_db.query(User).filter(User.id == token_data.sub).first()
    )
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
    user = await db.run_sync(
        lambda sync_db: sync_db.query(User).filter(User.id == token_data.sub).first()
    )
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


def require_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """要求管理员权限"""
    if not safe_role_compare(current_user.role, UserRole.ADMIN):
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

    user = await db.run_sync(
        lambda sync_db: sync_db.query(User).filter(User.id == token_data.sub).first()
    )
    if user and user.is_active and not user.is_locked_now():
        return user

    return None


class PermissionChecker:
    """权限检查器"""

    def __init__(self, required_permissions: list[str]):
        self.required_permissions = required_permissions

    def __call__(self, current_user: User = Depends(get_current_active_user)) -> User:
        """检查用户权限"""
        if not self._has_permission(current_user):
            raise forbidden("权限不足")
        return current_user

    def _has_permission(self, user: User) -> bool:
        """检查用户是否有所需权限"""
        # 管理员拥有所有权限
        if safe_role_compare(user.role, UserRole.ADMIN):
            return True

        # 这里可以扩展为更复杂的权限检查逻辑
        # 例如：检查用户角色对应的权限列表
        user_permissions = self._get_user_permissions(user)
        return any(perm in user_permissions for perm in self.required_permissions)

    def _get_user_permissions(self, user: User) -> list[str]:
        """获取用户权限列表"""
        # 这里可以根据用户角色返回对应的权限列表
        # 目前简化处理，管理员以外的用户只有基础权限
        if user.role == UserRole.USER:
            return ["read", "profile"]
        return []


def require_permissions(required_permissions: list[str]) -> PermissionChecker:
    """权限装饰器工厂函数"""
    return PermissionChecker(required_permissions)


class OrganizationPermissionChecker:
    """组织权限检查器"""

    def __init__(self, organization_id: str | None = None):
        self.organization_id = organization_id

    def __call__(self, current_user: User = Depends(get_current_active_user)) -> User:
        """检查用户是否有访问指定组织的权限"""
        if not self._can_access_organization(current_user):
            raise forbidden("无权访问该组织的数据")
        return current_user

    def _can_access_organization(self, user: User) -> bool:
        """检查用户是否可以访问组织"""
        # 管理员可以访问所有组织
        if safe_role_compare(user.role, UserRole.ADMIN):
            return True

        # 用户可以访问自己的默认组织
        if user.default_organization_id == self.organization_id:
            return True

        # 用户可以访问自己所属员工对应的组织
        # 这里需要查询Employee表，暂时简化处理
        return bool(user.employee_id)


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

            await db.run_sync(
                lambda sync_db: self.log_action(
                    db=sync_db,
                    user=current_user,
                    api_endpoint=request.url.path,
                    http_method=request.method,
                    request_params=request_params,
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
            )
        except Exception as e:
            logger.warning(f"审计日志记录失败: {e}")
        return current_user

    def log_action(
        self,
        db: Session,
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
        """记录操作日志"""
        from ..crud.auth import AuditLogCRUD

        audit_crud = AuditLogCRUD()
        audit_crud.create(
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

        # 管理员拥有所有权限
        if safe_role_compare(current_user.role, UserRole.ADMIN):
            return current_user

        # 使用RBAC服务检查权限
        rbac_service = RBACService(db)
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
        # 管理员拥有所有权限
        if safe_role_compare(current_user.role, UserRole.ADMIN):
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
        # 管理员拥有所有权限
        if safe_role_compare(current_user.role, UserRole.ADMIN):
            return current_user

        # 获取用户角色
        rbac_service = RBACService(db)
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
    if safe_role_compare(user.role, UserRole.ADMIN):
        return True

    # 使用RBAC服务进行细粒度权限检查
    try:
        rbac_service = RBACService(db)
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
    if current_user.role == UserRole.ADMIN:
        return {"is_admin": True, "roles": ["admin"], "permissions": ["all"]}

    rbac_service = RBACService(db)
    permissions_summary = await rbac_service.get_user_permissions_summary(
        current_user.id
    )

    return {
        "is_admin": False,
        "roles": [role.name for role in permissions_summary.roles],
        "permissions": dict(permissions_summary.effective_permissions.items()),
    }
