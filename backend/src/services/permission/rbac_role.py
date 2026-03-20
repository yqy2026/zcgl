"""
RBAC 角色管理

角色 CRUD、权限分配、角色查询等操作的 Mixin，供 ``RBACService`` 继承。
Mixin 依赖宿主类提供: ``self.db``, ``self.user_crud``,
``self._resolve_party_filter()``, ``self._invalidate_permission_cache_for_role()``,
``self._create_permission_audit_log()``, ``self._assign_permissions_to_role()``。
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from ...core.exception_handler import (
    DuplicateResourceError,
    InternalServerError,
    OperationNotAllowedError,
    ResourceNotFoundError,
)
from ...crud.rbac import (
    permission_crud,
    role_crud,
    user_role_assignment_crud,
)
from ...models.rbac import Permission, Role

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from ...crud.auth import UserCRUD
    from ...crud.query_builder import PartyFilter
    from ...schemas.rbac import RoleCreate, RoleUpdate


class RBACRoleMixin:
    """角色管理方法 — 由 RBACService 继承。"""

    # 以下属性/方法由 RBACService 提供
    db: AsyncSession
    user_crud: UserCRUD

    async def _resolve_party_filter(
        self,
        *,
        current_user_id: str | None = None,
        party_filter: PartyFilter | None = None,
    ) -> PartyFilter | None: ...  # type: ignore[empty-body]
    async def _invalidate_permission_cache_for_role(self, role_id: str) -> None: ...  # type: ignore[empty-body]
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
    async def _assign_permissions_to_role(
        self, role_id: str, permission_ids: list[str], operator_id: str
    ) -> None: ...  # type: ignore[empty-body]

    # ==================== 角色管理 ====================

    async def create_role(self, role_data: RoleCreate, created_by: str) -> Role:
        """创建角色"""
        existing_role = await role_crud.get_by_name(self.db, name=role_data.name)
        if existing_role:
            raise DuplicateResourceError("角色", "name", role_data.name)

        role = await role_crud.create(self.db, obj_in=role_data, created_by=created_by)

        if role_data.permission_ids:
            await self.update_role_permissions(
                role_id=str(role.id),
                permission_ids=role_data.permission_ids,
                updated_by=created_by,
            )

        return role

    async def update_role(
        self,
        role_id: str,
        role_data: RoleUpdate,
        updated_by: str,
        party_filter: PartyFilter | None = None,
        current_user_id: str | None = None,
    ) -> Role:
        """更新角色"""
        resolved_party_filter = await self._resolve_party_filter(
            current_user_id=current_user_id,
            party_filter=party_filter,
        )
        role = await role_crud.get(
            self.db,
            id=role_id,
            party_filter=resolved_party_filter,
        )
        if not role:
            raise ResourceNotFoundError("角色", role_id)

        if role.is_system_role:
            raise OperationNotAllowedError("系统角色不能修改", reason="system_role")

        if role_data.display_name and role_data.display_name != role.display_name:
            if await role_crud.check_display_name_exists_async(
                self.db, role_data.display_name, exclude_role_id=role_id
            ):
                raise DuplicateResourceError(
                    "角色", "display_name", role_data.display_name
                )

        update_data = role_data.model_dump(
            exclude_unset=True, exclude={"permission_ids"}
        )
        if update_data:
            update_data["updated_at"] = datetime.now(UTC)
            update_data["updated_by"] = updated_by
            role = await role_crud.update(self.db, db_obj=role, obj_in=update_data)

        if role_data.permission_ids is not None:
            await self.update_role_permissions(
                role_id=str(role.id),
                permission_ids=role_data.permission_ids,
                updated_by=updated_by,
                party_filter=resolved_party_filter,
                current_user_id=current_user_id,
            )

        return role

    async def delete_role(
        self,
        role_id: str,
        deleted_by: str,
        party_filter: PartyFilter | None = None,
        current_user_id: str | None = None,
    ) -> bool:
        """删除角色"""
        resolved_party_filter = await self._resolve_party_filter(
            current_user_id=current_user_id,
            party_filter=party_filter,
        )
        role = await role_crud.get(
            self.db,
            id=role_id,
            party_filter=resolved_party_filter,
        )
        if not role:
            return False

        if role.is_system_role:
            raise OperationNotAllowedError("系统角色不能删除", reason="system_role")

        role_name = role.name
        user_count = await user_role_assignment_crud.count_by_role(
            self.db, role_id=role_id
        )

        if user_count > 0:
            raise OperationNotAllowedError(
                f"角色正在被 {user_count} 个用户使用，无法删除",
                reason="role_in_use",
            )

        try:
            await role_crud.remove(self.db, id=role_id)
        except Exception as exc:  # pragma: no cover
            raise InternalServerError("删除角色失败", original_error=exc) from exc

        await self._invalidate_permission_cache_for_role(role_id)

        await self._create_permission_audit_log(
            action="role_delete",
            resource_type="role",
            resource_id=role_id,
            operator_id=deleted_by,
            old_permissions={"role_name": role_name},
            reason="角色删除",
        )

        return True

    async def update_role_permissions(
        self,
        *,
        role_id: str,
        permission_ids: list[str],
        updated_by: str,
        party_filter: PartyFilter | None = None,
        current_user_id: str | None = None,
    ) -> None:
        """更新角色权限"""
        resolved_party_filter = await self._resolve_party_filter(
            current_user_id=current_user_id,
            party_filter=party_filter,
        )
        role = await role_crud.get(
            self.db,
            id=role_id,
            party_filter=resolved_party_filter,
        )
        if not role:
            raise ResourceNotFoundError("角色", role_id)
        if role.is_system_role:
            raise OperationNotAllowedError("系统角色权限无法修改", reason="system_role")

        await self._assign_permissions_to_role(role_id, permission_ids, updated_by)
        await self.db.commit()
        await self._invalidate_permission_cache_for_role(role_id)

    async def get_role(
        self,
        role_id: str,
        party_filter: PartyFilter | None = None,
        current_user_id: str | None = None,
    ) -> Role | None:
        """获取角色详情"""
        resolved_party_filter = await self._resolve_party_filter(
            current_user_id=current_user_id,
            party_filter=party_filter,
        )
        return await role_crud.get(
            self.db,
            id=role_id,
            party_filter=resolved_party_filter,
        )

    async def get_roles(
        self,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
        category: str | None = None,
        is_active: bool | None = None,
        party_id: str | None = None,
        organization_id: str | None = None,  # DEPRECATED alias
        party_filter: PartyFilter | None = None,
        current_user_id: str | None = None,
    ) -> tuple[list[Role], int]:
        """获取角色列表"""
        resolved_party_filter = await self._resolve_party_filter(
            current_user_id=current_user_id,
            party_filter=party_filter,
        )
        return await role_crud.get_multi_with_filters(
            db=self.db,
            skip=skip,
            limit=limit,
            search=search,
            category=category,
            is_active=is_active,
            party_id=party_id,
            organization_id=organization_id,  # DEPRECATED alias
            party_filter=resolved_party_filter,
        )

    async def get_role_users(
        self,
        role_id: str,
        *,
        skip: int = 0,
        limit: int = 100,
        party_filter: PartyFilter | None = None,
        current_user_id: str | None = None,
    ) -> tuple[list[Any], int]:
        role = await self.get_role(
            role_id,
            party_filter=party_filter,
            current_user_id=current_user_id,
        )
        if not role:
            raise ResourceNotFoundError("角色", role_id)
        return await self.user_crud.get_users_by_role(self.db, role_id, skip, limit)

    async def get_role_statistics(self) -> dict[str, Any]:
        by_category = await role_crud.count_by_category(self.db)
        counts = await role_crud.count_by_flags(self.db)
        return {
            "total_roles": counts["total"],
            "active_roles": counts["active"],
            "system_roles": counts["system"],
            "custom_roles": counts["custom"],
            "by_category": by_category,
        }

    async def get_all_permissions_grouped(
        self, *, limit: int = 10000
    ) -> tuple[dict[str, list[Permission]], int]:
        permissions = await permission_crud.get_multi(self.db, skip=0, limit=limit)
        grouped: dict[str, list[Permission]] = {}
        for permission in permissions:
            resource = str(permission.resource)
            if resource not in grouped:
                grouped[resource] = []
            grouped[resource].append(permission)
        return grouped, len(permissions)
