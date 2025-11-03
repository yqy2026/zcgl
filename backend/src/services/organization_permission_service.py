from typing import Any
"""
组织架构权限服务
实现基于组织架构的数据隔离和权限控制
"""

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from ..models.asset import Asset, Ownership, Project
from ..models.auth import User
from ..models.organization import Employee, Organization
from ..models.rbac import UserRoleAssignment


class OrganizationPermissionService:
    """组织权限服务"""

    def __init__(self, db: Session):
        self.db = db

    def get_user_accessible_organizations(self, user_id: str) -> list[str]:
        """
        获取用户可访问的组织ID列表

        - 超级管理员：可访问所有组织
        - 组织管理员：可访问其管理的组织及子组织
        - 普通用户：可访问其所属组织及子组织
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return []

        # 超级管理员可访问所有组织
        if user.role == "ADMIN":
            organizations = (
                self.db.query(Organization.id).filter(not Organization.is_deleted).all()
            )
            return [org.id for org in organizations]

        # 获取用户角色
        user_roles = (
            self.db.query(UserRoleAssignment)
            .filter(
                and_(
                    UserRoleAssignment.user_id == user_id,
                    UserRoleAssignment.is_active,
                )
            )
            .all()
        )

        # 检查是否有组织管理员角色
        has_org_admin_role = any(
            assignment.role and "org_admin" in assignment.role.name.lower()
            for assignment in user_roles
        )

        if has_org_admin_role:
            # 组织管理员可访问其管理的组织及子组织
            return self._get_organization_tree_access(user_id)
        else:
            # 普通用户可访问其所属组织及子组织
            return self._get_user_organization_access(user_id)

    def get_user_accessible_organizations_with_details(
        self, user_id: str
    ) -> list[dict]:
        """
        获取用户可访问的组织详细信息
        """
        accessible_org_ids = self.get_user_accessible_organizations(user_id)

        organizations = (
            self.db.query(Organization)
            .filter(
                and_(
                    Organization.id.in_(accessible_org_ids),
                    not Organization.is_deleted,
                )
            )
            .all()
        )

        return [
            {
                "id": org.id,
                "name": org.name,
                "code": org.code,
                "level": org.level,
                "parent_id": org.parent_id,
                "path": org.path,
                "type": org.type,
                "status": org.status,
            }
            for org in organizations
        ]

    def check_organization_access(self, user_id: str, organization_id: str) -> bool:
        """
        检查用户是否有权访问指定组织
        """
        accessible_orgs = self.get_user_accessible_organizations(user_id)
        return organization_id in accessible_orgs

    def filter_assets_by_organization(self, user_id: str, query: Any) -> Any:
        """
        根据用户组织权限过滤资产查询
        """
        accessible_orgs = self.get_user_accessible_organizations(user_id)

        if not accessible_orgs:
            return query.filter(False)  # 无权限访问任何组织

        # 获取这些组织的权属方列表
        org_names = (
            self.db.query(Organization.name)
            .filter(Organization.id.in_(accessible_orgs))
            .all()
        )
        org_name_list = [org[0] for org in org_names if org[0]]

        if org_name_list:
            return query.filter(
                or_(
                    Asset.ownership_entity.in_(org_name_list),
                    Asset.management_entity.in_(org_name_list),
                )
            )

        return query

    def filter_projects_by_organization(self, user_id: str, query: Any) -> Any:
        """
        根据用户组织权限过滤项目查询
        """
        accessible_orgs = self.get_user_accessible_organizations(user_id)

        if not accessible_orgs:
            return query.filter(False)

        # 获取这些组织的权属方列表
        org_names = (
            self.db.query(Organization.name)
            .filter(Organization.id.in_(accessible_orgs))
            .all()
        )
        org_name_list = [org[0] for org in org_names if org[0]]

        if org_name_list:
            return query.filter(Project.ownership_entity.in_(org_name_list))

        return query

    def filter_ownership_by_organization(self, user_id: str, query: Any) -> Any:
        """
        根据用户组织权限过滤权属方查询
        """
        accessible_orgs = self.get_user_accessible_organizations(user_id)

        if not accessible_orgs:
            return query.filter(False)

        # 获取这些组织的权属方列表
        org_names = (
            self.db.query(Organization.name)
            .filter(Organization.id.in_(accessible_orgs))
            .all()
        )
        org_name_list = [org[0] for org in org_names if org[0]]

        if org_name_list:
            return query.filter(Ownership.name.in_(org_name_list))

        return query

    def get_organization_descendants(self, organization_id: str) -> list[str]:
        """
        获取组织的所有子组织ID
        """
        organization = (
            self.db.query(Organization)
            .filter(Organization.id == organization_id)
            .first()
        )

        if not organization:
            return []

        # 查找所有以该组织路径开头的子组织
        descendants = (
            self.db.query(Organization.id)
            .filter(
                and_(
                    Organization.path.like(f"{organization.path}/%"),
                    not Organization.is_deleted,
                )
            )
            .all()
        )

        return [desc.id for desc in descendants]

    def get_organization_hierarchy(self, user_id: str) -> list[dict]:
        """
        获取用户可访问的组织层次结构
        """
        accessible_orgs = self.get_user_accessible_organizations_with_details(user_id)

        # 构建层次结构
        org_map = {org["id"]: org for org in accessible_orgs}
        root_orgs = []

        for org in accessible_orgs:
            if org["parent_id"] and org["parent_id"] in org_map:
                org_map[org["parent_id"]]["children"] = org_map.get(
                    org["parent_id"], {}
                ).get("children", [])
                org_map[org["parent_id"]]["children"].append(org)
            else:
                root_orgs.append(org)

        return root_orgs

    def _get_organization_tree_access(self, user_id: str) -> list[str]:
        """
        获取组织管理员的组织访问权限
        """
        # 查找用户管理的员工记录
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or not user.employee_id:
            return []

        employee = (
            self.db.query(Employee).filter(Employee.id == user.employee_id).first()
        )
        if not employee:
            return []

        # 获取用户所属组织及其所有子组织
        org_id = employee.organization_id
        accessible_orgs = [org_id]
        accessible_orgs.extend(self.get_organization_descendants(org_id))

        return accessible_orgs

    def _get_user_organization_access(self, user_id: str) -> list[str]:
        """
        获取普通用户的组织访问权限
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or not user.employee_id:
            return []

        employee = (
            self.db.query(Employee).filter(Employee.id == user.employee_id).first()
        )
        if not employee:
            return []

        # 获取用户所属组织及其所有子组织
        org_id = employee.organization_id
        accessible_orgs = [org_id]
        accessible_orgs.extend(self.get_organization_descendants(org_id))

        return accessible_orgs

    def get_user_organization_role(self, user_id: str) -> str | None:
        """
        获取用户在组织中的角色
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or not user.employee_id:
            return None

        employee = (
            self.db.query(Employee).filter(Employee.id == user.employee_id).first()
        )
        if not employee:
            return None

        # 检查是否是组织管理员
        position = employee.position
        if position and "manager" in position.name.lower():
            return "manager"

        return "member"

    def can_manage_organization(self, user_id: str, organization_id: str) -> bool:
        """
        检查用户是否可以管理指定组织
        """
        # 超级管理员可以管理所有组织
        user = self.db.query(User).filter(User.id == user_id).first()
        if user and user.role == "ADMIN":
            return True

        if not user or not user.employee_id:
            return False

        # 检查是否是该组织的管理员
        employee = (
            self.db.query(Employee)
            .filter(
                and_(
                    Employee.id == user.employee_id,
                    Employee.organization_id == organization_id,
                )
            )
            .first()
        )

        if employee and employee.position:
            return "manager" in employee.position.name.lower()

        return False

    def get_accessible_users_in_organization(
        self, user_id: str, organization_id: str
    ) -> list[str]:
        """
        获取用户在指定组织中可以访问的用户列表
        """
        if not self.check_organization_access(user_id, organization_id):
            return []

        # 获取该组织及其子组织的所有用户
        accessible_orgs = [organization_id]
        accessible_orgs.extend(self.get_organization_descendants(organization_id))

        users = (
            self.db.query(User.id)
            .join(Employee)
            .filter(Employee.organization_id.in_(accessible_orgs))
            .all()
        )

        return [user.id for user in users]
