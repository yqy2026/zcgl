"""Batch database reads for current Party-scoped rent projections."""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.asset_contract import (
    ContractLifecycleEvent,
    ContractRentSchedule,
    TerminalContract,
    UpstreamContract,
)
from ..models.asset_ledger import RentLedgerEntry, RentPaymentRecord
from ..services.party_scope_resolver import EffectivePartyScope
from .asset_contract import AssetContractRepository


@dataclass
class RentQueryFacts:
    contracts: tuple[UpstreamContract | TerminalContract, ...]
    entries: tuple[RentLedgerEntry, ...]
    records: tuple[RentPaymentRecord, ...]
    schedules: tuple[ContractRentSchedule, ...]
    events: tuple[ContractLifecycleEvent, ...]


class RentLedgerQueryRepository:
    async def contract_entries(
        self, db: AsyncSession, *, contract_kind: str, contract_id: str
    ) -> tuple[tuple[RentLedgerEntry, ...], tuple[RentPaymentRecord, ...]]:
        entries = tuple(
            (
                await db.execute(
                    select(RentLedgerEntry)
                    .where(
                        RentLedgerEntry.contract_kind == contract_kind,
                        RentLedgerEntry.contract_id == contract_id,
                    )
                    .order_by(RentLedgerEntry.period_start, RentLedgerEntry.id)
                )
            )
            .scalars()
            .all()
        )
        ids = tuple(row.id for row in entries)
        records = (
            tuple(
                (
                    await db.execute(
                        select(RentPaymentRecord).where(
                            RentPaymentRecord.ledger_entry_id.in_(ids)
                        )
                    )
                )
                .scalars()
                .all()
            )
            if ids
            else ()
        )
        return entries, records

    async def matrix_facts(
        self,
        db: AsyncSession,
        *,
        scope: EffectivePartyScope,
        ledger_type: str,
        year: int,
    ) -> RentQueryFacts:
        kind = "upstream" if ledger_type == "upstream_rent" else "terminal"
        query: Select[tuple[UpstreamContract]] | Select[tuple[TerminalContract]]
        if kind == "upstream":
            query = AssetContractRepository._apply_upstream_scope(
                select(UpstreamContract), scope=scope
            ).where(UpstreamContract.contract_type == "lease")
        else:
            query = AssetContractRepository._apply_terminal_scope(
                select(TerminalContract), scope=scope
            )
        contracts = tuple(
            (await db.execute(query.order_by("contract_number"))).scalars().all()
        )
        ids = tuple(contract.id for contract in contracts)
        if not ids:
            return RentQueryFacts((), (), (), (), ())
        entries = tuple(
            (
                await db.execute(
                    select(RentLedgerEntry)
                    .where(
                        RentLedgerEntry.contract_kind == kind,
                        RentLedgerEntry.contract_id.in_(ids),
                        RentLedgerEntry.period.like(f"{year:04d}-%"),
                    )
                    .order_by(RentLedgerEntry.period_start, RentLedgerEntry.id)
                )
            )
            .scalars()
            .all()
        )
        entry_ids = tuple(entry.id for entry in entries)
        records = (
            tuple(
                (
                    await db.execute(
                        select(RentPaymentRecord)
                        .where(
                            RentPaymentRecord.ledger_entry_id.in_(entry_ids),
                        )
                        .order_by(RentPaymentRecord.created_at, RentPaymentRecord.id)
                    )
                )
                .scalars()
                .all()
            )
            if entry_ids
            else ()
        )
        schedules = tuple(
            (
                await db.execute(
                    select(ContractRentSchedule)
                    .where(
                        ContractRentSchedule.contract_kind == kind,
                        ContractRentSchedule.contract_id.in_(ids),
                        ContractRentSchedule.superseded_at.is_(None),
                    )
                    .order_by(ContractRentSchedule.stage_start)
                )
            )
            .scalars()
            .all()
        )
        events = tuple(
            (
                await db.execute(
                    select(ContractLifecycleEvent).where(
                        ContractLifecycleEvent.contract_kind == kind,
                        ContractLifecycleEvent.contract_id.in_(ids),
                    )
                )
            )
            .scalars()
            .all()
        )
        return RentQueryFacts(contracts, entries, records, schedules, events)

    async def detail_facts(
        self, db: AsyncSession, *, scope: EffectivePartyScope, entry_id: str
    ) -> RentQueryFacts | None:
        entry = (
            (
                await db.execute(
                    select(RentLedgerEntry).where(RentLedgerEntry.id == entry_id)
                )
            )
            .scalars()
            .one_or_none()
        )
        if entry is None:
            return None
        repository = AssetContractRepository()
        contract = (
            await repository.get_upstream(
                db, contract_id=entry.contract_id, scope=scope
            )
            if entry.contract_kind == "upstream"
            else await repository.get_terminal(
                db, contract_id=entry.contract_id, scope=scope
            )
        )
        if contract is None:
            return None
        records = tuple(
            (
                await db.execute(
                    select(RentPaymentRecord)
                    .where(
                        RentPaymentRecord.ledger_entry_id == entry.id,
                    )
                    .order_by(RentPaymentRecord.created_at, RentPaymentRecord.id)
                )
            )
            .scalars()
            .all()
        )
        schedules = await repository.list_rent_schedules(
            db, contract_kind=entry.contract_kind, contract_ids=(entry.contract_id,)
        )
        events = await repository.list_lifecycle_events(
            db, contract_kind=entry.contract_kind, contract_id=entry.contract_id
        )
        return RentQueryFacts((contract,), (entry,), records, schedules, events)

    async def terminal_outstanding_facts(
        self, db: AsyncSession, *, today: date
    ) -> tuple[tuple[RentLedgerEntry, ...], tuple[RentPaymentRecord, ...]]:
        entries = tuple(
            (
                await db.execute(
                    select(RentLedgerEntry).where(
                        RentLedgerEntry.contract_kind == "terminal",
                        RentLedgerEntry.voided_at.is_(None),
                        RentLedgerEntry.period <= today.strftime("%Y-%m"),
                    )
                )
            )
            .scalars()
            .all()
        )
        ids = tuple(entry.id for entry in entries)
        records = (
            tuple(
                (
                    await db.execute(
                        select(RentPaymentRecord).where(
                            RentPaymentRecord.ledger_entry_id.in_(ids)
                        )
                    )
                )
                .scalars()
                .all()
            )
            if ids
            else ()
        )
        return entries, records


rent_ledger_query_repository = RentLedgerQueryRepository()
