from typing import Any

"""
认证中间件
"""

import logging

from fastapi import Cookie, Depends, Header
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import and_
from sqlalchemy.orm import Session

from ..core.exception_handler import bad_request, forbidden, unauthorized
from ..core.config import settings
from ..core.cookie_auth import cookie_manager
from ..database import get_db
from ..models.auth import User, UserRole
from ..schemas.auth import TokenData
from ..schemas.rbac import PermissionCheckRequest
from ..services import RBACService

logger = logging.getLogger(__name__)


# OAuth2密码流 - 始终启用安全性
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def _is_token_blacklisted(jti: str) -> bool:
    """
    检查token是否在黑名单中
    未来可以扩展为Redis缓存或数据库表
    """
    try:
        # 尝试从token黑名单模块导入
        from ..core.token_blacklist import blacklist_manager

        return blacklist_manager.is_blacklisted(jti)
    except ImportError:
        # 如果没有实现token黑名单，返回False
        logger.debug(f"Token blacklist not implemented, allowing token {jti}")
        return False
    except Exception as e:
        logger.error(f"Error checking token blacklist: {e}")
        # 安全优先：出错时视为token在黑名单中，拒绝访问（fail-closed策略）
        return True


# JWT配置
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"


def safe_role_compare(role_value: Any, target_role: Any) -> bool:
    """安全地比较角色值，支持字符串和枚举类型"""
    if isinstance(role_value, str):
        return role_value == target_role.value  # type: ignore[no-any-return]
    return role_value == target_role  # type: ignore[no-any-return]


def get_current_user(
    auth_token: str | None = Cookie(None, alias=cookie_manager.cookie_name),
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
) -> User:
    """
    Get current authenticated user from JWT token.

    Authentication priority:
    1. httpOnly cookie (primary method for XSS protection)
    2. Authorization header (fallback for backward compatibility)

    This unified approach ensures ALL protected endpoints automatically
    support both cookie and Bearer token authentication.
    """

    credentials_exception = unauthorized("无效的认证凭据")

    # Try cookie first (primary method for XSS protection)
    token = None
    if auth_token:
        token = auth_token
        logger.debug("Authenticating using httpOnly cookie")
    elif authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        logger.debug("Authenticating using Authorization header (fallback)")

    # No token found in either cookie or header
    if not token:
        raise credentials_exception

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            audience="land-property-system",
            issuer="land-property-auth",
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
        if jti and _is_token_blacklisted(jti):
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
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == token_data.sub).first()
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise unauthorized("用户账户已被禁用")

    if user.is_locked_now():
        raise unauthorized("用户账户已被锁定，请稍后再试")

    logger.debug(f"Successfully authenticated user {user.username}")
    return user


def get_current_user_from_cookie(
    auth_token: str | None = Cookie(None, alias=cookie_manager.cookie_name),
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
) -> User:
    """
    Get current user from httpOnly cookie or Authorization header (fallback)

    This function implements cookie-first authentication with Bearer token fallback:
    1. First tries to read JWT from httpOnly cookie (primary method for XSS protection)
    2. Falls back to Authorization header (for backward compatibility)
    3. Validates the JWT token
    4. Returns the User object

    Args:
        auth_token: JWT from httpOnly cookie (automatically sent by browser)
        authorization: Bearer token from Authorization header (fallback)
        db: Database session

    Returns:
        User: Authenticated user object

    Raises:
        unauthorized: If no valid token found or user is inactive/locked
    """

    # Try cookie first (primary method for XSS protection)
    token = None
    if auth_token:
        token = auth_token
        logger.debug("Authenticating using httpOnly cookie")
    elif authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        logger.debug("Authenticating using Authorization header (fallback)")

    # No token found in either cookie or header
    if not token:
        raise unauthorized("Not authenticated")

    # Validate token using the same logic as get_current_user()
    credentials_exception = unauthorized("Invalid authentication credentials")

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            audience="land-property-system",
            issuer="land-property-auth",
        )
        user_id: str | None = payload.get("sub")
        username: str | None = payload.get("username")
        role: str | None = payload.get("role")
        exp: int | None = payload.get("exp")
        iat: int | None = payload.get("iat")
        jti: str | None = payload.get("jti")  # JWT ID for token tracking

        # Validate required fields
        if user_id is None or username is None or role is None:
            logger.warning(
                f"JWT token missing required fields: sub={user_id}, username={username}, role={role}"
            )
            raise credentials_exception

        # Validate expiration
        if exp is None:
            logger.warning("JWT token missing expiration time")
            raise credentials_exception

        # Validate issued at time
        if iat is None:
            logger.warning("JWT token missing issued at time")
            raise credentials_exception

        # Check if token is blacklisted
        if jti and _is_token_blacklisted(jti):
            logger.warning(f"JWT token {jti} is blacklisted")
            raise unauthorized("Token has been revoked")

        # Handle role conversion (string to enum)
        role_enum = role
        if isinstance(role, str):
            try:
                role_enum = UserRole(role)
            except ValueError:
                logger.warning(f"Invalid role value '{role}', defaulting to USER")
                role_enum = UserRole.USER
        elif isinstance(role, UserRole):
            # Already an enum, use as-is
            pass
        else:
            # Unknown type, default to USER
            logger.warning(
                f"Unknown role type '{type(role)}' with value '{role}', defaulting to USER"
            )
            role_enum = UserRole.USER

        # Create TokenData for validation
        try:
            token_data = TokenData(
                sub=user_id,
                username=username,
                role=role_enum,
                exp=payload.get("exp") if payload else None,
            )
        except Exception as e:
            logger.error(f"TokenData validation failed: {e}")
            raise credentials_exception
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        raise credentials_exception

    # Get user from database
    user = db.query(User).filter(User.id == token_data.sub).first()
    if user is None:
        raise credentials_exception

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


