"""
资产历史CRUD操作
"""

from typing import Any

from sqlalchemy import delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.asset import AssetHistory


class HistoryCRUD:
    """资产历史CRUD操作类"""

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
    ) -> tuple[list[AssetHistory], int]:
        clauses = []
        if asset_id:
            clauses.append(AssetHistory.asset_id == asset_id)

        count_stmt = select(func.count(AssetHistory.id))
        if clauses:
            count_stmt = count_stmt.where(*clauses)
        total = int((await db.execute(count_stmt)).scalar() or 0)

        stmt = select(AssetHistory).order_by(desc(AssetHistory.operation_time))
        if clauses:
            stmt = stmt.where(*clauses)
        stmt = stmt.offset(skip).limit(limit)
        result = await db.execute(stmt)
        items = list(result.scalars().all())
        return items, total

    async def create_async(
        self, db: AsyncSession, *, commit: bool = True, **kwargs: Any
    ) -> AssetHistory:
        if "operator_id" in kwargs and "operator" not in kwargs:
            kwargs["operator"] = kwargs["operator_id"]
        kwargs.pop("operator_id", None)
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
        return int(result.rowcount or 0)


# 创建全局实例
history_crud = HistoryCRUD()
