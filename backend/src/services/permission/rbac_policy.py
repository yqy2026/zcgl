"""
RBAC策略计算

权限检查逻辑：静态RBAC权限判断、统一授权记录匹配、管理员权限检测、
有效权限汇总计算。
"""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception_handler import ResourceNotFoundError
from ...crud.auth import UserCRUD
from ...crud.rbac import (
    permission_grant_crud,
    resource_permission_crud,
)
from ...models.rbac import (
    Permission,
    PermissionGrant,  # DEPRECATED
    Role,
)
from ...schemas.rbac import (
    PermissionCheckRequest,
    PermissionCheckResponse,
    PermissionResponse,
    ResourcePermissionResponse,  # DEPRECATED
    RoleResponse,
    UserPermissionSummary,
)
from .permission_cache_service import get_permission_cache_service

# Global admin permission used for full access
ADMIN_PERMISSION_RESOURCE = "system"
ADMIN_PERMISSION_ACTION = "admin"
LEGACY_ADMIN_PERMISSION_ACTION = "manage"

logger = logging.getLogger(__name__)


def role_has_admin_permission(role: Role) -> bool:
    """检查角色是否具有系统管理员权限（兼容 legacy manage）"""
    for permission in role.permissions:
        if permission.resource == ADMIN_PERMISSION_RESOURCE and permission.action in {
            ADMIN_PERMISSION_ACTION,
            LEGACY_ADMIN_PERMISSION_ACTION,
        }:
            return True
    return False


def role_has_permission(role: Role, permission_request: PermissionCheckRequest) -> bool:
    """检查角色是否有权限"""
    for permission in role.permissions:
        if (
            permission.resource == permission_request.resource
            and permission.action == permission_request.action
        ):
            return True
    return False


def get_role_permission_conditions(
    role: Role, permission_request: PermissionCheckRequest
) -> dict[str, Any] | None:
    """获取角色权限条件"""
    for permission in role.permissions:
        if (
            permission.resource == permission_request.resource
            and permission.action == permission_request.action
        ):
            return permission.conditions if permission.conditions else None
    return None  # pragma: no cover  # Defensive: only reached if role_has_permission check is bypassed


def scope_matches(
    grant: PermissionGrant,
    permission_request: PermissionCheckRequest,  # DEPRECATED
) -> bool:
    scope = (grant.scope or "global").lower()
    if scope == "global":
        return True

    request_resource_id = permission_request.resource_id
    request_context = permission_request.context or {}

    if grant.scope_id is None:
        return True

    if request_resource_id and str(request_resource_id) == str(grant.scope_id):
        return True

    context_scope_keys = [
        f"{scope}_id",
        "scope_id",
        "organization_id",  # DEPRECATED context key
        "party_id",
        "project_id",
        "asset_id",
    ]
    for key in context_scope_keys:
        context_value = request_context.get(key)
        if context_value is not None and str(context_value) == str(grant.scope_id):
            return True
    return False


def conditions_match(
    grant: PermissionGrant,
    permission_request: PermissionCheckRequest,  # DEPRECATED
) -> bool:
    if not grant.conditions:
        return True

    context = permission_request.context or {}
    for key, expected in grant.conditions.items():
        if key == "resource_id":
            actual = permission_request.resource_id
        else:
            actual = context.get(key)

        if isinstance(expected, list):
            if actual not in expected:
                return False
        elif actual != expected:
            return False
    return True


