"""Current-scope deposit views from batched facts and effective SQL totals."""

from dataclasses import asdict
from datetime import date
from decimal import Decimal
from typing import Literal, cast

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception_handler import ResourceNotFoundError
from ...crud.deposit_ledger import deposit_ledger_repository
from ...crud.deposit_queries import DepositQueryFacts, deposit_query_repository
from ...models.asset_contract import ContractLifecycleEvent, UpstreamContract
from ...schemas.deposit_commands import (
    DepositEntryResponse,
    DepositListResponse,
    DepositOffsetCandidate,
    DepositRecordResponse,
)
from ..party_scope_resolver import EffectivePartyScope
from .contract_projections import (
    derive_terminal_contract_status,
    derive_upstream_contract_status,
)
from .deposit_rules import DepositBalance, project_deposit_balance
from .rent_command_support import require_scope, scoped_contract
from .rent_ledger_projections import effective_paid
from .rent_ledger_query_service import business_today


def effective_deposit_ancestors(
    facts: DepositQueryFacts, contract_id: str
) -> frozenset[str]:
    """Only an unrevoked renewal authorizes access to a predecessor's rent."""
    contracts = {row.id: row for row in facts.contracts}
    active = active_deposit_events(facts.events)
    ids: set[str] = set()
    current = contract_id
    while current not in ids:
        ids.add(current)
        contract = contracts.get(current)
        if contract is None or contract.renewed_from_id is None:
            break
        parent = contract.renewed_from_id
        if not any(
            e.contract_id == parent
            and e.event_type == "renewed"
            and e.successor_contract_id == current
            for e in active
        ):
            break
        current = parent
    return frozenset(ids)


def active_deposit_events(
    events: tuple[ContractLifecycleEvent, ...],
) -> tuple[ContractLifecycleEvent, ...]:
    reversed_ids = {e.reversed_event_id for e in events if e.event_type == "reversed"}
    return tuple(
        e for e in events if e.event_type != "reversed" and e.id not in reversed_ids
    )


def project_deposit_facts(
    facts: DepositQueryFacts, *, today: date
) -> list[DepositEntryResponse]:
    contracts = {row.id: row for row in facts.contracts}
    entries = {row.contract_id: row for row in facts.entries}
    active = active_deposit_events(facts.events)
    projections: dict[str, DepositBalance] = {}

    def balance(contract_id: str, ancestors: frozenset[str]) -> DepositBalance:
        if contract_id in projections:
            return projections[contract_id]
        if contract_id in ancestors:
            raise ValueError("Cyclic deposit renewal chain")
        contract = contracts.get(contract_id)
        entry = entries.get(contract_id)
        if contract is None or entry is None:
            raise ResourceNotFoundError("DepositLedgerEntry", contract_id)
        events = tuple(e for e in facts.events if e.contract_id == contract_id)
        current = tuple(e for e in active if e.contract_id == contract_id)
        status = (
            derive_upstream_contract_status(
                contract, as_of=today, lifecycle_events=events
            )
            if isinstance(contract, UpstreamContract)
            else derive_terminal_contract_status(
                contract, as_of=today, lifecycle_events=events
            )
        )
        parent_id = contract.renewed_from_id
        carried_in = Decimal("0")
        if parent_id is not None and any(
            e.contract_id == parent_id
            and e.event_type == "renewed"
            and e.successor_contract_id == contract_id
            for e in active
        ):
            carried_in = balance(
                parent_id, ancestors | {contract_id}
            ).carried_out_amount
        income, expense = facts.totals.get(entry.id, (Decimal("0"), Decimal("0")))
        projections[contract_id] = project_deposit_balance(
            contract_kind=entry.contract_kind,
            contract_status=status,
            has_ended_event=any(
                e.event_type in {"terminated", "exited"} for e in current
            ),
            renewed=any(e.event_type == "renewed" for e in current),
            agreed_amount=contract.deposit_amount,
            income_amount=income,
            expense_amount=expense,
            carried_in_amount=carried_in,
        )
        return projections[contract_id]

    views = []
    for contract_id in sorted(facts.visible_contract_ids):
        entry = entries.get(contract_id)
        if entry is None:
            continue
        projected = balance(contract_id, frozenset())
        current = tuple(e for e in active if e.contract_id == contract_id)
        contract = contracts[contract_id]
        ended = any(e.event_type in {"terminated", "exited"} for e in current)
        if entry.contract_kind == "terminal":
            ended = ended or today > contract.end_date
        views.append(
            DepositEntryResponse(
                id=entry.id,
                contract_kind=cast(
                    Literal["upstream", "terminal"], entry.contract_kind
                ),
                contract_id=contract_id,
                collector=cast(Literal["operator", "owner"], entry.collector),
                version=entry.version,
                ended=ended,
                read_only=any(e.event_type == "renewed" for e in current),
                records=[
                    DepositRecordResponse.model_validate(r)
                    for r in facts.records
                    if r.deposit_entry_id == entry.id
                ],
                **asdict(projected),
            )
        )
    return views


