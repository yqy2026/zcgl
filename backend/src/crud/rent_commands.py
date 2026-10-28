"""Persistence helpers for rent commands, without transaction ownership."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.asset_contract import AssetContractWriteReceipt, ContractRentSchedule
from ..models.asset_ledger import RentPaymentRecord


class RentCommandRepository:
    async def find_reversal(
        self, db: AsyncSession, *, record_id: str
    ) -> RentPaymentRecord | None:
        return (
            (
                await db.execute(
                    select(RentPaymentRecord).where(
                        RentPaymentRecord.reverses_record_id == record_id
                    )
                )
            )
            .scalars()
            .one_or_none()
        )

    async def add_receipt(
        self, db: AsyncSession, *, receipt: AssetContractWriteReceipt
    ) -> None:
        db.add(receipt)
        await db.flush()

    async def replace_schedules(
        self,
        db: AsyncSession,
        *,
        old: tuple[ContractRentSchedule, ...],
        new: list[ContractRentSchedule],
        occurred_at: datetime,
        correlation_id: str,
    ) -> None:
        for row in old:
            row.superseded_at = occurred_at
            row.superseded_correlation_id = correlation_id
        await db.flush()
        db.add_all(new)
        await db.flush()


rent_command_repository = RentCommandRepository()
