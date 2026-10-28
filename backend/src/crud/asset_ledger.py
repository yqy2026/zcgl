"""Persistence operations for v5 rent obligations and append-only records."""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.asset_contract import (
    ContractLifecycleEvent,
    ContractRentSchedule,
    TerminalContract,
    UpstreamContract,
)
from ..models.asset_ledger import RentLedgerEntry, RentPaymentRecord


class AssetLedgerRepository:
    async def get_entry(
        self, db: AsyncSession, *, entry_id: str, for_update: bool = False
    ) -> RentLedgerEntry | None:
        statement = select(RentLedgerEntry).where(RentLedgerEntry.id == entry_id)
        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        return (await db.execute(statement)).scalar_one_or_none()

    async def list_entries(
        self,
        db: AsyncSession,
        *,
        contract_kind: str,
        contract_id: str,
        for_update: bool = False,
    ) -> tuple[RentLedgerEntry, ...]:
        statement = (
            select(RentLedgerEntry)
            .where(
                RentLedgerEntry.contract_kind == contract_kind,
                RentLedgerEntry.contract_id == contract_id,
            )
            .order_by(RentLedgerEntry.period_start, RentLedgerEntry.id)
        )
        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        return tuple((await db.execute(statement)).scalars().all())

    async def list_records(
        self, db: AsyncSession, *, entry_ids: Sequence[str]
    ) -> tuple[RentPaymentRecord, ...]:
        if not entry_ids:
            return ()
        statement = (
            select(RentPaymentRecord)
            .where(RentPaymentRecord.ledger_entry_id.in_(entry_ids))
            .order_by(RentPaymentRecord.created_at, RentPaymentRecord.id)
        )
        return tuple((await db.execute(statement)).scalars().all())

    async def get_record(
        self, db: AsyncSession, *, record_id: str
    ) -> RentPaymentRecord | None:
        return (
            await db.execute(
                select(RentPaymentRecord).where(RentPaymentRecord.id == record_id)
            )
        ).scalar_one_or_none()

    async def get_record_by_idempotency(
        self, db: AsyncSession, *, key: str
    ) -> RentPaymentRecord | None:
        return (
            await db.execute(
                select(RentPaymentRecord).where(
                    RentPaymentRecord.idempotency_key == key
                )
            )
        ).scalar_one_or_none()

    async def add_entry(self, db: AsyncSession, *, entry: RentLedgerEntry) -> None:
        db.add(entry)

    async def add_record(self, db: AsyncSession, *, record: RentPaymentRecord) -> None:
        db.add(record)

    async def load_contract_facts(
        self, db: AsyncSession, *, contract_kind: str, contract_id: str
    ) -> tuple[
        UpstreamContract | TerminalContract | None,
        tuple[ContractRentSchedule, ...],
        tuple[ContractLifecycleEvent, ...],
    ]:
        if contract_kind == "upstream":
            contract: UpstreamContract | TerminalContract | None = (
                await db.execute(
                    select(UpstreamContract).where(UpstreamContract.id == contract_id)
                )
            ).scalar_one_or_none()
        else:
            contract = (
                await db.execute(
                    select(TerminalContract).where(TerminalContract.id == contract_id)
                )
            ).scalar_one_or_none()
        schedules = (
            (
                await db.execute(
                    select(ContractRentSchedule)
                    .where(
                        ContractRentSchedule.contract_kind == contract_kind,
                        ContractRentSchedule.contract_id == contract_id,
                        ContractRentSchedule.superseded_at.is_(None),
                    )
                    .order_by(ContractRentSchedule.stage_start)
                )
            )
            .scalars()
            .all()
        )
        events = (
            (
                await db.execute(
                    select(ContractLifecycleEvent).where(
                        ContractLifecycleEvent.contract_kind == contract_kind,
                        ContractLifecycleEvent.contract_id == contract_id,
                    )
                )
            )
            .scalars()
            .all()
        )
        return contract, tuple(schedules), tuple(events)


asset_ledger_repository = AssetLedgerRepository()
