"""
催缴管理业务服务

将催缴相关的数据库操作从 API 层迁移至此服务层，
遵循项目架构规范：业务逻辑必须在 services/ 层。
"""

import logging
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception_handler import ResourceNotFoundError
from ...crud.collection import collection_crud
from ...crud.query_builder import PartyFilter
from ...models.collection import CollectionRecord, CollectionStatus
from ...models.contract_group import ContractLedgerEntry
from ...schemas.collection import (
    CollectionRecordCreate,
    CollectionRecordUpdate,
    CollectionTaskSummary,
)
from ...services.party_scope import resolve_user_party_filter

logger = logging.getLogger(__name__)


class CollectionService:
    """催缴管理业务服务"""

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
        return (
            len(
                [
                    party_id
                    for party_id in party_filter.party_ids
                    if str(party_id).strip() != ""
                ]
            )
            == 0
        )

    async def get_summary_async(
        self,
        db: AsyncSession,
        *,
        current_user_id: str | None = None,
        party_filter: PartyFilter | None = None,
    ) -> CollectionTaskSummary:
        resolved_party_filter = await self._resolve_party_filter(
            db,
            current_user_id=current_user_id,
            party_filter=party_filter,
        )
        if self._is_fail_closed_party_filter(resolved_party_filter):
            return CollectionTaskSummary(
                total_overdue_count=0,
                total_overdue_amount=Decimal("0"),
                pending_collection_count=0,
                this_month_collection_count=0,
                collection_success_rate=None,
            )

        today = date.today()
        current_month_start = date(today.year, today.month, 1)

        (
            total_overdue_count,
            total_overdue_amount,
        ) = await collection_crud.get_overdue_ledger_stats_async(
            db,
            today=today,
            party_filter=resolved_party_filter,
        )

        pending_collection_count = await collection_crud.count_by_statuses_async(
            db,
            statuses=[CollectionStatus.PENDING, CollectionStatus.IN_PROGRESS],
            party_filter=resolved_party_filter,
        )

        this_month_collection_count = await collection_crud.count_since_date_async(
            db,
            collection_date=current_month_start,
            party_filter=resolved_party_filter,
        )

        success_count = await collection_crud.count_by_statuses_async(
            db,
            statuses=[CollectionStatus.SUCCESS],
            party_filter=resolved_party_filter,
        )
        total_collection_count = await collection_crud.count_total_async(
            db,
            party_filter=resolved_party_filter,
        )

        collection_success_rate = None
        if total_collection_count > 0:
            collection_success_rate = (
                Decimal(success_count)
                / Decimal(total_collection_count)
                * Decimal("100")
            )

        return CollectionTaskSummary(
            total_overdue_count=total_overdue_count,
            total_overdue_amount=total_overdue_amount,
            pending_collection_count=pending_collection_count,
            this_month_collection_count=this_month_collection_count,
            collection_success_rate=collection_success_rate,
        )

    async def list_records_async(
        self,
        db: AsyncSession,
        *,
        ledger_id: str | None = None,
        contract_id: str | None = None,
        collection_status: CollectionStatus | None = None,
        page: int = 1,
        page_size: int = 20,
        current_user_id: str | None = None,
        party_filter: PartyFilter | None = None,
    ) -> dict[str, Any]:
        resolved_party_filter = await self._resolve_party_filter(
            db,
            current_user_id=current_user_id,
            party_filter=party_filter,
        )
        if self._is_fail_closed_party_filter(resolved_party_filter):
            return {"items": [], "total": 0, "page": page, "page_size": page_size}

        items, total = await collection_crud.get_multi_with_filters_async(
            db,
            ledger_id=ledger_id,
            contract_id=contract_id,
            collection_status=collection_status,
            page=page,
            page_size=page_size,
            party_filter=resolved_party_filter,
        )

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def get_by_id_async(
        self,
        db: AsyncSession,
        *,
        record_id: str,
        current_user_id: str | None = None,
        party_filter: PartyFilter | None = None,
    ) -> CollectionRecord | None:
        resolved_party_filter = await self._resolve_party_filter(
            db,
            current_user_id=current_user_id,
            party_filter=party_filter,
        )
        if self._is_fail_closed_party_filter(resolved_party_filter):
            return None
        return await collection_crud.get_by_id_async(
            db,
            record_id=record_id,
            party_filter=resolved_party_filter,
        )

    async def get_ledger_by_id_async(
        self,
        db: AsyncSession,
        *,
        ledger_id: str,
        current_user_id: str | None = None,
        party_filter: PartyFilter | None = None,
    ) -> ContractLedgerEntry | None:
        resolved_party_filter = await self._resolve_party_filter(
            db,
            current_user_id=current_user_id,
            party_filter=party_filter,
        )
        if self._is_fail_closed_party_filter(resolved_party_filter):
            return None
        return await collection_crud.get_ledger_by_id_async(
            db,
            ledger_id=ledger_id,
            party_filter=resolved_party_filter,
        )

    async def create_async(
        self,
        db: AsyncSession,
        *,
        obj_in: CollectionRecordCreate,
        operator: str | None = None,
        operator_id: str | None = None,
        current_user_id: str | None = None,
        party_filter: PartyFilter | None = None,
    ) -> CollectionRecord:
        ledger = await self.get_ledger_by_id_async(
            db,
            ledger_id=obj_in.ledger_id,
            current_user_id=current_user_id,
            party_filter=party_filter,
        )
        if not ledger:
            raise ResourceNotFoundError("租金台账", obj_in.ledger_id)

        record_data = obj_in.model_dump()
        if not record_data.get("operator") and operator:
            record_data["operator"] = operator
        if not record_data.get("operator_id") and operator_id:
            record_data["operator_id"] = operator_id

        return await collection_crud.create(db, obj_in=record_data)

    async def update_async(
        self,
        db: AsyncSession,
        *,
        db_obj: CollectionRecord,
        obj_in: CollectionRecordUpdate,
    ) -> CollectionRecord:
        return await collection_crud.update(db, db_obj=db_obj, obj_in=obj_in)

    async def delete_async(self, db: AsyncSession, *, db_obj: CollectionRecord) -> None:
        await collection_crud.remove(db, id=str(db_obj.id))


# 单例实例
collection_service = CollectionService()
