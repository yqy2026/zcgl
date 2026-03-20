"""
认证工具 — 权限检查器、审计日志、安全配置等辅助组件。
"""

import logging
from typing import Any

from fastapi import Depends, Request
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.exception_handler import forbidden, unauthorized
from ..crud.auth import AuditLogCRUD
from ..database import get_async_db
from ..models.auth import User
from ..schemas.rbac import PermissionCheckRequest
from ..services import RBACService
from ..services.permission.rbac_service import (
    ADMIN_PERMISSION_ACTION,
    ADMIN_PERMISSION_RESOURCE,
)
from .auth_core import (
    get_current_active_user,
    get_current_user,
    get_optional_current_user,
)

logger = logging.getLogger(__name__)


# ==================== 基础权限检查器 ====================


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


# ==================== 组织权限检查器 (DEPRECATED) ====================


class OrganizationPermissionChecker:  # DEPRECATED
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
) -> OrganizationPermissionChecker:  # DEPRECATED
    """组织权限装饰器工厂函数"""
    return OrganizationPermissionChecker(organization_id)  # DEPRECATED


# ==================== 审计日志 ====================


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


# ==================== 安全配置 ====================


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


# ==================== 资源权限检查器 (DEPRECATED) ====================


class ResourcePermissionChecker:  # DEPRECATED
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
        from ..models.rbac import ResourcePermission  # DEPRECATED

        stmt = select(ResourcePermission).where(  # DEPRECATED
            and_(
                ResourcePermission.user_id == current_user.id,  # DEPRECATED
                ResourcePermission.resource_type == self.resource_type,  # DEPRECATED
                ResourcePermission.resource_id == resource_id,  # DEPRECATED
                ResourcePermission.is_active,  # DEPRECATED
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
) -> ResourcePermissionChecker:  # DEPRECATED
    """资源权限装饰器工厂函数"""
    return ResourcePermissionChecker(resource_type, required_level)  # DEPRECATED


# ==================== 角色访问检查器 ====================


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


# ==================== 合同编辑 & 用户权限 ====================


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
            resource="contract",
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
