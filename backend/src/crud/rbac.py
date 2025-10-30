"""
RBAC相关CRUD操作
"""

from datetime import datetime

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from ..exceptions import BusinessLogicError
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


class RoleCRUD:
    """角色CRUD操作"""

    def get(self, db: Session, role_id: str) -> Role | None:
        """根据ID获取角色"""
        return db.query(Role).filter(Role.id == role_id).first()

    def get_by_name(self, db: Session, name: str) -> Role | None:
        """根据名称获取角色"""
        return db.query(Role).filter(Role.name == name).first()

    def get_multi(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
        category: str | None = None,
        is_active: bool | None = None,
        organization_id: str | None = None,
    ) -> tuple[list[Role], int]:
        """获取角色列表"""
        query = db.query(Role)

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

    def create(self, db: Session, obj_in: RoleCreate, created_by: str) -> Role:
        """创建角色"""
        # 检查角色名称唯一性
        existing_role = self.get_by_name(db, obj_in.name)
        if existing_role:
            raise BusinessLogicError("角色名称已存在")

        db_obj = Role(
            name=obj_in.name,
            display_name=obj_in.display_name,
            description=obj_in.description,
            level=obj_in.level,
            category=obj_in.category,
            is_system_role=obj_in.is_system_role,
            organization_id=obj_in.organization_id,
            scope=obj_in.scope,
            scope_id=obj_in.scope_id,
            created_by=created_by,
        )

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)

        return db_obj

    def update(
        self, db: Session, db_obj: Role, obj_in: RoleUpdate, updated_by: str
    ) -> Role:
        """更新角色"""
        if db_obj.is_system_role:
            raise BusinessLogicError("系统角色不能修改")

        # 检查显示名称唯一性
        if obj_in.display_name and obj_in.display_name != db_obj.display_name:
            existing_role = (
                db.query(Role)
                .filter(
                    and_(Role.display_name == obj_in.display_name, Role.id != db_obj.id)
                )
                .first()
            )
            if existing_role:
                raise BusinessLogicError("角色显示名称已存在")

        update_data = obj_in.dict(exclude_unset=True, exclude={"permission_ids"})
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db_obj.updated_at = func.now()
        db_obj.updated_by = updated_by

        db.commit()
        db.refresh(db_obj)

        return db_obj

    def delete(self, db: Session, role_id: str, deleted_by: str) -> bool:
        """删除角色"""
        role = self.get(db, role_id)
        if not role:
            return False

        if role.is_system_role:
            raise BusinessLogicError("系统角色不能删除")

        # 检查是否有用户使用此角色
        from ..models.rbac import UserRoleAssignment

        user_count = (
            db.query(UserRoleAssignment)
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

        db.delete(role)
        db.commit()

        return True

    def count(self, db: Session) -> int:
        """角色总数"""
        return db.query(func.count(Role.id)).scalar()

    def count_by_category(self, db: Session) -> dict:
        """按类别统计角色数"""
        result = (
            db.query(Role.category, func.count(Role.id)).group_by(Role.category).all()
        )
        return {category: count for category, count in result if category}


class PermissionCRUD:
    """权限CRUD操作"""

    def get(self, db: Session, permission_id: str) -> Permission | None:
        """根据ID获取权限"""
        return db.query(Permission).filter(Permission.id == permission_id).first()

    def get_by_name(self, db: Session, name: str) -> Permission | None:
        """根据名称获取权限"""
        return db.query(Permission).filter(Permission.name == name).first()

    def get_multi(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
        resource: str | None = None,
        action: str | None = None,
        is_system_permission: bool | None = None,
    ) -> tuple[list[Permission], int]:
        """获取权限列表"""
        query = db.query(Permission)

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
            query = query.filter(
                Permission.is_system_permission == is_system_permission
            )

        # 总数
        total = query.count()

        # 分页
        permissions = (
            query.order_by(Permission.resource, Permission.action)
            .offset(skip)
            .limit(limit)
            .all()
        )

        return permissions, total

    def create(
        self, db: Session, obj_in: PermissionCreate, created_by: str
    ) -> Permission:
        """创建权限"""
        # 检查权限名称唯一性
        existing_permission = self.get_by_name(db, obj_in.name)
        if existing_permission:
            raise BusinessLogicError("权限名称已存在")

        import json

        db_obj = Permission(
            name=obj_in.name,
            display_name=obj_in.display_name,
            description=obj_in.description,
            resource=obj_in.resource,
            action=obj_in.action,
            max_level=obj_in.max_level,
            conditions=json.dumps(obj_in.conditions) if obj_in.conditions else None,
            is_system_permission=obj_in.is_system_permission,
            requires_approval=obj_in.requires_approval,
            created_by=created_by,
        )

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)

        return db_obj

    def update(
        self, db: Session, db_obj: Permission, obj_in: PermissionUpdate, updated_by: str
    ) -> Permission:
        """更新权限"""
        import json

        update_data = obj_in.dict(exclude_unset=True)

        # 处理条件字段
        if "conditions" in update_data:
            update_data["conditions"] = (
                json.dumps(update_data["conditions"])
                if update_data["conditions"]
                else None
            )

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db_obj.updated_at = func.now()
        db_obj.updated_by = updated_by

        db.commit()
        db.refresh(db_obj)

        return db_obj

    def count(self, db: Session) -> int:
        """权限总数"""
        return db.query(func.count(Permission.id)).scalar()

    def count_by_resource(self, db: Session) -> dict:
        """按资源统计权限数"""
        result = (
            db.query(Permission.resource, func.count(Permission.id))
            .group_by(Permission.resource)
            .all()
        )
        return {resource: count for resource, count in result if resource}


