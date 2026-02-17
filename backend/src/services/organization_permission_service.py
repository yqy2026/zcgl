"""
Organization permission service.

Provides organization access checks and helper filters for organization-scoped data.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import false

from ..crud.auth import UserCRUD
from ..crud.organization import organization as organization_crud
from ..crud.rbac import resource_permission_crud, role_crud
from ..schemas.rbac import PermissionCheckRequest
from .permission.rbac_service import RBACService

logger = logging.getLogger(__name__)

_user_crud = UserCRUD()


def _utcnow_naive() -> datetime:
    """返回 naive UTC 时间。"""
    return datetime.now(UTC).replace(tzinfo=None)


class OrganizationPermissionService:
    """组织权限服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.rbac_service = RBACService(db)

    async def check_organization_access(
        self, user_id: str, organization_id: str
    ) -> bool:
        """检查用户是否可访问指定组织"""
        if not organization_id:
            return False
        user = await self._get_user(user_id)
        if not user:
            return False
        if await self.rbac_service.is_admin(user_id):
            return True

        if await self._has_global_permission(user_id, "read"):
            return True

        if await self._has_resource_permission(user_id, organization_id, "read"):
            return True

        accessible_orgs = await self.get_user_accessible_organizations(user_id)
        return organization_id in accessible_orgs

    async def can_manage_organization(self, user_id: str, organization_id: str) -> bool:
        """检查用户是否可管理指定组织"""
        if not organization_id:
            return False
        user = await self._get_user(user_id)
        if not user:
            return False
        if await self.rbac_service.is_admin(user_id):
            return True

        if await self._has_global_permission(
            user_id, "update"
        ) or await self._has_global_permission(user_id, "delete"):
            return True

        if await self._has_resource_permission(user_id, organization_id, "update"):
            return True
        if await self._has_resource_permission(user_id, organization_id, "delete"):
            return True

        return False

    async def filter_assets_by_organization(self, user_id: str, query: Any) -> Any:
        """过滤资产查询（若模型具备组织字段）"""
        return await self._apply_organization_filter(query, user_id)

    async def filter_projects_by_organization(self, user_id: str, query: Any) -> Any:
        """过滤项目查询（若模型具备组织字段）"""
        return await self._apply_organization_filter(query, user_id)

    async def filter_ownership_by_organization(self, user_id: str, query: Any) -> Any:
        """过滤权属方查询（若模型具备组织字段）"""
        return await self._apply_organization_filter(query, user_id)

    async def get_user_accessible_organizations(self, user_id: str) -> list[str]:
        """获取用户可访问组织ID列表"""
        user = await self._get_user(user_id)
        if not user:
            return []

        if await self.rbac_service.is_admin(
            user_id
        ) or await self._has_global_permission(user_id, "read"):
            return await self._get_all_organization_ids()

        org_ids: set[str] = set()

        if user.default_organization_id:
            org_ids.add(str(user.default_organization_id))

        roles = await self._get_user_roles(user_id)
        for role in roles:
            if role.organization_id:
                org_ids.add(str(role.organization_id))

        role_ids = [role.id for role in roles]
        if role_ids:
            role_permissions = await self._get_resource_permissions(role_ids=role_ids)
            org_ids.update(role_permissions)

        user_permissions = await self._get_resource_permissions(user_id=user_id)
        org_ids.update(user_permissions)

        return list(org_ids)

    async def get_user_accessible_organizations_with_details(
        self, user_id: str
    ) -> list[dict[str, Any]]:
        """获取用户可访问组织的详细信息"""
        org_ids = await self.get_user_accessible_organizations(user_id)
        if not org_ids:
            return []

        organizations = await organization_crud.get_by_ids_async(self.db, org_ids)

        return [
            {
                "id": org.id,
                "name": org.name,
                "code": org.code,
                "type": org.type,
                "status": org.status,
                "level": org.level,
                "parent_id": org.parent_id,
                "path": org.path,
            }
            for org in organizations
        ]

    async def get_organization_hierarchy(self, user_id: str) -> list[dict[str, Any]]:
        """获取用户可访问组织的层级结构"""
        org_ids = await self.get_user_accessible_organizations(user_id)
        if not org_ids:
            return []

        organizations = await organization_crud.get_by_ids_async(self.db, org_ids)

        nodes: dict[str, dict[str, Any]] = {}
        for org in organizations:
            nodes[str(org.id)] = {
                "id": org.id,
                "name": org.name,
                "code": org.code,
                "type": org.type,
                "status": org.status,
                "level": org.level,
                "parent_id": org.parent_id,
                "path": org.path,
                "children": [],
            }

        roots: list[dict[str, Any]] = []
        for org in organizations:
            node = nodes[str(org.id)]
            parent_id = org.parent_id
            if parent_id and str(parent_id) in nodes:
                nodes[str(parent_id)]["children"].append(node)
            else:
                roots.append(node)

        return roots

    async def get_user_organization_role(self, user_id: str) -> str | None:
        """获取用户在组织中的角色名称"""
        user = await self._get_user(user_id)
        if not user:
            return None
        if await self.rbac_service.is_admin(user_id):
            return "admin"

        target_org = user.default_organization_id

        roles = await self._get_user_roles(user_id)
        if target_org:
            matching = [role for role in roles if role.organization_id == target_org]
            if matching:
                matching.sort(key=lambda r: r.level or 0)
                return matching[0].name

        return roles[0].name if roles else None

    async def _apply_organization_filter(self, query: Any, user_id: str) -> Any:
        org_ids = await self.get_user_accessible_organizations(user_id)
        if not org_ids:
            if hasattr(query, "filter"):
                return query.filter(false())
            if hasattr(query, "where"):
                return query.where(false())
            return query

        for desc in query.column_descriptions:
            entity = desc.get("entity")
            if entity is None:
                continue
            if hasattr(entity, "organization_id"):
                if hasattr(query, "filter"):
                    return query.filter(entity.organization_id.in_(org_ids))
                if hasattr(query, "where"):
                    return query.where(entity.organization_id.in_(org_ids))
                return query

        logger.debug(
            "Skipping organization filter; entity has no organization_id column"
        )
        return query

    async def _get_user(self, user_id: str) -> Any:
        return await _user_crud.get_async(self.db, user_id)

    async def _get_user_roles(self, user_id: str) -> list[Any]:
        return await role_crud.get_roles_by_user_async(
            self.db, user_id, now=_utcnow_naive()
        )

    async def _get_all_organization_ids(self) -> list[str]:
        return await organization_crud.get_ids_by_condition_async(
            self.db, is_deleted=False
        )

    async def _get_resource_permissions(
        self, user_id: str | None = None, role_ids: list[str] | None = None
    ) -> list[str]:
        return await resource_permission_crud.get_resource_ids_by_conditions_async(
            self.db,
            resource_type="organization",
            user_id=user_id,
            role_ids=role_ids,
            now=_utcnow_naive(),
        )

    async def _has_global_permission(self, user_id: str, action: str) -> bool:
        try:
            request = PermissionCheckRequest(
                resource="organization",
                action=action,
                resource_id=None,
                context=None,
            )
            response = await self.rbac_service.check_permission(user_id, request)
            return response.has_permission
        except Exception as exc:
            logger.warning(
                "RBAC global permission check failed: %s", exc, exc_info=True
            )
            return False

    async def _has_resource_permission(
        self, user_id: str, organization_id: str, action: str
    ) -> bool:
        try:
            request = PermissionCheckRequest(
                resource="organization",
                action=action,
                resource_id=organization_id,
                context=None,
            )
            response = await self.rbac_service.check_permission(user_id, request)
            return response.has_permission
        except Exception as exc:
            logger.warning(
                "RBAC resource permission check failed: %s", exc, exc_info=True
            )
            return False
