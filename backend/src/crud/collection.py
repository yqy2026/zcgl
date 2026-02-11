"""
Collection CRUD operations.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..constants.rent_contract_constants import PaymentStatus
from ..models.collection import CollectionRecord, CollectionStatus
from ..models.rent_contract import RentLedger
from ..schemas.collection import CollectionRecordCreate, CollectionRecordUpdate
from .base import CRUDBase


class CRUDCollectionRecord(
    CRUDBase[CollectionRecord, CollectionRecordCreate, CollectionRecordUpdate]
):
    """CRUD for CollectionRecord."""

    async def get_overdue_ledger_stats_async(
        self, db: AsyncSession, *, today: date
    ) -> tuple[int, Decimal]:
        stmt = (
            select(
                func.count(RentLedger.id).label("total_count"),
                func.sum(RentLedger.overdue_amount).label("total_amount"),
            )
            .where(
                and_(
                    RentLedger.payment_status.in_(
                        [PaymentStatus.UNPAID, PaymentStatus.PARTIAL]
                    ),
                    RentLedger.due_date < today,
                    RentLedger.data_status == "正常",
                )
            )
            .select_from(RentLedger)
        )
        stats = (await db.execute(stmt)).first()
        total_count = int(stats.total_count) if stats and stats.total_count else 0
        total_amount = stats.total_amount if stats and stats.total_amount else Decimal("0")
        return total_count, total_amount

    async def count_by_statuses_async(
        self, db: AsyncSession, *, statuses: list[CollectionStatus]
    ) -> int:
        stmt = select(func.count(CollectionRecord.id))
        if statuses:
            stmt = stmt.where(CollectionRecord.collection_status.in_(statuses))
        return int((await db.execute(stmt)).scalar() or 0)

    async def count_since_date_async(
        self, db: AsyncSession, *, collection_date: date
    ) -> int:
        stmt = select(func.count(CollectionRecord.id)).where(
            CollectionRecord.collection_date >= collection_date
        )
        return int((await db.execute(stmt)).scalar() or 0)

    async def count_total_async(self, db: AsyncSession) -> int:
        stmt = select(func.count(CollectionRecord.id))
        return int((await db.execute(stmt)).scalar() or 0)

    async def get_multi_with_filters_async(
        self,
        db: AsyncSession,
        *,
        ledger_id: str | None = None,
        contract_id: str | None = None,
        collection_status: CollectionStatus | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[CollectionRecord], int]:
        conditions = []
        if ledger_id:
            conditions.append(CollectionRecord.ledger_id == ledger_id)
        if contract_id:
            conditions.append(CollectionRecord.contract_id == contract_id)
        if collection_status:
            conditions.append(CollectionRecord.collection_status == collection_status)

        count_stmt = select(func.count(CollectionRecord.id))
        if conditions:
            count_stmt = count_stmt.where(and_(*conditions))
        total = int((await db.execute(count_stmt)).scalar() or 0)

        offset = (page - 1) * page_size
        stmt = select(CollectionRecord)
        if conditions:
            stmt = stmt.where(and_(*conditions))
        stmt = (
            stmt.order_by(CollectionRecord.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        items = list((await db.execute(stmt)).scalars().all())
        return items, total

    async def get_by_id_async(
        self, db: AsyncSession, *, record_id: str
    ) -> CollectionRecord | None:
        stmt = select(CollectionRecord).where(CollectionRecord.id == record_id)
        return (await db.execute(stmt)).scalars().first()

    async def get_ledger_by_id_async(
        self, db: AsyncSession, *, ledger_id: str
    ) -> RentLedger | None:
        stmt = select(RentLedger).where(RentLedger.id == ledger_id)
        return (await db.execute(stmt)).scalars().first()


collection_crud = CRUDCollectionRecord(CollectionRecord)
