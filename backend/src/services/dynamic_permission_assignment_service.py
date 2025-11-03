"""
动态权限分配服务
支持临时权限、条件权限和权限模板的动态分配
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from ..models.auth import User
from ..models.dynamic_permission import (
    ConditionalPermission,
    DynamicPermission,
    DynamicPermissionAudit,
    PermissionTemplate,
    TemporaryPermission,
)
from ..models.rbac import Permission


class DynamicPermissionService:
    """动态权限分配服务"""

    def __init__(self, db: Session):
        self.db = db

    def create_temporary_permission(
        self,
        user_id: str,
        permission_id: str,
        scope: str,
        scope_id: str | None,
        expires_at: datetime,
        assigned_by: str,
        reason: str | None = None,
    ) -> TemporaryPermission:
        """创建临时权限"""

        # 检查权限是否存在
        permission = (
            self.db.query(Permission).filter(Permission.id == permission_id).first()
        )
        if not permission:
            raise ValueError(f"权限不存在: {permission_id}")

        # 检查用户是否存在
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"用户不存在: {user_id}")

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
            raise ValueError("用户已拥有相同的临时权限")

        # 创建临时权限
        temp_permission = TemporaryPermission(
            user_id=user_id,
            permission_id=permission_id,
            scope=scope,
            scope_id=scope_id,
            expires_at=expires_at,
            assigned_by=assigned_by,
        )

        self.db.add(temp_permission)

        # 创建审计日志
        audit_log = DynamicPermissionAudit(
            user_id=user_id,
            permission_id=permission_id,
            action="ASSIGN_TEMPORARY",
            permission_type="temporary",
            scope=scope,
            scope_id=scope_id,
            assigned_by=assigned_by,
            reason=reason,
            conditions={"expires_at": expires_at.isoformat()},
        )
        self.db.add(audit_log)

        self.db.commit()
        self.db.refresh(temp_permission)

        return temp_permission

    def create_conditional_permission(
        self,
        user_id: str,
        permission_id: str,
        scope: str,
        scope_id: str | None,
        conditions: dict[str, Any],
        assigned_by: str,
        reason: str | None = None,
    ) -> ConditionalPermission:
        """创建条件权限"""

        # 检查权限是否存在
        permission = (
            self.db.query(Permission).filter(Permission.id == permission_id).first()
        )
        if not permission:
            raise ValueError(f"权限不存在: {permission_id}")

        # 检查用户是否存在
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"用户不存在: {user_id}")

        # 验证条件格式
        if not conditions:
            raise ValueError("条件权限必须提供条件")

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
            raise ValueError("用户已拥有相同的条件权限")

        # 创建条件权限
        conditional_permission = ConditionalPermission(
            user_id=user_id,
            permission_id=permission_id,
            scope=scope,
            scope_id=scope_id,
            conditions=conditions,
            assigned_by=assigned_by,
        )

        self.db.add(conditional_permission)

        # 创建审计日志
        audit_log = DynamicPermissionAudit(
            user_id=user_id,
            permission_id=permission_id,
            action="ASSIGN_CONDITIONAL",
            permission_type="conditional",
            scope=scope,
            scope_id=scope_id,
            assigned_by=assigned_by,
            reason=reason,
            conditions=conditions,
        )
        self.db.add(audit_log)

        self.db.commit()
        self.db.refresh(conditional_permission)

        return conditional_permission

    def create_permission_template(
        self,
        name: str,
        description: str,
        permission_ids: list[str],
        scope: str,
        conditions: dict[str, Any] | None,
        created_by: str,
    ) -> PermissionTemplate:
        """创建权限模板"""

        # 验证权限ID是否存在
        permissions = (
            self.db.query(Permission).filter(Permission.id.in_(permission_ids)).all()
        )

        if len(permissions) != len(permission_ids):
            raise ValueError("部分权限ID不存在")

        # 检查模板名称是否已存在
        existing = (
            self.db.query(PermissionTemplate)
            .filter(PermissionTemplate.name == name, PermissionTemplate.is_active)
            .first()
        )

        if existing:
            raise ValueError(f"权限模板名称已存在: {name}")

        # 创建权限模板
        template = PermissionTemplate(
            name=name,
            description=description,
            permission_ids=permission_ids,
            scope=scope,
            conditions=conditions,
            created_by=created_by,
        )

        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)

        return template

    def assign_permissions_from_template(
        self,
        user_id: str,
        template_id: str,
        scope_id: str | None,
        assigned_by: str,
        reason: str | None = None,
    ) -> List[TemporaryPermission | ConditionalPermission]:
        """从模板分配权限给用户"""

        # 获取权限模板
        template = (
            self.db.query(PermissionTemplate)
            .filter(
                PermissionTemplate.id == template_id,
                PermissionTemplate.is_active,
            )
            .first()
        )

        if not template:
            raise ValueError(f"权限模板不存在: {template_id}")

        assigned_permissions = []

        # 根据模板条件创建权限
        for permission_id in template.permission_ids:
            if template.conditions:
                # 如果有条件，创建条件权限
                conditional_permission = self.create_conditional_permission(
                    user_id=user_id,
                    permission_id=permission_id,
                    scope=template.scope,
                    scope_id=scope_id,
                    conditions=template.conditions,
                    assigned_by=assigned_by,
                    reason=f"通过模板分配: {template.name} - {reason or ''}",
                )
                assigned_permissions.append(conditional_permission)
            else:
                # 如果没有条件，创建动态权限
                dynamic_permission = self.create_dynamic_permission(
                    user_id=user_id,
                    permission_id=permission_id,
                    scope=template.scope,
                    scope_id=scope_id,
                    permission_type="template_based",
                    conditions=None,
                    assigned_by=assigned_by,
                    reason=f"通过模板分配: {template.name} - {reason or ''}",
                )
                assigned_permissions.append(dynamic_permission)

        return assigned_permissions

    def create_dynamic_permission(
        self,
        user_id: str,
        permission_id: str,
        scope: str,
        scope_id: str | None,
        permission_type: str,
        conditions: dict[str, Any] | None,
        assigned_by: str,
        expires_at: datetime | None = None,
        reason: str | None = None,
    ) -> DynamicPermission:
        """创建动态权限"""

        # 检查权限是否存在
        permission = (
            self.db.query(Permission).filter(Permission.id == permission_id).first()
        )
        if not permission:
            raise ValueError(f"权限不存在: {permission_id}")

        # 检查用户是否存在
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"用户不存在: {user_id}")

        # 创建动态权限
        dynamic_permission = DynamicPermission(
            user_id=user_id,
            permission_id=permission_id,
            scope=scope,
            scope_id=scope_id,
            permission_type=permission_type,
            conditions=conditions,
            expires_at=expires_at,
            assigned_by=assigned_by,
        )

        self.db.add(dynamic_permission)

        # 创建审计日志
        audit_log = DynamicPermissionAudit(
            user_id=user_id,
            permission_id=permission_id,
            action="ASSIGN",
            permission_type=permission_type,
            scope=scope,
            scope_id=scope_id,
            assigned_by=assigned_by,
            reason=reason,
            conditions=conditions,
        )
        self.db.add(audit_log)

        self.db.commit()
        self.db.refresh(dynamic_permission)

        return dynamic_permission

    def revoke_permission(
        self,
        user_id: str,
        permission_id: str,
        scope: str,
        scope_id: str | None,
        revoked_by: str,
        reason: str | None = None,
    ) -> bool:
        """撤销用户权限"""

        revoked_count = 0

        # 撤销动态权限
        dynamic_permissions = (
            self.db.query(DynamicPermission)
            .filter(
                and_(
                    DynamicPermission.user_id == user_id,
                    DynamicPermission.permission_id == permission_id,
                    DynamicPermission.scope == scope,
                    DynamicPermission.scope_id == scope_id,
                    DynamicPermission.is_active,
                )
            )
            .all()
        )

        for perm in dynamic_permissions:
            perm.is_active = False
            perm.revoked_by = revoked_by
            perm.revoked_at = datetime.now(UTC)
            revoked_count += 1

        # 撤销临时权限
        temp_permissions = (
            self.db.query(TemporaryPermission)
            .filter(
                and_(
                    TemporaryPermission.user_id == user_id,
                    TemporaryPermission.permission_id == permission_id,
                    TemporaryPermission.scope == scope,
                    TemporaryPermission.scope_id == scope_id,
                    TemporaryPermission.is_active,
                )
            )
            .all()
        )

        for perm in temp_permissions:
            perm.is_active = False
            revoked_count += 1

        # 撤销条件权限
        conditional_permissions = (
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
            .all()
        )

        for perm in conditional_permissions:
            perm.is_active = False
            revoked_count += 1

        if revoked_count > 0:
            # 创建审计日志
            audit_log = DynamicPermissionAudit(
                user_id=user_id,
                permission_id=permission_id,
                action="REVOKE",
                permission_type="mixed",
                scope=scope,
                scope_id=scope_id,
                assigned_by=revoked_by,
                reason=reason,
            )
            self.db.add(audit_log)

        self.db.commit()
        return revoked_count > 0

    def get_user_permissions(
        self,
        user_id: str,
        include_expired: bool = False,
        include_inactive: bool = False,
    ) -> Dict[str, Any][str, list[dict[str, Any]]]:
        """获取用户的所有动态权限"""

        result = {
            "dynamic_permissions": [],
            "temporary_permissions": [],
            "conditional_permissions": [],
        }

        # 获取动态权限
        query = self.db.query(DynamicPermission).filter(
            DynamicPermission.user_id == user_id
        )
        if not include_inactive:
            query = query.filter(DynamicPermission.is_active)
        if not include_expired:
            query = query.filter(
                or_(
                    DynamicPermission.expires_at.is_(None),
                    DynamicPermission.expires_at > datetime.now(UTC),
                )
            )

        dynamic_perms = query.all()
        for perm in dynamic_perms:
            result["dynamic_permissions"].append(
                {
                    "id": perm.id,
                    "permission_id": perm.permission_id,
                    "permission_type": perm.permission_type,
                    "scope": perm.scope,
                    "scope_id": perm.scope_id,
                    "conditions": perm.conditions,
                    "expires_at": perm.expires_at,
                    "assigned_at": perm.assigned_at,
                    "assigned_by": perm.assigned_by,
                    "is_active": perm.is_active,
                }
            )

        # 获取临时权限
        query = self.db.query(TemporaryPermission).filter(
            TemporaryPermission.user_id == user_id
        )
        if not include_inactive:
            query = query.filter(TemporaryPermission.is_active)
        if not include_expired:
            query = query.filter(TemporaryPermission.expires_at > datetime.now(UTC))

        temp_perms = query.all()
        for perm in temp_perms:
            result["temporary_permissions"].append(
                {
                    "id": perm.id,
                    "permission_id": perm.permission_id,
                    "scope": perm.scope,
                    "scope_id": perm.scope_id,
                    "expires_at": perm.expires_at,
                    "assigned_at": perm.assigned_at,
                    "assigned_by": perm.assigned_by,
                    "is_active": perm.is_active,
                }
            )

        # 获取条件权限
        query = self.db.query(ConditionalPermission).filter(
            ConditionalPermission.user_id == user_id
        )
        if not include_inactive:
            query = query.filter(ConditionalPermission.is_active)

        conditional_perms = query.all()
        for perm in conditional_perms:
            result["conditional_permissions"].append(
                {
                    "id": perm.id,
                    "permission_id": perm.permission_id,
                    "scope": perm.scope,
                    "scope_id": perm.scope_id,
                    "conditions": perm.conditions,
                    "assigned_at": perm.assigned_at,
                    "assigned_by": perm.assigned_by,
                    "is_active": perm.is_active,
                }
            )

        return result

    def check_user_permission(
        self,
        user_id: str,
        required_permission: str,
        scope: str,
        scope_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """检查用户是否拥有特定权限"""

        # 检查动态权限
        dynamic_perm = (
            self.db.query(DynamicPermission)
            .join(Permission)
            .filter(
                and_(
                    DynamicPermission.user_id == user_id,
                    Permission.name == required_permission,
                    DynamicPermission.scope == scope,
                    or_(
                        DynamicPermission.scope_id.is_(None),
                        DynamicPermission.scope_id == scope_id,
                    ),
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
            # 如果有条件，需要验证条件
            if dynamic_perm.conditions and context:
                if self._evaluate_conditions(dynamic_perm.conditions, context):
                    return {
                        "has_permission": True,
                        "source": "dynamic_permission",
                        "permission_id": dynamic_perm.id,
                    }
                else:
                    return {"has_permission": False, "reason": "条件不满足"}
            else:
                return {
                    "has_permission": True,
                    "source": "dynamic_permission",
                    "permission_id": dynamic_perm.id,
                }

        # 检查临时权限
        temp_perm = (
            self.db.query(TemporaryPermission)
            .join(Permission)
            .filter(
                and_(
                    TemporaryPermission.user_id == user_id,
                    Permission.name == required_permission,
                    TemporaryPermission.scope == scope,
                    or_(
                        TemporaryPermission.scope_id.is_(None),
                        TemporaryPermission.scope_id == scope_id,
                    ),
                    TemporaryPermission.is_active,
                    TemporaryPermission.expires_at > datetime.now(UTC),
                )
            )
            .first()
        )

        if temp_perm:
            return {
                "has_permission": True,
                "source": "temporary_permission",
                "permission_id": temp_perm.id,
            }

        # 检查条件权限
        conditional_perm = (
            self.db.query(ConditionalPermission)
            .join(Permission)
            .filter(
                and_(
                    ConditionalPermission.user_id == user_id,
                    Permission.name == required_permission,
                    ConditionalPermission.scope == scope,
                    or_(
                        ConditionalPermission.scope_id.is_(None),
                        ConditionalPermission.scope_id == scope_id,
                    ),
                    ConditionalPermission.is_active,
                )
            )
            .first()
        )

        if conditional_perm:
            # 条件权限必须有上下文
            if context and conditional_perm.conditions:
                if self._evaluate_conditions(conditional_perm.conditions, context):
                    return {
                        "has_permission": True,
                        "source": "conditional_permission",
                        "permission_id": conditional_perm.id,
                    }
                else:
                    return {"has_permission": False, "reason": "条件不满足"}
            else:
                return {"has_permission": False, "reason": "缺少上下文信息"}

        return {"has_permission": False, "reason": "未找到匹配的权限"}

    def _evaluate_conditions(
        self, conditions: dict[str, Any], context: dict[str, Any]
    ) -> bool:
        """评估权限条件"""

        try:
            # 时间条件
            if "time_range" in conditions:
                time_range = conditions["time_range"]
                current_time = datetime.now().time()
                start_time = datetime.strptime(time_range["start"], "%H:%M").time()
                end_time = datetime.strptime(time_range["end"], "%H:%M").time()

                if not (start_time <= current_time <= end_time):
                    return False

            # IP地址条件
            if "ip_addresses" in conditions:
                if context.get("ip_address") not in conditions["ip_addresses"]:
                    return False

            # 工作日条件
            if "weekdays" in conditions:
                current_weekday = datetime.now().weekday()  # 0=Monday, 6=Sunday
                if current_weekday not in conditions["weekdays"]:
                    return False

            # 自定义条件
            if "custom" in conditions:
                for custom_condition in conditions["custom"]:
                    field = custom_condition["field"]
                    operator = custom_condition["operator"]
                    value = custom_condition["value"]

                    context_value = context.get(field)
                    if context_value is None:
                        return False

                    if operator == "equals":
                        if context_value != value:
                            return False
                    elif operator == "in":
                        if context_value not in value:
                            return False
                    elif operator == "greater_than":
                        if context_value <= value:
                            return False
                    elif operator == "less_than":
                        if context_value >= value:
                            return False

            return True

        except Exception:
            return False

    def cleanup_expired_permissions(self) -> Dict[str, Any][str, int]:
        """清理过期的权限"""

        now = datetime.now(UTC)
        cleaned_count = {"dynamic_permissions": 0, "temporary_permissions": 0}

        # 清理过期的动态权限
        expired_dynamic = (
            self.db.query(DynamicPermission)
            .filter(
                and_(
                    DynamicPermission.expires_at.is_not(None),
                    DynamicPermission.expires_at <= now,
                    DynamicPermission.is_active,
                )
            )
            .all()
        )

        for perm in expired_dynamic:
            perm.is_active = False
            cleaned_count["dynamic_permissions"] += 1

        # 清理过期的临时权限
        expired_temp = (
            self.db.query(TemporaryPermission)
            .filter(
                and_(
                    TemporaryPermission.expires_at <= now,
                    TemporaryPermission.is_active,
                )
            )
            .all()
        )

        for perm in expired_temp:
            perm.is_active = False
            cleaned_count["temporary_permissions"] += 1

        self.db.commit()
        return cleaned_count

    def get_permission_audit_log(
        self,
        user_id: str | None = None,
        permission_id: str | None = None,
        action: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
    ) -> List[dict[str, Any]]:
        """获取权限审计日志"""

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

        audit_logs = (
            query.order_by(DynamicPermissionAudit.created_at.desc()).limit(limit).all()
        )

        result = []
        for log in audit_logs:
            result.append(
                {
                    "id": log.id,
                    "user_id": log.user_id,
                    "permission_id": log.permission_id,
                    "action": log.action,
                    "permission_type": log.permission_type,
                    "scope": log.scope,
                    "scope_id": log.scope_id,
                    "assigned_by": log.assigned_by,
                    "reason": log.reason,
                    "conditions": log.conditions,
                    "created_at": log.created_at,
                }
            )

        return result