class UserRoleAssignmentCRUD:
    """用户角色分配CRUD操作"""

    def get(self, db: Session, assignment_id: str) -> UserRoleAssignment | None:
        """根据ID获取分配记录"""
        return (
            db.query(UserRoleAssignment)
            .filter(UserRoleAssignment.id == assignment_id)
            .first()
        )

    def get_user_active_assignments(
        self, db: Session, user_id: str
    ) -> list[UserRoleAssignment]:
        """获取用户活跃的角色分配"""
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

    def get_multi(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        user_id: str | None = None,
        role_id: str | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[UserRoleAssignment], int]:
        """获取分配列表"""
        query = db.query(UserRoleAssignment)

        # 筛选条件
        if user_id:
            query = query.filter(UserRoleAssignment.user_id == user_id)
        if role_id:
            query = query.filter(UserRoleAssignment.role_id == role_id)
        if is_active is not None:
            query = query.filter(UserRoleAssignment.is_active == is_active)

        # 总数
        total = query.count()

        # 分页
        assignments = (
            query.order_by(UserRoleAssignment.assigned_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        return assignments, total

    def create(
        self, db: Session, obj_in: UserRoleAssignmentCreate, assigned_by: str
    ) -> UserRoleAssignment:
        """创建用户角色分配"""
        # 检查是否已分配
        existing_assignment = (
            db.query(UserRoleAssignment)
            .filter(
                and_(
                    UserRoleAssignment.user_id == obj_in.user_id,
                    UserRoleAssignment.role_id == obj_in.role_id,
                    UserRoleAssignment.is_active,
                )
            )
            .first()
        )

        if existing_assignment:
            raise BusinessLogicError("用户已分配此角色")

        import json

        db_obj = UserRoleAssignment(
            user_id=obj_in.user_id,
            role_id=obj_in.role_id,
            assigned_by=assigned_by,
            expires_at=obj_in.expires_at,
            reason=obj_in.reason,
            notes=obj_in.notes,
            context=json.dumps(obj_in.context) if obj_in.context else None,
        )

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)

        return db_obj

    def update(
        self, db: Session, db_obj: UserRoleAssignment, obj_in: UserRoleAssignmentUpdate
    ) -> UserRoleAssignment:
        """更新用户角色分配"""
        update_data = obj_in.dict(exclude_unset=True)

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db_obj.updated_at = func.now()

        db.commit()
        db.refresh(db_obj)

        return db_obj

    def revoke(self, db: Session, user_id: str, role_id: str) -> bool:
        """撤销用户角色"""
        assignment = (
            db.query(UserRoleAssignment)
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

        assignment.is_active = False
        assignment.updated_at = func.now()

        db.commit()

        return True

    def count_active(self, db: Session) -> int:
        """活跃分配总数"""
        return (
            db.query(func.count(UserRoleAssignment.id))
            .filter(UserRoleAssignment.is_active)
            .scalar()
        )


class ResourcePermissionCRUD:
    """资源权限CRUD操作"""

    def get(self, db: Session, permission_id: str) -> ResourcePermission | None:
        """根据ID获取资源权限"""
        return (
            db.query(ResourcePermission)
            .filter(ResourcePermission.id == permission_id)
            .first()
        )

    def get_user_resource_permissions(
        self,
        db: Session,
        user_id: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
    ) -> list[ResourcePermission]:
        """获取用户资源权限"""
        query = db.query(ResourcePermission).filter(
            and_(
                ResourcePermission.user_id == user_id,
                ResourcePermission.is_active,
                or_(
                    ResourcePermission.expires_at.is_(None),
                    ResourcePermission.expires_at > func.now(),
                ),
            )
        )

        if resource_type:
            query = query.filter(ResourcePermission.resource_type == resource_type)
        if resource_id:
            query = query.filter(ResourcePermission.resource_id == resource_id)

        return query.all()

    def get_multi(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        resource_type: str | None = None,
        resource_id: str | None = None,
        user_id: str | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[ResourcePermission], int]:
        """获取资源权限列表"""
        query = db.query(ResourcePermission)

        # 筛选条件
        if resource_type:
            query = query.filter(ResourcePermission.resource_type == resource_type)
        if resource_id:
            query = query.filter(ResourcePermission.resource_id == resource_id)
        if user_id:
            query = query.filter(ResourcePermission.user_id == user_id)
        if is_active is not None:
            query = query.filter(ResourcePermission.is_active == is_active)

        # 总数
        total = query.count()

        # 分页
        permissions = (
            query.order_by(ResourcePermission.granted_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        return permissions, total

    def create(
        self, db: Session, obj_in: ResourcePermissionCreate, granted_by: str
    ) -> ResourcePermission:
        """创建资源权限"""
        import json

        db_obj = ResourcePermission(
            resource_type=obj_in.resource_type,
            resource_id=obj_in.resource_id,
            user_id=obj_in.user_id,
            role_id=obj_in.role_id,
            permission_id=obj_in.permission_id,
            permission_level=obj_in.permission_level,
            granted_by=granted_by,
            reason=obj_in.reason,
            conditions=json.dumps(obj_in.conditions) if obj_in.conditions else None,
            expires_at=obj_in.expires_at,
        )

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)

        return db_obj

    def update(
        self, db: Session, db_obj: ResourcePermission, obj_in: ResourcePermissionUpdate
    ) -> ResourcePermission:
        """更新资源权限"""
        import json

        update_data = obj_in.dict(exclude_unset=True)

        # 处理条件字段
        if "conditions" in update_data:
            update_data["conditions"] = (
                json.dumps(update_data["conditions"])
                if update_data["conditions"]
                else None
            )

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db_obj.updated_at = func.now()

        db.commit()
        db.refresh(db_obj)

        return db_obj

    def revoke(self, db: Session, permission_id: str) -> bool:
        """撤销资源权限"""
        permission = self.get(db, permission_id)
        if not permission:
            return False

        permission.is_active = False
        permission.updated_at = func.now()

        db.commit()

        return True

    def count_active(self, db: Session) -> int:
        """活跃资源权限总数"""
        return (
            db.query(func.count(ResourcePermission.id))
            .filter(ResourcePermission.is_active)
            .scalar()
        )


class PermissionAuditLogCRUD:
    """权限审计日志CRUD操作"""

    def get_multi(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        action: str | None = None,
        resource_type: str | None = None,
        operator_id: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> tuple[list[PermissionAuditLog], int]:
        """获取审计日志列表"""
        query = db.query(PermissionAuditLog)

        # 筛选条件
        if action:
            query = query.filter(PermissionAuditLog.action == action)
        if resource_type:
            query = query.filter(PermissionAuditLog.resource_type == resource_type)
        if operator_id:
            query = query.filter(PermissionAuditLog.operator_id == operator_id)
        if start_date:
            query = query.filter(PermissionAuditLog.created_at >= start_date)
        if end_date:
            query = query.filter(PermissionAuditLog.created_at <= end_date)

        # 总数
        total = query.count()

        # 分页
        logs = (
            query.order_by(PermissionAuditLog.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        return logs, total

    def create(self, db: Session, **kwargs) -> PermissionAuditLog:
        """创建审计日志"""
        import json

        db_obj = PermissionAuditLog(
            action=kwargs.get("action"),
            resource_type=kwargs.get("resource_type"),
            resource_id=kwargs.get("resource_id"),
            user_id=kwargs.get("user_id"),
            operator_id=kwargs.get("operator_id"),
            old_permissions=json.dumps(kwargs.get("old_permissions"))
            if kwargs.get("old_permissions")
            else None,
            new_permissions=json.dumps(kwargs.get("new_permissions"))
            if kwargs.get("new_permissions")
            else None,
            reason=kwargs.get("reason"),
            ip_address=kwargs.get("ip_address"),
            user_agent=kwargs.get("user_agent"),
        )

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)

        return db_obj

    def count(self, db: Session) -> int:
        """审计日志总数"""
        return db.query(func.count(PermissionAuditLog.id)).scalar()

    def get_action_statistics(self, db: Session, days: int = 30) -> dict:
        """获取操作统计"""
        from datetime import timedelta

        start_date = datetime.now() - timedelta(days=days)

        result = (
            db.query(PermissionAuditLog.action, func.count(PermissionAuditLog.id))
            .filter(PermissionAuditLog.created_at >= start_date)
            .group_by(PermissionAuditLog.action)
            .all()
        )

        return {action: count for action, count in result}
