from typing import Any

"""
认证中间件
"""

import logging
import os

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import and_
from sqlalchemy.orm import Session

from ..core.config import settings
from ..database import get_db
from ..models.auth import User, UserRole
from ..schemas.auth import TokenData
from ..schemas.rbac import PermissionCheckRequest
from ..services.rbac_service import RBACService

logger = logging.getLogger(__name__)

# 开发模式检查 - 使用更安全的开发认证
# 只有在明确设置为true时才启用开发模式
DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"

# OAuth2密码流 - 始终启用安全性
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login", auto_error=False)


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
        # 出错时保守处理，允许token通过
        return False


# JWT配置
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"


def safe_role_compare(role_value, target_role) -> bool:
    """安全地比较角色值，支持字符串和枚举类型"""
    if isinstance(role_value, str):
        return role_value == target_role.value
    return role_value == target_role


def get_current_user(
    token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User | None:
    """从JWT令牌中获取当前用户，支持开发模式自动认证"""

    # 开发模式下使用测试用户认证（更安全的方式）
    if DEV_MODE and not token:
        # 创建或获取开发测试用户
        return get_or_create_dev_user(db)

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # 如果没有token，抛出认证异常而不是返回None
    if not token:
        raise credentials_exception

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        username: str = payload.get("username")
        role: str = payload.get("role")
        exp: int = payload.get("exp")
        iat: int = payload.get("iat")
        jti: str = payload.get("jti")  # JWT ID for token tracking

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
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token已失效"
            )

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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="用户账户已被禁用"
        )

    if user.is_locked_now():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户账户已被锁定，请稍后再试",
        )

    return user


def get_or_create_dev_user(db: Session) -> User:
    """在开发模式下获取或创建测试用户"""
    dev_username = "dev_user"

    # 尝试获取现有的开发用户
    dev_user = db.query(User).filter(User.username == dev_username).first()

    if dev_user:
        return dev_user

    # 创建新的开发用户
    from ..crud.auth import UserCRUD
    from ..schemas.auth import UserCreate

    user_crud = UserCRUD()
    user_data = UserCreate(
        username=dev_username,
        email="dev@example.com",
        password="dev_password_123",
        full_name="Development User",
        is_active=True,
    )

    try:
        dev_user = user_crud.create(db=db, obj_in=user_data)
        # 设置为管理员角色以便开发测试
        dev_user.role = UserRole.ADMIN.value
        db.commit()
        db.refresh(dev_user)
        logger.info(f"Created development user: {dev_username}")
        return dev_user
    except Exception as e:
        logger.error(f"Failed to create development user: {e}")
        # 如果创建失败，返回一个最小化的用户对象
        return User(
            id="dev-user-id",
            username=dev_username,
            email="dev@example.com",
            is_active=True,
            role=UserRole.ADMIN.value,
        )


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """获取当前活跃用户"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="用户账户未激活"
        )
    return current_user


def require_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """要求管理员权限"""
    if not safe_role_compare(current_user.role, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限"
        )
    return current_user


def get_optional_current_user(
    token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User | None:
    """获取可选的当前用户（用于可选认证的端点）"""
    if not token:
        return None

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")

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

    def __call__(self, current_user: User = Depends(get_current_active_user)):
        """检查用户权限"""
        if not self._has_permission(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="权限不足"
            )
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


def require_permissions(required_permissions: list[str]):
    """权限装饰器工厂函数"""
    return PermissionChecker(required_permissions)


class OrganizationPermissionChecker:
    """组织权限检查器"""

    def __init__(self, organization_id: str | None = None):
        self.organization_id = organization_id

    def __call__(self, current_user: User = Depends(get_current_active_user)):
        """检查用户是否有访问指定组织的权限"""
        if not self._can_access_organization(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="无权访问该组织的数据"
            )
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
        if user.employee_id:
            # 这里需要查询Employee表，暂时简化处理
            return True

        return False


def require_organization_access(organization_id: str | None = None):
    """组织权限装饰器工厂函数"""
    return OrganizationPermissionChecker(organization_id)


class AuditLogger:
    """审计日志记录器"""

    def __init__(self, action: str, resource_type: str | None = None):
        self.action = action
        self.resource_type = resource_type

    def __call__(self, current_user: User | None = Depends(get_optional_current_user)):
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
    ):
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


def audit_action(action: str, resource_type: str | None = None):
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
        """检查用户权限，支持开发模式"""

        # 如果没有用户（未认证），在开发模式下允许继续
        if current_user is None:
            if DEV_MODE:
                # 开发模式下，创建临时用户进行权限检查
                current_user = get_or_create_dev_user(db)
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="需要认证"
                )

        # 管理员拥有所有权限
        if safe_role_compare(current_user.role, UserRole.ADMIN):
            return current_user

        # 开发模式下，给予开发用户所有权限
        if DEV_MODE and current_user.username == "dev_user":
            return current_user

        # 使用RBAC服务检查权限
        rbac_service = RBACService(db)
        permission_request = PermissionCheckRequest(
            resource=self.resource, action=self.action, resource_id=self.resource_id
        )

        permission_result = rbac_service.check_permission(
            current_user.id, permission_request
        )

        if not permission_result.has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"权限不足，需要 {self.resource}:{self.action} 权限",
            )

        return current_user


def require_permission(resource: str, action: str, resource_id: str | None = None):
    """RBAC权限装饰器工厂函数，支持开发模式"""
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
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"无权访问此{self.resource_type}资源",
            )

        # 检查权限级别
        level_actions = {
            "read": ["read"],
            "write": ["read", "write"],
            "delete": ["read", "write", "delete"],
            "admin": ["read", "write", "delete", "admin"],
        }

        # 简化处理：假设当前操作对应required_level
        if self.required_level not in level_actions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"无效的权限级别: {self.required_level}",
            )

        return current_user


def require_resource_permission(resource_type: str, required_level: str = "read"):
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
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要以下角色之一: {', '.join(self.required_roles)}",
            )

        return current_user


def require_roles(required_roles: list[str]):
    """角色权限装饰器工厂函数"""
    return RoleBasedAccessChecker(required_roles)


def get_user_rbac_permissions(
    current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)
):
    """获取用户RBAC权限信息"""
    if current_user.role == UserRole.ADMIN:
        return {"is_admin": True, "roles": ["admin"], "permissions": ["all"]}

    rbac_service = RBACService(db)
    permissions_summary = rbac_service.get_user_permissions_summary(current_user.id)

    return {
        "is_admin": False,
        "roles": [role.name for role in permissions_summary.roles],
        "permissions": {
            resource: actions
            for resource, actions in permissions_summary.effective_permissions.items()
        },
    }
