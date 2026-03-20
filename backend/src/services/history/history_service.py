"""
History 服务层
"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception_handler import ResourceNotFoundError, not_found
from ...crud.asset import asset_crud
from ...crud.history import history_crud
from ...crud.query_builder import PartyFilter
from ...services.party_scope import resolve_user_party_filter

logger = logging.getLogger(__name__)


class HistoryService:
    async def _resolve_party_filter(
        self,
        db: AsyncSession,
        *,
        current_user_id: str | None = None,
        party_filter: PartyFilter | None = None,
    ) -> PartyFilter | None:
        return await resolve_user_party_filter(
            db,
            current_user_id=current_user_id,
            party_filter=party_filter,
            logger=logger,
            allow_legacy_default_organization_fallback=False,
        )

    @staticmethod
    def _is_fail_closed_party_filter(party_filter: PartyFilter | None) -> bool:
        if party_filter is None:
            return False
        return len([party_id for party_id in party_filter.party_ids if str(party_id).strip() != ""]) == 0

    async def get_history_list(
        self,
        db: AsyncSession,
        *,
        skip: int,
        limit: int,
        asset_id: str | None,
        current_user_id: str | None = None,
        party_filter: PartyFilter | None = None,
    ) -> tuple[list[Any], int]:
        resolved_party_filter = await self._resolve_party_filter(
            db,
            current_user_id=current_user_id,
            party_filter=party_filter,
        )
        if self._is_fail_closed_party_filter(resolved_party_filter):
            return [], 0

        if asset_id:
            asset = await asset_crud.get_async(
                db=db,
                id=asset_id,
                party_filter=resolved_party_filter,
            )
            if not asset:
                raise ResourceNotFoundError("Asset", asset_id)

        return await history_crud.get_multi_with_count_async(
            db,
            skip=skip,
            limit=limit,
            asset_id=asset_id,
            party_filter=resolved_party_filter,
        )

    async def get_history_detail(
        self,
        db: AsyncSession,
        *,
        history_id: str,
        current_user_id: str | None = None,
        party_filter: PartyFilter | None = None,
    ) -> Any:
        resolved_party_filter = await self._resolve_party_filter(
            db,
            current_user_id=current_user_id,
            party_filter=party_filter,
        )
        if self._is_fail_closed_party_filter(resolved_party_filter):
            raise not_found(
                f"历史记录 {history_id} 不存在",
                resource_type="history",
                resource_id=history_id,
            )

        history_record = await history_crud.get_async(db=db, id=history_id)
        if not history_record:
            raise not_found(
                f"历史记录 {history_id} 不存在",
                resource_type="history",
                resource_id=history_id,
            )

        asset = await asset_crud.get_async(
            db=db,
            id=history_record.asset_id,
            party_filter=resolved_party_filter,
        )
        if not asset:
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
