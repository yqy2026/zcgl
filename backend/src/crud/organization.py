from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..crud.asset import SensitiveDataHandler
from ..crud.base import CRUDBase
from ..models.organization import Organization
from ..schemas.organization import OrganizationCreate, OrganizationUpdate


class CRUDOrganization(CRUDBase[Organization, OrganizationCreate, OrganizationUpdate]):
    """组织架构CRUD操作 - 支持敏感字段加密"""

    def __init__(self, model: type[Organization]) -> None:
        super().__init__(model)
        # 组织模块已移除联系人/负责人字段，当前无PII字段需要加密
        self.sensitive_data_handler = SensitiveDataHandler(searchable_fields=set())

    async def create_async(
        self,
        db: AsyncSession,
        *,
        obj_in: OrganizationCreate | dict[str, Any],
        **kwargs: Any,
    ) -> Organization:
        if isinstance(obj_in, dict):
            obj_in_data = obj_in
        else:
            obj_in_data = obj_in.model_dump()
        encrypted_data = self.sensitive_data_handler.encrypt_data(obj_in_data)
        return await super().create(db=db, obj_in=encrypted_data, **kwargs)

    async def get_async(
        self, db: AsyncSession, id: Any, use_cache: bool = True
    ) -> Organization | None:
        result = await super().get(db=db, id=id, use_cache=use_cache)
        if result is not None:
            self.sensitive_data_handler.decrypt_data(result.__dict__)
        return result

    async def update_async(
        self,
        db: AsyncSession,
        *,
        db_obj: Organization,
        obj_in: OrganizationUpdate | dict[str, Any],
        commit: bool = True,
    ) -> Organization:
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)
        encrypted_data = self._encrypt_update_data(update_data)
        return await super().update(
            db=db, db_obj=db_obj, obj_in=encrypted_data, commit=commit
        )

    def _encrypt_update_data(self, update_data: dict[str, Any]) -> dict[str, Any]:
        """加密更新数据中的敏感字段"""
        encrypted_data = {}
        for field_name, value in update_data.items():
            if field_name in self.sensitive_data_handler.ALL_PII_FIELDS:
                encrypted_data[field_name] = self.sensitive_data_handler.encrypt_field(
                    field_name, value
                )
            else:
                encrypted_data[field_name] = value
        return encrypted_data

    async def get_multi_with_filters_async(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        parent_id: str | None = None,
        keyword: str | None = None,
    ) -> list[Organization]:
        stmt = select(Organization).where(Organization.is_deleted.is_(False))

        if parent_id:
            stmt = stmt.where(Organization.parent_id == parent_id)

        if keyword:
            stmt = stmt.where(
                or_(
                    Organization.name.ilike(f"%{keyword}%"),
                    Organization.description.ilike(f"%{keyword}%"),
                )
            )

        stmt = stmt.order_by(Organization.level.asc(), Organization.sort_order.asc())
        stmt = stmt.offset(skip).limit(limit)
        result = list((await db.execute(stmt)).scalars().all())

        for item in result:
            self.sensitive_data_handler.decrypt_data(item.__dict__)

        return result

    async def get_multi_with_count_async(
        self,
        db: AsyncSession,
        *,
        filters: dict[str, Any] | None = None,
        search: str | None = None,
        search_fields: list[str] | None = None,
        search_conditions: list[Any] | None = None,
        skip: int = 0,
        limit: int = 100,
        order_by: str | None = None,
        order_desc: bool = True,
        parent_id: str | None = None,
        keyword: str | None = None,
    ) -> tuple[list[Organization], int]:
        if filters:
            parent_id = parent_id or filters.get("parent_id")
            keyword = keyword or filters.get("keyword")
        if search:
            keyword = keyword or search

        conditions: list[Any] = [Organization.is_deleted.is_(False)]
        if parent_id:
            conditions.append(Organization.parent_id == parent_id)
        if keyword:
            conditions.append(
                or_(
                    Organization.name.ilike(f"%{keyword}%"),
                    Organization.description.ilike(f"%{keyword}%"),
                )
            )

        total_stmt = select(func.count(Organization.id)).where(*conditions)
        total = int((await db.execute(total_stmt)).scalar() or 0)

        stmt = select(Organization).where(*conditions)
        if order_by and hasattr(Organization, order_by):
            order_column = getattr(Organization, order_by)
            stmt = stmt.order_by(
                order_column.desc() if order_desc else order_column.asc()
            )
        else:
            stmt = stmt.order_by(
                Organization.level.asc(), Organization.sort_order.asc()
            )

        stmt = stmt.offset(skip).limit(limit)
        items = list((await db.execute(stmt)).scalars().all())

        for item in items:
            self.sensitive_data_handler.decrypt_data(item.__dict__)

        return items, total

    async def get_tree_async(
        self, db: AsyncSession, parent_id: str | None = None
    ) -> list[Organization]:
        stmt = select(Organization).where(
            and_(
                Organization.is_deleted.is_(False),
                Organization.parent_id == parent_id,
            )
        )
        result = list(
            (
                await db.execute(
                    stmt.order_by(Organization.sort_order, Organization.name)
                )
            )
            .scalars()
            .all()
        )

        for item in result:
            self.sensitive_data_handler.decrypt_data(item.__dict__)

        return result

    async def get_children_async(
        self, db: AsyncSession, parent_id: str, recursive: bool = False
    ) -> list[Organization]:
        if not recursive:
            stmt = select(Organization).where(
                and_(
                    Organization.parent_id == parent_id,
                    Organization.is_deleted.is_(False),
                )
            )
            result = list(
                (
                    await db.execute(
                        stmt.order_by(Organization.sort_order, Organization.name)
                    )
                )
                .scalars()
                .all()
            )
        else:
            recursive_result: list[Organization] = []
            direct_children = await self.get_children_async(db, parent_id, False)
            for child in direct_children:
                recursive_result.append(child)
                child_id = str(getattr(child, "id", ""))
                if child_id:
                    recursive_result.extend(
                        await self.get_children_async(db, child_id, True)
                    )
            result = recursive_result

        for item in result:
            self.sensitive_data_handler.decrypt_data(item.__dict__)

        return result

    async def get_path_to_root_async(
        self, db: AsyncSession, org_id: str
    ) -> list[Organization]:
        path: list[Organization] = []
        current: Organization | None = await self.get_async(db, id=org_id)

        while current:
            path.insert(0, current)
            if current.parent_id:
                current = await self.get_async(db, id=current.parent_id)
            else:
                break

        return path

    async def search_async(
        self, db: AsyncSession, keyword: str, skip: int = 0, limit: int = 100
    ) -> list[Organization]:
        return await self.get_multi_with_filters_async(
            db, skip=skip, limit=limit, keyword=keyword
        )


# 创建CRUD实例
organization = CRUDOrganization(Organization)
