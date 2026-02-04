from typing import Any

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..crud.base import CRUDBase
from ..models.rbac import (
    Permission,
    PermissionAuditLog,
    ResourcePermission,
    Role,
    UserRoleAssignment,
)
from ..schemas.rbac import (
    PermissionCreate,
    PermissionUpdate,
    ResourcePermissionCreate,
    ResourcePermissionUpdate,
    RoleCreate,
    RoleUpdate,
    UserRoleAssignmentCreate,
    UserRoleAssignmentUpdate,
)


class CRUDRole(CRUDBase[Role, RoleCreate, RoleUpdate]):
    """角色CRUD操作"""

    async def create(
        self,
        db: AsyncSession,
        *,
        obj_in: RoleCreate | dict[str, Any],
        commit: bool = True,
        **kwargs: Any,
    ) -> Role:
        """创建角色（过滤permission_ids字段）"""
        if isinstance(obj_in, dict):
            obj_in_data = obj_in
        else:
            obj_in_data = obj_in.model_dump()

        # 移除permission_ids字段（这不是Role模型的字段）
        obj_in_data.pop("permission_ids", None)

        return await super().create(db, obj_in=obj_in_data, commit=commit, **kwargs)

    async def get_by_name(self, db: AsyncSession, name: str) -> Role | None:
        """根据名称获取角色"""
        stmt = select(Role).where(Role.name == name)
        return (await db.execute(stmt)).scalars().first()

    async def get_multi_with_filters(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
        category: str | None = None,
        is_active: bool | None = None,
        organization_id: str | None = None,
    ) -> tuple[list[Role], int]:
        """获取角色列表"""
        filters: dict[str, Any] = {}

        if category:
            filters["category"] = category
        if is_active is not None:
            filters["is_active"] = is_active
        if organization_id:
            filters["organization_id"] = organization_id

        return await self.get_multi_with_count(
            db,
            filters=filters,
            search=search,
            search_fields=["name", "display_name", "description"],
            order_by="level",
            order_desc=False,
            skip=skip,
            limit=limit,
        )

    # Override count to use QueryBuilder implicitly or keep custom if complex logic needed
    # But for standard counts, CRUDBase.count works if filters aligned.
    # Here we keep custom count_by_category logic.

    async def count_by_category(self, db: AsyncSession) -> dict[str, Any]:
        """按类别统计角色数"""
        stmt = select(Role.category, func.count(Role.id)).group_by(Role.category)
        result = (await db.execute(stmt)).all()
        return {category: count for category, count in result if category}

    async def count_by_flags(self, db: AsyncSession) -> dict[str, int]:
        """按激活/系统/自定义统计角色数量"""
        stmt = select(
            func.count(Role.id).label("total"),
            func.sum(case((Role.is_active.is_(True), 1), else_=0)).label("active"),
            func.sum(case((Role.is_system_role.is_(True), 1), else_=0)).label("system"),
            func.sum(case((Role.is_system_role.is_(False), 1), else_=0)).label("custom"),
        )
        result = (await db.execute(stmt)).one()

        return {
            "total": int(result.total or 0),
            "active": int(result.active or 0),
            "system": int(result.system or 0),
            "custom": int(result.custom or 0),
        }


class CRUDPermission(CRUDBase[Permission, PermissionCreate, PermissionUpdate]):
    """权限CRUD操作"""

    async def get_multi_with_filters(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
        resource: str | None = None,
        action: str | None = None,
        is_system_permission: bool | None = None,
    ) -> list[Permission]:
        """获取权限列表"""
        filters: dict[str, Any] = {}

        if resource:
            filters["resource"] = resource
        if action:
            filters["action"] = action
        if is_system_permission is not None:
            filters["is_system_permission"] = is_system_permission

        stmt = self.query_builder.build_query(
            filters=filters,
            search_query=search,
            search_fields=["name", "display_name", "description"],
            sort_by="resource",
            skip=skip,
            limit=limit,
        )

        result = (await db.execute(stmt)).scalars().all()
        return list(result)

    async def count_by_resource(self, db: AsyncSession) -> dict[str, Any]:
        """按资源统计权限数"""
        stmt = select(Permission.resource, func.count(Permission.id)).group_by(
            Permission.resource
        )
        result = (await db.execute(stmt)).all()
        return {resource: count for resource, count in result if resource}


class CRUDUserRoleAssignment(
    CRUDBase[UserRoleAssignment, UserRoleAssignmentCreate, UserRoleAssignmentUpdate]
):
    """用户角色分配CRUD"""

    async def get_by_user_and_role(
        self, db: AsyncSession, user_id: str, role_id: str
    ) -> UserRoleAssignment | None:
        stmt = select(UserRoleAssignment).where(
            UserRoleAssignment.user_id == user_id,
            UserRoleAssignment.role_id == role_id,
        )
        return (await db.execute(stmt)).scalars().first()

    async def get_user_active_assignments(
        self, db: AsyncSession, user_id: str
    ) -> list[UserRoleAssignment]:
        """获取用户活跃角色"""
        stmt = select(UserRoleAssignment).where(
            and_(
                UserRoleAssignment.user_id == user_id,
                UserRoleAssignment.is_active,
                or_(
                    UserRoleAssignment.expires_at.is_(None),
                    UserRoleAssignment.expires_at > func.now(),
                ),
            )
        )
        return list((await db.execute(stmt)).scalars().all())

    async def count_by_role(self, db: AsyncSession, role_id: str) -> int:
        stmt = select(func.count(UserRoleAssignment.id)).where(
            UserRoleAssignment.role_id == role_id,
            UserRoleAssignment.is_active.is_(True),
        )
        result = await db.execute(stmt)
        return int(result.scalar() or 0)


class CRUDResourcePermission(
    CRUDBase[ResourcePermission, ResourcePermissionCreate, ResourcePermissionUpdate]
):
    """资源权限CRUD"""

    pass


class CRUDPermissionAuditLog(
    CRUDBase[PermissionAuditLog, Any, Any]
):  # Read only mostly
    """权限审计日志CRUD"""

    pass


role_crud = CRUDRole(Role)
permission_crud = CRUDPermission(Permission)
user_role_assignment_crud = CRUDUserRoleAssignment(UserRoleAssignment)
resource_permission_crud = CRUDResourcePermission(ResourcePermission)
permission_audit_log_crud = CRUDPermissionAuditLog(PermissionAuditLog)
