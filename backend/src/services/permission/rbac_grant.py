"""
RBAC 统一授权记录（PermissionGrant）管理 — DEPRECATED

所有 PermissionGrant CRUD 方法的 Mixin，供 ``RBACService`` 继承。
Mixin 依赖宿主类提供: ``self.db``, ``self.user_crud``,
``self._invalidate_user_permission_cache()``, ``self._create_permission_audit_log()``。
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from ...core.exception_handler import (
    InvalidRequestError,
    ResourceNotFoundError,
)
from ...crud.rbac import permission_crud, permission_grant_crud
from ...models.rbac import PermissionGrant

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from ...crud.auth import UserCRUD
    from ...schemas.rbac import PermissionGrantUpdate

VALID_GRANT_EFFECTS = {"allow", "deny"}


class RBACGrantMixin:
    """PermissionGrant 管理方法 — 由 RBACService 继承。"""

    # 以下属性由 RBACService.__init__ 提供
    db: AsyncSession
    user_crud: UserCRUD

    # 以下方法由 RBACService 提供
    async def _invalidate_user_permission_cache(self, user_id: str) -> None: ...  # type: ignore[empty-body]
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
    ) -> None: ...  # type: ignore[empty-body]

    async def grant_permission_to_user(
        self,
        *,
        user_id: str,
        permission_id: str,
        grant_type: str,
        granted_by: str,
        effect: str = "allow",
        scope: str = "global",
        scope_id: str | None = None,
        conditions: dict[str, Any] | None = None,
        starts_at: datetime | None = None,
        expires_at: datetime | None = None,
        priority: int = 100,
        source_type: str | None = None,
        source_id: str | None = None,
        reason: str | None = None,
    ) -> PermissionGrant:  # DEPRECATED
        """创建统一授权记录"""
        user = await self.user_crud.get_async(self.db, user_id)
        if not user:
            raise ResourceNotFoundError("用户", user_id)

        permission = await permission_crud.get(self.db, id=permission_id)
        if not permission:
            raise ResourceNotFoundError("权限", permission_id)

        normalized_effect = (effect or "allow").strip().lower()
        if normalized_effect not in VALID_GRANT_EFFECTS:
            raise InvalidRequestError(
                "授权效果必须是 allow 或 deny",
                field="effect",
                details={"allowed_values": sorted(VALID_GRANT_EFFECTS)},
            )

        if starts_at and expires_at and expires_at <= starts_at:
            raise InvalidRequestError(
                "expires_at 必须晚于 starts_at",
                field="expires_at",
            )

        grant = await permission_grant_crud.create(
            self.db,
            obj_in={
                "user_id": user_id,
                "permission_id": permission_id,
                "grant_type": (grant_type or "direct").strip().lower(),
                "effect": normalized_effect,
                "scope": (scope or "global").strip().lower(),
                "scope_id": scope_id,
                "conditions": conditions,
                "starts_at": starts_at,
                "expires_at": expires_at,
                "priority": priority,
                "source_type": source_type,
                "source_id": source_id,
                "granted_by": granted_by,
                "reason": reason,
                "is_active": True,
            },
        )

        await self._invalidate_user_permission_cache(user_id)

        await self._create_permission_audit_log(
            action="permission_grant_create",
            resource_type="permission_grant",
            resource_id=str(grant.id),
            operator_id=granted_by,
            new_permissions={
                "user_id": user_id,
                "permission_id": permission_id,
                "grant_type": grant.grant_type,
                "effect": grant.effect,
                "scope": grant.scope,
                "scope_id": grant.scope_id,
            },
            reason=reason,
        )
        return grant

    async def get_permission_grant(
        self, grant_id: str
    ) -> PermissionGrant | None:  # DEPRECATED
        """获取统一授权记录详情"""
        return await permission_grant_crud.get(self.db, id=grant_id)

    async def list_permission_grants(
        self,
        *,
        skip: int = 0,
        limit: int = 20,
        user_id: str | None = None,
        permission_id: str | None = None,
        grant_type: str | None = None,
        effect: str | None = None,
        scope: str | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[PermissionGrant], int]:  # DEPRECATED
        """分页查询统一授权记录"""
        return await permission_grant_crud.list_with_filters_async(
            self.db,
            skip=skip,
            limit=limit,
            user_id=user_id,
            permission_id=permission_id,
            grant_type=grant_type,
            effect=effect,
            scope=scope,
            is_active=is_active,
        )

    async def update_permission_grant(
        self,
        grant_id: str,
        grant_data: PermissionGrantUpdate,
        updated_by: str,  # DEPRECATED
    ) -> PermissionGrant:  # DEPRECATED
        """更新统一授权记录"""
        grant = await permission_grant_crud.get(self.db, id=grant_id)
        if not grant:
            raise ResourceNotFoundError("统一授权记录", grant_id)

        update_data = grant_data.model_dump(exclude_unset=True)
        old_state = {
            "effect": grant.effect,
            "scope": grant.scope,
            "scope_id": grant.scope_id,
            "starts_at": grant.starts_at.isoformat() if grant.starts_at else None,
            "expires_at": grant.expires_at.isoformat() if grant.expires_at else None,
            "priority": grant.priority,
            "is_active": grant.is_active,
        }

        if "effect" in update_data and update_data["effect"] is not None:
            normalized_effect = str(update_data["effect"]).strip().lower()
            if normalized_effect not in VALID_GRANT_EFFECTS:
                raise InvalidRequestError(
                    "授权效果必须是 allow 或 deny",
                    field="effect",
                    details={"allowed_values": sorted(VALID_GRANT_EFFECTS)},
                )
            update_data["effect"] = normalized_effect

        if "scope" in update_data and update_data["scope"] is not None:
            update_data["scope"] = str(update_data["scope"]).strip().lower()

        starts_at = update_data.get("starts_at", grant.starts_at)
        expires_at = update_data.get("expires_at", grant.expires_at)
        if starts_at and expires_at and expires_at <= starts_at:
            raise InvalidRequestError(
                "expires_at 必须晚于 starts_at",
                field="expires_at",
            )

        if update_data.get("is_active") is False and grant.is_active:
            update_data["revoked_at"] = datetime.now(UTC)
            update_data["revoked_by"] = updated_by
        if update_data.get("is_active") is True and not grant.is_active:
            update_data["revoked_at"] = None
            update_data["revoked_by"] = None

        update_data["updated_at"] = datetime.now(UTC)
        updated_grant = await permission_grant_crud.update(
            self.db,
            db_obj=grant,
            obj_in=update_data,
        )

        target_user_id = str(
            getattr(updated_grant, "user_id", getattr(grant, "user_id", ""))
        ).strip()
        if target_user_id != "":
            await self._invalidate_user_permission_cache(target_user_id)

        await self._create_permission_audit_log(
            action="permission_grant_update",
            resource_type="permission_grant",
            resource_id=str(updated_grant.id),
            operator_id=updated_by,
            old_permissions=old_state,
            new_permissions={
                "effect": updated_grant.effect,
                "scope": updated_grant.scope,
                "scope_id": updated_grant.scope_id,
                "starts_at": (
                    updated_grant.starts_at.isoformat()
                    if updated_grant.starts_at
                    else None
                ),
                "expires_at": (
                    updated_grant.expires_at.isoformat()
                    if updated_grant.expires_at
                    else None
                ),
                "priority": updated_grant.priority,
                "is_active": updated_grant.is_active,
            },
            reason=update_data.get("reason"),
        )
        return updated_grant

    async def revoke_permission_grant(self, grant_id: str, revoked_by: str) -> bool:
        """撤销统一授权记录"""
        grant = await permission_grant_crud.get(self.db, id=grant_id)
        if not grant:
            return False
        if not grant.is_active:
            return True

        grant.is_active = False
        grant.revoked_at = datetime.now(UTC)
        grant.revoked_by = revoked_by
        grant.updated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(grant)
        target_user_id = str(getattr(grant, "user_id", "")).strip()
        if target_user_id != "":
            await self._invalidate_user_permission_cache(target_user_id)

        await self._create_permission_audit_log(
            action="permission_grant_revoke",
            resource_type="permission_grant",
            resource_id=grant_id,
            operator_id=revoked_by,
            old_permissions={
                "effect": grant.effect,
                "scope": grant.scope,
                "scope_id": grant.scope_id,
                "is_active": True,
            },
            new_permissions={
                "effect": grant.effect,
                "scope": grant.scope,
                "scope_id": grant.scope_id,
                "is_active": False,
            },
            reason=grant.reason,
        )
        return True