class DepositQueryService:
    async def get(
        self, db: AsyncSession, *, entry_id: str, scope: EffectivePartyScope
    ) -> DepositEntryResponse:
        require_scope(scope, scope.user_id)
        entry = await deposit_ledger_repository.get_entry(db, entry_id=entry_id)
        if entry is None:
            raise ResourceNotFoundError("DepositLedgerEntry", entry_id)
        await scoped_contract(
            db, kind=entry.contract_kind, contract_id=entry.contract_id, scope=scope
        )
        facts = await deposit_query_repository.load_facts(
            db,
            scope=scope,
            contract_kind=entry.contract_kind,
            contract_id=entry.contract_id,
        )
        for view in project_deposit_facts(facts, today=business_today()):
            if view.id == entry_id:
                if (
                    view.ended
                    and not view.read_only
                    and view.contract_kind == "terminal"
                    and view.collector == "operator"
                ):
                    (
                        entries,
                        records,
                    ) = await deposit_query_repository.load_offset_candidates(
                        db,
                        scope=scope,
                        contract_ids=effective_deposit_ancestors(
                            facts, entry.contract_id
                        ),
                    )
                    for rent in entries:
                        remaining = rent.due_amount - effective_paid(
                            tuple(r for r in records if r.ledger_entry_id == rent.id)
                        )
                        if remaining > 0:
                            view.offset_candidates.append(
                                DepositOffsetCandidate(
                                    id=rent.id,
                                    contract_id=rent.contract_id,
                                    period_start=rent.period_start,
                                    period_end=rent.period_end,
                                    due_date=rent.due_date,
                                    remaining_amount=remaining,
                                )
                            )
                return view
        raise ResourceNotFoundError("DepositLedgerEntry", entry_id)

    async def list(
        self,
        db: AsyncSession,
        *,
        scope: EffectivePartyScope,
        status: str | None = None,
        contract_kind: str | None = None,
        contract_id: str | None = None,
        party_id: str | None = None,
        project_id: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> DepositListResponse:
        require_scope(scope, scope.user_id)
        views = []
        for kind in (
            (contract_kind,) if contract_kind is not None else ("upstream", "terminal")
        ):
            facts = await deposit_query_repository.load_facts(
                db,
                scope=scope,
                contract_kind=kind,
                contract_id=contract_id,
                party_id=party_id,
                project_id=project_id,
            )
            views.extend(project_deposit_facts(facts, today=business_today()))
        selected = [
            view
            for view in views
            if (
                view.status == status
                if status is not None
                else view.status != "settled"
            )
        ]
        selected.sort(key=lambda view: (view.contract_kind, view.contract_id, view.id))
        return DepositListResponse(
            items=selected[(page - 1) * page_size : page * page_size],
            total=len(selected),
            page=page,
            page_size=page_size,
        )


deposit_query_service = DepositQueryService()
