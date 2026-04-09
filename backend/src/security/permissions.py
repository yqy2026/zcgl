import logging
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, cast

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.exception_handler import (
    BaseBusinessError,
    forbidden,
    internal_error,
    unauthorized,
)
from ..database import get_async_db
from ..middleware.auth import get_current_user
from ..models.auth import User
from ..services import RBACService
from ..services.permission.rbac_service import (
    ADMIN_PERMISSION_ACTION,
    ADMIN_PERMISSION_RESOURCE,
    normalize_permission_action,
)

"""
权限验证装饰器
提供统一的权限验证装饰器，简化API端点的权限控制
"""

logger = logging.getLogger(__name__)


def _is_admin_permission(resource: str, action: str) -> bool:
    return resource == ADMIN_PERMISSION_RESOURCE and action == ADMIN_PERMISSION_ACTION


def permission_required[**P, R](
    resource: str, action: str, resource_id_param: str | None = None
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """
    权限验证装饰器

    Args:
        resource: 资源名称 (如: 'asset', 'user', 'role')
        action: 操作类型 (如: 'read', 'create', 'update', 'delete')
        resource_id_param: 资源ID参数名 (用于特定资源权限检查)
    """
    normalized_action = normalize_permission_action(action)

    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # 获取当前用户
            current_user = kwargs.get("current_user")
            if not current_user:
                raise unauthorized("未认证用户")
            current_user = cast(User, current_user)

            # 获取数据库会话
            db = kwargs.get("db")
            if not db:
                raise internal_error("数据库会话未找到")
            db = cast(AsyncSession, db)

            try:
                # 初始化RBAC服务
                rbac_service = RBACService(db)

                # 检查基础权限
                user_id_value: str = str(getattr(current_user, "id", ""))
                if _is_admin_permission(resource, normalized_action):
                    has_permission = await rbac_service.is_admin(user_id=user_id_value)
                else:
                    has_permission = await rbac_service.check_user_permission(
                        user_id=user_id_value,
                        resource=resource,
                        action=normalized_action,
                    )

                # 如果有资源ID参数，检查特定资源权限
                if resource_id_param and has_permission:
                    resource_id = kwargs.get(resource_id_param)
                    if resource_id is not None:
                        resource_id_value = str(resource_id)
                        has_permission = await rbac_service.check_resource_access(
                            user_id=user_id_value,
                            resource=resource,
                            resource_id=resource_id_value,
                            action=normalized_action,
                        )

                if not has_permission:
                    logger.warning(
                        f"用户 {current_user.username} 尝试访问未授权资源: {resource}:{action}"
                        f" -> {resource}:{normalized_action}"
                    )
                    raise forbidden(
                        f"权限不足，需要 {resource}:{normalized_action} 权限"
                    )

                logger.info(
                    f"用户 {current_user.username} 权限验证通过: "
                    f"{resource}:{normalized_action}"
                )

                # 执行原函数
                return await func(*args, **kwargs)

            except HTTPException:
                # Re-raise HTTPException directly (e.g., 403 permission denied)
                raise
            except BaseBusinessError as e:
                logger.error(f"权限验证业务逻辑错误: {str(e)}")
                raise forbidden(str(e))
            except Exception as e:
                logger.error(f"权限验证系统错误: {str(e)}")
                raise internal_error("权限验证失败")

        return wrapper

    return decorator


def admin_required[**P, R](
    func: Callable[P, Awaitable[R]],
) -> Callable[P, Awaitable[R]]:
    """
    管理员权限装饰器
    """
    return permission_required(ADMIN_PERMISSION_RESOURCE, ADMIN_PERMISSION_ACTION)(func)


def role_required[**P, R](
    role_code: str,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """
    角色要求装饰器

    Args:
        role_code: 角色代码 (如: 'admin', 'manager', 'user')
    """

    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            current_user = kwargs.get("current_user")
            if not current_user:
                raise unauthorized("未认证用户")
            current_user = cast(User, current_user)

            db = kwargs.get("db")
            if not db:
                raise internal_error("数据库会话未找到")
            db = cast(AsyncSession, db)

            rbac_service = RBACService(db)
            user_id_value: str = str(getattr(current_user, "id", ""))
            roles = await rbac_service.get_user_roles(user_id_value)
            role_names = {role.name for role in roles}

            if role_code not in role_names:
                raise forbidden(f"权限不足，需要 {role_code} 角色")

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_any_role(role_codes: list[str]) -> Callable[[User, AsyncSession], Any]:
    """依赖工厂：用户命中任一角色即可放行。"""

    normalized_role_codes = {
        str(role_code).strip()
        for role_code in role_codes
        if str(role_code).strip() != ""
    }

    async def dependency(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_async_db),
    ) -> User:
        if not current_user:
            raise unauthorized("未认证用户")

        rbac_service = RBACService(db)
        user_id_value = str(getattr(current_user, "id", ""))
        roles = await rbac_service.get_user_roles(user_id_value)
        role_names = {str(role.name).strip() for role in roles if getattr(role, "name", None)}

        if normalized_role_codes.isdisjoint(role_names):
            required_roles = ", ".join(sorted(normalized_role_codes))
            raise forbidden(f"权限不足，需要以下任一角色：{required_roles}")

        return current_user

    return dependency


def organization_required[**P, R](
    organization_id_param: str = "organization_id",
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """
    组织权限验证装饰器

    Args:
        organization_id_param: 组织ID参数名
    """

    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            current_user = kwargs.get("current_user")
            if not current_user:
                raise unauthorized("未认证用户")
            current_user = cast(User, current_user)

            db = kwargs.get("db")
            if not db:
                raise internal_error("数据库会话未找到")
            db = cast(AsyncSession, db)

            # 获取目标组织ID
            target_org_id = kwargs.get(organization_id_param)
            if target_org_id is None:
                target_org_id = current_user.default_organization_id
            target_org_id_value = str(target_org_id)

            # 检查组织访问权限
            rbac_service = RBACService(db)
            has_access = await rbac_service.check_organization_access(
                user_id=str(current_user.id), organization_id=target_org_id_value
            )

            if not has_access:
                raise forbidden("权限不足，无法访问该组织资源")

            return await func(*args, **kwargs)

        return wrapper

    return decorator


# 权限依赖工厂函数
def get_current_user_with_permissions(
    resource: str, action: str
) -> Callable[[User, AsyncSession], Any]:
    """
    获取具有特定权限的当前用户
    """
    normalized_action = normalize_permission_action(action)

    async def dependency(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_async_db),
    ) -> User:
        if not current_user:
            raise unauthorized("未认证用户")

        rbac_service = RBACService(db)
        user_id_value: str = str(getattr(current_user, "id", ""))
        if _is_admin_permission(resource, normalized_action):
            has_permission = await rbac_service.is_admin(user_id=user_id_value)
        else:
            has_permission = await rbac_service.check_user_permission(
                user_id=user_id_value,
                resource=resource,
                action=normalized_action,
            )

        if not has_permission:
            raise forbidden(f"权限不足，需要 {resource}:{normalized_action} 权限")

        return current_user

    return dependency


# 预定义权限依赖
def require_asset_read() -> Callable[[User, AsyncSession], Any]:
    return get_current_user_with_permissions("asset", "read")


def require_asset_view() -> Callable[[User, AsyncSession], Any]:
    return require_asset_read()


def require_asset_create() -> Callable[[User, AsyncSession], Any]:
    return get_current_user_with_permissions("asset", "create")


def require_asset_update() -> Callable[[User, AsyncSession], Any]:
    return get_current_user_with_permissions("asset", "update")


def require_asset_edit() -> Callable[[User, AsyncSession], Any]:
    return require_asset_update()


def require_asset_delete() -> Callable[[User, AsyncSession], Any]:
    return get_current_user_with_permissions("asset", "delete")


def require_approval_read() -> Callable[[User, AsyncSession], Any]:
    return get_current_user_with_permissions("approval", "read")


def require_approval_start() -> Callable[[User, AsyncSession], Any]:
    return get_current_user_with_permissions("approval", "start")


def require_approval_approve() -> Callable[[User, AsyncSession], Any]:
    return get_current_user_with_permissions("approval", "approve")


def require_approval_reject() -> Callable[[User, AsyncSession], Any]:
    return get_current_user_with_permissions("approval", "reject")


def require_approval_withdraw() -> Callable[[User, AsyncSession], Any]:
    return get_current_user_with_permissions("approval", "withdraw")


def require_user_management() -> Callable[[User, AsyncSession], Any]:
    return get_current_user_with_permissions("user", "read")


def require_role_management() -> Callable[[User, AsyncSession], Any]:
    return get_current_user_with_permissions("role", "read")


def require_system_logs() -> Callable[[User, AsyncSession], Any]:
    return get_current_user_with_permissions("system", "logs")


def require_organization_management() -> Callable[[User, AsyncSession], Any]:
    return get_current_user_with_permissions("organization", "read")


# 权限检查工具类
class PermissionChecker:
    """权限检查工具类"""

    def __init__(self, db: AsyncSession, user: User):
        self.db = db
        self.user = user
        self.rbac_service = RBACService(db)

    async def has_permission(self, resource: str, action: str) -> bool:
        """检查用户是否具有指定权限"""
        user_id_value: str = getattr(self.user, "id", "")
        normalized_action = normalize_permission_action(action)
        if _is_admin_permission(resource, normalized_action):
            return bool(await self.rbac_service.is_admin(user_id=user_id_value))
        return bool(
            await self.rbac_service.check_user_permission(
                user_id=user_id_value,
                resource=resource,
                action=normalized_action,
            )
        )

    async def can_access_resource(
        self, resource: str, resource_id: str, action: str
    ) -> bool:
        """检查用户是否可以访问特定资源"""
        user_id_value: str = getattr(self.user, "id", "")
        normalized_action = normalize_permission_action(action)
        return bool(
            await self.rbac_service.check_resource_access(
                user_id=user_id_value,
                resource=resource,
                resource_id=resource_id,
                action=normalized_action,
            )
        )

    async def can_access_organization(self, organization_id: str) -> bool:
        """检查用户是否可以访问组织"""
        user_id_value: str = getattr(self.user, "id", "")
        return bool(
            await self.rbac_service.check_organization_access(
                user_id=user_id_value, organization_id=organization_id
            )
        )

    async def has_role(self, role_code: str) -> bool:
        """检查用户是否具有指定角色"""
        user_id_value: str = getattr(self.user, "id", "")
        roles = await self.rbac_service.get_user_roles(user_id_value)
        role_names = {role.name for role in roles}
        return role_code in role_names

    async def is_admin(self) -> bool:
        """检查用户是否是管理员"""
        user_id_value: str = getattr(self.user, "id", "")
        return await self.rbac_service.is_admin(user_id_value)


# 便捷权限检查装饰器
def asset_permission_required(
    action: str, asset_id_param: str = "asset_id"
) -> Callable[..., Any]:
    """资产权限装饰器"""
    return permission_required("asset", action, asset_id_param)


def user_permission_required(
    action: str, user_id_param: str = "user_id"
) -> Callable[..., Any]:
    """用户权限装饰器"""
    return permission_required("user", action, user_id_param)


def rental_permission_required(
    action: str, contract_id_param: str = "contract_id"
) -> Callable[..., Any]:
    """租赁权限装饰器"""
    return permission_required("rental", action, contract_id_param)
