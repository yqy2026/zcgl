from typing import Any


class AssetNotFoundError(Exception):
    """Asset not found error"""

    pass


class DuplicateAssetError(Exception):
    """Duplicate asset error"""

    pass


"""
权限委托和继承服�?
支持权限的层级继承和用户间委�?
"""

from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from ...exceptions import BusinessLogicError
from ...models.auth import User
from ...models.dynamic_permission import PermissionDelegation
from ...models.organization import Organization
from ...models.rbac import Permission, Role, UserRoleAssignment


class DelegationScope(str, Enum):
    """委托范围"""

    GLOBAL = "global"
    ORGANIZATION = "organization"
    DEPARTMENT = "department"
    PROJECT = "project"
    ASSET = "asset"


class InheritanceType(str, Enum):
    """继承类型"""

    DIRECT = "direct"  # 直接继承
    INDIRECT = "indirect"  # 间接继承
    DELEGATED = "delegated"  # 委托继承


class PermissionDelegationService:
    """权限委托服务"""

    def __init__(self, db: Session):
        self.db = db

    def delegate_permissions(
        self,
        delegator_id: str,
        delegatee_id: str,
        permission_ids: list[str],
        scope: DelegationScope,
        scope_id: str | None = None,
        starts_at: datetime | None = None,
        ends_at: datetime | None = None,
        conditions: dict[str, Any] | None = None,
        reason: str | None = None,
        can_redelegate: bool = False,
    ) -> PermissionDelegation:
        """
        委托权限给其他用�?

        Args:
            delegator_id: 委托人ID
            delegatee_id: 被委托人ID
            permission_ids: 权限ID列表
            scope: 委托范围
            scope_id: 范围ID
            starts_at: 开始时�?
            ends_at: 结束时间
            conditions: 委托条件
            reason: 委托原因
            can_redelegate: 是否可以再委�?

        Returns:
            创建的委托记�?
        """
        # 验证用户存在
        delegator = self.db.query(User).filter(User.id == delegator_id).first()
        delegatee = self.db.query(User).filter(User.id == delegatee_id).first()

        if not delegator:
            raise BusinessLogicError(f"委托�?{delegator_id} 不存�?)
        if not delegatee:
            raise BusinessLogicError(f"被委托人 {delegatee_id} 不存�?)

        # 检查委托人是否拥有这些权限
        delegator_permissions = self.get_user_effective_permissions(
            delegator_id, scope, scope_id
        )
        delegator_permission_ids = {p["permission_id"] for p in delegator_permissions}

        missing_permissions = set(permission_ids) - delegator_permission_ids
        if missing_permissions:
            raise BusinessLogicError(f"委托人缺少权�? {list(missing_permissions)}")

        # 检查是否已存在相同的委�?
        existing = (
            self.db.query(PermissionDelegation)
            .filter(
                and_(
                    PermissionDelegation.delegator_id == delegator_id,
                    PermissionDelegation.delegatee_id == delegatee_id,
                    PermissionDelegation.scope == scope,
                    PermissionDelegation.scope_id == scope_id,
                    PermissionDelegation.is_active,
                    or_(
                        PermissionDelegation.ends_at.is_(None),
                        PermissionDelegation.ends_at > datetime.now(UTC),
                    ),
                )
            )
            .first()
        )

        if existing:
            # 更新现有委托
            existing.permission_ids = permission_ids
            existing.starts_at = starts_at or datetime.now(UTC)
            existing.ends_at = ends_at
            existing.conditions = conditions
            existing.reason = reason
            existing.can_redelegate = can_redelegate
            existing.updated_at = datetime.now(UTC)
            delegation = existing
        else:
            # 创建新的委托
            delegation = PermissionDelegation(
                delegator_id=delegator_id,
                delegatee_id=delegatee_id,
                permission_ids=permission_ids,
                scope=scope,
                scope_id=scope_id,
                starts_at=starts_at or datetime.now(UTC),
                ends_at=ends_at,
                conditions=conditions,
                reason=reason,
                can_redelegate=can_redelegate,
                is_active=True,
                created_at=datetime.now(UTC),
            )
            self.db.add(delegation)

        self.db.commit()
        self.db.refresh(delegation)

        return delegation

    def revoke_delegation(
        self,
        delegation_id: str,
        revoked_by: str | None = None,
        reason: str | None = None,
    ) -> bool:
        """
        撤销权限委托

        Args:
            delegation_id: 委托ID
            revoked_by: 撤销�?
            reason: 撤销原因

        Returns:
            是否成功撤销
        """
        delegation = (
            self.db.query(PermissionDelegation)
            .filter(PermissionDelegation.id == delegation_id)
            .first()
        )

        if not delegation:
            return False

        delegation.is_active = False
        delegation.revoked_at = datetime.now(UTC)
        delegation.revoked_by = revoked_by
        delegation.revocation_reason = reason

        self.db.commit()
        return True

    def get_user_delegated_permissions(
        self,
        user_id: str,
        scope: DelegationScope | None = None,
        scope_id: str | None = None,
        include_expired: bool = False,
    ) -> list[dict[str, Any]]:
        """
        获取用户被委托的权限

        Args:
            user_id: 用户ID
            scope: 委托范围筛�?
            scope_id: 范围ID筛�?
            include_expired: 是否包含已过期的委托

        Returns:
            被委托的权限列表
        """
        query = self.db.query(PermissionDelegation).filter(
            and_(
                PermissionDelegation.delegatee_id == user_id,
                PermissionDelegation.is_active,
            )
        )

        if not include_expired:
            query = query.filter(
                or_(
                    PermissionDelegation.ends_at.is_(None),
                    PermissionDelegation.ends_at > datetime.now(UTC),
                )
            )

        if scope:
            query = query.filter(PermissionDelegation.scope == scope)

        if scope_id:
            query = query.filter(PermissionDelegation.scope_id == scope_id)

        # 检查委托时间是否已开�?
        now = datetime.now(UTC)
        query = query.filter(
            or_(
                PermissionDelegation.starts_at.is_(None),
                PermissionDelegation.starts_at <= now,
            )
        )

        delegations = query.all()
        result = []

        for delegation in delegations:
            # 获取权限详细信息
            permissions = (
                self.db.query(Permission)
                .filter(Permission.id.in_(delegation.permission_ids))
                .all()
            )

            for permission in permissions:
                result.append(
                    {
                        "delegation_id": delegation.id,
                        "permission_id": permission.id,
                        "permission_name": permission.name,
                        "permission_code": permission.code,
                        "delegator_id": delegation.delegator_id,
                        "scope": delegation.scope,
                        "scope_id": delegation.scope_id,
                        "starts_at": delegation.starts_at,
                        "ends_at": delegation.ends_at,
                        "conditions": delegation.conditions,
                        "can_redelegate": delegation.can_redelegate,
                        "inheritance_type": InheritanceType.DELEGATED,
                        "reason": delegation.reason,
                    }
                )

        return result

    def get_user_delegated_permissions_to_others(
        self, user_id: str, include_expired: bool = False
    ) -> list[dict[str, Any]]:
        """
        获取用户委托给他人的权限

        Args:
            user_id: 用户ID
            include_expired: 是否包含已过期的委托

        Returns:
            委托给他人的权限列表
        """
        query = self.db.query(PermissionDelegation).filter(
            PermissionDelegation.delegator_id == user_id
        )

        if not include_expired:
            query = query.filter(
                and_(
                    PermissionDelegation.is_active,
                    or_(
                        PermissionDelegation.ends_at.is_(None),
                        PermissionDelegation.ends_at > datetime.now(UTC),
                    ),
                )
            )

        delegations = query.all()
        result = []

        for delegation in delegations:
            # 获取被委托人信息
            delegatee = (
                self.db.query(User).filter(User.id == delegation.delegatee_id).first()
            )
            if delegatee:
                result.append(
                    {
                        "delegation_id": delegation.id,
                        "delegatee_id": delegation.delegatee_id,
                        "delegatee_name": delegatee.username,
                        "delegatee_email": delegatee.email,
                        "permission_ids": delegation.permission_ids,
                        "scope": delegation.scope,
                        "scope_id": delegation.scope_id,
                        "starts_at": delegation.starts_at,
                        "ends_at": delegation.ends_at,
                        "is_active": delegation.is_active,
                        "can_redelegate": delegation.can_redelegate,
                        "reason": delegation.reason,
                        "created_at": delegation.created_at,
                    }
                )

        return result

    def get_inherited_permissions(
        self, user_id: str, organization_id: str, include_indirect: bool = True
    ) -> list[dict[str, Any]]:
        """
        获取从组织层级继承的权限

        Args:
            user_id: 用户ID
            organization_id: 组织ID
            include_indirect: 是否包含间接继承

        Returns:
            继承的权限列�?
        """
        # 获取组织信息
        organization = (
            self.db.query(Organization)
            .filter(Organization.id == organization_id)
            .first()
        )

        if not organization:
            return []

        inherited_permissions = []

        # 获取用户在该组织的角�?
        from ..services.organization_permission_service import (
            OrganizationPermissionService,
        )

        org_service = OrganizationPermissionService(self.db)
        user_role = org_service.get_user_organization_role(user_id)

        if not user_role:
            return []

        # 获取组织级别的权限分�?
        role_assignments = (
            self.db.query(UserRoleAssignment)
            .join(Role)
            .filter(
                and_(
                    UserRoleAssignment.user_id == user_id,
                    Role.organization_id == organization_id,
                    UserRoleAssignment.is_active,
                )
            )
            .all()
        )

        for assignment in role_assignments:
            # 获取角色的权�?
            role = self.db.query(Role).filter(Role.id == assignment.role_id).first()
            if role:
                for permission in role.permissions:
                    inherited_permissions.append(
                        {
                            "permission_id": permission.id,
                            "permission_name": permission.name,
                            "permission_code": permission.code,
                            "source_type": "role",
                            "source_id": assignment.role_id,
                            "source_name": assignment.role.name,
                            "organization_id": organization_id,
                            "organization_name": organization.name,
                            "inheritance_type": InheritanceType.DIRECT,
                            "user_role": user_role,
                        }
                    )

        # 如果包含间接继承，获取父级组织的权限
        if include_indirect and organization.parent_id:
            parent_permissions = self.get_inherited_permissions(
                user_id, organization.parent_id, include_indirect=True
            )

            for perm in parent_permissions:
                perm["inheritance_type"] = InheritanceType.INDIRECT
                perm["child_organization_id"] = organization_id
                perm["child_organization_name"] = organization.name
                inherited_permissions.append(perm)

        return inherited_permissions

    def get_user_effective_permissions(
        self,
        user_id: str,
        scope: DelegationScope | None = None,
        scope_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        获取用户的有效权限（包括直接权限、继承权限和委托权限�?

        Args:
            user_id: 用户ID
            scope: 权限范围
            scope_id: 范围ID

        Returns:
            有效权限列表
        """
        all_permissions = []

        # 1. 获取基于角色的权�?
        role_permissions = self.get_user_role_permissions(user_id)
        all_permissions.extend(role_permissions)

        # 2. 获取动态权�?
        from ..services.dynamic_permission_service import DynamicPermissionService

        dynamic_service = DynamicPermissionService(self.db)
        dynamic_permissions = dynamic_service.get_user_dynamic_permissions(user_id)

        for dp in dynamic_permissions:
            if not scope or dp["scope"] == scope.value:
                all_permissions.append(
                    {
                        "permission_id": dp["permission_id"],
                        "permission_name": dp["permission_name"],
                        "permission_code": dp["permission_code"],
                        "source_type": "dynamic",
                        "source_id": dp["id"],
                        "scope": dp["scope"],
                        "scope_id": dp["scope_id"],
                        "inheritance_type": InheritanceType.DIRECT,
                        "expires_at": dp["expires_at"],
                    }
                )

        # 3. 获取委托权限
        delegated_permissions = self.get_user_delegated_permissions(
            user_id, scope, scope_id
        )
        all_permissions.extend(delegated_permissions)

        # 4. 如果指定了组织范围，获取继承权限
        if scope == DelegationScope.ORGANIZATION and scope_id:
            inherited_permissions = self.get_inherited_permissions(user_id, scope_id)
            all_permissions.extend(inherited_permissions)

        # 去重并合�?
        unique_permissions = {}
        for perm in all_permissions:
            key = (perm["permission_id"], perm.get("scope"), perm.get("scope_id"))
            if key not in unique_permissions:
                unique_permissions[key] = perm
            else:
                # 合并权限信息，优先级：委�?> 继承 > 直接 > 动�?
                existing = unique_permissions[key]
                if perm.get("inheritance_type") == InheritanceType.DELEGATED:
                    unique_permissions[key] = perm
                elif perm.get(
                    "inheritance_type"
                ) == InheritanceType.INDIRECT and existing.get(
                    "inheritance_type"
                ) not in [InheritanceType.DELEGATED, InheritanceType.INDIRECT]:
                    unique_permissions[key] = perm

        return list(unique_permissions.values())

    def get_user_role_permissions(self, user_id: str) -> list[dict[str, Any]]:
        """
        获取用户基于角色的权�?

        Args:
            user_id: 用户ID

        Returns:
            角色权限列表
        """
        # 获取用户的活跃角色分�?
        role_assignments = (
            self.db.query(UserRoleAssignment)
            .join(Role)
            .filter(
                and_(
                    UserRoleAssignment.user_id == user_id,
                    UserRoleAssignment.is_active,
                    or_(
                        UserRoleAssignment.expires_at.is_(None),
                        UserRoleAssignment.expires_at > datetime.now(UTC),
                    ),
                )
            )
            .all()
        )

        permissions = []
        for assignment in role_assignments:
            # 获取角色的权�?
            role = self.db.query(Role).filter(Role.id == assignment.role_id).first()
            if role:
                for permission in role.permissions:
                    permissions.append(
                        {
                            "permission_id": permission.id,
                            "permission_name": permission.name,
                            "permission_code": permission.code,
                            "source_type": "role",
                            "source_id": assignment.role_id,
                            "source_name": assignment.role.name,
                            "inheritance_type": InheritanceType.DIRECT,
                            "assignment_id": assignment.id,
                        }
                    )

        return permissions

    def check_permission_with_delegation(
        self,
        user_id: str,
        permission_code: str,
        scope: DelegationScope | None = None,
        scope_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> tuple[bool, str, dict[str, Any]]:
        """
        检查用户权限（包括委托权限�?

        Args:
            user_id: 用户ID
            permission_code: 权限代码
            scope: 权限范围
            scope_id: 范围ID
            context: 上下文信�?

        Returns:
            (是否有权�? 原因, 权限详情)
        """
        # 获取用户的有效权�?
        effective_permissions = self.get_user_effective_permissions(
            user_id, scope, scope_id
        )

        # 查找匹配的权�?
        for perm in effective_permissions:
            if perm.get("permission_code") == permission_code:
                # 检查权限是否过�?
                if perm.get("expires_at") and perm["expires_at"] <= datetime.now(UTC):
                    continue

                # 检查权限条�?
                if perm.get("conditions") and context:
                    if not self._evaluate_delegation_conditions(
                        perm["conditions"], context
                    ):
                        continue

                return True, f"通过 {perm.get('inheritance_type', 'direct')} 权限", perm

        return False, "没有找到相应权限", {}

    def _evaluate_delegation_conditions(
        self, conditions: dict[str, Any], context: dict[str, Any]
    ) -> bool:
        """
        评估委托条件

        Args:
            conditions: 委托条件
            context: 上下文信�?

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

            # 自定义条�?
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
            # 条件评估出错，默认拒�?
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

    def cleanup_expired_delegations(self) -> int:
        """
        清理过期的委�?

        Returns:
            清理的委托数�?
        """
        expired_delegations = (
            self.db.query(PermissionDelegation)
            .filter(
                and_(
                    PermissionDelegation.is_active,
                    PermissionDelegation.ends_at <= datetime.now(UTC),
                )
            )
            .all()
        )

        for delegation in expired_delegations:
            delegation.is_active = False

        self.db.commit()
        return len(expired_delegations)

    def get_delegation_chain(
        self, original_delegator_id: str, permission_id: str, max_depth: int = 5
    ) -> list[dict[str, Any]]:
        """
        获取权限委托�?

        Args:
            original_delegator_id: 原始委托人ID
            permission_id: 权限ID
            max_depth: 最大深�?

        Returns:
            委托链信�?
        """
        chain = []
        visited = set()

        def trace_delegation(delegator_id: str, depth: int) -> bool:
            if depth > max_depth or delegator_id in visited:
                return False

            visited.add(delegator_id)

            # 查找该用户委托出去的权限
            delegations = (
                self.db.query(PermissionDelegation)
                .filter(
                    and_(
                        PermissionDelegation.delegator_id == delegator_id,
                        PermissionDelegation.is_active,
                        PermissionDelegation.permission_ids.contains([permission_id]),
                        or_(
                            PermissionDelegation.ends_at.is_(None),
                            PermissionDelegation.ends_at > datetime.now(UTC),
                        ),
                    )
                )
                .all()
            )

            for delegation in delegations:
                delegatee_info = (
                    self.db.query(User)
                    .filter(User.id == delegation.delegatee_id)
                    .first()
                )

                if delegatee_info:
                    chain.append(
                        {
                            "level": depth,
                            "delegator_id": delegator_id,
                            "delegatee_id": delegation.delegatee_id,
                            "delegatee_name": delegatee_info.username,
                            "delegation_id": delegation.id,
                            "scope": delegation.scope,
                            "scope_id": delegation.scope_id,
                            "can_redelegate": delegation.can_redelegate,
                            "created_at": delegation.created_at,
                        }
                    )

                    # 如果可以再委托，继续追踪
                    if delegation.can_redelegate:
                        trace_delegation(delegation.delegatee_id, depth + 1)

            return True

        trace_delegation(original_delegator_id, 1)
        return chain

    def analyze_permission_coverage(self, organization_id: str) -> dict[str, Any]:
        """
        分析权限覆盖情况

        Args:
            organization_id: 组织ID

        Returns:
            权限覆盖分析结果
        """
        # 获取组织中的所有用�?
        from ..services.organization_permission_service import (
            OrganizationPermissionService,
        )

        org_service = OrganizationPermissionService(self.db)
        accessible_users = org_service.get_accessible_users_in_organization(
            "", organization_id
        )

        total_users = len(accessible_users)
        if total_users == 0:
            return {"total_users": 0, "coverage_analysis": []}

        # 获取所有权�?
        all_permissions = self.db.query(Permission).all()

        coverage_analysis = []
        for permission in all_permissions:
            users_with_permission = 0

            for user_id in accessible_users:
                has_perm, _, _ = self.check_permission_with_delegation(
                    user_id,
                    permission.code,
                    DelegationScope.ORGANIZATION,
                    organization_id,
                )
                if has_perm:
                    users_with_permission += 1

            coverage_percentage = (
                (users_with_permission / total_users) * 100 if total_users > 0 else 0
            )

            coverage_analysis.append(
                {
                    "permission_id": permission.id,
                    "permission_name": permission.name,
                    "permission_code": permission.code,
                    "users_with_permission": users_with_permission,
                    "coverage_percentage": round(coverage_percentage, 2),
                }
            )

        # 按覆盖率排序
        coverage_analysis.sort(key=lambda x: x["coverage_percentage"], reverse=True)

        return {
            "total_users": total_users,
            "total_permissions": len(all_permissions),
            "coverage_analysis": coverage_analysis,
            "average_coverage": round(
                sum(c["coverage_percentage"] for c in coverage_analysis)
                / len(coverage_analysis),
                2,
            )
            if coverage_analysis
            else 0,
        }
