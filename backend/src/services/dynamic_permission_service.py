"""
动态权限分配服务
支持临时权限、条件权限和动态权限分配
"""

from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from ..exceptions import BusinessLogicError
from ..models.auth import User as AuthUser
from ..models.dynamic_permission import (
    ConditionalPermission,
    DynamicPermission,
    DynamicPermissionAudit,
    PermissionTemplate,
    TemporaryPermission,
)
from ..models.rbac import Permission


class PermissionType(str, Enum):
    """权限类型"""

    ROLE_BASED = "role_based"  # 基于角色的权限
    USER_SPECIFIC = "user_specific"  # 用户特定权限
    TEMPORARY = "temporary"  # 临时权限
    CONDITIONAL = "conditional"  # 条件权限
    TEMPLATE_BASED = "template_based"  # 基于模板的权限


class AssignmentScope(str, Enum):
    """分配范围"""

    GLOBAL = "global"  # 全局范围
    ORGANIZATION = "organization"  # 组织范围
    PROJECT = "project"  # 项目范围
    ASSET = "asset"  # 资产范围
    CUSTOM = "custom"  # 自定义范围


class DynamicPermissionService:
    """动态权限分配服务"""

    def __init__(self, db: Session):
        self.db = db

    def assign_dynamic_permission(
        self,
        user_id: str,
        permission_ids: list[str],
        permission_type: PermissionType,
        scope: AssignmentScope,
        scope_id: str | None = None,
        expires_at: datetime | None = None,
        conditions: dict[str, Any] | None = None,
        assigned_by: str | None = None,
        reason: str | None = None,
    ) -> List[DynamicPermission]:
        """
        分配动态权限

        Args:
            user_id: 用户ID
            permission_ids: 权限ID列表
            permission_type: 权限类型
            scope: 权限范围
            scope_id: 范围ID（当scope不是global时需要）
            expires_at: 过期时间
            conditions: 权限条件
            assigned_by: 分配人
            reason: 分配原因

        Returns:
            创建的动态权限列表
        """
        if not assigned_by:
            raise BusinessLogicError("必须指定分配人")

        # 验证用户存在
        user = self.db.query(AuthUser).filter(AuthUser.id == user_id).first()
        if not user:
            raise BusinessLogicError(f"用户 {user_id} 不存在")

        created_permissions = []

        for permission_id in permission_ids:
            # 验证权限存在
            permission = (
                self.db.query(Permission).filter(Permission.id == permission_id).first()
            )
            if not permission:
                raise BusinessLogicError(f"权限 {permission_id} 不存在")

            # 检查是否已存在相同的动态权限
            existing = (
                self.db.query(DynamicPermission)
                .filter(
                    and_(
                        DynamicPermission.user_id == user_id,
                        DynamicPermission.permission_id == permission_id,
                        DynamicPermission.permission_type == permission_type,
                        DynamicPermission.scope == scope,
                        DynamicPermission.scope_id == scope_id,
                        DynamicPermission.is_active,
                        or_(
                            DynamicPermission.expires_at.is_(None),
                            DynamicPermission.expires_at > datetime.now(UTC),
                        ),
                    )
                )
                .first()
            )

            if existing:
                continue  # 跳过已存在的权限

            # 创建动态权限
            dynamic_permission = DynamicPermission(
                user_id=user_id,
                permission_id=permission_id,
                permission_type=permission_type,
                scope=scope,
                scope_id=scope_id,
                expires_at=expires_at,
                conditions=conditions,
                assigned_by=assigned_by,
                assigned_at=datetime.now(UTC),
                is_active=True,
            )

            self.db.add(dynamic_permission)
            created_permissions.append(dynamic_permission)

            # 记录审计日志
            audit_log = DynamicPermissionAudit(
                user_id=user_id,
                permission_id=permission_id,
                action="ASSIGN",
                permission_type=permission_type,
                scope=scope,
                scope_id=scope_id,
                assigned_by=assigned_by,
                reason=reason or "动态权限分配",
                created_at=datetime.now(UTC),
            )
            self.db.add(audit_log)

        self.db.commit()
        return created_permissions

    def assign_temporary_permission(
        self,
        user_id: str,
        permission_ids: list[str],
        duration_hours: int,
        scope: AssignmentScope = AssignmentScope.GLOBAL,
        scope_id: str | None = None,
        assigned_by: str | None = None,
        reason: str | None = None,
    ) -> List[TemporaryPermission]:
        """
        分配临时权限

        Args:
            user_id: 用户ID
            permission_ids: 权限ID列表
            duration_hours: 有效时长（小时）
            scope: 权限范围
            scope_id: 范围ID
            assigned_by: 分配人
            reason: 分配原因

        Returns:
            创建的临时权限列表
        """
        expires_at = datetime.now(UTC) + timedelta(hours=duration_hours)
        created_permissions = []

        for permission_id in permission_ids:
            # 验证权限存在
            permission = (
                self.db.query(Permission).filter(Permission.id == permission_id).first()
            )
            if not permission:
                raise BusinessLogicError(f"权限 {permission_id} 不存在")

            # 检查是否已存在相同的临时权限
            existing = (
                self.db.query(TemporaryPermission)
                .filter(
                    and_(
                        TemporaryPermission.user_id == user_id,
                        TemporaryPermission.permission_id == permission_id,
                        TemporaryPermission.scope == scope,
                        TemporaryPermission.scope_id == scope_id,
                        TemporaryPermission.is_active,
                        TemporaryPermission.expires_at > datetime.now(UTC),
                    )
                )
                .first()
            )

            if existing:
                continue  # 跳过已存在的权限

            # 创建临时权限
            temporary_permission = TemporaryPermission(
                user_id=user_id,
                permission_id=permission_id,
                scope=scope,
                scope_id=scope_id,
                expires_at=expires_at,
                assigned_by=assigned_by,
                assigned_at=datetime.now(UTC),
                is_active=True,
            )

            self.db.add(temporary_permission)
            created_permissions.append(temporary_permission)

            # 记录审计日志
            audit_log = DynamicPermissionAudit(
                user_id=user_id,
                permission_id=permission_id,
                action="ASSIGN_TEMPORARY",
                permission_type=PermissionType.TEMPORARY,
                scope=scope,
                scope_id=scope_id,
                assigned_by=assigned_by,
                reason=reason or f"临时权限分配，有效期{duration_hours}小时",
                created_at=datetime.now(UTC),
            )
            self.db.add(audit_log)

        self.db.commit()
        return created_permissions

    def assign_conditional_permission(
        self,
        user_id: str,
        permission_id: str,
        conditions: dict[str, Any],
        scope: AssignmentScope = AssignmentScope.GLOBAL,
        scope_id: str | None = None,
        assigned_by: str | None = None,
        reason: str | None = None,
    ) -> ConditionalPermission:
        """
        分配条件权限

        Args:
            user_id: 用户ID
            permission_id: 权限ID
            conditions: 权限条件
            scope: 权限范围
            scope_id: 范围ID
            assigned_by: 分配人
            reason: 分配原因

        Returns:
            创建的条件权限
        """
        # 验证权限存在
        permission = (
            self.db.query(Permission).filter(Permission.id == permission_id).first()
        )
        if not permission:
            raise BusinessLogicError(f"权限 {permission_id} 不存在")

        # 检查是否已存在相同的条件权限
        existing = (
            self.db.query(ConditionalPermission)
            .filter(
                and_(
                    ConditionalPermission.user_id == user_id,
                    ConditionalPermission.permission_id == permission_id,
                    ConditionalPermission.scope == scope,
                    ConditionalPermission.scope_id == scope_id,
                    ConditionalPermission.is_active,
                )
            )
            .first()
        )

        if existing:
            # 更新现有权限的条件
            existing.conditions = conditions
            existing.assigned_by = assigned_by
            existing.assigned_at = datetime.now(UTC)
            conditional_permission = existing
        else:
            # 创建新的条件权限
            conditional_permission = ConditionalPermission(
                user_id=user_id,
                permission_id=permission_id,
                scope=scope,
                scope_id=scope_id,
                conditions=conditions,
                assigned_by=assigned_by,
                assigned_at=datetime.now(UTC),
                is_active=True,
            )
            self.db.add(conditional_permission)

        # 记录审计日志
        audit_log = DynamicPermissionAudit(
            user_id=user_id,
            permission_id=permission_id,
            action="ASSIGN_CONDITIONAL",
            permission_type=PermissionType.CONDITIONAL,
            scope=scope,
            scope_id=scope_id,
            assigned_by=assigned_by,
            reason=reason or "条件权限分配",
            conditions=conditions,
            created_at=datetime.now(UTC),
        )
        self.db.add(audit_log)

        self.db.commit()
        return conditional_permission

    def revoke_dynamic_permission(
        self,
        permission_id: str,
        user_id: str | None = None,
        revoked_by: str | None = None,
        reason: str | None = None,
    ) -> bool:
        """
        撤销动态权限

        Args:
            permission_id: 动态权限ID
            user_id: 用户ID（可选，如果指定则只撤销该用户的权限）
            revoked_by: 撤销人
            reason: 撤销原因

        Returns:
            是否成功撤销
        """
        query = self.db.query(DynamicPermission).filter(
            DynamicPermission.id == permission_id, DynamicPermission.is_active
        )

        if user_id:
            query = query.filter(DynamicPermission.user_id == user_id)

        permissions = query.all()

        if not permissions:
            return False

        for permission in permissions:
            permission.is_active = False
            permission.revoked_at = datetime.now(UTC)
            permission.revoked_by = revoked_by

            # 记录审计日志
            audit_log = DynamicPermissionAudit(
                user_id=permission.user_id,
                permission_id=permission.permission_id,
                action="REVOKE",
                permission_type=permission.permission_type,
                scope=permission.scope,
                scope_id=permission.scope_id,
                assigned_by=revoked_by,
                reason=reason or "权限撤销",
                created_at=datetime.now(UTC),
            )
            self.db.add(audit_log)

        self.db.commit()
        return True

    def create_permission_template(
        self,
        name: str,
        description: str,
        permission_ids: list[str],
        scope: AssignmentScope,
        conditions: dict[str, Any] | None = None,
        created_by: str | None = None,
    ) -> PermissionTemplate:
        """
        创建权限模板

        Args:
            name: 模板名称
            description: 模板描述
            permission_ids: 权限ID列表
            scope: 权限范围
            conditions: 权限条件
            created_by: 创建人

        Returns:
            创建的权限模板
        """
        # 验证所有权限存在
        permissions = (
            self.db.query(Permission).filter(Permission.id.in_(permission_ids)).all()
        )

        if len(permissions) != len(permission_ids):
            raise BusinessLogicError("部分权限不存在")

        template = PermissionTemplate(
            name=name,
            description=description,
            permission_ids=permission_ids,
            scope=scope,
            conditions=conditions,
            created_by=created_by,
            created_at=datetime.now(UTC),
            is_active=True,
        )

        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)

        return template

    def assign_permissions_from_template(
        self,
        user_id: str,
        template_id: str,
        scope_id: str | None = None,
        expires_at: datetime | None = None,
        assigned_by: str | None = None,
        reason: str | None = None,
    ) -> List[DynamicPermission]:
        """
        从模板分配权限

        Args:
            user_id: 用户ID
            template_id: 模板ID
            scope_id: 范围ID
            expires_at: 过期时间
            assigned_by: 分配人
            reason: 分配原因

        Returns:
            创建的动态权限列表
        """
        template = (
            self.db.query(PermissionTemplate)
            .filter(
                PermissionTemplate.id == template_id,
                PermissionTemplate.is_active,
            )
            .first()
        )

        if not template:
            raise BusinessLogicError(f"权限模板 {template_id} 不存在或已禁用")

        return self.assign_dynamic_permission(
            user_id=user_id,
            permission_ids=template.permission_ids,
            permission_type=PermissionType.TEMPLATE_BASED,
            scope=template.scope,
            scope_id=scope_id,
            expires_at=expires_at,
            conditions=template.conditions,
            assigned_by=assigned_by,
            reason=reason or f"从模板 {template.name} 分配权限",
        )

    def get_user_dynamic_permissions(
        self,
        user_id: str,
        include_expired: bool = False,
        scope: AssignmentScope | None = None,
        scope_id: str | None = None,
    ) -> List[dict[str, Any]]:
        """
        获取用户的动态权限

        Args:
            user_id: 用户ID
            include_expired: 是否包含已过期的权限
            scope: 权限范围筛选
            scope_id: 范围ID筛选

        Returns:
            动态权限列表
        """
        permissions = []

        # 获取动态权限
        dynamic_query = self.db.query(DynamicPermission).filter(
            DynamicPermission.user_id == user_id, DynamicPermission.is_active
        )

        if not include_expired:
            dynamic_query = dynamic_query.filter(
                or_(
                    DynamicPermission.expires_at.is_(None),
                    DynamicPermission.expires_at > datetime.now(UTC),
                )
            )

        if scope:
            dynamic_query = dynamic_query.filter(DynamicPermission.scope == scope)

        if scope_id:
            dynamic_query = dynamic_query.filter(DynamicPermission.scope_id == scope_id)

        dynamic_perms = dynamic_query.all()
        for perm in dynamic_perms:
            permission_info = (
                self.db.query(Permission)
                .filter(Permission.id == perm.permission_id)
                .first()
            )

            if permission_info:
                permissions.append(
                    {
                        "id": perm.id,
                        "permission_id": perm.permission_id,
                        "permission_name": permission_info.name,
                        "permission_code": permission_info.code,
                        "permission_type": perm.permission_type,
                        "scope": perm.scope,
                        "scope_id": perm.scope_id,
                        "expires_at": perm.expires_at,
                        "conditions": perm.conditions,
                        "assigned_by": perm.assigned_by,
                        "assigned_at": perm.assigned_at,
                        "is_expired": perm.expires_at
                        and perm.expires_at <= datetime.now(UTC),
                    }
                )

        # 获取临时权限
        temp_query = self.db.query(TemporaryPermission).filter(
            TemporaryPermission.user_id == user_id,
            TemporaryPermission.is_active,
            TemporaryPermission.expires_at > datetime.now(UTC),
        )

        if scope:
            temp_query = temp_query.filter(TemporaryPermission.scope == scope)

        if scope_id:
            temp_query = temp_query.filter(TemporaryPermission.scope_id == scope_id)

        temp_perms = temp_query.all()
        for perm in temp_perms:
            permission_info = (
                self.db.query(Permission)
                .filter(Permission.id == perm.permission_id)
                .first()
            )

            if permission_info:
                permissions.append(
                    {
                        "id": perm.id,
                        "permission_id": perm.permission_id,
                        "permission_name": permission_info.name,
                        "permission_code": permission_info.code,
                        "permission_type": PermissionType.TEMPORARY,
                        "scope": perm.scope,
                        "scope_id": perm.scope_id,
                        "expires_at": perm.expires_at,
                        "assigned_by": perm.assigned_by,
                        "assigned_at": perm.assigned_at,
                        "is_expired": False,
                    }
                )

        # 获取条件权限
        cond_query = self.db.query(ConditionalPermission).filter(
            ConditionalPermission.user_id == user_id,
            ConditionalPermission.is_active,
        )

        if scope:
            cond_query = cond_query.filter(ConditionalPermission.scope == scope)

        if scope_id:
            cond_query = cond_query.filter(ConditionalPermission.scope_id == scope_id)

        cond_perms = cond_query.all()
        for perm in cond_perms:
            permission_info = (
                self.db.query(Permission)
                .filter(Permission.id == perm.permission_id)
                .first()
            )

            if permission_info:
                permissions.append(
                    {
                        "id": perm.id,
                        "permission_id": perm.permission_id,
                        "permission_name": permission_info.name,
                        "permission_code": permission_info.code,
                        "permission_type": PermissionType.CONDITIONAL,
                        "scope": perm.scope,
                        "scope_id": perm.scope_id,
                        "conditions": perm.conditions,
                        "assigned_by": perm.assigned_by,
                        "assigned_at": perm.assigned_at,
                        "is_expired": False,
                    }
                )

        return permissions

    def check_dynamic_permission(
        self, user_id: str, permission_code: str, context: dict[str, Any] | None = None
    ) -> tuple[bool, str]:
        """
        检查用户是否具有动态权限

        Args:
            user_id: 用户ID
            permission_code: 权限代码
            context: 上下文信息（用于条件权限检查）

        Returns:
            (是否有权限, 原因)
        """
        # 获取权限信息
        permission = (
            self.db.query(Permission).filter(Permission.code == permission_code).first()
        )

        if not permission:
            return False, f"权限 {permission_code} 不存在"

        # 检查动态权限
        dynamic_perm = (
            self.db.query(DynamicPermission)
            .filter(
                and_(
                    DynamicPermission.user_id == user_id,
                    DynamicPermission.permission_id == permission.id,
                    DynamicPermission.is_active,
                    or_(
                        DynamicPermission.expires_at.is_(None),
                        DynamicPermission.expires_at > datetime.now(UTC),
                    ),
                )
            )
            .first()
        )

        if dynamic_perm:
            # 检查条件权限
            if dynamic_perm.conditions and context:
                if self._evaluate_conditions(dynamic_perm.conditions, context):
                    return True, "动态权限通过条件检查"
                else:
                    return False, "动态权限条件不满足"
            return True, "具有动态权限"

        # 检查临时权限
        temp_perm = (
            self.db.query(TemporaryPermission)
            .filter(
                and_(
                    TemporaryPermission.user_id == user_id,
                    TemporaryPermission.permission_id == permission.id,
                    TemporaryPermission.is_active,
                    TemporaryPermission.expires_at > datetime.now(UTC),
                )
            )
            .first()
        )

        if temp_perm:
            return True, "具有临时权限"

        # 检查条件权限
        cond_perm = (
            self.db.query(ConditionalPermission)
            .filter(
                and_(
                    ConditionalPermission.user_id == user_id,
                    ConditionalPermission.permission_id == permission.id,
                    ConditionalPermission.is_active,
                )
            )
            .first()
        )

        if cond_perm:
            if cond_perm.conditions and context:
                if self._evaluate_conditions(cond_perm.conditions, context):
                    return True, "条件权限通过条件检查"
                else:
                    return False, "条件权限条件不满足"
            elif not cond_perm.conditions:
                return True, "具有无条件权限"

        return False, "没有找到相应的动态权限"

    def _evaluate_conditions(
        self, conditions: dict[str, Any], context: dict[str, Any]
    ) -> bool:
        """
        评估权限条件

        Args:
            conditions: 权限条件
            context: 上下文信息

        Returns:
            是否满足条件
        """
        try:
            # 时间条件
            if "time_range" in conditions:
                time_range = conditions["time_range"]
                current_time = datetime.now(UTC).time()
                start_time = datetime.strptime(time_range["start"], "%H:%M").time()
                end_time = datetime.strptime(time_range["end"], "%H:%M").time()

                if not (start_time <= current_time <= end_time):
                    return False

            # IP条件
            if "allowed_ips" in conditions:
                client_ip = context.get("client_ip")
                if client_ip not in conditions["allowed_ips"]:
                    return False

            # 组织条件
            if "organizations" in conditions:
                user_orgs = context.get("user_organizations", [])
                required_orgs = conditions["organizations"]
                if not any(org in required_orgs for org in user_orgs):
                    return False

            # 自定义条件
            if "custom_conditions" in conditions:
                for condition in conditions["custom_conditions"]:
                    field = condition["field"]
                    operator = condition["operator"]
                    value = condition["value"]

                    context_value = context.get(field)
                    if not self._evaluate_single_condition(
                        context_value, operator, value
                    ):
                        return False

            return True

        except Exception:
            # 条件评估出错，默认拒绝
            return False

    def _evaluate_single_condition(
        self, context_value: Any, operator: str, expected_value: Any
    ) -> bool:
        """评估单个条件"""
        if operator == "equals":
            return context_value == expected_value
        elif operator == "not_equals":
            return context_value != expected_value
        elif operator == "in":
            return context_value in expected_value
        elif operator == "not_in":
            return context_value not in expected_value
        elif operator == "greater_than":
            return context_value > expected_value
        elif operator == "less_than":
            return context_value < expected_value
        elif operator == "greater_equal":
            return context_value >= expected_value
        elif operator == "less_equal":
            return context_value <= expected_value
        else:
            return False

    def cleanup_expired_permissions(self) -> int:
        """
        清理过期的权限

        Returns:
            清理的权限数量
        """
        cleaned_count = 0

        # 清理过期的动态权限
        expired_dynamic = (
            self.db.query(DynamicPermission)
            .filter(
                and_(
                    DynamicPermission.is_active,
                    DynamicPermission.expires_at <= datetime.now(UTC),
                )
            )
            .all()
        )

        for perm in expired_dynamic:
            perm.is_active = False
            cleaned_count += 1

        # 清理过期的临时权限
        expired_temp = (
            self.db.query(TemporaryPermission)
            .filter(
                and_(
                    TemporaryPermission.is_active,
                    TemporaryPermission.expires_at <= datetime.now(UTC),
                )
            )
            .all()
        )

        for perm in expired_temp:
            perm.is_active = False
            cleaned_count += 1

        self.db.commit()
        return cleaned_count

    def get_permission_audit_logs(
        self,
        user_id: str | None = None,
        permission_id: str | None = None,
        action: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        page: int = 1,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """
        获取权限审计日志

        Args:
            user_id: 用户ID筛选
            permission_id: 权限ID筛选
            action: 操作筛选
            start_date: 开始日期
            end_date: 结束日期
            page: 页码
            limit: 每页数量

        Returns:
            审计日志分页结果
        """
        query = self.db.query(DynamicPermissionAudit)

        if user_id:
            query = query.filter(DynamicPermissionAudit.user_id == user_id)

        if permission_id:
            query = query.filter(DynamicPermissionAudit.permission_id == permission_id)

        if action:
            query = query.filter(DynamicPermissionAudit.action == action)

        if start_date:
            query = query.filter(DynamicPermissionAudit.created_at >= start_date)

        if end_date:
            query = query.filter(DynamicPermissionAudit.created_at <= end_date)

        total = query.count()
        logs = (
            query.order_by(DynamicPermissionAudit.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
            .all()
        )

        return {
            "logs": logs,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit,
        }
