"""
催缴管理业务服务

将催缴相关的数据库操作从 API 层迁移至此服务层，
遵循项目架构规范：业务逻辑必须在 services/ 层。
"""

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...constants.rent_contract_constants import PaymentStatus
from ...core.exception_handler import ResourceNotFoundError
from ...models.collection import CollectionRecord, CollectionStatus
from ...models.rent_contract import RentLedger
from ...schemas.collection import (
    CollectionRecordCreate,
    CollectionRecordUpdate,
    CollectionTaskSummary,
)


class CollectionService:
    """催缴管理业务服务"""

    async def get_summary_async(self, db: AsyncSession) -> CollectionTaskSummary:
        today = date.today()
        current_month_start = date(today.year, today.month, 1)

        overdue_stmt = (
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
        overdue_stats = (await db.execute(overdue_stmt)).first()

        total_overdue_count = (
            int(overdue_stats.total_count) if overdue_stats and overdue_stats.total_count else 0
        )
        total_overdue_amount = (
            overdue_stats.total_amount if overdue_stats and overdue_stats.total_amount else Decimal("0")
        )

        pending_stmt = select(func.count(CollectionRecord.id)).where(
            CollectionRecord.collection_status.in_(
                [CollectionStatus.PENDING, CollectionStatus.IN_PROGRESS]
            )
        )
        pending_collection_count = int((await db.execute(pending_stmt)).scalar() or 0)

        this_month_stmt = select(func.count(CollectionRecord.id)).where(
            CollectionRecord.collection_date >= current_month_start
        )
        this_month_collection_count = int((await db.execute(this_month_stmt)).scalar() or 0)

        success_stmt = select(func.count(CollectionRecord.id)).where(
            CollectionRecord.collection_status == CollectionStatus.SUCCESS
        )
        success_count = int((await db.execute(success_stmt)).scalar() or 0)

        total_stmt = select(func.count(CollectionRecord.id))
        total_collection_count = int((await db.execute(total_stmt)).scalar() or 0)

        collection_success_rate = None
        if total_collection_count > 0:
            collection_success_rate = (
                Decimal(success_count) / Decimal(total_collection_count) * Decimal("100")
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
    ) -> dict[str, Any]:
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
        records = (await db.execute(stmt)).scalars().all()

        return {
            "items": records,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

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

    async def create_async(
        self,
        db: AsyncSession,
        *,
        obj_in: CollectionRecordCreate,
        operator: str | None = None,
        operator_id: str | None = None,
    ) -> CollectionRecord:
        ledger = await self.get_ledger_by_id_async(db, ledger_id=obj_in.ledger_id)
        if not ledger:
            raise ResourceNotFoundError("租金台账", obj_in.ledger_id)

        record_data = obj_in.model_dump()
        if not record_data.get("operator") and operator:
            record_data["operator"] = operator
        if not record_data.get("operator_id") and operator_id:
            record_data["operator_id"] = operator_id

        record = CollectionRecord(**record_data)
        db.add(record)
        await db.commit()
        await db.refresh(record)

        return record

    async def update_async(
        self,
        db: AsyncSession,
        *,
        db_obj: CollectionRecord,
        obj_in: CollectionRecordUpdate,
    ) -> CollectionRecord:
        update_dict = obj_in.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(db_obj, field, value)

        await db.commit()
        await db.refresh(db_obj)

        return db_obj

    async def delete_async(
        self, db: AsyncSession, *, db_obj: CollectionRecord
    ) -> None:
        await db.delete(db_obj)
        await db.commit()


# 单例实例
collection_service = CollectionService()
