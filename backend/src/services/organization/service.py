from datetime import datetime
from typing import Any

from sqlalchemy import and_, func, literal, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception_handler import OperationNotAllowedError, ResourceNotFoundError
from ...crud.organization import organization as organization_crud
from ...crud.organization_history import OrganizationHistoryCRUD
from ...models.organization import Organization, OrganizationHistory
from ...schemas.organization import OrganizationCreate, OrganizationUpdate
from ..enum_validation_service import get_enum_validation_service_async


class OrganizationService:
    """组织架构服务层"""

    ORGANIZATION_TYPE_ENUM = "organization_type"
    ORGANIZATION_STATUS_ENUM = "organization_status"

    async def get_organizations(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100
    ) -> tuple[list[Organization], int]:
        return await organization_crud.get_multi_with_count_async(
            db,
            skip=skip,
            limit=limit,
        )

    async def search_organizations(
        self,
        db: AsyncSession,
        *,
        keyword: str,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[Organization], int]:
        return await organization_crud.get_multi_with_count_async(
            db,
            keyword=keyword,
            skip=skip,
            limit=limit,
        )

    async def get_organization(
        self, db: AsyncSession, *, org_id: str
    ) -> Organization | None:
        return await organization_crud.get_async(db, id=org_id)

    async def get_organization_tree(
        self, db: AsyncSession, *, parent_id: str | None = None
    ) -> list[Organization]:
        return await organization_crud.get_tree_async(db, parent_id=parent_id)

    async def get_organization_children(
        self,
        db: AsyncSession,
        *,
        org_id: str,
        recursive: bool = False,
    ) -> list[Organization]:
        return await organization_crud.get_children_async(
            db,
            parent_id=org_id,
            recursive=recursive,
        )

    async def get_organization_path(
        self,
        db: AsyncSession,
        *,
        org_id: str,
    ) -> list[Organization]:
        return await organization_crud.get_path_to_root_async(db, org_id=org_id)

    async def advanced_search_organizations(
        self,
        db: AsyncSession,
        *,
        keyword: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Organization]:
        if keyword:
            normalized = keyword.strip()
            if normalized:
                return await organization_crud.search_async(
                    db,
                    keyword=normalized,
                    skip=skip,
                    limit=limit,
                )

        return await organization_crud.get_multi_with_filters_async(
            db,
            skip=skip,
            limit=limit,
        )

    async def create_organization(
        self, db: AsyncSession, *, obj_in: OrganizationCreate
    ) -> Organization:
        await self._validate_enum_fields(
            db,
            type_value=obj_in.type,
            status_value=obj_in.status,
        )

        level = 1
        parent = None

        if obj_in.parent_id:
            parent = await organization_crud.get_async(db, obj_in.parent_id)
            if not parent:
                raise ResourceNotFoundError("组织", obj_in.parent_id)
            parent_level: int = getattr(parent, "level") or 0
            level = parent_level + 1

        db_obj = Organization(**obj_in.model_dump())
        object.__setattr__(db_obj, "level", level)
        object.__setattr__(db_obj, "path", "/")

        db.add(db_obj)
        await db.flush()

        if parent:
            object.__setattr__(
                db_obj,
                "path",
                f"{parent.path}/{db_obj.id}"
                if parent.path
                else f"/{parent.id}/{db_obj.id}",
            )
        else:
            object.__setattr__(db_obj, "path", f"/{db_obj.id}")

        await db.commit()
        await db.refresh(db_obj)

        org_id_value: str = getattr(db_obj, "id")
        await self._create_history(db, org_id_value, "create", created_by=obj_in.created_by)

        return db_obj

    async def update_organization(
        self, db: AsyncSession, *, org_id: str, obj_in: OrganizationUpdate
    ) -> Organization:
        db_obj: Organization | None = await organization_crud.get_async(db, org_id)
        if not db_obj:
            raise ResourceNotFoundError("组织", org_id)

        old_values = {}
        update_data = obj_in.model_dump(exclude_unset=True)

        if "type" in update_data and update_data["type"] is None:
            raise ValueError("组织类型不能为空")
        if "status" in update_data and update_data["status"] is None:
            raise ValueError("组织状态不能为空")

        await self._validate_enum_fields(
            db,
            type_value=update_data.get("type"),
            status_value=update_data.get("status"),
        )

        for field, new_value in update_data.items():
            if field == "updated_by":
                continue
            old_value = getattr(db_obj, field)
            if old_value != new_value:
                old_values[field] = {"old": str(old_value), "new": str(new_value)}

        if "parent_id" in update_data:
            new_parent_id = update_data["parent_id"]
            if new_parent_id != db_obj.parent_id:
                if new_parent_id:
                    if await self._would_create_cycle(db, org_id, new_parent_id):
                        raise OperationNotAllowedError(
                            "不能将组织移动到其子组织下",
                            reason="organization_cycle",
                        )

                    parent = await organization_crud.get_async(db, new_parent_id)
                    if parent:
                        object.__setattr__(db_obj, "level", (parent.level or 0) + 1)
                        object.__setattr__(
                            db_obj,
                            "path",
                            f"{parent.path}/{db_obj.id}"
                            if parent.path
                            else f"/{parent.id}/{db_obj.id}",
                        )
                    else:
                        raise ResourceNotFoundError("组织", new_parent_id)
                else:
                    object.__setattr__(db_obj, "level", 1)
                    object.__setattr__(db_obj, "path", f"/{db_obj.id}")

                await self._update_children_path(db, db_obj)

        for field, value in update_data.items():
            if field != "updated_by":
                setattr(db_obj, field, value)

        setattr(db_obj, "updated_at", datetime.now())
        await db.commit()
        await db.refresh(db_obj)

        for field, values in old_values.items():
            org_id_value: str = getattr(db_obj, "id")
            await self._create_history(
                db,
                org_id_value,
                "update",
                field,
                values["old"],
                values["new"],
                created_by=obj_in.updated_by,
            )

        return db_obj

    async def delete_organization(
        self, db: AsyncSession, *, org_id: str, deleted_by: str | None = None
    ) -> bool:
        db_obj = await organization_crud.get_async(db, org_id)
        if not db_obj:
            return False

        children = await organization_crud.get_children_async(db, org_id)
        if children:
            raise OperationNotAllowedError(
                "不能删除有子组织的组织，请先删除或移动子组织",
                reason="organization_has_children",
            )

        setattr(db_obj, "is_deleted", True)
        setattr(db_obj, "updated_at", datetime.now())
        await db.commit()

        await self._create_history(db, org_id, "delete", created_by=deleted_by)

        return True

    async def get_statistics(self, db: AsyncSession) -> dict[str, Any]:
        base_condition = Organization.is_deleted.is_(False)

        status_rows = (
            await db.execute(
                select(Organization.status, func.count(Organization.id))
                .where(base_condition)
                .group_by(Organization.status)
            )
        ).all()
        type_rows = (
            await db.execute(
                select(Organization.type, func.count(Organization.id))
                .where(base_condition)
                .group_by(Organization.type)
            )
        ).all()
        level_rows = (
            await db.execute(
                select(Organization.level, func.count(Organization.id))
                .where(base_condition)
                .group_by(Organization.level)
            )
        ).all()

        total = sum(int(count or 0) for _, count in status_rows)
        if total == 0:
            total = sum(int(count or 0) for _, count in level_rows)

        active = sum(
            int(count or 0) for status, count in status_rows if str(status) == "active"
        )
        inactive = max(total - active, 0)

        type_stats = {
            str(org_type): int(count or 0)
            for org_type, count in type_rows
            if org_type is not None
        }
        level_stats = {
            f"level_{int(level)}": int(count or 0)
            for level, count in level_rows
            if level is not None
        }

        return {
            "total": total,
            "active": active,
            "inactive": inactive,
            "by_type": type_stats,
            "by_level": level_stats,
        }

    async def get_history(
        self, db: AsyncSession, org_id: str, skip: int = 0, limit: int = 100
    ) -> list[OrganizationHistory]:
        """获取组织变更历史"""
        history_crud = OrganizationHistoryCRUD()
        return await history_crud.get_multi_async(
            db=db, org_id=org_id, skip=skip, limit=limit
        )

    async def get_history_with_count(
        self, db: AsyncSession, org_id: str, skip: int = 0, limit: int = 100
    ) -> tuple[list[OrganizationHistory], int]:
        history_crud = OrganizationHistoryCRUD()
        return await history_crud.get_multi_with_count_async(
            db=db, org_id=org_id, skip=skip, limit=limit
        )

    async def _would_create_cycle(
        self, db: AsyncSession, org_id: str, new_parent_id: str
    ) -> bool:
        if not new_parent_id:
            return False

        base = (
            select(Organization.id, Organization.parent_id)
            .where(Organization.id == new_parent_id)
            .cte(name="org_ancestors", recursive=True)
        )
        recursive = select(Organization.id, Organization.parent_id).where(
            Organization.id == base.c.parent_id
        )
        ancestors = base.union(recursive)

        stmt = select(ancestors.c.id).where(ancestors.c.id == org_id).limit(1)
        result = await db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def _update_children_path(
        self, db: AsyncSession, parent_org: Organization
    ) -> None:
        parent_org_id: str | None = getattr(parent_org, "id", None)
        if not parent_org_id:
            return

        parent_level: int = getattr(parent_org, "level") or 1
        parent_path: str | None = getattr(parent_org, "path")
        base_path = parent_path if parent_path else f"/{parent_org_id}"
        parent_parent_id: str | None = getattr(parent_org, "parent_id", None)

        base = (
            select(
                literal(parent_org_id, type_=Organization.id.type).label("id"),
                literal(
                    parent_parent_id, type_=Organization.parent_id.type
                ).label("parent_id"),
                literal(base_path, type_=Organization.path.type).label("path"),
                literal(parent_level, type_=Organization.level.type).label("level"),
            )
            .cte(name="org_tree", recursive=True)
        )
        recursive = select(
            Organization.id,
            Organization.parent_id,
            func.concat(base.c.path, "/", Organization.id).label("path"),
            (base.c.level + 1).label("level"),
        ).where(
            and_(
                Organization.parent_id == base.c.id,
                Organization.is_deleted.is_(False),
            )
        )
        org_tree = base.union_all(recursive)

        stmt = (
            update(Organization)
            .where(Organization.id == org_tree.c.id)
            .values(
                path=org_tree.c.path,
                level=org_tree.c.level,
                updated_at=datetime.now(),
            )
            .execution_options(synchronize_session=False)
        )
        await db.execute(stmt)

    async def _create_history(
        self,
        db: AsyncSession,
        org_id: str,
        action: str,
        field_name: str | None = None,
        old_value: str | None = None,
        new_value: str | None = None,
        created_by: str | None = None,
    ) -> None:
        history = OrganizationHistory(
            organization_id=org_id,
            action=action,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            created_by=created_by,
        )
        db.add(history)
        await db.commit()

    async def _validate_enum_fields(
        self,
        db: AsyncSession,
        *,
        type_value: str | None,
        status_value: str | None,
    ) -> None:
        enum_validation_service = get_enum_validation_service_async(db)

        if type_value is not None:
            is_valid, error = await enum_validation_service.validate_value(
                self.ORGANIZATION_TYPE_ENUM,
                type_value,
                allow_empty=False,
                context={"module": "organization", "field": "type"},
            )
            if not is_valid:
                raise ValueError(f"组织类型无效: {error}")

        if status_value is not None:
            is_valid, error = await enum_validation_service.validate_value(
                self.ORGANIZATION_STATUS_ENUM,
                status_value,
                allow_empty=False,
                context={"module": "organization", "field": "status"},
            )
            if not is_valid:
                raise ValueError(f"组织状态无效: {error}")


organization_service = OrganizationService()
