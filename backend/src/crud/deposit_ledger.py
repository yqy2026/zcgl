"""Deposit persistence without scope policy or transaction ownership."""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.deposit_ledger import DepositLedgerEntry, DepositRecord


class DepositLedgerRepository:
    async def get_entry(
        self, db: AsyncSession, *, entry_id: str, for_update: bool = False
    ) -> DepositLedgerEntry | None:
        statement = select(DepositLedgerEntry).where(DepositLedgerEntry.id == entry_id)
        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        return (await db.execute(statement)).scalar_one_or_none()

    async def get_by_contract(
        self,
        db: AsyncSession,
        *,
        contract_kind: str,
        contract_id: str,
        for_update: bool = False,
    ) -> DepositLedgerEntry | None:
        statement = select(DepositLedgerEntry).where(
            DepositLedgerEntry.contract_kind == contract_kind,
            DepositLedgerEntry.contract_id == contract_id,
        )
        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        return (await db.execute(statement)).scalar_one_or_none()

    async def list_entries(self, db: AsyncSession) -> tuple[DepositLedgerEntry, ...]:
        statement = select(DepositLedgerEntry).order_by(
            DepositLedgerEntry.contract_kind,
            DepositLedgerEntry.contract_id,
            DepositLedgerEntry.id,
        )
        return tuple((await db.execute(statement)).scalars().all())

    async def list_records(
        self, db: AsyncSession, *, entry_ids: Sequence[str]
    ) -> tuple[DepositRecord, ...]:
        if not entry_ids:
            return ()
        statement = (
            select(DepositRecord)
            .where(DepositRecord.deposit_entry_id.in_(entry_ids))
            .order_by(DepositRecord.created_at, DepositRecord.id)
        )
        return tuple((await db.execute(statement)).scalars().all())

    async def get_record(
        self, db: AsyncSession, *, record_id: str
    ) -> DepositRecord | None:
        return (
            await db.execute(select(DepositRecord).where(DepositRecord.id == record_id))
        ).scalar_one_or_none()

    async def get_record_by_idempotency(
        self, db: AsyncSession, *, key: str
    ) -> DepositRecord | None:
        return (
            await db.execute(
                select(DepositRecord).where(DepositRecord.idempotency_key == key)
            )
        ).scalar_one_or_none()

    async def find_reversal(
        self, db: AsyncSession, *, record_id: str
    ) -> DepositRecord | None:
        return (
            await db.execute(
                select(DepositRecord).where(
                    DepositRecord.reverses_record_id == record_id
                )
            )
        ).scalar_one_or_none()

    async def add_entry(self, db: AsyncSession, *, entry: DepositLedgerEntry) -> None:
        db.add(entry)

    async def add_record(self, db: AsyncSession, *, record: DepositRecord) -> None:
        db.add(record)


deposit_ledger_repository = DepositLedgerRepository()
