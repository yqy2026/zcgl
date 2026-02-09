import inspect
from typing import Any


class AssetNotFoundError(Exception):
    """Asset not found error"""

    pass


class DuplicateAssetError(Exception):
    """Duplicate asset error"""

    pass


"""
RBAC服务层
"""

from datetime import UTC, datetime

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.exception_handler import (
    DuplicateResourceError,
    InternalServerError,
    InvalidRequestError,
    OperationNotAllowedError,
    ResourceConflictError,
    ResourceNotFoundError,
)
from ...crud.auth import UserCRUD
from ...crud.rbac import (
    permission_audit_log_crud,
    permission_crud,
    permission_grant_crud,
    role_crud,
    user_role_assignment_crud,
)
from ...models.rbac import (
    Permission,
    PermissionGrant,
    ResourcePermission,
    Role,
    UserRoleAssignment,
    role_permissions,
)
from ...schemas.rbac import (
    PermissionCheckRequest,
    PermissionCheckResponse,
    PermissionCreate,
    PermissionGrantUpdate,
    PermissionResponse,
    ResourcePermissionResponse,
    RoleCreate,
    RoleResponse,
    RoleUpdate,
    UserPermissionSummary,
    UserRoleAssignmentCreate,
)

# Global admin permission used for full access
ADMIN_PERMISSION_RESOURCE = "system"
ADMIN_PERMISSION_ACTION = "admin"
VALID_GRANT_EFFECTS = {"allow", "deny"}


