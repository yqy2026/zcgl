from typing import Any


class AssetNotFoundError(Exception):
    """Asset not found error"""

    pass


class DuplicateAssetError(Exception):
    """Duplicate asset error"""

    pass


"""
RBAC服务层
"""

from datetime import UTC, datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.exception_handler import (
    DuplicateResourceError,
    InternalServerError,
    OperationNotAllowedError,
    ResourceConflictError,
    ResourceNotFoundError,
)
from ...crud.auth import UserCRUD
from ...crud.rbac import (
    permission_audit_log_crud,
    permission_crud,
    role_crud,
    user_role_assignment_crud,
)
from ...models.rbac import (
    Permission,
    ResourcePermission,
    Role,
    UserRoleAssignment,
    role_permissions,
)
from ...schemas.rbac import (
    PermissionCheckRequest,
    PermissionCheckResponse,
    PermissionCreate,
    PermissionResponse,
    ResourcePermissionResponse,
    RoleCreate,
    RoleResponse,
    RoleUpdate,
    UserPermissionSummary,
    UserRoleAssignmentCreate,
)

# RBAC role names that should be treated as full administrators
ADMIN_ROLE_NAMES = {"admin", "super_admin"}


class RBACService:
    """RBAC服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_crud = UserCRUD()

    @staticmethod
    def _is_admin_role(role: Role) -> bool:
        return role.name.lower() in ADMIN_ROLE_NAMES

    # ==================== 角色管理 ====================

    async def create_role(self, role_data: RoleCreate, created_by: str) -> Role:
        """创建角色"""
        existing_role = await role_crud.get_by_name(self.db, name=role_data.name)
        if existing_role:
            raise DuplicateResourceError("角色", "name", role_data.name)

        role = await role_crud.create(
            self.db, obj_in=role_data, created_by=created_by
        )

        # 添加权限
        if role_data.permission_ids:
            await self.update_role_permissions(
                role_id=str(role.id),
                permission_ids=role_data.permission_ids,
                updated_by=created_by,
            )

        return role

    async def update_role(
        self, role_id: str, role_data: RoleUpdate, updated_by: str
    ) -> Role:
        """更新角色"""
        role = await role_crud.get(self.db, id=role_id)
        if not role:
            raise ResourceNotFoundError("角色", role_id)

        if role.is_system_role:
            raise OperationNotAllowedError("系统角色不能修改", reason="system_role")

        # 检查名称唯一性
        if role_data.display_name and role_data.display_name != role.display_name:
            existing_role = (
                (
                    await self.db.execute(
                        select(Role).where(
                            and_(
                                Role.display_name == role_data.display_name,
                                Role.id != role_id,
                            )
                        )
                    )
                )
                .scalars()
                .first()
            )
            if existing_role:
                raise DuplicateResourceError("角色", "display_name", role_data.display_name)

        # 更新字段
        update_data = role_data.model_dump(
            exclude_unset=True, exclude={"permission_ids"}
        )
        if update_data:
            update_data["updated_at"] = datetime.now(UTC)
            update_data["updated_by"] = updated_by
            role = await role_crud.update(self.db, db_obj=role, obj_in=update_data)

        # 更新权限
        if role_data.permission_ids is not None:
            await self.update_role_permissions(
                role_id=str(role.id),
                permission_ids=role_data.permission_ids,
                updated_by=updated_by,
            )

        return role

    async def delete_role(self, role_id: str, deleted_by: str) -> bool:
        """删除角色"""
        role = await role_crud.get(self.db, id=role_id)
        if not role:
            return False

        if role.is_system_role:
            raise OperationNotAllowedError("系统角色不能删除", reason="system_role")

        # 保存角色名称用于审计日志（在删除之前）
        role_name = role.name

        # 检查是否有用户使用此角色
        user_count = await user_role_assignment_crud.count_by_role(
            self.db, role_id=role_id
        )

        if user_count > 0:
            raise OperationNotAllowedError(
                f"角色正在被 {user_count} 个用户使用，无法删除",
                reason="role_in_use",
            )

        try:
            await role_crud.remove(self.db, id=role_id)
        except Exception as exc:  # pragma: no cover - defensive for DB layer errors
            raise InternalServerError("删除角色失败", original_error=exc) from exc

        # 记录审计日志（使用保存的role_name，因为role已被删除）
        await self._create_permission_audit_log(
            action="role_delete",
            resource_type="role",
            resource_id=role_id,
            operator_id=deleted_by,
            old_permissions={"role_name": role_name},
            reason="角色删除",
        )

        return True

    async def update_role_permissions(
        self,
        *,
        role_id: str,
        permission_ids: list[str],
        updated_by: str,
    ) -> None:
        """更新角色权限"""
        role = await role_crud.get(self.db, id=role_id)
        if not role:
            raise ResourceNotFoundError("角色", role_id)
        if role.is_system_role:
            raise OperationNotAllowedError("系统角色权限无法修改", reason="system_role")

        await self._assign_permissions_to_role(role_id, permission_ids, updated_by)
        await self.db.commit()

    async def get_role(self, role_id: str) -> Role | None:
        """获取角色详情"""
        return await role_crud.get(self.db, id=role_id)

    async def get_roles(
        self,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
        category: str | None = None,
        is_active: bool | None = None,
        organization_id: str | None = None,
    ) -> tuple[list[Role], int]:
        """获取角色列表"""
        return await role_crud.get_multi_with_filters(
            db=self.db,
            skip=skip,
            limit=limit,
            search=search,
            category=category,
            is_active=is_active,
            organization_id=organization_id,
        )

    # ==================== 权限管理 ====================

    async def create_permission(
        self, permission_data: PermissionCreate, created_by: str
    ) -> Permission:
        """创建权限"""
        existing_permission = await permission_crud.get_by_name(
            self.db, name=permission_data.name
        )
        if existing_permission:
            raise DuplicateResourceError("权限", "name", permission_data.name)

        return await permission_crud.create(
            self.db, obj_in=permission_data, created_by=created_by
        )

    async def get_permission(self, permission_id: str) -> Permission | None:
        """获取权限详情"""
        return await permission_crud.get(self.db, id=permission_id)

    async def get_permissions(
        self,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
        resource: str | None = None,
        action: str | None = None,
        is_system_permission: bool | None = None,
    ) -> tuple[list[Permission], int]:
        """获取权限列表"""
        filters: dict[str, Any] = {}
        if resource:
            filters["resource"] = resource
        if action:
            filters["action"] = action
        if is_system_permission is not None:
            filters["is_system_permission"] = is_system_permission

        stmt = permission_crud.query_builder.build_query(
            filters=filters,
            search_query=search,
            search_fields=["name", "display_name", "description"],
            sort_by="resource",
            sort_desc=False,
            skip=skip,
            limit=limit,
        )
        permissions = list((await self.db.execute(stmt)).scalars().all())

        count_stmt = permission_crud.query_builder.build_count_query(
            filters=filters,
            search_query=search,
            search_fields=["name", "display_name", "description"],
        )
        total = int((await self.db.execute(count_stmt)).scalar() or 0)

        return permissions, total

    # ==================== 用户角色分配 ====================

    async def assign_role_to_user(
        self, assignment_data: UserRoleAssignmentCreate, assigned_by: str
    ) -> UserRoleAssignment:
        """为用户分配角色"""
        user = await self.user_crud.get_async(self.db, assignment_data.user_id)
        if not user:
            raise ResourceNotFoundError("用户", assignment_data.user_id)

        # 检查角色是否存在
        role = await role_crud.get(self.db, id=assignment_data.role_id)
        if not role:
            raise ResourceNotFoundError("角色", assignment_data.role_id)

        # 检查是否已分配
        existing_assignment = await user_role_assignment_crud.get_by_user_and_role(
            self.db,
            user_id=assignment_data.user_id,
            role_id=assignment_data.role_id,
        )

        if existing_assignment:
            if existing_assignment.is_active:
                raise ResourceConflictError(
                    "用户已分配此角色",
                    resource_type="user_role_assignment",
                )
            existing_assignment.is_active = True
            existing_assignment.expires_at = assignment_data.expires_at
            existing_assignment.assigned_by = assigned_by
            existing_assignment.assigned_at = datetime.now(UTC)
            existing_assignment.reason = assignment_data.reason
            existing_assignment.notes = assignment_data.notes
            existing_assignment.context = assignment_data.context
            await self.db.commit()
            await self.db.refresh(existing_assignment)
            assignment = existing_assignment
        else:
            assignment = await user_role_assignment_crud.create(
                self.db,
                obj_in=assignment_data,
                assigned_by=assigned_by,
            )

        # 记录审计日志
        await self._create_permission_audit_log(
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

    async def revoke_role_from_user(
        self, user_id: str, role_id: str, revoked_by: str
    ) -> bool:
        """撤销用户角色"""
        assignment = await user_role_assignment_crud.get_by_user_and_role(
            self.db, user_id=user_id, role_id=role_id
        )

        if not assignment or not assignment.is_active:
            return False

        assignment.is_active = False
        assignment.updated_at = datetime.now(UTC)

        await self.db.commit()

        # 记录审计日志
        await self._create_permission_audit_log(
            action="role_revoke",
            resource_type="user_role",
            resource_id=user_id,
            operator_id=revoked_by,
            old_permissions={"role_id": role_id},
            reason="角色撤销",
        )

        return True

    async def revoke_user_role(
        self, user_id: str, role_id: str, revoked_by: str | None = None
    ) -> bool:
        """撤销用户角色（兼容命名）"""
        operator_id = revoked_by or user_id
        return await self.revoke_role_from_user(user_id, role_id, revoked_by=operator_id)

    async def get_user_roles(
        self, user_id: str, active_only: bool = True
    ) -> list[Role]:
        """获取用户角色"""
        stmt = (
            select(Role)
            .join(UserRoleAssignment)
            .where(UserRoleAssignment.user_id == user_id)
            .options(selectinload(Role.permissions))
        )

        if active_only:
            stmt = stmt.where(UserRoleAssignment.is_active)
            stmt = stmt.where(
                or_(
                    UserRoleAssignment.expires_at.is_(None),
                    UserRoleAssignment.expires_at > datetime.now(UTC),
                )
            )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ==================== 权限检查 ====================

    async def check_permission(
        self, user_id: str, permission_request: PermissionCheckRequest
    ) -> PermissionCheckResponse:
        """检查用户权限"""
        user = await self.user_crud.get_async(self.db, user_id)
        if not user or not user.is_active:
            return PermissionCheckResponse(
                has_permission=False, reason="用户不存在或已禁用", conditions=None
            )

        # 获取用户的有效角色
        user_roles = await self.get_user_roles(user_id)
        if any(self._is_admin_role(role) for role in user_roles):
            return PermissionCheckResponse(
                has_permission=True,
                granted_by=["admin_role"],
                conditions=None,
                reason=None,
            )
        if not user_roles:
            return PermissionCheckResponse(
                has_permission=False, reason="用户未分配任何角色", conditions=None
            )

        # 检查资源权限
        resource_permissions = await self._get_user_resource_permissions(
            user_id, permission_request
        )
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
                role_conditions = self._get_role_permission_conditions(
                    role, permission_request
                )
                if role_conditions:
                    if conditions is None:
                        conditions = role_conditions
                    else:
                        conditions = {**conditions, **role_conditions}

        return PermissionCheckResponse(
            has_permission=len(granted_by) > 0,
            granted_by=granted_by,
            conditions=conditions,
            reason=None,
        )

    async def is_admin(self, user_id: str) -> bool:
        """判断用户是否为管理员（基于RBAC角色）"""
        roles = await self.get_user_roles(user_id)
        return any(self._is_admin_role(role) for role in roles)

    async def get_user_role_summary(self, user_id: str) -> dict[str, Any]:
        """获取用户角色汇总信息（含主角色与管理员标记）"""
        roles = await self.get_user_roles(user_id)
        roles_sorted = sorted(roles, key=lambda role: role.level or 0)
        primary = roles_sorted[0] if roles_sorted else None
        return {
            "roles": [role.name for role in roles_sorted],
            "role_ids": [str(role.id) for role in roles_sorted],
            "primary_role_id": str(primary.id) if primary else None,
            "primary_role_name": (
                primary.display_name if primary and primary.display_name else None
            ),
            "is_admin": any(self._is_admin_role(role) for role in roles_sorted),
        }

    async def get_user_permissions_summary(self, user_id: str) -> UserPermissionSummary:
        """获取用户权限汇总"""
        user = await self.user_crud.get_async(self.db, user_id)
        if not user:
            raise ResourceNotFoundError("用户", user_id)

        # 获取用户角色
        roles = await self.get_user_roles(user_id)

        # 获取角色权限
        role_permissions = set()
        for role in roles:
            for permission in role.permissions:
                role_permissions.add(permission)

        # 获取资源权限
        resource_permissions_stmt = select(ResourcePermission).where(
            and_(
                ResourcePermission.user_id == user_id,
                ResourcePermission.is_active,
                or_(
                    ResourcePermission.expires_at.is_(None),
                    ResourcePermission.expires_at > datetime.now(),
                ),
            )
        )
        resource_permissions = list(
            (await self.db.execute(resource_permissions_stmt)).scalars().all()
        )

        # 计算有效权限
        effective_permissions = self._calculate_effective_permissions(
            roles, resource_permissions
        )

        roles_response = [RoleResponse.model_validate(role) for role in roles]
        permissions_response = [
            PermissionResponse.model_validate(permission)
            for permission in role_permissions
        ]
        resource_permissions_response = [
            ResourcePermissionResponse.model_validate(resource_permission)
            for resource_permission in resource_permissions
        ]

        return UserPermissionSummary(
            user_id=user_id,
            username=user.username,
            roles=roles_response,
            permissions=permissions_response,
            resource_permissions=resource_permissions_response,
            effective_permissions=effective_permissions,
        )

    # ==================== 私有方法 ====================

    async def _assign_permissions_to_role(
        self, role_id: str, permission_ids: list[str], operator_id: str
    ) -> None:
        """为角色分配权限"""
        stmt = (
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.id == role_id)
        )
        role = (await self.db.execute(stmt)).scalars().first()
        if not role:
            raise ResourceNotFoundError("角色", role_id)
        if role.is_system_role:
            raise OperationNotAllowedError(
                "系统角色权限无法修改", reason="system_role"
            )

        permissions: list[Permission] = []
        if permission_ids:
            stmt = select(Permission).where(Permission.id.in_(permission_ids))
            permissions = list((await self.db.execute(stmt)).scalars().all())
            found_ids = {str(permission.id) for permission in permissions}
            missing_ids = sorted(set(permission_ids) - found_ids)
            if missing_ids:
                raise ResourceNotFoundError(
                    "权限",
                    ",".join(missing_ids),
                    details={"missing_permission_ids": missing_ids},
                )

        role.permissions.clear()
        if permissions:
            role.permissions.extend(permissions)
        role.updated_at = datetime.now(UTC)
        role.updated_by = operator_id

        await self.db.flush()
        await self.db.execute(
            role_permissions.update()
            .where(role_permissions.c.role_id == role_id)
            .values(created_by=operator_id)
        )

    async def _get_user_resource_permissions(
        self, user_id: str, permission_request: PermissionCheckRequest
    ) -> dict[str, Any] | None:
        """获取用户资源权限"""
        stmt = select(ResourcePermission).where(
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
        permission = (await self.db.execute(stmt)).scalars().first()

        if not permission:
            return None

        # 检查权限级别
        if not self._check_permission_level(
            permission.permission_level, permission_request.action
        ):
            return None

        return {
            "permission_level": permission.permission_level,
            "conditions": permission.conditions if permission.conditions else None,
        }

    def _role_has_permission(
        self, role: Role, permission_request: PermissionCheckRequest
    ) -> bool:
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
                return permission.conditions if permission.conditions else None
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
        self, roles: list[Role], resource_permissions: list[Any]
    ) -> dict[str, list[str]]:
        """计算有效权限"""
        effective_permissions: dict[str, list[str]] = {}

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

    async def _create_permission_audit_log(
        self,
        action: str,
        resource_type: str,
        resource_id: str,
        operator_id: str,
        old_permissions: dict[str, Any] | None = None,
        new_permissions: dict[str, Any] | None = None,
        reason: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """创建权限审计日志"""
        await permission_audit_log_crud.create(
            self.db,
            obj_in={
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "operator_id": operator_id,
                "old_permissions": old_permissions,
                "new_permissions": new_permissions,
                "reason": reason,
                "ip_address": ip_address,
                "user_agent": user_agent,
            },
        )

    def _can_manage_role(self, manager_level: int, subordinate_level: int) -> bool:
        """检查是否可以管理指定级别的角色"""
        return manager_level > subordinate_level

    # ==================== Permission Decorator Adapter Methods ====================
    # These methods provide the interface expected by permission decorators
    # They adapt the existing check_permission method to the decorator's expected signature

    async def check_user_permission(
        self, user_id: str, resource: str, action: str
    ) -> bool:
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
            resource_id=None,
            context=None,
        )

        response = await self.check_permission(user_id, permission_request)
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
            context=None,
        )

        response = await self.check_permission(user_id, permission_request)
        return response.has_permission

    async def check_organization_access(
        self, user_id: str, organization_id: str
    ) -> bool:
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
            resource_id=organization_id,
            context=None,
        )

        response = await self.check_permission(user_id, permission_request)
        return response.has_permission
