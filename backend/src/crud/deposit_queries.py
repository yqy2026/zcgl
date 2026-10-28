"""Batch Party-scoped deposit facts, including hidden renewal ancestors."""

from dataclasses import dataclass
from decimal import Decimal
from typing import cast

from sqlalchemy import Select, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from ..models.asset_contract import (
    ContractLifecycleEvent,
    TerminalContract,
    TerminalContractAssetUnit,
    UpstreamContract,
    UpstreamContractAssetUnit,
)
from ..models.asset_ledger import RentLedgerEntry, RentPaymentRecord
from ..models.asset_unit import AssetUnit
from ..models.deposit_ledger import DepositLedgerEntry, DepositRecord
from ..services.party_scope_resolver import EffectivePartyScope
from .asset_contract import AssetContractRepository


@dataclass
class DepositQueryFacts:
    contracts: tuple[UpstreamContract | TerminalContract, ...]
    entries: tuple[DepositLedgerEntry, ...]
    records: tuple[DepositRecord, ...]
    events: tuple[ContractLifecycleEvent, ...]
    visible_contract_ids: frozenset[str]
    totals: dict[str, tuple[Decimal, Decimal]]


class DepositQueryRepository:
    async def load_offset_candidates(
        self,
        db: AsyncSession,
        *,
        scope: EffectivePartyScope,
        contract_ids: frozenset[str],
    ) -> tuple[tuple[RentLedgerEntry, ...], tuple[RentPaymentRecord, ...]]:
        if not contract_ids:
            return (), ()
        visible = (
            AssetContractRepository._apply_terminal_scope(
                select(TerminalContract), scope=scope
            )
            .with_only_columns(TerminalContract.id)
            .where(TerminalContract.id.in_(contract_ids))
        )
        entries = tuple(
            (
                await db.execute(
                    select(RentLedgerEntry)
                    .where(
                        RentLedgerEntry.contract_kind == "terminal",
                        RentLedgerEntry.contract_id.in_(visible),
                        RentLedgerEntry.entry_type == "terminal_receivable",
                        RentLedgerEntry.voided_at.is_(None),
                    )
                    .order_by(RentLedgerEntry.due_date, RentLedgerEntry.id)
                )
            )
            .scalars()
            .all()
        )
        if not entries:
            return (), ()
        records = tuple(
            (
                await db.execute(
                    select(RentPaymentRecord).where(
                        RentPaymentRecord.ledger_entry_id.in_(
                            tuple(row.id for row in entries)
                        )
                    )
                )
            )
            .scalars()
            .all()
        )
        return entries, records

    async def load_facts(
        self,
        db: AsyncSession,
        *,
        scope: EffectivePartyScope,
        contract_kind: str,
        contract_id: str | None = None,
        party_id: str | None = None,
        project_id: str | None = None,
    ) -> DepositQueryFacts:
        model: type[UpstreamContract] | type[TerminalContract]
        query: Select[tuple[UpstreamContract]] | Select[tuple[TerminalContract]]
        if contract_kind == "upstream":
            model = UpstreamContract
            query = AssetContractRepository._apply_upstream_scope(
                select(UpstreamContract), scope=scope
            ).where(UpstreamContract.contract_type == "lease")
            if party_id is not None:
                query = query.where(
                    or_(
                        UpstreamContract.owner_party_id == party_id,
                        UpstreamContract.operator_party_id == party_id,
                    )
                )
            if project_id is not None:
                coverage = (
                    select(UpstreamContractAssetUnit.asset_unit_id)
                    .join(
                        AssetUnit,
                        AssetUnit.id == UpstreamContractAssetUnit.asset_unit_id,
                    )
                    .where(
                        UpstreamContractAssetUnit.upstream_contract_id
                        == UpstreamContract.id,
                        AssetUnit.project_id == project_id,
                    )
                )
                query = query.where(coverage.exists())
        elif contract_kind == "terminal":
            model = TerminalContract
            query = AssetContractRepository._apply_terminal_scope(
                select(TerminalContract), scope=scope
            )
            if party_id is not None:
                query = query.where(
                    or_(
                        TerminalContract.lessor_party_id == party_id,
                        TerminalContract.tenant_party_id == party_id,
                    )
                )
            if project_id is not None:
                coverage = (
                    select(TerminalContractAssetUnit.asset_unit_id)
                    .join(
                        AssetUnit,
                        AssetUnit.id == TerminalContractAssetUnit.asset_unit_id,
                    )
                    .where(
                        TerminalContractAssetUnit.terminal_contract_id
                        == TerminalContract.id,
                        AssetUnit.project_id == project_id,
                    )
                )
                query = query.where(coverage.exists())
        else:
            raise ValueError("Unknown deposit contract kind")
        if contract_id is not None:
            query = query.where(model.id == contract_id)
        visible = tuple(
            (await db.execute(query.order_by(model.contract_number, model.id)))
            .scalars()
            .all()
        )
        visible_ids = frozenset(row.id for row in visible)
        if not visible_ids:
            return DepositQueryFacts((), (), (), (), frozenset(), {})

        # UNION, rather than UNION ALL, makes even a corrupt cyclic chain finite.
        table = model.__table__
        chain = (
            select(table.c.id, table.c.renewed_from_id)
            .where(table.c.id.in_(visible_ids))
            .cte("deposit_renewal_ancestors", recursive=True)
        )
        parent = table.alias("deposit_parent")
        chain = chain.union(
            select(parent.c.id, parent.c.renewed_from_id).join(
                chain, parent.c.id == chain.c.renewed_from_id
            )
        )
        all_contracts = select(model).where(model.id.in_(select(chain.c.id)))
        if contract_kind == "upstream":
            all_contracts = all_contracts.where(
                UpstreamContract.contract_type == "lease"
            )
        contracts = cast(
            tuple[UpstreamContract | TerminalContract, ...],
            tuple((await db.execute(all_contracts.order_by(model.id))).scalars().all()),
        )
        ids = tuple(row.id for row in contracts)
        entries = tuple(
            (
                await db.execute(
                    select(DepositLedgerEntry)
                    .where(
                        DepositLedgerEntry.contract_kind == contract_kind,
                        DepositLedgerEntry.contract_id.in_(ids),
                    )
                    .order_by(DepositLedgerEntry.id)
                )
            )
            .scalars()
            .all()
        )
        entry_ids = tuple(row.id for row in entries)
        visible_entry_ids = tuple(
            row.id for row in entries if row.contract_id in visible_ids
        )
        records = (
            tuple(
                (
                    await db.execute(
                        select(DepositRecord)
                        .where(DepositRecord.deposit_entry_id.in_(visible_entry_ids))
                        .order_by(DepositRecord.created_at, DepositRecord.id)
                    )
                )
                .scalars()
                .all()
            )
            if visible_entry_ids
            else ()
        )
        events = tuple(
            (
                await db.execute(
                    select(ContractLifecycleEvent)
                    .where(
                        ContractLifecycleEvent.contract_kind == contract_kind,
                        ContractLifecycleEvent.contract_id.in_(ids),
                    )
                    .order_by(
                        ContractLifecycleEvent.created_at, ContractLifecycleEvent.id
                    )
                )
            )
            .scalars()
            .all()
        )
        totals: dict[str, tuple[Decimal, Decimal]] = {}
        if entry_ids:
            reversal = aliased(DepositRecord)
            reversed_record = (
                select(reversal.id)
                .where(reversal.reverses_record_id == DepositRecord.id)
                .exists()
            )
            aggregate = (
                select(
                    DepositRecord.deposit_entry_id,
                    func.sum(
                        case(
                            (
                                DepositRecord.record_type.in_(
                                    ("collect", "owner_reported_collect", "pay")
                                ),
                                DepositRecord.amount,
                            ),
                            else_=0,
                        )
                    ),
                    func.sum(
                        case(
                            (
                                DepositRecord.record_type.in_(
                                    (
                                        "refund",
                                        "owner_reported_refund",
                                        "recover",
                                        "deduct",
                                        "forfeit",
                                    )
                                ),
                                DepositRecord.amount,
                            ),
                            else_=0,
                        )
                    ),
                )
                .where(
                    DepositRecord.deposit_entry_id.in_(entry_ids),
                    DepositRecord.record_type != "reversal",
                    ~reversed_record,
                )
                .group_by(DepositRecord.deposit_entry_id)
            )
            for entry_id, income, expense in (await db.execute(aggregate)).all():
                totals[entry_id] = (income, expense)
        return DepositQueryFacts(
            contracts, entries, records, events, visible_ids, totals
        )


deposit_query_repository = DepositQueryRepository()
