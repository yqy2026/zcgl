"""
RBAC缓存管理

角色/用户权限缓存失效、组织可见范围缓存失效等缓存相关操作。
"""

import logging
from datetime import UTC, datetime
from inspect import isawaitable

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.rbac import UserRoleAssignment
from .permission_cache_service import get_permission_cache_service

logger = logging.getLogger(__name__)


def invalidate_user_accessible_organizations_cache(user_id: str | None = None) -> None:
    """
    失效组织可见范围缓存（延迟导入避免循环依赖）。
    """
    from ..organization_permission_service import (
        invalidate_user_accessible_organizations_cache as _invalidate_cache,
    )

    _invalidate_cache(user_id)


async def invalidate_user_permission_cache(db: AsyncSession, user_id: str) -> None:
    """失效单用户权限缓存与组织可见范围缓存。"""
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


async def get_active_user_ids_by_role(db: AsyncSession, role_id: str) -> list[str]:
    """查询当前角色关联的活跃用户ID列表。"""
    now = datetime.now(UTC)
    stmt = select(UserRoleAssignment.user_id).where(
        UserRoleAssignment.role_id == role_id,
        UserRoleAssignment.is_active.is_(True),
        or_(
            UserRoleAssignment.expires_at.is_(None),
            UserRoleAssignment.expires_at > now,
        ),
    )
    rows = (await db.execute(stmt)).all()
    if isawaitable(rows):
        rows = await rows
    user_ids = [str(row[0]) for row in rows if row and row[0] is not None]
    return sorted(set(user_ids))


async def invalidate_permission_cache_for_role(db: AsyncSession, role_id: str) -> None:
    """角色维度缓存失效（角色缓存 + 受影响用户缓存）。"""
    cache_service = get_permission_cache_service()
    try:
        await cache_service.invalidate_role_cache(role_id)
    except Exception:
        logger.warning(
            "Failed to invalidate role cache for %s",
            role_id,
            exc_info=True,
        )

    user_ids = await get_active_user_ids_by_role(db, role_id)
    for user_id in user_ids:
        await invalidate_user_permission_cache(db, user_id)