def calculate_effective_permissions(
    roles: list[Role],
    resource_permissions: list[Any],
    granted_permissions: list[Permission] | None = None,
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

    # 统一授权记录（permission_grants）映射出的权限
    for permission in granted_permissions or []:
        resource = permission.resource
        action = permission.action
        if resource not in effective_permissions:
            effective_permissions[resource] = []
        if action not in effective_permissions[resource]:
            effective_permissions[resource].append(action)

    return effective_permissions


async def check_static_permission(
    db: AsyncSession,
    user_id: str,
    permission_request: PermissionCheckRequest,
    get_user_roles_fn: Any,
) -> PermissionCheckResponse:
    """检查静态RBAC权限（角色+系统管理员权限）"""
    user_roles = await get_user_roles_fn(user_id)
    if await user_has_admin_permission(db, user_id, user_roles, get_user_roles_fn):
        return PermissionCheckResponse(
            has_permission=True,
            granted_by=["system_admin_permission"],
            conditions=None,
            reason=None,
        )
    if not user_roles:
        return PermissionCheckResponse(
            has_permission=False,
            granted_by=[],
            conditions=None,
            reason="用户未分配任何角色",
        )

    granted_by: list[str] = []
    conditions: dict[str, Any] | None = None
    for role in user_roles:
        if not role_has_permission(role, permission_request):
            continue
        granted_by.append(f"role_{role.name}")
        role_conditions = get_role_permission_conditions(role, permission_request)
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

    return PermissionCheckResponse(
        has_permission=False,
        granted_by=[],
        conditions=None,
        reason="静态角色权限未命中",
    )


async def get_matching_permission_grants(
    db: AsyncSession, user_id: str, permission_request: PermissionCheckRequest
) -> list[PermissionGrant]:  # DEPRECATED
    return await permission_grant_crud.get_matching_grants_async(
        db,
        user_id=user_id,
        resource=permission_request.resource,
        action=permission_request.action,
        now=datetime.now(),
    )


async def check_grant_permission(
    db: AsyncSession, user_id: str, permission_request: PermissionCheckRequest
) -> PermissionCheckResponse:
    """检查统一授权记录权限（动态/临时/资源级）"""
    grants = await get_matching_permission_grants(db, user_id, permission_request)
    if not grants:
        return PermissionCheckResponse(
            has_permission=False,
            granted_by=[],
            conditions=None,
            reason="统一授权未命中",
        )

    valid_grants = [
        grant
        for grant in grants
        if scope_matches(grant, permission_request)
        and conditions_match(grant, permission_request)
    ]
    if not valid_grants:
        return PermissionCheckResponse(
            has_permission=False,
            granted_by=[],
            conditions=None,
            reason="统一授权条件不满足",
        )

    def _grant_sort_key(grant: PermissionGrant) -> tuple[int, float]:  # DEPRECATED
        created_at = getattr(grant, "created_at", None)
        created_at_ts = (
            created_at.timestamp() if isinstance(created_at, datetime) else 0.0
        )
        return int(getattr(grant, "priority", 0) or 0), created_at_ts

    valid_grants.sort(key=_grant_sort_key, reverse=True)

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


async def user_has_admin_permission(
    db: AsyncSession,
    user_id: str,
    roles: list[Role],
    get_user_roles_fn: Any,
) -> bool:
    """检查用户是否具备系统管理员权限（基于权限而非角色名）"""
    if any(role_has_admin_permission(role) for role in roles):
        return True

    for action in {ADMIN_PERMISSION_ACTION, LEGACY_ADMIN_PERMISSION_ACTION}:
        admin_request = PermissionCheckRequest(
            resource=ADMIN_PERMISSION_RESOURCE,
            action=action,
            resource_id=None,
            context=None,
        )
        grant_result = await check_grant_permission(db, user_id, admin_request)
        if grant_result.has_permission:
            return True
    return False


async def get_user_permissions_summary(
    db: AsyncSession,
    user_id: str,
    get_user_roles_fn: Any,
    *,
    user_crud: Any | None = None,
) -> UserPermissionSummary:
    """获取用户权限汇总"""
    if user_crud is None:
        user_crud = UserCRUD()
    user = await user_crud.get_async(db, user_id)
    if not user:
        raise ResourceNotFoundError("用户", user_id)

    cache_service = get_permission_cache_service()
    cached_summary = await cache_service.get_user_permission_summary(user_id)
    if isinstance(cached_summary, dict):
        try:
            return UserPermissionSummary.model_validate(cached_summary)
        except Exception:
            logger.warning(
                "Invalid cached permission summary for user %s, fallback to DB",
                user_id,
                exc_info=True,
            )

    # 获取用户角色
    roles = await get_user_roles_fn(user_id)

    # 获取角色权限
    role_permissions = set()
    for role in roles:
        for permission in role.permissions:
            role_permissions.add(permission)

    # 获取统一授权权限（动态/临时/资源级授权合并）
    granted_permissions = await permission_grant_crud.get_granted_permissions_async(
        db, user_id, now=datetime.now()
    )
    for permission in granted_permissions:
        role_permissions.add(permission)

    # 获取资源权限
    resource_permissions = await resource_permission_crud.get_multi(
        db,
        filters={
            "user_id": user_id,
            "is_active": True,
        },
        skip=0,
        limit=10000,
    )

    # 计算有效权限
    effective_permissions = calculate_effective_permissions(
        roles, resource_permissions, granted_permissions
    )

    roles_response = [RoleResponse.model_validate(role) for role in roles]
    permissions_response = [
        PermissionResponse.model_validate(permission) for permission in role_permissions
    ]
    resource_permissions_response = [
        ResourcePermissionResponse.model_validate(resource_permission)  # DEPRECATED
        for resource_permission in resource_permissions
    ]

    summary = UserPermissionSummary(
        user_id=user_id,
        username=user.username,
        roles=roles_response,
        permissions=permissions_response,
        resource_permissions=resource_permissions_response,
        effective_permissions=effective_permissions,
    )
    await cache_service.set_user_permission_summary(
        user_id,
        summary.model_dump(mode="json"),
    )
    return summary
