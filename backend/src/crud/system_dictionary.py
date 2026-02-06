from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.asset import SystemDictionary
from ..schemas.asset import SystemDictionaryCreate, SystemDictionaryUpdate
from .base import CRUDBase


class CRUDSystemDictionary(
    CRUDBase[SystemDictionary, SystemDictionaryCreate, SystemDictionaryUpdate]
):
    """系统字典CRUD操作类"""

    def __init__(self) -> None:
        super().__init__(SystemDictionary)

    def _build_filters(
        self,
        *,
        dict_type: str | None = None,
        is_active: bool | None = None,
    ) -> dict[str, Any]:
        qb_filters: dict[str, Any] = {}
        if dict_type is not None:
            qb_filters["dict_type"] = dict_type
        if is_active is not None:
            qb_filters["is_active"] = is_active
        return qb_filters

    async def get_by_type_and_code_async(
        self, db: AsyncSession, *, dict_type: str, dict_code: str
    ) -> SystemDictionary | None:
        stmt = select(SystemDictionary).where(
            and_(
                SystemDictionary.dict_type == dict_type,
                SystemDictionary.dict_code == dict_code,
            )
        )
        return (await db.execute(stmt)).scalars().first()

    async def get_multi_with_filters_async(
        self,
        db: AsyncSession,
        *,
        filters: dict[str, Any] | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[SystemDictionary]:
        qb_filters = self._build_filters(
            dict_type=filters.get("dict_type") if filters else None,
            is_active=filters.get("is_active") if filters else None,
        )

        query = self.query_builder.build_query(
            filters=qb_filters,
            sort_by="sort_order",
            sort_desc=False,
            skip=skip,
            limit=limit,
        )
        return list((await db.execute(query)).scalars().all())

    async def get_by_type_async(
        self, db: AsyncSession, *, dict_type: str, is_active: bool = True
    ) -> list[SystemDictionary]:
        filters = self._build_filters(dict_type=dict_type, is_active=is_active)

        query = self.query_builder.build_query(
            filters=filters,
            sort_by="sort_order",
            sort_desc=False,
        )
        return list((await db.execute(query)).scalars().all())

    async def get_types_async(self, db: AsyncSession) -> list[str]:
        try:
            from ..models.enum_field import EnumFieldType

            stmt = (
                select(EnumFieldType.code)
                .where(EnumFieldType.is_deleted.is_(False))
                .distinct()
            )
            enum_types = (await db.execute(stmt)).scalars().all()
            return sorted([code for code in enum_types if code])
        except ImportError:
            return []


# 创建系统字典CRUD实例
system_dictionary_crud = CRUDSystemDictionary()
