"""Rent counterparts of append-only deposit deductions."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.asset_ledger import RentPaymentRecord


class DepositPairRepository:
    async def rent_record(
        self, db: AsyncSession, *, deposit_record_id: str
    ) -> RentPaymentRecord | None:
        return (
            await db.execute(
                select(RentPaymentRecord).where(
                    RentPaymentRecord.paired_deposit_record_id == deposit_record_id,
                )
            )
        ).scalar_one_or_none()


deposit_pair_repository = DepositPairRepository()
