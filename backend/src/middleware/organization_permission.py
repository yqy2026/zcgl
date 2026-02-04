"""
组织权限中间件
实现基于组织架构的权限控制和数据隔离
"""

import ipaddress
from collections.abc import Callable
from typing import Any

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.exception_handler import bad_request, forbidden
from ..database import get_async_db
from ..models.auth import User
from ..security.audit_logger import SecurityEventLogger
from ..security.roles import RoleNormalizer
from ..services.organization_permission_service import OrganizationPermissionService
from ..utils.async_db import AsyncServiceClassAdapter
from .auth import get_current_active_user


def require_organization_access(
    organization_id_param: str = "organization_id",
) -> Callable[..., Any]:
    """
    组织访问权限装饰器工厂函数

    Args:
        organization_id_param: 组织ID参数名
    """

    async def dependency(
        organization_id: str | None = None,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_async_db),
        request: Request = Depends(),
    ) -> Any:
        """
        检查用户是否有权访问指定组织
        """
        if organization_id is None:
            raise bad_request("组织ID不能为空")

        org_service = OrganizationPermissionService(db)
        if not await org_service.check_organization_access(current_user.id, organization_id):
            # Log permission denied event
            security_logger = AsyncServiceClassAdapter(db, SecurityEventLogger)

            # Extract and validate client IP
            client_ip = request.client.host if request.client else "unknown"
            try:
                ipaddress.ip_address(client_ip)
            except ValueError:
                client_ip = "unknown"

            await security_logger.log_permission_denied(
                user_id=str(current_user.id),
                resource=f"organization:{organization_id}",
                action="access",
                ip=client_ip,
            )

            # Check for alert threshold
            if await security_logger.should_alert(ip=client_ip):
                # Log security alert when threshold exceeded
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(
                    f"Security alert threshold exceeded for IP: {client_ip}, "
                    f"user: {current_user.id}, resource: organization:{organization_id}"
                )

            raise forbidden("无权访问该组织的数据")

        return organization_id

    return dependency


def require_organization_management(
    organization_id_param: str = "organization_id",
) -> Callable[..., Any]:
    """
    组织管理权限装饰器工厂函数

    Args:
        organization_id_param: 组织ID参数名
    """

    async def dependency(
        organization_id: str | None = None,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_async_db),
        request: Request = Depends(),
    ) -> Any:
        """
        检查用户是否有权管理指定组织
        """
        if organization_id is None:
            raise bad_request("组织ID不能为空")

        org_service = OrganizationPermissionService(db)
        if not await org_service.can_manage_organization(current_user.id, organization_id):
            # Log permission denied event
            security_logger = AsyncServiceClassAdapter(db, SecurityEventLogger)

            # Extract and validate client IP
            client_ip = request.client.host if request.client else "unknown"
            try:
                ipaddress.ip_address(client_ip)
            except ValueError:
                client_ip = "unknown"

            await security_logger.log_permission_denied(
                user_id=str(current_user.id),
                resource=f"organization:{organization_id}",
                action="manage",
                ip=client_ip,
            )

            # Check for alert threshold
            if await security_logger.should_alert(ip=client_ip):
                # Log security alert when threshold exceeded
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(
                    f"Security alert threshold exceeded for IP: {client_ip}, "
                    f"user: {current_user.id}, resource: organization:{organization_id}"
                )

            raise forbidden("无权管理该组织")

        return organization_id

    return dependency


class OrganizationDataFilter:
    """
    组织数据过滤器
    用于根据用户组织权限过滤查询结果
    """

    def __init__(self, db: AsyncSession, user_id: str):
        self.db = db
        self.user_id = user_id
        self.org_service = OrganizationPermissionService(db)

    async def filter_assets_query(self, query: Any) -> Any:
        """过滤资产查询"""
        return await self.org_service.filter_assets_by_organization(self.user_id, query)

    async def filter_projects_query(self, query: Any) -> Any:
        """过滤项目查询"""
        return await self.org_service.filter_projects_by_organization(
            self.user_id, query
        )

    async def filter_ownership_query(self, query: Any) -> Any:
        """过滤权属方查询"""
        return await self.org_service.filter_ownership_by_organization(
            self.user_id, query
        )

    async def get_accessible_organizations(self) -> list[str]:
        """获取可访问的组织ID列表"""
        result = await self.org_service.get_user_accessible_organizations(self.user_id)
        assert isinstance(result, list)  # nosec B101  # Defensive type check
        return result

    async def get_accessible_organizations_with_details(self) -> list[dict[str, Any]]:
        """获取可访问的组织详细信息"""
        result = await self.org_service.get_user_accessible_organizations_with_details(
            self.user_id
        )
        assert isinstance(result, list)  # nosec B101  # Defensive type check
        return result

    async def get_organization_hierarchy(self) -> list[dict[str, Any]]:
        """获取组织层次结构"""
        result = await self.org_service.get_organization_hierarchy(self.user_id)
        assert isinstance(result, list)  # nosec B101  # Defensive type check
        return result


