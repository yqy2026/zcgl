from inspect import isawaitable
from typing import Any

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..crud.base import CRUDBase
from ..models.rbac import (
    Permission,
    PermissionAuditLog,
    PermissionGrant,
    ResourcePermission,
    Role,
    UserRoleAssignment,
    role_permissions,
)
from ..schemas.rbac import (
    PermissionCreate,
    PermissionGrantCreate,
    PermissionGrantUpdate,
    PermissionUpdate,
    ResourcePermissionCreate,
    ResourcePermissionUpdate,
    RoleCreate,
    RoleUpdate,
    UserRoleAssignmentCreate,
    UserRoleAssignmentUpdate,
)
from .query_builder import TenantFilter


async def _scalars_all(result: Any) -> list[Any]:
    """兼容真实 AsyncSession 与测试 AsyncMock 的 scalars().all() 行为。"""
    scalars_result = result.scalars()
    if isawaitable(scalars_result):
        scalars_result = await scalars_result

    all_result = scalars_result.all()
    if isawaitable(all_result):
        all_result = await all_result

    return list(all_result)


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
        stmt = select(Role).where(Role.name == name).options(
            selectinload(Role.permissions)
        )
        return (await db.execute(stmt)).scalars().first()

    async def get(
        self,
        db: AsyncSession,
        id: Any,
        use_cache: bool = True,
        tenant_filter: TenantFilter | None = None,
    ) -> Role | None:
        """根据ID获取单个记录（预加载权限）"""
        stmt = (
            select(Role)
            .where(Role.id == id)
            .options(selectinload(Role.permissions))
        )
        if tenant_filter is not None:
            stmt = self.query_builder.apply_tenant_filter(stmt, tenant_filter)
        result = (await db.execute(stmt)).scalars().first()
        if use_cache and result is not None:  # pragma: no cover
            cache_key = self._get_cache_key(
                "get",
                id=id,
                tenant_filter=self._serialize_tenant_filter(tenant_filter),
            )  # pragma: no cover
            self._set_cache(cache_key, result)  # pragma: no cover
        return result

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
        tenant_filter: TenantFilter | None = None,
    ) -> tuple[list[Role], int]:
        """获取角色列表"""
        filters: dict[str, Any] = {}

        if category:
            filters["category"] = category
        if is_active is not None:
            filters["is_active"] = is_active
        if organization_id:
            filters["organization_id"] = organization_id

        stmt = self.query_builder.build_query(
            filters=filters,
            search_query=search,
            search_fields=["name", "display_name", "description"],
            sort_by="level",
            sort_desc=False,
            skip=skip,
            limit=limit,
            tenant_filter=tenant_filter,
        ).options(selectinload(Role.permissions))

        count_stmt = self.query_builder.build_count_query(
            filters=filters,
            search_query=search,
            search_fields=["name", "display_name", "description"],
            tenant_filter=tenant_filter,
        )

        result = await _scalars_all(await db.execute(stmt))
        total = int((await db.execute(count_stmt)).scalar() or 0)
        return result, total

    async def get_roles_by_user_async(
        self,
        db: AsyncSession,
        user_id: str,
        *,
        active_only: bool = True,
        include_permissions: bool = False,
        now: Any = None,
    ) -> list[Role]:
        """获取用户的角色列表"""
        stmt = (
            select(Role)
            .join(UserRoleAssignment, Role.id == UserRoleAssignment.role_id)
            .where(UserRoleAssignment.user_id == user_id)
        )
        if include_permissions:
            stmt = stmt.options(selectinload(Role.permissions))
        if active_only:
            _now = now or func.now()
            stmt = stmt.where(
                UserRoleAssignment.is_active,
                or_(
                    UserRoleAssignment.expires_at.is_(None),
                    UserRoleAssignment.expires_at > _now,
                ),
            )
        result = await db.execute(stmt)
        return await _scalars_all(result)

    async def check_display_name_exists_async(
        self, db: AsyncSession, display_name: str, exclude_role_id: str | None = None
    ) -> bool:
        """检查 display_name 是否已存在（排除指定角色）"""
        stmt = select(Role).where(Role.display_name == display_name)
        if exclude_role_id:
            stmt = stmt.where(Role.id != exclude_role_id)
        result = await db.execute(stmt)
        return result.scalars().first() is not None

    async def update_permissions_created_by_async(
        self, db: AsyncSession, role_id: str, created_by: str
    ) -> None:
        """更新角色权限关联表的 created_by 字段"""
        from sqlalchemy import update
        stmt = (
            update(role_permissions)
            .where(role_permissions.c.role_id == role_id)
            .values(created_by=created_by)
        )
        await db.execute(stmt)

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
            func.sum(case((Role.is_system_role.is_(False), 1), else_=0)).label(
                "custom"
            ),
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

    async def get_by_name(self, db: AsyncSession, name: str) -> Permission | None:
        """根据名称获取权限"""
        stmt = select(Permission).where(Permission.name == name)
        return (await db.execute(stmt)).scalars().first()

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
        tenant_filter: TenantFilter | None = None,
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
            tenant_filter=tenant_filter,
        )

        result = await _scalars_all(await db.execute(stmt))
        return result

    async def get_by_ids_async(
        self, db: AsyncSession, permission_ids: list[str]
    ) -> list[Permission]:
        """批量获取权限"""
        if not permission_ids:
            return []
        stmt = select(Permission).where(Permission.id.in_(permission_ids))
        result = await db.execute(stmt)
        return await _scalars_all(result)

    async def get_multi_with_count_async(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
        resource: str | None = None,
        action: str | None = None,
        is_system_permission: bool | None = None,
        tenant_filter: TenantFilter | None = None,
    ) -> tuple[list[Permission], int]:
        """获取权限列表（含总数）"""
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
            sort_desc=False,
            skip=skip,
            limit=limit,
            tenant_filter=tenant_filter,
        )
        count_stmt = self.query_builder.build_count_query(
            filters=filters,
            search_query=search,
            search_fields=["name", "display_name", "description"],
            tenant_filter=tenant_filter,
        )

        permissions = await _scalars_all(await db.execute(stmt))
        total = int((await db.execute(count_stmt)).scalar() or 0)
        return permissions, total

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
        result = await db.execute(stmt)
        return await _scalars_all(result)

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

    async def get_resource_ids_by_conditions_async(
        self,
        db: AsyncSession,
        *,
        resource_type: str,
        user_id: str | None = None,
        role_ids: list[str] | None = None,
        now: Any = None,
    ) -> list[str]:
        """获取满足条件的资源ID列表（用于组织权限过滤）"""
        conditions = [
            ResourcePermission.resource_type == resource_type,
            ResourcePermission.is_active.is_(True),
            or_(
                ResourcePermission.expires_at.is_(None),
                ResourcePermission.expires_at > (now or func.now()),
            ),
        ]

        if user_id:
            conditions.append(ResourcePermission.user_id == user_id)
        elif role_ids:
            conditions.append(ResourcePermission.role_id.in_(role_ids))
        else:
            return []

        stmt = select(ResourcePermission.resource_id).where(and_(*conditions))
        resource_ids = await _scalars_all(await db.execute(stmt))
        return [str(resource_id) for resource_id in resource_ids]