class RBACService:
    """RBAC服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_crud = UserCRUD()

    # ==================== 角色管理 ====================

    async def create_role(self, role_data: RoleCreate, created_by: str) -> Role:
        """创建角色"""
        existing_role = await role_crud.get_by_name(self.db, name=role_data.name)
        if existing_role:
            raise DuplicateResourceError("角色", "name", role_data.name)

        role = await role_crud.create(
            self.db, obj_in=role_data, created_by=created_by
        )

        # 添加权限
        if role_data.permission_ids:
            await self.update_role_permissions(
                role_id=str(role.id),
                permission_ids=role_data.permission_ids,
                updated_by=created_by,
            )

        return role

    async def update_role(
        self, role_id: str, role_data: RoleUpdate, updated_by: str
    ) -> Role:
        """更新角色"""
        role = await role_crud.get(self.db, id=role_id)
        if not role:
            raise ResourceNotFoundError("角色", role_id)

        if role.is_system_role:
            raise OperationNotAllowedError("系统角色不能修改", reason="system_role")

        # 检查名称唯一性
        if role_data.display_name and role_data.display_name != role.display_name:
            existing_role = (
                (
                    await self.db.execute(
                        select(Role).where(
                            and_(
                                Role.display_name == role_data.display_name,
                                Role.id != role_id,
                            )
                        )
                    )
                )
                .scalars()
                .first()
            )
            if existing_role:
                raise DuplicateResourceError("角色", "display_name", role_data.display_name)

        # 更新字段
        update_data = role_data.model_dump(
            exclude_unset=True, exclude={"permission_ids"}
        )
        if update_data:
            update_data["updated_at"] = datetime.now(UTC)
            update_data["updated_by"] = updated_by
            role = await role_crud.update(self.db, db_obj=role, obj_in=update_data)

        # 更新权限
        if role_data.permission_ids is not None:
            await self.update_role_permissions(
                role_id=str(role.id),
                permission_ids=role_data.permission_ids,
                updated_by=updated_by,
            )

        return role

    async def delete_role(self, role_id: str, deleted_by: str) -> bool:
        """删除角色"""
        role = await role_crud.get(self.db, id=role_id)
        if not role:
            return False

        if role.is_system_role:
            raise OperationNotAllowedError("系统角色不能删除", reason="system_role")

        # 保存角色名称用于审计日志（在删除之前）
        role_name = role.name

        # 检查是否有用户使用此角色
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
        except Exception as exc:  # pragma: no cover - defensive for DB layer errors
            raise InternalServerError("删除角色失败", original_error=exc) from exc

        # 记录审计日志（使用保存的role_name，因为role已被删除）
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
    ) -> None:
        """更新角色权限"""
        role = await role_crud.get(self.db, id=role_id)
        if not role:
            raise ResourceNotFoundError("角色", role_id)
        if role.is_system_role:
            raise OperationNotAllowedError("系统角色权限无法修改", reason="system_role")

        await self._assign_permissions_to_role(role_id, permission_ids, updated_by)
        await self.db.commit()

    async def get_role(self, role_id: str) -> Role | None:
        """获取角色详情"""
        return await role_crud.get(self.db, id=role_id)

    async def get_roles(
        self,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
        category: str | None = None,
        is_active: bool | None = None,
        organization_id: str | None = None,
    ) -> tuple[list[Role], int]:
        """获取角色列表"""
        return await role_crud.get_multi_with_filters(
            db=self.db,
            skip=skip,
            limit=limit,
            search=search,
            category=category,
            is_active=is_active,
            organization_id=organization_id,
        )

    async def get_role_users(
        self,
        role_id: str,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[Any], int]:
        role = await self.get_role(role_id)
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
        """获取权限列表"""
        filters: dict[str, Any] = {}
        if resource:
            filters["resource"] = resource
        if action:
            filters["action"] = action
        if is_system_permission is not None:
            filters["is_system_permission"] = is_system_permission

        stmt = permission_crud.query_builder.build_query(
            filters=filters,
            search_query=search,
            search_fields=["name", "display_name", "description"],
            sort_by="resource",
            sort_desc=False,
            skip=skip,
            limit=limit,
        )
        permissions = list((await self.db.execute(stmt)).scalars().all())

        count_stmt = permission_crud.query_builder.build_count_query(
            filters=filters,
            search_query=search,
            search_fields=["name", "display_name", "description"],
        )
        total = int((await self.db.execute(count_stmt)).scalar() or 0)

        return permissions, total

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
        stmt = (
            select(Role)
            .join(UserRoleAssignment)
            .where(UserRoleAssignment.user_id == user_id)
            .options(selectinload(Role.permissions))
        )

        if active_only:
            now_naive = datetime.now(UTC).replace(tzinfo=None)
            stmt = stmt.where(UserRoleAssignment.is_active)
            stmt = stmt.where(
                or_(
                    UserRoleAssignment.expires_at.is_(None),
                    UserRoleAssignment.expires_at > now_naive,
                )
            )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ==================== 权限检查 ====================

    async def check_permission(
        self, user_id: str, permission_request: PermissionCheckRequest
    ) -> PermissionCheckResponse:
        """检查用户权限"""
        user = await self.user_crud.get_async(self.db, user_id)
        if not user or not user.is_active:
            return PermissionCheckResponse(
                has_permission=False, reason="用户不存在或已禁用", conditions=None
            )

        static_result = await self._check_static_permission(user_id, permission_request)
        if static_result.has_permission:
            return static_result

        grant_result = await self._check_grant_permission(user_id, permission_request)
        if grant_result.has_permission:
            return grant_result

        if grant_result.reason == "命中拒绝授权":
            deny_reason = grant_result.reason
        else:
            deny_reason = static_result.reason or grant_result.reason or "权限不足"
        return PermissionCheckResponse(
            has_permission=False,
            granted_by=[],
            conditions=None,
            reason=deny_reason,
        )

    async def is_admin(self, user_id: str) -> bool:
        """判断用户是否为管理员（基于RBAC权限）"""
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
        is_admin = await self._user_has_admin_permission(user_id, roles_sorted)
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
        user = await self.user_crud.get_async(self.db, user_id)
        if not user:
            raise ResourceNotFoundError("用户", user_id)

        # 获取用户角色
        roles = await self.get_user_roles(user_id)

        # 获取角色权限
        role_permissions = set()
        for role in roles:
            for permission in role.permissions:
                role_permissions.add(permission)

        # 获取统一授权权限（动态/临时/资源级授权合并）
        now = datetime.now()
        grant_stmt = (
            select(Permission)
            .join(PermissionGrant, PermissionGrant.permission_id == Permission.id)
            .where(
                and_(
                    PermissionGrant.user_id == user_id,
                    PermissionGrant.is_active,
                    PermissionGrant.effect == "allow",
                    or_(PermissionGrant.starts_at.is_(None), PermissionGrant.starts_at <= now),
                    or_(PermissionGrant.expires_at.is_(None), PermissionGrant.expires_at > now),
                )
            )
        )
        granted_permissions = list((await self.db.execute(grant_stmt)).scalars().all())
        for permission in granted_permissions:
            role_permissions.add(permission)

        # 获取资源权限
        resource_permissions_stmt = select(ResourcePermission).where(
            and_(
                ResourcePermission.user_id == user_id,
                ResourcePermission.is_active,
                or_(
                    ResourcePermission.expires_at.is_(None),
                    ResourcePermission.expires_at > datetime.now(),
                ),
            )
        )
        resource_permissions = list(
            (await self.db.execute(resource_permissions_stmt)).scalars().all()
        )

        # 计算有效权限
        effective_permissions = self._calculate_effective_permissions(
            roles, resource_permissions, granted_permissions
        )

        roles_response = [RoleResponse.model_validate(role) for role in roles]
        permissions_response = [
            PermissionResponse.model_validate(permission)
            for permission in role_permissions
        ]
        resource_permissions_response = [
            ResourcePermissionResponse.model_validate(resource_permission)
            for resource_permission in resource_permissions
        ]

        return UserPermissionSummary(
            user_id=user_id,
            username=user.username,
            roles=roles_response,
            permissions=permissions_response,
            resource_permissions=resource_permissions_response,
            effective_permissions=effective_permissions,
        )

    # ==================== 私有方法 ====================

    async def _assign_permissions_to_role(
        self, role_id: str, permission_ids: list[str], operator_id: str
    ) -> None:
        """为角色分配权限"""
        stmt = (
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.id == role_id)
        )
        role = (await self.db.execute(stmt)).scalars().first()
        if not role:
            raise ResourceNotFoundError("角色", role_id)
        if role.is_system_role:
            raise OperationNotAllowedError(
                "系统角色权限无法修改", reason="system_role"
            )

        permissions: list[Permission] = []
        if permission_ids:
            stmt = select(Permission).where(Permission.id.in_(permission_ids))
            permissions = list((await self.db.execute(stmt)).scalars().all())
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
        await self.db.execute(
            role_permissions.update()
            .where(role_permissions.c.role_id == role_id)
            .values(created_by=operator_id)
        )

    async def _check_static_permission(
        self, user_id: str, permission_request: PermissionCheckRequest
    ) -> PermissionCheckResponse:
        """检查静态RBAC权限（角色+系统管理员权限）"""
        user_roles = await self.get_user_roles(user_id)
        if await self._user_has_admin_permission(user_id, user_roles):
            return PermissionCheckResponse(
                has_permission=True,
                granted_by=["system_admin_permission"],
                conditions=None,
                reason=None,
            )
        if not user_roles:
            return PermissionCheckResponse(
                has_permission=False, granted_by=[], conditions=None, reason="用户未分配任何角色"
            )

        granted_by: list[str] = []
        conditions: dict[str, Any] | None = None
        for role in user_roles:
            if not self._role_has_permission(role, permission_request):
                continue
            granted_by.append(f"role_{role.name}")
            role_conditions = self._get_role_permission_conditions(
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

        return PermissionCheckResponse(
            has_permission=False,
            granted_by=[],
            conditions=None,
            reason="静态角色权限未命中",
        )

    async def _check_grant_permission(
        self, user_id: str, permission_request: PermissionCheckRequest
    ) -> PermissionCheckResponse:
        """检查统一授权记录权限（动态/临时/资源级）"""
        grants = await self._get_matching_permission_grants(user_id, permission_request)
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
            if self._scope_matches(grant, permission_request)
            and self._conditions_match(grant, permission_request)
        ]
        if not valid_grants:
            return PermissionCheckResponse(
                has_permission=False,
                granted_by=[],
                conditions=None,
                reason="统一授权条件不满足",
            )

        def _grant_sort_key(grant: PermissionGrant) -> tuple[int, float]:
            created_at = getattr(grant, "created_at", None)
            created_at_ts = (
                created_at.timestamp()
                if isinstance(created_at, datetime)
                else 0.0
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

    async def _get_matching_permission_grants(
        self, user_id: str, permission_request: PermissionCheckRequest
    ) -> list[PermissionGrant]:
        now = datetime.now()
        stmt = (
            select(PermissionGrant)
            .join(Permission, Permission.id == PermissionGrant.permission_id)
            .where(
                and_(
                    PermissionGrant.user_id == user_id,
                    PermissionGrant.is_active,
                    Permission.resource == permission_request.resource,
                    Permission.action == permission_request.action,
                    or_(PermissionGrant.starts_at.is_(None), PermissionGrant.starts_at <= now),
                    or_(PermissionGrant.expires_at.is_(None), PermissionGrant.expires_at > now),
                )
            )
        )
        result = await self.db.execute(stmt)
        scalars_result = result.scalars()
        if inspect.isawaitable(scalars_result):
            scalars_result = await scalars_result

        all_method = getattr(scalars_result, "all", None)
        if all_method is None:
            return []

        all_result = all_method()
        if inspect.isawaitable(all_result):
            all_result = await all_result
        if all_result is None:
            return []
        if isinstance(all_result, list):
            return all_result
        try:
            return list(all_result)
        except TypeError:
            return []

    def _scope_matches(
        self, grant: PermissionGrant, permission_request: PermissionCheckRequest
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
            "organization_id",
            "project_id",
            "asset_id",
        ]
        for key in context_scope_keys:
            context_value = request_context.get(key)
            if context_value is not None and str(context_value) == str(grant.scope_id):
                return True
        return False

    def _conditions_match(
        self, grant: PermissionGrant, permission_request: PermissionCheckRequest
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
    ) -> PermissionGrant:
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

    async def get_permission_grant(self, grant_id: str) -> PermissionGrant | None:
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
    ) -> tuple[list[PermissionGrant], int]:
        """分页查询统一授权记录"""
        filters = []

        if user_id:
            filters.append(PermissionGrant.user_id == user_id)
        if permission_id:
            filters.append(PermissionGrant.permission_id == permission_id)
        if grant_type:
            filters.append(PermissionGrant.grant_type == grant_type.strip().lower())
        if effect:
            filters.append(PermissionGrant.effect == effect.strip().lower())
        if scope:
            filters.append(PermissionGrant.scope == scope.strip().lower())
        if is_active is not None:
            filters.append(PermissionGrant.is_active == is_active)

        stmt = select(PermissionGrant).order_by(desc(PermissionGrant.created_at))
        count_stmt = select(func.count(PermissionGrant.id))

        if filters:
            stmt = stmt.where(and_(*filters))
            count_stmt = count_stmt.where(and_(*filters))

        stmt = stmt.offset(skip).limit(limit)
        grants = list((await self.db.execute(stmt)).scalars().all())
        total = int((await self.db.execute(count_stmt)).scalar() or 0)
        return grants, total

    async def update_permission_grant(
        self, grant_id: str, grant_data: PermissionGrantUpdate, updated_by: str
    ) -> PermissionGrant:
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

    def _role_has_admin_permission(self, role: Role) -> bool:
        """检查角色是否具有系统管理员权限"""
        for permission in role.permissions:
            if (
                permission.resource == ADMIN_PERMISSION_RESOURCE
                and permission.action == ADMIN_PERMISSION_ACTION
            ):
                return True

        return False

    async def _user_has_admin_permission(
        self, user_id: str, roles: list[Role]
    ) -> bool:
        """检查用户是否具备系统管理员权限（基于权限而非角色名）"""
        if any(self._role_has_admin_permission(role) for role in roles):
            return True

        admin_request = PermissionCheckRequest(
            resource=ADMIN_PERMISSION_RESOURCE,
            action=ADMIN_PERMISSION_ACTION,
            resource_id=None,
            context=None,
        )
        grant_result = await self._check_grant_permission(user_id, admin_request)
        return grant_result.has_permission

    def _role_has_permission(
        self, role: Role, permission_request: PermissionCheckRequest
    ) -> bool:
        """检查角色是否有权限"""
        for permission in role.permissions:
            if (
                permission.resource == permission_request.resource
                and permission.action == permission_request.action
            ):
                return True
        return False

    def _get_role_permission_conditions(
        self, role: Role, permission_request: PermissionCheckRequest
    ) -> dict[str, Any] | None:
        """获取角色权限条件"""
        for permission in role.permissions:
            if (
                permission.resource == permission_request.resource
                and permission.action == permission_request.action
            ):
                return permission.conditions if permission.conditions else None
        return None  # pragma: no cover  # Defensive: only reached if role_has_permission check is bypassed

    def _calculate_effective_permissions(
        self,
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

    def _can_manage_role(self, manager_level: int, subordinate_level: int) -> bool:
        """检查是否可以管理指定级别的角色"""
        return manager_level > subordinate_level

    # ==================== Permission Decorator Adapter Methods ====================
    # These methods provide the interface expected by permission decorators
    # They adapt the existing check_permission method to the decorator's expected signature

    async def check_user_permission(
        self, user_id: str, resource: str, action: str
    ) -> bool:
        """
        检查用户权限 - 适配器方法供装饰器使用

        Args:
            user_id: 用户ID
            resource: 资源名称 (如: 'asset', 'user', 'role')
            action: 操作类型 (如: 'view', 'create', 'edit', 'delete')

        Returns:
            bool: 是否有权限
        """
        if (
            resource == ADMIN_PERMISSION_RESOURCE
            and action == ADMIN_PERMISSION_ACTION
        ):
            return await self.is_admin(user_id)

        from ...schemas.rbac import PermissionCheckRequest

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
        """
        检查资源访问权限 - 适配器方法供装饰器使用

        Args:
            user_id: 用户ID
            resource: 资源名称
            resource_id: 资源ID
            action: 操作类型

        Returns:
            bool: 是否有访问权限
        """
        from ...schemas.rbac import PermissionCheckRequest

        permission_request = PermissionCheckRequest(
            resource=resource,
            action=action,
            resource_id=resource_id,
            context=None,
        )

        response = await self.check_permission(user_id, permission_request)
        return response.has_permission

    async def check_organization_access(
        self, user_id: str, organization_id: str
    ) -> bool:
        """
        检查组织访问权限 - 适配器方法供装饰器使用

        Args:
            user_id: 用户ID
            organization_id: 组织ID

        Returns:
            bool: 是否有组织访问权限
        """
        from ...schemas.rbac import PermissionCheckRequest

        permission_request = PermissionCheckRequest(
            resource="organization",
            action="view",
            resource_id=organization_id,
            context=None,
        )

        response = await self.check_permission(user_id, permission_request)
        return response.has_permission
