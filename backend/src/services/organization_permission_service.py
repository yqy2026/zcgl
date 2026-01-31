"""
Organization permission service.

Provides organization access checks and helper filters for organization-scoped data.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from sqlalchemy.sql import false

from ..models.auth import User
from ..models.organization import Employee, Organization
from ..models.rbac import ResourcePermission, Role, UserRoleAssignment
from ..schemas.rbac import PermissionCheckRequest
from ..security.roles import RoleNormalizer
from .permission.rbac_service import RBACService

logger = logging.getLogger(__name__)


class OrganizationPermissionService:
    """组织权限服务"""

    def __init__(self, db: Session):
        self.db = db
        self.rbac_service = RBACService(db)

    def check_organization_access(self, user_id: str, organization_id: str) -> bool:
        """检查用户是否可访问指定组织"""
        if not organization_id:
            return False
        user = self._get_user(user_id)
        if not user:
            return False
        if RoleNormalizer.is_admin(user.role):
            return True

        if self._has_global_permission(user_id, "read"):
            return True

        if self._has_resource_permission(user_id, organization_id, "read"):
            return True

        accessible_orgs = self.get_user_accessible_organizations(user_id)
        return organization_id in accessible_orgs

    def can_manage_organization(self, user_id: str, organization_id: str) -> bool:
        """检查用户是否可管理指定组织"""
        if not organization_id:
            return False
        user = self._get_user(user_id)
        if not user:
            return False
        if RoleNormalizer.is_admin(user.role):
            return True

        if self._has_global_permission(user_id, "update") or self._has_global_permission(
            user_id, "delete"
        ):
            return True

        if self._has_resource_permission(user_id, organization_id, "update"):
            return True
        if self._has_resource_permission(user_id, organization_id, "delete"):
            return True

        return False

    def filter_assets_by_organization(self, user_id: str, query: Any) -> Any:
        """过滤资产查询（若模型具备组织字段）"""
        return self._apply_organization_filter(query, user_id)

    def filter_projects_by_organization(self, user_id: str, query: Any) -> Any:
        """过滤项目查询（若模型具备组织字段）"""
        return self._apply_organization_filter(query, user_id)

    def filter_ownership_by_organization(self, user_id: str, query: Any) -> Any:
        """过滤权属方查询（若模型具备组织字段）"""
        return self._apply_organization_filter(query, user_id)

    def get_user_accessible_organizations(self, user_id: str) -> list[str]:
        """获取用户可访问组织ID列表"""
        user = self._get_user(user_id)
        if not user:
            return []

        if RoleNormalizer.is_admin(user.role) or self._has_global_permission(
            user_id, "read"
        ):
            return self._get_all_organization_ids()

        org_ids: set[str] = set()

        if user.default_organization_id:
            org_ids.add(str(user.default_organization_id))

        if user.employee_id:
            employee = (
                self.db.query(Employee)
                .filter(Employee.id == user.employee_id)
                .first()
            )
            if employee and employee.organization_id:
                org_ids.add(str(employee.organization_id))

        roles = self._get_user_roles(user_id)
        for role in roles:
            if role.organization_id:
                org_ids.add(str(role.organization_id))

        role_ids = [role.id for role in roles]
        if role_ids:
            role_permissions = self._get_resource_permissions(role_ids=role_ids)
            org_ids.update(role_permissions)

        user_permissions = self._get_resource_permissions(user_id=user_id)
        org_ids.update(user_permissions)

        return list(org_ids)

    def get_user_accessible_organizations_with_details(
        self, user_id: str
    ) -> list[dict[str, Any]]:
        """获取用户可访问组织的详细信息"""
        org_ids = self.get_user_accessible_organizations(user_id)
        if not org_ids:
            return []

        organizations = (
            self.db.query(Organization)
            .filter(Organization.id.in_(org_ids), Organization.is_deleted.is_(False))
            .all()
        )

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

    def get_organization_hierarchy(self, user_id: str) -> list[dict[str, Any]]:
        """获取用户可访问组织的层级结构"""
        org_ids = self.get_user_accessible_organizations(user_id)
        if not org_ids:
            return []

        organizations = (
            self.db.query(Organization)
            .filter(Organization.id.in_(org_ids), Organization.is_deleted.is_(False))
            .all()
        )

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

    def get_user_organization_role(self, user_id: str) -> str | None:
        """获取用户在组织中的角色名称"""
        user = self._get_user(user_id)
        if not user:
            return None
        if RoleNormalizer.is_admin(user.role):
            return "admin"

        target_org = user.default_organization_id
        if user.employee_id and not target_org:
            employee = (
                self.db.query(Employee)
                .filter(Employee.id == user.employee_id)
                .first()
            )
            target_org = employee.organization_id if employee else None

        roles = self._get_user_roles(user_id)
        if target_org:
            matching = [role for role in roles if role.organization_id == target_org]
            if matching:
                matching.sort(key=lambda r: r.level or 0)
                return matching[0].name

        return roles[0].name if roles else None

    def _apply_organization_filter(self, query: Any, user_id: str) -> Any:
        org_ids = self.get_user_accessible_organizations(user_id)
        if not org_ids:
            return query.filter(false())

        for desc in query.column_descriptions:
            entity = desc.get("entity")
            if entity is None:
                continue
            if hasattr(entity, "organization_id"):
                return query.filter(entity.organization_id.in_(org_ids))

        logger.debug(
            "Skipping organization filter; entity has no organization_id column"
        )
        return query

    def _get_user(self, user_id: str) -> User | None:
        return self.db.query(User).filter(User.id == user_id).first()

    def _get_user_roles(self, user_id: str) -> list[Role]:
        return (
            self.db.query(Role)
            .join(UserRoleAssignment, Role.id == UserRoleAssignment.role_id)
            .filter(
                UserRoleAssignment.user_id == user_id,
                UserRoleAssignment.is_active,
                or_(
                    UserRoleAssignment.expires_at.is_(None),
                    UserRoleAssignment.expires_at > datetime.now(UTC),
                ),
            )
            .all()
        )

    def _get_all_organization_ids(self) -> list[str]:
        return [
            str(org_id)
            for org_id, in self.db.query(Organization.id)
            .filter(Organization.is_deleted.is_(False))
            .all()
        ]

    def _get_resource_permissions(
        self, user_id: str | None = None, role_ids: list[str] | None = None
    ) -> list[str]:
        conditions = [ResourcePermission.resource_type == "organization"]
        conditions.append(ResourcePermission.is_active.is_(True))
        conditions.append(
            or_(
                ResourcePermission.expires_at.is_(None),
                ResourcePermission.expires_at > datetime.now(UTC),
            )
        )

        if user_id:
            conditions.append(ResourcePermission.user_id == user_id)
        elif role_ids:
            conditions.append(ResourcePermission.role_id.in_(role_ids))
        else:
            return []

        results = self.db.query(ResourcePermission.resource_id).filter(and_(*conditions))
        return [str(item[0]) for item in results.all()]

    def _has_global_permission(self, user_id: str, action: str) -> bool:
        try:
            request = PermissionCheckRequest(
                resource="organization",
                action=action,
                resource_id=None,
                context=None,
            )
            return self.rbac_service.check_permission(user_id, request).has_permission
        except Exception as exc:
            logger.warning(
                "RBAC global permission check failed: %s", exc, exc_info=True
            )
            return False

    def _has_resource_permission(
        self, user_id: str, organization_id: str, action: str
    ) -> bool:
        try:
            request = PermissionCheckRequest(
                resource="organization",
                action=action,
                resource_id=organization_id,
                context=None,
            )
            return self.rbac_service.check_permission(user_id, request).has_permission
        except Exception as exc:
            logger.warning(
                "RBAC resource permission check failed: %s", exc, exc_info=True
            )
            return False
