"""Queries used only by transaction-local lifecycle deposit settlement."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.deposit_ledger import DepositRecord


class DepositSettlementRepository:
    async def event_deductions(
        self, db: AsyncSession, *, event_id: str
    ) -> tuple[DepositRecord, ...]:
        statement = (
            select(DepositRecord)
            .where(
                DepositRecord.lifecycle_event_id == event_id,
                DepositRecord.record_type == "deduct",
            )
            .order_by(DepositRecord.id)
        )
        return tuple((await db.execute(statement)).scalars().all())


deposit_settlement_repository = DepositSettlementRepository()
