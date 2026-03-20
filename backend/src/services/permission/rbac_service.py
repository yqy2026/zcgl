"""
RBAC服务层
"""

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception_handler import (
    DuplicateResourceError,
    OperationNotAllowedError,
    ResourceConflictError,
    ResourceNotFoundError,
)
from ...crud.auth import UserCRUD
from ...crud.query_builder import PartyFilter
from ...crud.rbac import (
    permission_audit_log_crud,
    permission_crud,
    role_crud,
    user_role_assignment_crud,
)
from ...models.rbac import Permission, Role, UserRoleAssignment
from ...schemas.rbac import (
    PermissionCheckRequest,
    PermissionCheckResponse,
    PermissionCreate,
    UserPermissionSummary,
    UserRoleAssignmentCreate,
)
from ...services.party_scope import resolve_user_party_filter
from .rbac_cache import (
    invalidate_permission_cache_for_role,
)
from .rbac_grant import RBACGrantMixin
from .rbac_policy import (
    ADMIN_PERMISSION_ACTION,
    ADMIN_PERMISSION_RESOURCE,
    LEGACY_ADMIN_PERMISSION_ACTION,
    calculate_effective_permissions,
    conditions_match,
    get_role_permission_conditions,
    get_user_permissions_summary,
    role_has_admin_permission,
    role_has_permission,
    scope_matches,
    user_has_admin_permission,
)
from .rbac_role import RBACRoleMixin

# Re-export public constants for backward compatibility
__all__ = [
    "ADMIN_PERMISSION_ACTION",
    "ADMIN_PERMISSION_RESOURCE",
    "LEGACY_ADMIN_PERMISSION_ACTION",
    "RBACService",
]

logger = logging.getLogger(__name__)

_user_crud = UserCRUD()


# Backward-compat re-export (used by __init__.py and external callers)
from .rbac_cache import (  # noqa: E402, F811
    get_permission_cache_service,
    invalidate_user_accessible_organizations_cache,
)


