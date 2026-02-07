from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.system_dictionary import AssetCustomField
from ..schemas.asset import AssetCustomFieldCreate, AssetCustomFieldUpdate
from .base import CRUDBase


class CRUDCustomField(
    CRUDBase[AssetCustomField, AssetCustomFieldCreate, AssetCustomFieldUpdate]
):
    """自定义字段CRUD操作类"""

    async def get_by_field_name_async(
        self, db: AsyncSession, *, field_name: str
    ) -> AssetCustomField | None:
        result = await db.execute(
            select(AssetCustomField).filter(AssetCustomField.field_name == field_name)
        )
        return result.scalars().first()

    async def get_multi_by_ids_async(
        self, db: AsyncSession, ids: list[str]
    ) -> list[AssetCustomField]:
        if len(ids) == 0:
            return []
        result = await db.execute(
            select(AssetCustomField).where(AssetCustomField.id.in_(ids))
        )
        return list(result.scalars().all())

    async def get_multi_by_field_names_async(
        self, db: AsyncSession, field_names: list[str]
    ) -> list[AssetCustomField]:
        if len(field_names) == 0:
            return []
        result = await db.execute(
            select(AssetCustomField).where(AssetCustomField.field_name.in_(field_names))
        )
        return list(result.scalars().all())

    async def get_multi_with_filters_async(
        self,
        db: AsyncSession,
        *,
        filters: dict[str, Any] | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[AssetCustomField]:
        if filters is None:
            filters = {}

        base_query = select(self.model)

        qb_filters: dict[str, Any] = {}
        if filters:
            if "field_type" in filters:
                qb_filters["field_type"] = filters["field_type"]
            if "is_required" in filters:
                qb_filters["is_required"] = filters["is_required"]
            if "is_active" in filters:
                qb_filters["is_active"] = filters["is_active"]

        query = self.query_builder.build_query(
            filters=qb_filters,
            base_query=base_query,
            sort_by="sort_order",
            sort_desc=False,
            skip=skip,
            limit=limit,
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_active_fields_async(
        self, db: AsyncSession
    ) -> list[AssetCustomField]:
        base_query = select(self.model)

        query = self.query_builder.build_query(
            filters={"is_active": True},
            base_query=base_query,
            sort_by="sort_order",
            sort_desc=False,
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_asset_field_values_async(
        self, db: AsyncSession, *, asset_id: str
    ) -> list[dict[str, Any]]:
        return []
    # Removed: validate_field_value (moved to Service)
    # Removed: update_asset_field_values (moved to Service)
    # Removed: toggle_active_status (moved to Service)
    # Removed: update_sort_orders (moved to Service)


# 创建自定义字段CRUD实例
custom_field_crud: CRUDCustomField = CRUDCustomField(AssetCustomField)
