from typing import Any

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

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

    def create(
        self,
        db: Session,
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

        return super().create(db, obj_in=obj_in_data, commit=commit, **kwargs)

    def get_by_name(self, db: Session, name: str) -> Role | None:
        """根据名称获取角色"""
        return db.query(Role).filter(Role.name == name).first()

    def get_multi_with_filters(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
        category: str | None = None,
        is_active: bool | None = None,
        organization_id: str | None = None,
    ) -> list[Role]:
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
        )

        result = db.execute(stmt)
        return list(result.scalars().all())

    # Override count to use QueryBuilder implicitly or keep custom if complex logic needed
    # But for standard counts, CRUDBase.count works if filters aligned.
    # Here we keep custom count_by_category logic.

    def count_by_category(self, db: Session) -> dict[str, Any]:
        """按类别统计角色数"""
        from sqlalchemy import func

        result = (
            db.query(Role.category, func.count(Role.id)).group_by(Role.category).all()
        )
        return {category: count for category, count in result if category}


class CRUDPermission(CRUDBase[Permission, PermissionCreate, PermissionUpdate]):
    """权限CRUD操作"""

    def get_multi_with_filters(
        self,
        db: Session,
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

        result = db.execute(stmt)
        return list(result.scalars().all())

    def count_by_resource(self, db: Session) -> dict[str, Any]:
        """按资源统计权限数"""
        from sqlalchemy import func

        result = (
            db.query(Permission.resource, func.count(Permission.id))
            .group_by(Permission.resource)
            .all()
        )
        return {resource: count for resource, count in result if resource}


class CRUDUserRoleAssignment(
    CRUDBase[UserRoleAssignment, UserRoleAssignmentCreate, UserRoleAssignmentUpdate]
):
    """用户角色分配CRUD"""

    def get_by_user_and_role(
        self, db: Session, user_id: str, role_id: str
    ) -> UserRoleAssignment | None:
        return (
            db.query(UserRoleAssignment)
            .filter(
                UserRoleAssignment.user_id == user_id,
                UserRoleAssignment.role_id == role_id,
            )
            .first()
        )

    def get_user_active_assignments(
        self, db: Session, user_id: str
    ) -> list[UserRoleAssignment]:
        """获取用户活跃角色"""
        from sqlalchemy import func

        return (
            db.query(UserRoleAssignment)
            .filter(
                and_(
                    UserRoleAssignment.user_id == user_id,
                    UserRoleAssignment.is_active,
                    or_(
                        UserRoleAssignment.expires_at.is_(None),
                        UserRoleAssignment.expires_at > func.now(),
                    ),
                )
            )
            .all()
        )

    def count_by_role(self, db: Session, role_id: str) -> int:
        return (
            db.query(UserRoleAssignment)
            .filter(
                UserRoleAssignment.role_id == role_id,
                UserRoleAssignment.is_active.is_(True),
            )
            .count()
        )


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
