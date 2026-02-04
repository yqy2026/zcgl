from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception_handler import (
    DuplicateResourceError,
    InternalServerError,
    OperationNotAllowedError,
    ResourceConflictError,
    ResourceNotFoundError,
)
from ...crud.rbac import (
    permission_crud,
    role_crud,
    user_role_assignment_crud,
)
from ...models.rbac import Permission, Role, UserRoleAssignment
from ...schemas.rbac import (
    RoleCreate,
    RoleUpdate,
    UserRoleAssignmentCreate,
)


class RBACService:
    """RBAC服务层，封装业务逻辑"""

    # ================= Role Management =================

    async def create_role(
        self, db: AsyncSession, *, obj_in: RoleCreate, created_by: str
    ) -> Role:
        """创建角色"""
        # 业务规则：名称唯一
        existing_role = await role_crud.get_by_name(db, name=obj_in.name)
        if existing_role:
            raise DuplicateResourceError("角色", "name", obj_in.name)

        # Create role
        role: Role = await role_crud.create(
            db, obj_in=obj_in, created_by=created_by
        )

        # Handle initial permissions
        if obj_in.permission_ids:
            await self.update_role_permissions(
                db,
                role_id=str(role.id),
                permission_ids=obj_in.permission_ids,
                updated_by=created_by,
            )

        return role

    async def update_role(
        self, db: AsyncSession, *, role_id: str, obj_in: RoleUpdate, updated_by: str
    ) -> Role:
        """更新角色"""
        role = await role_crud.get(db, id=role_id)
        if not role:
            raise ResourceNotFoundError("角色", role_id)

        if role.is_system_role:
            # System roles typically have restrictions, but let's allow updating non-critical fields if needed.
            # Current logic restricts modification of system roles.
            pass

        # Update basic fields
        role = await role_crud.update(db, db_obj=role, obj_in=obj_in)
        # Set audit fields manually (needs separate commit)
        role.updated_by = updated_by
        db.add(role)
        await db.commit()
        await db.refresh(role)

        # Update permissions if provided
        if obj_in.permission_ids is not None:
            await self.update_role_permissions(
                db,
                role_id=role.id,
                permission_ids=obj_in.permission_ids,
                updated_by=updated_by,
            )

        return role

    async def delete_role(
        self, db: AsyncSession, *, role_id: str, deleted_by: str
    ) -> bool:
        """删除角色"""
        role = await role_crud.get(db, id=role_id)
        if not role:
            return False

        if role.is_system_role:
            raise OperationNotAllowedError(
                "系统角色不能删除",
                reason="system_role",
            )

        # Check usage
        user_count = await user_role_assignment_crud.count_by_role(
            db, role_id=role_id
        )
        if user_count > 0:
            raise OperationNotAllowedError(
                f"角色正在被 {user_count} 个用户使用，无法删除",
                reason="role_in_use",
            )

        # Use remove instead of delete (CRUDBase has remove, not delete)
        try:
            await role_crud.remove(db, id=role_id)
            return True
        except Exception as exc:
            raise InternalServerError("删除角色失败", original_error=exc) from exc

    async def update_role_permissions(
        self, db: AsyncSession, *, role_id: str, permission_ids: list[str], updated_by: str
    ) -> None:
        """更新角色权限"""
        role = await role_crud.get(db, id=role_id)
        if not role:
            raise ResourceNotFoundError("角色", role_id)

        if role.is_system_role:
            # Depends on policy. Let's assume system roles' permissions are fixed in code/migration.
            raise OperationNotAllowedError(
                "系统角色权限无法修改",
                reason="system_role",
            )

        # Clear existing
        role.permissions.clear()

        # Add new
        for perm_id in permission_ids:
            perm = await permission_crud.get(db, id=perm_id)
            if perm:
                role.permissions.append(perm)

        role.updated_by = updated_by
        role.updated_at = datetime.now()
        await db.commit()
        await db.refresh(role)

    # ================= User Assignment Management =================

    async def assign_role_to_user(
        self, db: AsyncSession, *, obj_in: UserRoleAssignmentCreate, assigned_by: str
    ) -> UserRoleAssignment:
        """分配角色给用户"""
        # Check if already assigned
        existing = await user_role_assignment_crud.get_by_user_and_role(
            db, user_id=obj_in.user_id, role_id=obj_in.role_id
        )
        if existing:
            # If inactive, reactivate? Or raise?
            if not existing.is_active:
                existing.is_active = True
                existing.expires_at = obj_in.expires_at
                existing.assigned_by = assigned_by
                existing.assigned_at = datetime.now()
                await db.commit()
                return existing
            else:
                raise ResourceConflictError(
                    "用户已分配此角色",
                    resource_type="user_role_assignment",
                )

        return await user_role_assignment_crud.create(
            db, obj_in=obj_in, assigned_by=assigned_by
        )

    async def revoke_user_role(
        self, db: AsyncSession, *, user_id: str, role_id: str
    ) -> bool:
        """撤销用户角色"""
        assignment = await user_role_assignment_crud.get_by_user_and_role(
            db, user_id=user_id, role_id=role_id
        )
        if not assignment or not assignment.is_active:
            return False

        assignment.is_active = False
        assignment.updated_at = datetime.now()
        await db.commit()
        return True

    # ================= Permission Check =================

    async def check_permission(
        self, db: AsyncSession, *, user_id: str, resource: str, action: str
    ) -> bool:
        """检查用户是否有特定权限"""
        # 1. Check Super Admin (if implied, distinct from RBAC)

        # 2. Check Role Permissions
        user_roles = await user_role_assignment_crud.get_user_active_assignments(
            db, user_id=user_id
        )
        role_ids = [ur.role_id for ur in user_roles]

        # This query implies: find a permission that matches resource/action and is assigned to one of the user's roles
        # Optimization: Use SQL Join
        # Permission -> RolePermission -> Role -> UserRoleAssignment
        # But for now, iterate or use existing check logic if simple.

        # Let's create a query for efficiency
        stmt = select(Permission).join(Permission.roles).where(
            Permission.resource == resource,
            Permission.action == action,
            Role.id.in_(role_ids),
            Role.is_active.is_(True),
        )
        has_perm = (await db.execute(stmt)).scalars().first()

        if has_perm:
            return True

        return False


rbac_service = RBACService()
