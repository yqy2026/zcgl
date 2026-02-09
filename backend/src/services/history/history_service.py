"""
History 服务层
"""

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception_handler import ResourceNotFoundError, not_found
from ...crud.asset import asset_crud
from ...crud.history import history_crud


class HistoryService:
    async def get_history_list(
        self,
        db: AsyncSession,
        *,
        skip: int,
        limit: int,
        asset_id: str | None,
    ) -> tuple[list, int]:
        if asset_id:
            asset = await asset_crud.get_async(db=db, id=asset_id)
            if not asset:
                raise ResourceNotFoundError("Asset", asset_id)

        return await history_crud.get_multi_with_count_async(
            db,
            skip=skip,
            limit=limit,
            asset_id=asset_id,
        )

    async def get_history_detail(
        self,
        db: AsyncSession,
        *,
        history_id: str,
    ):
        history_record = await history_crud.get_async(db=db, id=history_id)
        if not history_record:
            raise not_found(
                f"历史记录 {history_id} 不存在",
                resource_type="history",
                resource_id=history_id,
            )
        return history_record

    async def delete_history(
        self,
        db: AsyncSession,
        *,
        history_id: str,
    ) -> bool:
        history_record = await history_crud.get_async(db=db, id=history_id)
        if not history_record:
            raise not_found(
                f"历史记录 {history_id} 不存在",
                resource_type="history",
                resource_id=history_id,
            )

        await history_crud.remove_async(db=db, id=history_id)
        return True


def get_history_service() -> HistoryService:
    return HistoryService()