class RBACService(RBACRoleMixin, RBACGrantMixin):
    """RBAC服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_crud = UserCRUD()

    # 角色管理方法继承自 RBACRoleMixin

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
        """获取权限列表（全局权限元数据，不按主体隔离）。"""
        return await permission_crud.get_multi_with_count_async(
            self.db,
            skip=skip,
            limit=limit,
            search=search,
            resource=resource,
            action=action,
            is_system_permission=is_system_permission,
        )

    async def _resolve_party_filter(
        self,
        *,
        current_user_id: str | None = None,
        party_filter: PartyFilter | None = None,
    ) -> PartyFilter | None:
        return await resolve_user_party_filter(
            self.db,
            current_user_id=current_user_id,
            party_filter=party_filter,
            logger=logger,
            allow_legacy_default_organization_fallback=False,
        )

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

        await self._invalidate_user_permission_cache(str(assignment_data.user_id))

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
        await self._invalidate_user_permission_cache(user_id)

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

    async def get_user_roles(
        self, user_id: str, active_only: bool = True
    ) -> list[Role]:
        """获取用户角色"""
        return await role_crud.get_roles_by_user_async(
            self.db, user_id, active_only=active_only, include_permissions=True
        )

    # ==================== 权限检查 ====================

    async def check_permission(
        self, user_id: str, permission_request: PermissionCheckRequest
    ) -> PermissionCheckResponse:
        """检查用户权限。

        Uses instance methods ``get_user_roles``, ``_user_has_admin_permission``
        and ``_get_matching_permission_grants`` so that tests can patch them on
        the service instance.
        """
        user = await self.user_crud.get_async(self.db, user_id)
        if not user or not user.is_active:
            return PermissionCheckResponse(
                has_permission=False, reason="用户不存在或已禁用", conditions=None
            )

        # --- static RBAC (roles + admin) ---
        user_roles = await self.get_user_roles(user_id)
        if await self._user_has_admin_permission(user_id, user_roles):
            return PermissionCheckResponse(
                has_permission=True,
                granted_by=["system_admin_permission"],
                conditions=None,
                reason=None,
            )
        if user_roles:
            granted_by: list[str] = []
            conditions: dict[str, Any] | None = None
            for role in user_roles:
                if not role_has_permission(role, permission_request):
                    continue
                granted_by.append(f"role_{role.name}")
                role_conditions = get_role_permission_conditions(
                    role, permission_request
                )
                if role_conditions:
                    if conditions is None:
                        conditions = dict(role_conditions)
                    else:
                        conditions = {**conditions, **role_conditions}
            if granted_by:
                return PermissionCheckResponse(
                    has_permission=True,
                    granted_by=granted_by,
                    conditions=conditions,
                    reason=None,
                )
            static_reason = "静态角色权限未命中"
        else:
            static_reason = "用户未分配任何角色"

        # --- grant-based permission ---
        grants = await self._get_matching_permission_grants(user_id, permission_request)
        if not grants:
            return PermissionCheckResponse(
                has_permission=False,
                granted_by=[],
                conditions=None,
                reason=static_reason,
            )

        valid_grants = [
            g
            for g in grants
            if scope_matches(g, permission_request)
            and conditions_match(g, permission_request)
        ]
        if not valid_grants:
            return PermissionCheckResponse(
                has_permission=False,
                granted_by=[],
                conditions=None,
                reason="统一授权条件不满足",
            )

        valid_grants.sort(
            key=lambda g: (
                int(getattr(g, "priority", 0) or 0),
                (
                    getattr(g, "created_at").timestamp()
                    if hasattr(getattr(g, "created_at", None), "timestamp")
                    else 0.0
                ),
            ),
            reverse=True,
        )

        deny_grants = [g for g in valid_grants if (g.effect or "allow") == "deny"]
        if deny_grants:
            deny = deny_grants[0]
            return PermissionCheckResponse(
                has_permission=False,
                granted_by=[f"grant_{deny.id}"],
                conditions=deny.conditions if deny.conditions else None,
                reason="命中拒绝授权",
            )

        allow_grants = [g for g in valid_grants if (g.effect or "allow") == "allow"]
        if not allow_grants:
            return PermissionCheckResponse(
                has_permission=False,
                granted_by=[],
                conditions=None,
                reason="统一授权无可用ALLOW记录",
            )

        merged_conditions: dict[str, Any] | None = None
        for grant in allow_grants:
            if not grant.conditions:
                continue
            if merged_conditions is None:
                merged_conditions = dict(grant.conditions)
            else:
                merged_conditions = {**merged_conditions, **grant.conditions}

        return PermissionCheckResponse(
            has_permission=True,
            granted_by=[f"grant_{grant.id}" for grant in allow_grants],
            conditions=merged_conditions,
            reason=None,
        )

    async def is_admin(self, user_id: str) -> bool:
        """判断用户是否为管理员（兼容 system:admin / system:manage）"""
        admin_request = PermissionCheckRequest(
            resource=ADMIN_PERMISSION_RESOURCE,
            action=ADMIN_PERMISSION_ACTION,
            resource_id=None,
            context=None,
        )
        result = await self.check_permission(user_id, admin_request)
        return result.has_permission

    async def get_user_role_summary(self, user_id: str) -> dict[str, Any]:
        """获取用户角色汇总信息（含主角色与管理员标记）"""
        roles = await self.get_user_roles(user_id)
        roles_sorted = sorted(roles, key=lambda role: role.level or 0)
        primary = roles_sorted[0] if roles_sorted else None
        is_admin = await user_has_admin_permission(
            self.db, user_id, roles_sorted, self.get_user_roles
        )
        return {
            "roles": [role.name for role in roles_sorted],
            "role_ids": [str(role.id) for role in roles_sorted],
            "primary_role_id": str(primary.id) if primary else None,
            "primary_role_name": (
                primary.display_name if primary and primary.display_name else None
            ),
            "is_admin": is_admin,
        }

    async def get_user_permissions_summary(self, user_id: str) -> UserPermissionSummary:
        """获取用户权限汇总"""
        return await get_user_permissions_summary(
            self.db, user_id, self.get_user_roles, user_crud=self.user_crud
        )

    # 统一授权记录管理方法继承自 RBACGrantMixin

    # ==================== 私有方法 ====================

    async def _invalidate_user_permission_cache(self, user_id: str) -> None:
        """失效单用户权限缓存与组织可见范围缓存。

        NOTE: 内联缓存操作而非委托给 ``rbac_cache.invalidate_user_permission_cache``，
        确保测试 ``patch("src.services.permission.rbac_service.get_permission_cache_service")``
        能正确拦截调用。
        """
        cache_service = get_permission_cache_service()
        try:
            await cache_service.invalidate_user_cache(user_id)
        except Exception:
            logger.warning(
                "Failed to invalidate permission cache for user %s",
                user_id,
                exc_info=True,
            )

        try:
            invalidate_user_accessible_organizations_cache(user_id)
        except Exception:
            logger.warning(
                "Failed to invalidate organization access cache for user %s",
                user_id,
                exc_info=True,
            )

        try:
            from ..authz import AUTHZ_USER_ROLE_UPDATED, authz_event_bus

            authz_event_bus.publish_invalidation(
                event_type=AUTHZ_USER_ROLE_UPDATED,
                payload={"user_id": user_id},
            )
        except Exception:
            logger.warning(
                "Failed to publish authz user-role invalidation event for user %s",
                user_id,
                exc_info=True,
            )

    async def _invalidate_permission_cache_for_role(self, role_id: str) -> None:
        """角色维度缓存失效（角色缓存 + 受影响用户缓存）。"""
        await invalidate_permission_cache_for_role(self.db, role_id)

    async def _assign_permissions_to_role(
        self, role_id: str, permission_ids: list[str], operator_id: str
    ) -> None:
        """为角色分配权限"""
        role = await role_crud.get(self.db, id=role_id)
        if not role:
            raise ResourceNotFoundError("角色", role_id)
        if role.is_system_role:
            raise OperationNotAllowedError("系统角色权限无法修改", reason="system_role")

        permissions: list[Permission] = []
        if permission_ids:
            permissions = await permission_crud.get_by_ids_async(
                self.db, permission_ids
            )
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
        await role_crud.update_permissions_created_by_async(
            self.db, role_id, operator_id
        )

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

    # ==================== 向后兼容实例方法代理 ====================
    # 以下方法已提取为 rbac_policy.py 的独立函数，
    # 但保留实例方法签名以兼容现有测试的 `service._xxx(...)` 调用。

    def _role_has_permission(
        self, role: Role, permission_request: PermissionCheckRequest
    ) -> bool:
        return role_has_permission(role, permission_request)

    def _role_has_admin_permission(self, role: Role) -> bool:
        return role_has_admin_permission(role)

    def _get_role_permission_conditions(
        self, role: Role, permission_request: PermissionCheckRequest
    ) -> dict[str, Any] | None:
        return get_role_permission_conditions(role, permission_request)

    def _calculate_effective_permissions(
        self,
        roles: list[Role],
        resource_permissions: list[Any],
        granted_permissions: list[Permission] | None = None,
    ) -> dict[str, list[str]]:
        return calculate_effective_permissions(
            roles, resource_permissions, granted_permissions
        )

    async def _user_has_admin_permission(self, user_id: str, roles: list[Role]) -> bool:
        return await user_has_admin_permission(
            self.db, user_id, roles, self.get_user_roles
        )

    @staticmethod
    def _can_manage_role(manager_level: int, subordinate_level: int) -> bool:
        """检查是否可以管理指定级别的角色"""
        return manager_level > subordinate_level

    async def _get_matching_permission_grants(
        self,
        user_id: str,
        permission_request: PermissionCheckRequest,
    ) -> list:
        """向后兼容代理 — 供测试 ``patch.object(service, '_get_matching_permission_grants', ...)``。"""
        from .rbac_policy import get_matching_permission_grants

        return await get_matching_permission_grants(
            self.db, user_id, permission_request
        )

    # ==================== Permission Decorator Adapter Methods ====================

    async def check_user_permission(
        self, user_id: str, resource: str, action: str
    ) -> bool:
        """检查用户权限 - 适配器方法供装饰器使用"""
        if resource == ADMIN_PERMISSION_RESOURCE and action in {
            ADMIN_PERMISSION_ACTION,
            LEGACY_ADMIN_PERMISSION_ACTION,
        }:
            return await self.is_admin(user_id)

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
        """检查资源访问权限 - 适配器方法供装饰器使用"""
        permission_request = PermissionCheckRequest(
            resource=resource,
            action=action,
            resource_id=resource_id,
            context=None,
        )

        response = await self.check_permission(user_id, permission_request)
        return response.has_permission

    async def check_organization_access(  # DEPRECATED compatibility API
        self,
        user_id: str,
        organization_id: str,  # DEPRECATED alias
    ) -> bool:
        """检查组织访问权限 - 适配器方法供装饰器使用"""
        permission_request = PermissionCheckRequest(
            resource="organization",
            action="view",
            resource_id=organization_id,  # DEPRECATED alias
            context=None,
        )

        response = await self.check_permission(user_id, permission_request)
        return response.has_permission