class CRUDPermissionAuditLog(
    CRUDBase[PermissionAuditLog, Any, Any]
):  # Read only mostly
    """权限审计日志CRUD"""

    pass


class CRUDPermissionGrant(
    CRUDBase[PermissionGrant, PermissionGrantCreate, PermissionGrantUpdate]
):
    """统一权限授权CRUD"""

    async def get_matching_grants_async(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        resource: str,
        action: str,
        now: Any = None,
    ) -> list[PermissionGrant]:
        """获取匹配的权限授权记录（用于权限检查）"""
        _now = now or func.now()
        stmt = (
            select(PermissionGrant)
            .join(Permission, Permission.id == PermissionGrant.permission_id)
            .where(
                and_(
                    PermissionGrant.user_id == user_id,
                    PermissionGrant.is_active,
                    Permission.resource == resource,
                    Permission.action == action,
                    or_(PermissionGrant.starts_at.is_(None), PermissionGrant.starts_at <= _now),
                    or_(PermissionGrant.expires_at.is_(None), PermissionGrant.expires_at > _now),
                )
            )
        )
        result = await db.execute(stmt)
        return await _scalars_all(result)

    async def list_with_filters_async(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 20,
        user_id: str | None = None,
        permission_id: str | None = None,
        grant_type: str | None = None,
        effect: str | None = None,
        scope: str | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[PermissionGrant], int]:
        """分页查询统一授权记录（含总数）"""
        from sqlalchemy import desc

        filters = []
        if user_id:
            filters.append(PermissionGrant.user_id == user_id)
        if permission_id:
            filters.append(PermissionGrant.permission_id == permission_id)
        if grant_type:
            filters.append(PermissionGrant.grant_type == grant_type.strip().lower())
        if effect:
            filters.append(PermissionGrant.effect == effect.strip().lower())
        if scope:
            filters.append(PermissionGrant.scope == scope.strip().lower())
        if is_active is not None:
            filters.append(PermissionGrant.is_active == is_active)

        stmt = select(PermissionGrant).order_by(desc(PermissionGrant.created_at))
        count_stmt = select(func.count(PermissionGrant.id))

        if filters:
            stmt = stmt.where(and_(*filters))
            count_stmt = count_stmt.where(and_(*filters))

        stmt = stmt.offset(skip).limit(limit)
        grants = await _scalars_all(await db.execute(stmt))
        total = int((await db.execute(count_stmt)).scalar() or 0)
        return grants, total

    async def get_granted_permissions_async(
        self, db: AsyncSession, user_id: str, now: Any = None
    ) -> list[Permission]:
        """获取用户的授权权限列表（用于权限汇总）"""
        _now = now or func.now()
        stmt = (
            select(Permission)
            .join(PermissionGrant, PermissionGrant.permission_id == Permission.id)
            .where(
                and_(
                    PermissionGrant.user_id == user_id,
                    PermissionGrant.is_active,
                    PermissionGrant.effect == "allow",
                    or_(PermissionGrant.starts_at.is_(None), PermissionGrant.starts_at <= _now),
                    or_(PermissionGrant.expires_at.is_(None), PermissionGrant.expires_at > _now),
                )
            )
        )
        result = await db.execute(stmt)
        return await _scalars_all(result)


role_crud = CRUDRole(Role)
permission_crud = CRUDPermission(Permission)
user_role_assignment_crud = CRUDUserRoleAssignment(UserRoleAssignment)
resource_permission_crud = CRUDResourcePermission(ResourcePermission)
permission_audit_log_crud = CRUDPermissionAuditLog(PermissionAuditLog)
permission_grant_crud = CRUDPermissionGrant(PermissionGrant)
