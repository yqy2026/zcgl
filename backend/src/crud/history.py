"""
资产历史CRUD操作
"""

from typing import Any

from sqlalchemy import delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.asset import Asset
from ..models.asset_history import AssetHistory
from .query_builder import PartyFilter, QueryBuilder


class HistoryCRUD:
    """资产历史CRUD操作类"""

    def __init__(self) -> None:
        self.asset_query_builder = QueryBuilder(Asset)

    @staticmethod
    def _apply_asset_filter(stmt: Any, *, asset_id: str | None) -> Any:
        if asset_id:
            return stmt.where(AssetHistory.asset_id == asset_id)
        return stmt

    def _apply_party_scope(self, stmt: Any, *, party_filter: PartyFilter) -> Any:
        scoped_stmt = stmt.join(Asset, Asset.id == AssetHistory.asset_id)
        return self.asset_query_builder.apply_party_filter(scoped_stmt, party_filter)

    async def get_async(self, db: AsyncSession, id: str) -> AssetHistory | None:
        stmt = select(AssetHistory).where(AssetHistory.id == id)
        result = await db.execute(stmt)
        return result.scalars().first()

    async def get_by_asset_id_async(
        self, db: AsyncSession, asset_id: str
    ) -> list[AssetHistory]:
        stmt = (
            select(AssetHistory)
            .where(AssetHistory.asset_id == asset_id)
            .order_by(desc(AssetHistory.operation_time))
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_multi_with_count_async(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        asset_id: str | None = None,
        party_filter: PartyFilter | None = None,
    ) -> tuple[list[AssetHistory], int]:
        count_stmt = select(func.count(AssetHistory.id)).select_from(AssetHistory)
        if party_filter is not None:
            count_stmt = self._apply_party_scope(
                count_stmt,
                party_filter=party_filter,
            )
        count_stmt = self._apply_asset_filter(count_stmt, asset_id=asset_id)
        total = int((await db.execute(count_stmt)).scalar() or 0)

        stmt = select(AssetHistory).order_by(desc(AssetHistory.operation_time))
        if party_filter is not None:
            stmt = self._apply_party_scope(
                stmt,
                party_filter=party_filter,
            )
        stmt = self._apply_asset_filter(stmt, asset_id=asset_id)
        stmt = stmt.offset(skip).limit(limit)
        result = await db.execute(stmt)
        items = list(result.scalars().all())
        return items, total

    async def create_async(
        self, db: AsyncSession, *, commit: bool = True, **kwargs: Any
    ) -> AssetHistory:
        db_obj = AssetHistory(**kwargs)
        db.add(db_obj)
        if commit:
            await db.commit()
            await db.refresh(db_obj)
        else:
            await db.flush()
            await db.refresh(db_obj)
        return db_obj

    async def remove_async(self, db: AsyncSession, id: str) -> AssetHistory | None:
        obj = await self.get_async(db, id)
        if obj:
            await db.delete(obj)
            await db.commit()
        return obj

    async def remove_by_asset_id_async(
        self, db: AsyncSession, *, asset_id: str, commit: bool = True
    ) -> int:
        """Delete all history records for a given asset (async)."""
        result = await db.execute(
            delete(AssetHistory).where(AssetHistory.asset_id == asset_id)
        )
        if commit:
            await db.commit()
        else:
            await db.flush()
        return int(getattr(result, "rowcount", 0) or 0)


# 创建全局实例
history_crud = HistoryCRUD()
