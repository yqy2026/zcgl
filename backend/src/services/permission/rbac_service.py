from typing import Any, cast


class AssetNotFoundError(Exception):
    """Asset not found error"""

    pass


class DuplicateAssetError(Exception):
    """Duplicate asset error"""

    pass


"""
RBAC服务层
"""

import json
from datetime import UTC, datetime

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from ...exceptions import BusinessLogicError
from ...models.auth import User
from ...models.rbac import (
    Permission,
    PermissionAuditLog,
    ResourcePermission,
    Role,
    UserRoleAssignment,
    role_permissions,
)
from ...schemas.rbac import (
    PermissionCheckRequest,
    PermissionCheckResponse,
    PermissionCreate,
    RoleCreate,
    RoleUpdate,
    UserPermissionSummary,
    UserRoleAssignmentCreate,
)


class RBACService:
    """RBAC服务"""

    def __init__(self, db: Session):
        self.db = db

    # ==================== 角色管理 ====================

    def create_role(self, role_data: RoleCreate, created_by: str) -> Role:
        """创建角色"""
        # 检查角色名称唯一性
        existing_role = self.db.query(Role).filter(Role.name == role_data.name).first()
        if existing_role:
            raise BusinessLogicError("角色名称已存在")

        role = Role(
            name=role_data.name,
            display_name=role_data.display_name,
            description=role_data.description,
            level=role_data.level,
            category=role_data.category,
            is_system_role=role_data.is_system_role,
            organization_id=role_data.organization_id,
            scope=role_data.scope,
            scope_id=role_data.scope_id,
            created_by=created_by,
        )

        self.db.add(role)
        self.db.commit()
        self.db.refresh(role)

        # 添加权限
        if role_data.permission_ids:
            self._assign_permissions_to_role(
                cast("str", role.id), role_data.permission_ids, created_by
            )

        return role

    def update_role(self, role_id: str, role_data: RoleUpdate, updated_by: str) -> Role:
        """更新角色"""
        role = self.db.query(Role).filter(Role.id == role_id).first()
        if not role:
            raise BusinessLogicError("角色不存在")

        if cast("bool", role.is_system_role):
            raise BusinessLogicError("系统角色不能修改")

        # 检查名称唯一性
        if role_data.display_name and role_data.display_name != role.display_name:
            existing_role = (
                self.db.query(Role)
                .filter(and_(Role.display_name == role_data.display_name, Role.id != role_id))
                .first()
            )
            if existing_role:
                raise BusinessLogicError("角色显示名称已存在")

        # 更新字段
        update_data = role_data.dict(exclude_unset=True, exclude={"permission_ids"})
        for field, value in update_data.items():
            setattr(role, field, value)

        role.updated_at = datetime.now(UTC)  # type: ignore
        role.updated_by = updated_by  # type: ignore

        # 更新权限
        if role_data.permission_ids is not None:
            self._assign_permissions_to_role(
                cast("str", role.id), role_data.permission_ids, updated_by
            )

        self.db.commit()
        self.db.refresh(role)

        return role

    def delete_role(self, role_id: str, deleted_by: str) -> bool:
        """删除角色"""
        role = self.db.query(Role).filter(Role.id == role_id).first()
        if not role:
            return False

        if cast("bool", role.is_system_role):
            raise BusinessLogicError("系统角色不能删除")

        # 保存角色名称用于审计日志（在删除之前）
        role_name = role.name

        # 检查是否有用户使用此角色
        user_count = (
            self.db.query(UserRoleAssignment)
            .filter(
                and_(
                    UserRoleAssignment.role_id == role_id,
                    UserRoleAssignment.is_active,
                )
            )
            .count()
        )

        if user_count > 0:
            raise BusinessLogicError(f"角色正在被 {user_count} 个用户使用，无法删除")

        # 删除角色权限关联
        self.db.execute(Role.__table__.delete().where(Role.id == role_id))
        self.db.commit()

        # 记录审计日志（使用保存的role_name，因为role已被删除）
        self._create_permission_audit_log(
            action="role_delete",
            resource_type="role",
            resource_id=role_id,
            operator_id=deleted_by,
            old_permissions={"role_name": role_name},
            reason="角色删除",
        )

        return True

    def get_role(self, role_id: str) -> Role | None:
        """获取角色详情"""
        return self.db.query(Role).filter(Role.id == role_id).first()

    def get_roles(
        self,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
        category: str | None = None,
        is_active: bool | None = None,
        organization_id: str | None = None,
    ) -> tuple[list[Role], int]:
        """获取角色列表"""
        query = self.db.query(Role)

        # 搜索条件
        if search:
            search_filter = or_(
                Role.name.ilike(f"%{search}%"),
                Role.display_name.ilike(f"%{search}%"),
                Role.description.ilike(f"%{search}%"),
            )
            query = query.filter(search_filter)

        # 筛选条件
        if category:
            query = query.filter(Role.category == category)
        if is_active is not None:
            query = query.filter(Role.is_active == is_active)
        if organization_id:
            query = query.filter(Role.organization_id == organization_id)

        # 总数
        total = query.count()

        # 分页
        roles = query.order_by(Role.level, Role.name).offset(skip).limit(limit).all()

        return roles, total

    # ==================== 权限管理 ====================

    def create_permission(self, permission_data: PermissionCreate, created_by: str) -> Permission:
        """创建权限"""
        # 检查权限名称唯一性
        existing_permission = (
            self.db.query(Permission).filter(Permission.name == permission_data.name).first()
        )
        if existing_permission:
            raise BusinessLogicError("权限名称已存在")

        permission = Permission(
            name=permission_data.name,
            display_name=permission_data.display_name,
            description=permission_data.description,
            resource=permission_data.resource,
            action=permission_data.action,
            max_level=permission_data.max_level,
            conditions=json.dumps(permission_data.conditions)
            if permission_data.conditions
            else None,
            is_system_permission=permission_data.is_system_permission,
            requires_approval=permission_data.requires_approval,
            created_by=created_by,
        )

        self.db.add(permission)
        self.db.commit()
        self.db.refresh(permission)

        return permission

    def get_permission(self, permission_id: str) -> Permission | None:
        """获取权限详情"""
        return self.db.query(Permission).filter(Permission.id == permission_id).first()

    def get_permissions(
        self,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
        resource: str | None = None,
        action: str | None = None,
        is_system_permission: bool | None = None,
    ) -> tuple[list[Permission], int]:
        """获取权限列表"""
        query = self.db.query(Permission)

        # 搜索条件
        if search:
            search_filter = or_(
                Permission.name.ilike(f"%{search}%"),
                Permission.display_name.ilike(f"%{search}%"),
                Permission.description.ilike(f"%{search}%"),
            )
            query = query.filter(search_filter)

        # 筛选条件
        if resource:
            query = query.filter(Permission.resource == resource)
        if action:
            query = query.filter(Permission.action == action)
        if is_system_permission is not None:
            query = query.filter(Permission.is_system_permission == is_system_permission)

        # 总数
        total = query.count()

        # 分页
        permissions = (
            query.order_by(Permission.resource, Permission.action).offset(skip).limit(limit).all()
        )

        return permissions, total

    # ==================== 用户角色分配 ====================

    def assign_role_to_user(
        self, assignment_data: UserRoleAssignmentCreate, assigned_by: str
    ) -> UserRoleAssignment:
        """为用户分配角色"""
        # 检查用户是否存在
        user = self.db.query(User).filter(User.id == assignment_data.user_id).first()
        if not user:
            raise BusinessLogicError("用户不存在")

        # 检查角色是否存在
        role = self.db.query(Role).filter(Role.id == assignment_data.role_id).first()
        if not role:
            raise BusinessLogicError("角色不存在")

        # 检查是否已分配
        existing_assignment = (
            self.db.query(UserRoleAssignment)
            .filter(
                and_(
                    UserRoleAssignment.user_id == assignment_data.user_id,
                    UserRoleAssignment.role_id == assignment_data.role_id,
                    UserRoleAssignment.is_active,
                )
            )
            .first()
        )

        if existing_assignment:
            raise BusinessLogicError("用户已分配此角色")

        assignment = UserRoleAssignment(
            user_id=assignment_data.user_id,
            role_id=assignment_data.role_id,
            assigned_by=assigned_by,
            expires_at=assignment_data.expires_at,
            reason=assignment_data.reason,
            notes=assignment_data.notes,
            context=json.dumps(assignment_data.context) if assignment_data.context else None,
        )

        self.db.add(assignment)
        self.db.commit()
        self.db.refresh(assignment)

        # 记录审计日志
        self._create_permission_audit_log(
            action="role_assign",
            resource_type="user_role",
            resource_id=assignment_data.user_id,
            operator_id=assigned_by,
            new_permissions={
                "role_id": assignment_data.role_id,
                "role_name": role.name,
            },
            reason=assignment_data.reason,
        )

        return assignment

    def revoke_role_from_user(self, user_id: str, role_id: str, revoked_by: str) -> bool:
        """撤销用户角色"""
        assignment = (
            self.db.query(UserRoleAssignment)
            .filter(
                and_(
                    UserRoleAssignment.user_id == user_id,
                    UserRoleAssignment.role_id == role_id,
                    UserRoleAssignment.is_active,
                )
            )
            .first()
        )

        if not assignment:
            return False

        assignment.is_active = False  # type: ignore
        assignment.updated_at = datetime.now(UTC)  # type: ignore

        self.db.commit()

        # 记录审计日志
        self._create_permission_audit_log(
            action="role_revoke",
            resource_type="user_role",
            resource_id=user_id,
            operator_id=revoked_by,
            old_permissions={"role_id": role_id},
            reason="角色撤销",
        )

        return True

    def get_user_roles(self, user_id: str, active_only: bool = True) -> list[Role]:
        """获取用户角色"""
        query = (
            self.db.query(Role)
            .join(UserRoleAssignment)
            .filter(UserRoleAssignment.user_id == user_id)
        )

        if active_only:
            query = query.filter(UserRoleAssignment.is_active)
            query = query.filter(
                or_(
                    UserRoleAssignment.expires_at.is_(None),
                    UserRoleAssignment.expires_at > datetime.now(UTC),
                )
            )

        return query.all()

    # ==================== 权限检查 ====================

    def check_permission(
        self, user_id: str, permission_request: PermissionCheckRequest
    ) -> PermissionCheckResponse:
        """检查用户权限"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or not cast("bool", user.is_active):
            return PermissionCheckResponse(
                has_permission=False, reason="用户不存在或已禁用", conditions=None
            )

        # 管理员拥有所有权限
        if cast("str", user.role) == "admin":
            return PermissionCheckResponse(
                has_permission=True,
                granted_by=["admin_role"],
                conditions=None,
                reason=None,
            )

        # 获取用户的有效角色
        user_roles = self.get_user_roles(user_id)
        if not user_roles:
            return PermissionCheckResponse(
                has_permission=False, reason="用户未分配任何角色", conditions=None
            )

        # 检查资源权限
        resource_permissions = self._get_user_resource_permissions(user_id, permission_request)
        if resource_permissions:
            return PermissionCheckResponse(
                has_permission=True,
                granted_by=["resource_permission"],
                conditions=resource_permissions.get("conditions"),
                reason=None,
            )

        # 检查角色权限
        granted_by = []
        conditions = None

        for role in user_roles:
            if self._role_has_permission(role, permission_request):
                granted_by.append(f"role_{role.name}")
                # 如果有权限条件，使用最严格的条件
                role_conditions = self._get_role_permission_conditions(role, permission_request)
                if role_conditions:
                    conditions = (
                        role_conditions if not conditions else {**conditions, **role_conditions}
                    )

        return PermissionCheckResponse(
            has_permission=len(granted_by) > 0,
            granted_by=granted_by,
            conditions=conditions,
            reason=None,
        )

    def get_user_permissions_summary(self, user_id: str) -> UserPermissionSummary:
        """获取用户权限汇总"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise BusinessLogicError("用户不存在")

        # 获取用户角色
        roles = self.get_user_roles(user_id)

        # 获取角色权限
        role_permissions = set()
        for role in roles:
            for permission in role.permissions:
                role_permissions.add(permission)

        # 获取资源权限
        resource_permissions = (
            self.db.query(ResourcePermission)
            .filter(
                and_(
                    ResourcePermission.user_id == user_id,
                    ResourcePermission.is_active,
                    or_(
                        ResourcePermission.expires_at.is_(None),
                        ResourcePermission.expires_at > datetime.now(),
                    ),
                )
            )
            .all()
        )

        # 计算有效权限
        effective_permissions = self._calculate_effective_permissions(roles, resource_permissions)

        return UserPermissionSummary(
            user_id=user_id,
            username=cast("str", user.username),
            roles=roles,  # type: ignore
            permissions=list(role_permissions),
            resource_permissions=resource_permissions,  # type: ignore
            effective_permissions=effective_permissions,
        )

    # ==================== 私有方法 ====================

    def _assign_permissions_to_role(
        self, role_id: str, permission_ids: list[str], operator_id: str
    ):
        """为角色分配权限"""

        # 清除现有权限
        self.db.execute(role_permissions.delete().where(role_permissions.c.role_id == role_id))

        # 添加新权限
        for permission_id in permission_ids:
            self.db.execute(
                role_permissions.insert().values(
                    role_id=role_id, permission_id=permission_id, created_by=operator_id
                )
            )

    def _get_user_resource_permissions(
        self, user_id: str, permission_request: PermissionCheckRequest
    ) -> dict[str, Any] | None:
        """获取用户资源权限"""
        permission = (
            self.db.query(ResourcePermission)
            .filter(
                and_(
                    ResourcePermission.user_id == user_id,
                    ResourcePermission.resource_type == permission_request.resource,
                    or_(
                        ResourcePermission.resource_id.is_(None),
                        ResourcePermission.resource_id == permission_request.resource_id,
                    ),
                    ResourcePermission.is_active,
                    or_(
                        ResourcePermission.expires_at.is_(None),
                        ResourcePermission.expires_at > datetime.now(),
                    ),
                )
            )
            .first()
        )

        if not permission:
            return None

        # 检查权限级别
        if not self._check_permission_level(
            cast("str", permission.permission_level), permission_request.action
        ):
            return None

        return {
            "permission_level": permission.permission_level,
            "conditions": json.loads(cast("str", permission.conditions))
            if cast("str", permission.conditions)
            else None,
        }

    def _role_has_permission(self, role: Role, permission_request: PermissionCheckRequest) -> bool:
        """检查角色是否有权限"""
        for permission in role.permissions:
            if (
                permission.resource == permission_request.resource
                and permission.action == permission_request.action
            ):
                return True
        return False

    def _get_role_permission_conditions(
        self, role: Role, permission_request: PermissionCheckRequest
    ) -> dict[str, Any] | None:
        """获取角色权限条件"""
        for permission in role.permissions:
            if (
                permission.resource == permission_request.resource
                and permission.action == permission_request.action
            ):
                return json.loads(permission.conditions) if permission.conditions else None
        return None  # pragma: no cover  # Defensive: only reached if role_has_permission check is bypassed

    def _check_permission_level(self, permission_level: str, action: str) -> bool:
        """检查权限级别"""
        level_hierarchy = {
            "read": ["read"],
            "write": ["read", "write"],
            "delete": ["read", "write", "delete"],
            "admin": ["read", "write", "delete", "admin"],
        }

        return action in level_hierarchy.get(permission_level, [])

    def _calculate_effective_permissions(
        self, roles: list[Role], resource_permissions: list
    ) -> dict[str, list[str]]:
        """计算有效权限"""
        effective_permissions = {}

        # 角色权限
        for role in roles:
            for permission in role.permissions:
                resource = permission.resource
                action = permission.action

                if resource not in effective_permissions:
                    effective_permissions[resource] = []
                if action not in effective_permissions[resource]:
                    effective_permissions[resource].append(action)

        # 资源权限
        for rp in resource_permissions:
            resource = rp.resource_type

            # 根据权限级别添加权限
            level_actions = {
                "read": ["read"],
                "write": ["read", "write"],
                "delete": ["read", "write", "delete"],
                "admin": ["read", "write", "delete", "admin"],
            }

            actions = level_actions.get(rp.permission_level, [])
            for action in actions:
                if resource not in effective_permissions:
                    effective_permissions[resource] = []
                if action not in effective_permissions[resource]:
                    effective_permissions[resource].append(action)

        return effective_permissions

    def _create_permission_audit_log(
        self,
        action: str,
        resource_type: str,
        resource_id: str,
        operator_id: str,
        old_permissions: dict | None = None,
        new_permissions: dict | None = None,
        reason: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ):
        """创建权限审计日志"""
        audit_log = PermissionAuditLog(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            operator_id=operator_id,
            old_permissions=json.dumps(old_permissions) if old_permissions else None,
            new_permissions=json.dumps(new_permissions) if new_permissions else None,
            reason=reason,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        self.db.add(audit_log)
        self.db.commit()

    def _can_manage_role(self, manager_level: int, subordinate_level: int) -> bool:
        """检查是否可以管理指定级别的角色"""
        return manager_level > subordinate_level

    # ==================== Permission Decorator Adapter Methods ====================
    # These methods provide the interface expected by permission decorators
    # They adapt the existing check_permission method to the decorator's expected signature

    async def check_user_permission(self, user_id: str, resource: str, action: str) -> bool:
        """
        检查用户权限 - 适配器方法供装饰器使用

        Args:
            user_id: 用户ID
            resource: 资源名称 (如: 'asset', 'user', 'role')
            action: 操作类型 (如: 'view', 'create', 'edit', 'delete')

        Returns:
            bool: 是否有权限
        """
        from ...schemas.rbac import PermissionCheckRequest

        permission_request = PermissionCheckRequest(
            resource=resource,
            action=action,
        )

        response = self.check_permission(user_id, permission_request)
        return response.has_permission

    async def check_resource_access(
        self, user_id: str, resource: str, resource_id: str, action: str
    ) -> bool:
        """
        检查资源访问权限 - 适配器方法供装饰器使用

        Args:
            user_id: 用户ID
            resource: 资源名称
            resource_id: 资源ID
            action: 操作类型

        Returns:
            bool: 是否有访问权限
        """
        from ...schemas.rbac import PermissionCheckRequest

        permission_request = PermissionCheckRequest(
            resource=resource,
            action=action,
            resource_id=resource_id,
        )

        response = self.check_permission(user_id, permission_request)
        return response.has_permission

    async def check_organization_access(self, user_id: str, organization_id: str) -> bool:
        """
        检查组织访问权限 - 适配器方法供装饰器使用

        Args:
            user_id: 用户ID
            organization_id: 组织ID

        Returns:
            bool: 是否有组织访问权限
        """
        from ...schemas.rbac import PermissionCheckRequest

        permission_request = PermissionCheckRequest(
            resource="organization",
            action="view",
            organization_id=organization_id,
        )

        response = self.check_permission(user_id, permission_request)
        return response.has_permission