def get_optional_current_user(
    token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User | None:
    """获取可选的当前用户（用于可选认证的端点）"""
    if not token:
        return None

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            audience="land-property-system",
            issuer="land-property-auth",
        )
        user_id: str | None = payload.get("sub")

        if user_id is None:
            return None

        user = db.query(User).filter(User.id == user_id).first()
        if user and user.is_active and not user.is_locked_now():
            return user
    except JWTError:
        pass

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

    def __call__(
        self, current_user: User | None = Depends(get_optional_current_user)
    ) -> User | None:
        """记录审计日志"""
        # 这个装饰器不阻止操作，只是记录日志
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
            "algorithm": ALGORITHM,
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

    def __call__(
        self,
        current_user: User | None = Depends(get_current_user),
        db: Session = Depends(get_db),
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

        permission_result = rbac_service.check_permission(
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

    def __call__(
        self,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db),
        resource_id: str | None = None,
    ) -> User:
        """检查用户资源权限"""
        # 管理员拥有所有权限
        if safe_role_compare(current_user.role, UserRole.ADMIN):
            return current_user

        # 检查是否有对应的资源权限
        from ..models.rbac import ResourcePermission

        resource_permission = (
            db.query(ResourcePermission)
            .filter(
                and_(
                    ResourcePermission.user_id == current_user.id,
                    ResourcePermission.resource_type == self.resource_type,
                    ResourcePermission.resource_id == resource_id,
                    ResourcePermission.is_active,
                )
            )
            .first()
        )

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

    def __call__(
        self,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db),
    ) -> User:
        """检查用户角色"""
        # 管理员拥有所有权限
        if safe_role_compare(current_user.role, UserRole.ADMIN):
            return current_user

        # 获取用户角色
        rbac_service = RBACService(db)
        user_roles = rbac_service.get_user_roles(current_user.id)

        user_role_names = [role.name for role in user_roles]

        # 检查是否有所需角色
        if not any(role_name in self.required_roles for role_name in user_role_names):
            raise forbidden(f"需要以下角色之一: {', '.join(self.required_roles)}")

        return current_user


def require_roles(required_roles: list[str]) -> RoleBasedAccessChecker:
    """角色权限装饰器工厂函数"""
    return RoleBasedAccessChecker(required_roles)


def can_edit_contract(user: User, db: Session, contract_id: str) -> bool:
    """
    检查用户是否可以编辑合同

    规则:
    - 管理员可以编辑任何合同
    - 其他角色需要通过RBAC服务检查特定权限
    """
    if user.role == UserRole.ADMIN:
        return True

    # 使用RBAC服务进行细粒度权限检查
    try:
        from ..schemas.rbac import PermissionCheckRequest
        from ..services.permission.rbac_service import RBACService

        rbac_service = RBACService(db)
        permission_request = PermissionCheckRequest(
            resource="rent_contract",
            action="edit",
            resource_id=contract_id,
            context=None,
        )

        result = rbac_service.check_permission(user.id, permission_request)
        return result.has_permission
    except Exception:
        # 如果RBAC检查失败，默认拒绝权限（安全优先）
        return False


def get_user_rbac_permissions(
    current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)
) -> dict[str, Any]:
    """获取用户RBAC权限信息"""
    if current_user.role == UserRole.ADMIN:
        return {"is_admin": True, "roles": ["admin"], "permissions": ["all"]}

    rbac_service = RBACService(db)
    permissions_summary = rbac_service.get_user_permissions_summary(current_user.id)

    return {
        "is_admin": False,
        "roles": [role.name for role in permissions_summary.roles],
        "permissions": dict(permissions_summary.effective_permissions.items()),
    }