async def get_organization_filter(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> OrganizationDataFilter:
    """
    获取组织数据过滤器依赖
    """
    # Extract the actual user_id from the Column
    user_id = current_user.id
    return OrganizationDataFilter(db, str(user_id))


async def get_accessible_organizations(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> list[dict[str, Any]]:
    """
    获取用户可访问的组织列表
    """
    org_service = OrganizationPermissionService(db)
    result = await org_service.get_user_accessible_organizations_with_details(current_user.id)
    assert isinstance(result, list)  # nosec B101  # Defensive type check
    return result


async def get_user_organization_role(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> str | None:
    """
    获取用户在组织中的角色
    """
    org_service = OrganizationPermissionService(db)
    result = await org_service.get_user_organization_role(current_user.id)
    # The result might already be str | None, but we need to ensure it matches the return type
    if result is None or isinstance(result, str):
        return result
    return str(result)


# 导入必要的依赖已在顶部完成


class OrganizationPermissionChecker:
    """
    组织权限检查器
    """

    def __init__(
        self, required_permission: str, organization_id_param: str | None = None
    ) -> None:
        self.required_permission = required_permission
        self.organization_id_param = organization_id_param

    async def __call__(
        self,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_async_db),
        request: Request = Depends(),
    ) -> User:
        """
        Check user permissions with case-insensitive role comparison
        """
        # Check for admin role (case-insensitive)
        if RoleNormalizer.is_admin(current_user.role):
            return current_user

        # If there's an organization ID parameter, check organization permission
        if self.organization_id_param:
            organization_id = await self._extract_organization_id(request)
            if organization_id is None:
                raise bad_request("组织ID不能为空")

            org_service = OrganizationPermissionService(db)
            if not await org_service.check_organization_access(current_user.id, organization_id):
                # Log permission denied event
                security_logger = AsyncServiceClassAdapter(db, SecurityEventLogger)

                client_ip = request.client.host if request.client else "unknown"
                try:
                    ipaddress.ip_address(client_ip)
                except ValueError:
                    client_ip = "unknown"

                await security_logger.log_permission_denied(
                    user_id=str(current_user.id),
                    resource=f"organization:{organization_id}",
                    action=self.required_permission,
                    ip=client_ip,
                )

                if await security_logger.should_alert(ip=client_ip):
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.warning(
                        f"Security alert threshold exceeded for IP: {client_ip}, "
                        f"user: {current_user.id}, resource: organization:{organization_id}"
                    )

                raise forbidden("无权访问该组织的数据")

        # Check if user has any organization access permissions
        org_service = OrganizationPermissionService(db)
        accessible_orgs = await org_service.get_user_accessible_organizations(current_user.id)

        if not accessible_orgs:
            # Log permission denied event
            security_logger = AsyncServiceClassAdapter(db, SecurityEventLogger)

            # Extract and validate client IP
            client_ip = request.client.host if request.client else "unknown"
            try:
                ipaddress.ip_address(client_ip)
            except ValueError:
                client_ip = "unknown"

            await security_logger.log_permission_denied(
                user_id=str(current_user.id),
                resource="organizations",
                action="access",
                ip=client_ip,
            )

            # Check for alert threshold
            if await security_logger.should_alert(ip=client_ip):
                # Log security alert when threshold exceeded
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(
                    f"Security alert threshold exceeded for IP: {client_ip}, "
                    f"user: {current_user.id}, resource: organizations"
                )

            raise forbidden("无任何组织访问权限")

        return current_user

    async def _extract_organization_id(self, request: Request) -> str | None:
        """从请求中提取组织ID"""
        param = self.organization_id_param
        if not param:
            return None

        if param in request.path_params:
            return str(request.path_params.get(param))

        if param in request.query_params:
            return str(request.query_params.get(param))

        content_type = request.headers.get("content-type", "")
        if content_type.startswith("application/json"):
            try:
                payload = await request.json()
                if isinstance(payload, dict):
                    value = payload.get(param)
                    if value is not None:
                        return str(value)
            except Exception:
                return None

        return None


def require_organization_permission(
    required_permission: str, organization_id_param: str | None = None
) -> OrganizationPermissionChecker:
    """
    组织权限装饰器工厂函数
    """
    return OrganizationPermissionChecker(required_permission, organization_id_param)


# 从现有中间件导入需要的函数已在顶部完成
