import logging
from collections.abc import Callable
from functools import wraps
from typing import Any

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..exceptions import BusinessLogicError
from ..middleware.auth import get_current_user
from ..models.auth import User
from ..services.rbac_service import RBACService


class AssetNotFoundError(Exception):
    """Asset not found error"""

    pass


class DuplicateAssetError(Exception):
    """Duplicate asset error"""

    pass


"""
权限验证装饰器
提供统一的权限验证装饰器，简化API端点的权限控制
"""

logger = logging.getLogger(__name__)


def permission_required(
    resource: str, action: str, resource_id_param: str | None = None
):
    """
    权限验证装饰器

    Args:
        resource: 资源名称 (如: 'asset', 'user', 'role')
        action: 操作类型 (如: 'view', 'create', 'edit', 'delete')
        resource_id_param: 资源ID参数名 (用于特定资源权限检查)
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # 获取当前用户
            current_user = kwargs.get("current_user")
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="未认证用户"
                )

            # 获取数据库会话
            db = kwargs.get("db")
            if not db:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="数据库会话未找到",
                )

            try:
                # 初始化RBAC服务
                rbac_service = RBACService(db)

                # 检查基础权限
                has_permission = await rbac_service.check_user_permission(
                    user_id=current_user.id, resource=resource, action=action
                )

                # 如果有资源ID参数，检查特定资源权限
                if resource_id_param and has_permission:
                    resource_id = kwargs.get(resource_id_param)
                    if resource_id:
                        has_permission = await rbac_service.check_resource_access(
                            user_id=current_user.id,
                            resource=resource,
                            resource_id=resource_id,
                            action=action,
                        )

                if not has_permission:
                    logger.warning(
                        f"用户 {current_user.username} 尝试访问未授权资源: {resource}:{action}"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"权限不足，需要 {resource}:{action} 权限",
                    )

                logger.info(
                    f"用户 {current_user.username} 权限验证通过: {resource}:{action}"
                )

                # 执行原函数
                return await func(*args, **kwargs)

            except BusinessLogicError as e:
                logger.error(f"权限验证业务逻辑错误: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail=str(e)
                )
            except Exception as e:
                logger.error(f"权限验证系统错误: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="权限验证失败",
                )

        return wrapper

    return decorator


def admin_required(func: Callable) -> Callable:
    """
    管理员权限装饰器
    """
    return permission_required("system", "admin")(func)


def role_required(role_code: str):
    """
    角色要求装饰器

    Args:
        role_code: 角色代码 (如: 'admin', 'manager', 'user')
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            current_user = kwargs.get("current_user")
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="未认证用户"
                )

            # 检查用户是否具有指定角色
            user_roles = (
                [role.code for role in current_user.roles] if current_user.roles else []
            )
            if role_code not in user_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"权限不足，需要 {role_code} 角色",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def organization_required(organization_id_param: str = "organization_id"):
    """
    组织权限验证装饰器

    Args:
        organization_id_param: 组织ID参数名
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            current_user = kwargs.get("current_user")
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="未认证用户"
                )

            db = kwargs.get("db")
            if not db:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="数据库会话未找到",
                )

            # 获取目标组织ID
            target_org_id = kwargs.get(organization_id_param)
            if not target_org_id:
                target_org_id = current_user.organization_id

            # 检查组织访问权限
            rbac_service = RBACService(db)
            has_access = await rbac_service.check_organization_access(
                user_id=current_user.id, organization_id=target_org_id
            )

            if not has_access:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="权限不足，无法访问该组织资源",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


# 权限依赖工厂函数
def get_current_user_with_permissions(resource: str, action: str):
    """
    获取具有特定权限的当前用户
    """

    async def dependency(
        current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
    ) -> User:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="未认证用户"
            )

        rbac_service = RBACService(db)
        has_permission = await rbac_service.check_user_permission(
            user_id=current_user.id, resource=resource, action=action
        )

        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"权限不足，需要 {resource}:{action} 权限",
            )

        return current_user

    return dependency


# 预定义权限依赖
def require_asset_view():
    return get_current_user_with_permissions("asset", "view")


def require_asset_create():
    return get_current_user_with_permissions("asset", "create")


def require_asset_edit():
    return get_current_user_with_permissions("asset", "edit")


def require_asset_delete():
    return get_current_user_with_permissions("asset", "delete")


def require_user_management():
    return get_current_user_with_permissions("user", "view")


def require_role_management():
    return get_current_user_with_permissions("role", "view")


def require_system_logs():
    return get_current_user_with_permissions("system", "logs")


def require_organization_management():
    return get_current_user_with_permissions("organization", "view")


# 权限检查工具类
class PermissionChecker:
    """权限检查工具类"""

    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user
        self.rbac_service = RBACService(db)

    async def has_permission(self, resource: str, action: str) -> bool:
        """检查用户是否具有指定权限"""
        return await self.rbac_service.check_user_permission(
            user_id=self.user.id, resource=resource, action=action
        )

    async def can_access_resource(
        self, resource: str, resource_id: str, action: str
    ) -> bool:
        """检查用户是否可以访问特定资源"""
        return await self.rbac_service.check_resource_access(
            user_id=self.user.id,
            resource=resource,
            resource_id=resource_id,
            action=action,
        )

    async def can_access_organization(self, organization_id: str) -> bool:
        """检查用户是否可以访问组织"""
        return await self.rbac_service.check_organization_access(
            user_id=self.user.id, organization_id=organization_id
        )

    def has_role(self, role_code: str) -> bool:
        """检查用户是否具有指定角色"""
        user_roles = [role.code for role in self.user.roles] if self.user.roles else []
        return role_code in user_roles

    def is_admin(self) -> bool:
        """检查用户是否是管理员"""
        return self.has_role("admin")


# 便捷权限检查装饰器
def asset_permission_required(action: str, asset_id_param: str = "asset_id"):
    """资产权限装饰器"""
    return permission_required("asset", action, asset_id_param)


def user_permission_required(action: str, user_id_param: str = "user_id"):
    """用户权限装饰器"""
    return permission_required("user", action, user_id_param)


def rental_permission_required(action: str, contract_id_param: str = "contract_id"):
    """租赁权限装饰器"""
    return permission_required("rental", action, contract_id_param)
