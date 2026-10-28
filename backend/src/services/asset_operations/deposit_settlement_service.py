"""Transaction-local deposit allocations bound to lifecycle previews."""

from datetime import date, timedelta
from decimal import Decimal
from typing import NotRequired, TypedDict
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception_handler import ResourceNotFoundError
from ...crud.asset_contract import asset_contract_repository
from ...crud.asset_ledger import asset_ledger_repository
from ...crud.asset_unit import asset_unit_repository
from ...crud.deposit_ledger import deposit_ledger_repository
from ...crud.deposit_queries import deposit_query_repository
from ...crud.deposit_settlements import deposit_settlement_repository
from ...models.asset_contract import (
    ContractLifecycleEvent,
    TerminalContract,
    UpstreamContract,
)
from ...models.asset_ledger import RentLedgerEntry
from ...schemas.asset_operations import TerminalContractTerminationProposal
from ...schemas.deposit_commands import DepositRecordRequest, DepositReversalRequest
from ..party_scope_resolver import EffectivePartyScope
from .business_change_service import contract_snapshot
from .deposit_query_service import active_deposit_events, deposit_query_service
from .rent_command_support import audit, scoped_contract
from .rent_errors import rent_error
from .rent_ledger_projections import effective_paid
from .rent_ledger_query_service import business_today
from .rent_obligation_service import rent_obligation_service


class OffsetCandidate(TypedDict):
    ledger_entry_id: str
    due_date: date
    remaining: Decimal
    period_start: NotRequired[date]
    period_end: NotRequired[date]
    contract_id: NotRequired[str]
    version: NotRequired[int]


class Offset(TypedDict):
    ledger_entry_id: str
    amount: Decimal


def choose_offsets(
    candidates: list[OffsetCandidate],
    balance: Decimal,
    mode: str,
    requested: list[Offset],
) -> list[Offset]:
    if mode not in {"auto", "none", "manual"} or (mode != "manual" and requested):
        raise rent_error(
            "DEPOSIT_OFFSET_NOT_ALLOWED", "抵扣方式与明细不一致", status=422
        )
    if mode == "none":
        return []
    available = {row["ledger_entry_id"]: row["remaining"] for row in candidates}
    result: list[Offset] = []
    if mode == "manual":
        seen: set[str] = set()
        for row in requested:
            key, amount = row["ledger_entry_id"], row["amount"]
            if (
                key in seen
                or key not in available
                or amount <= 0
                or amount > available[key]
            ):
                raise rent_error("DEPOSIT_OFFSET_TARGET_INVALID", "抵扣明细无效")
            seen.add(key)
            result.append(row)
    else:
        for candidate in sorted(
            candidates, key=lambda row: (row["due_date"], row["ledger_entry_id"])
        ):
            amount = min(balance, candidate["remaining"])
            if amount > 0:
                result.append(
                    {"ledger_entry_id": candidate["ledger_entry_id"], "amount": amount}
                )
                balance -= amount
        return result
    if sum((row["amount"] for row in result), Decimal(0)) > balance:
        raise rent_error("DEPOSIT_AMOUNT_EXCEEDS_REMAINING", "抵扣金额超过可用押金")
    return result


class DepositSettlementService:
    async def _visible_ancestors(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        scope: EffectivePartyScope,
    ) -> list[str]:
        contract = await scoped_contract(
            db, kind="terminal", contract_id=contract_id, scope=scope
        )
        if contract.renewed_from_id is None:
            return []
        facts = await deposit_query_repository.load_facts(
            db, scope=scope, contract_kind="terminal", contract_id=contract_id
        )
        by_id = {row.id: row for row in facts.contracts}
        active = active_deposit_events(facts.events)
        child = contract
        seen = {contract_id}
        ancestors = []
        while child.renewed_from_id is not None:
            parent_id = child.renewed_from_id
            if parent_id in seen or not any(
                event.contract_id == parent_id
                and event.event_type == "renewed"
                and event.successor_contract_id == child.id
                for event in active
            ):
                break
            parent = by_id.get(parent_id)
            if not isinstance(parent, TerminalContract):
                break
            if (
                await asset_contract_repository.get_terminal(
                    db, contract_id=parent_id, scope=scope
                )
                is None
            ):
                break
            ancestors.append(parent_id)
            seen.add(parent_id)
            child = parent
        return ancestors

    async def prelock(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        scope: EffectivePartyScope,
        proposal: TerminalContractTerminationProposal | None = None,
        event_id: str | None = None,
    ) -> None:
        targets = {contract_id}
        if proposal is not None and proposal.deposit_offset_mode == "auto":
            targets.update(
                await self._visible_ancestors(db, contract_id=contract_id, scope=scope)
            )
        offset_ids = (
            [row.ledger_entry_id for row in proposal.deposit_offsets]
            if proposal is not None
            else []
        )
        if event_id is not None:
            offset_ids.extend(
                row.offset_ledger_entry_id
                for row in await deposit_settlement_repository.event_deductions(
                    db, event_id=event_id
                )
                if row.offset_ledger_entry_id is not None
            )
        for offset_id in offset_ids:
            if offset_id == "clawback" or offset_id.startswith("generated:"):
                continue
            rent = await asset_ledger_repository.get_entry(db, entry_id=offset_id)
            if rent is None or rent.contract_kind != "terminal":
                raise ResourceNotFoundError("RentLedgerEntry", offset_id)
            targets.add(rent.contract_id)
        unit_ids: set[str] = set()
        for target in sorted(targets):
            await scoped_contract(db, kind="terminal", contract_id=target, scope=scope)
            coverages = await asset_contract_repository.list_terminal_coverages(
                db, contract_id=target
            )
            unit_ids.update(row.asset_unit_id for row in coverages)
        units = await asset_unit_repository.lock_for_write(
            db, unit_ids=sorted(unit_ids), scope=scope
        )
        if {unit.id for unit in units} != unit_ids:
            raise ResourceNotFoundError("TerminalContract", contract_id)
        for target in sorted(targets):
            if (
                await asset_contract_repository.get_terminal(
                    db, contract_id=target, scope=scope, for_update=True
                )
                is None
            ):
                raise ResourceNotFoundError("TerminalContract", target)

    async def preview(
        self,
        db: AsyncSession,
        *,
        contract: TerminalContract | UpstreamContract,
        scope: EffectivePartyScope,
        proposal: TerminalContractTerminationProposal | None = None,
    ) -> dict[str, object]:
        kind = "terminal" if isinstance(contract, TerminalContract) else "upstream"
        if (
            isinstance(contract, UpstreamContract)
            and contract.contract_type == "management_agreement"
        ):
            return {"applicable": False}
        entry = await deposit_ledger_repository.get_by_contract(
            db, contract_kind=kind, contract_id=contract.id
        )
        if entry is None:
            raise ResourceNotFoundError("DepositLedgerEntry", contract.id)
        view = await deposit_query_service.get(db, entry_id=entry.id, scope=scope)
        result: dict[str, object] = {
            "entry_id": entry.id,
            "version": view.version,
            "held_amount": str(view.held_amount),
            "offsets": [],
            "recoverable_amount": str(view.held_amount),
        }
        if proposal is None:
            return result
        if proposal.clawback_amount > 0 and (
            not isinstance(contract, TerminalContract)
            or contract.contract_mode != "sublease"
            or proposal.termination_type != "early"
            or proposal.clawback_basis.strip() == ""
        ):
            raise rent_error(
                "RENT_LEDGER_MANUAL_ENTRY_NOT_ALLOWED",
                "补收免租仅用于提前终止的转租合同，且须填写依据",
            )
        entries = await asset_ledger_repository.list_entries(
            db, contract_kind=kind, contract_id=contract.id
        )
        if (
            isinstance(contract, TerminalContract)
            and proposal.deposit_offset_mode in {"auto", "manual"}
            and contract.renewed_from_id is not None
        ):
            for parent_id in await self._visible_ancestors(
                db, contract_id=contract.id, scope=scope
            ):
                entries += await asset_ledger_repository.list_entries(
                    db, contract_kind="terminal", contract_id=parent_id
                )
        records = await asset_ledger_repository.list_records(
            db, entry_ids=tuple(row.id for row in entries)
        )
        plan = await rent_obligation_service.preview(
            db,
            contract_kind=kind,
            contract_id=contract.id,
            effective_end=proposal.effective_date - timedelta(days=1),
        )
        candidates: list[OffsetCandidate] = []
        today = business_today()
        for target in plan.created:
            if proposal.deposit_offset_mode == "manual" or target.period_start.replace(
                day=1
            ) <= today.replace(day=1):
                candidates.append(
                    {
                        "ledger_entry_id": f"generated:{target.period_start.isoformat()}",
                        "due_date": target.due_date,
                        "remaining": target.due_amount,
                        "period_start": target.period_start,
                        "period_end": target.period_end,
                        "contract_id": contract.id,
                    }
                )
        for row in entries:
            if (
                row.entry_type != "terminal_receivable"
                or (row.contract_id == contract.id and row.id in plan.voided)
                or row.voided_at is not None
            ):
                continue
            projected_target = plan.targets.get(row.period_start)
            due = (
                projected_target.due_amount
                if row.contract_id == contract.id
                and row.id in plan.updated
                and projected_target is not None
                else row.due_amount
            )
            remaining = due - effective_paid(
                [record for record in records if record.ledger_entry_id == row.id]
            )
            if remaining > 0 and (
                proposal.deposit_offset_mode == "manual"
                or row.period_start.replace(day=1) <= today.replace(day=1)
            ):
                candidates.append(
                    {
                        "ledger_entry_id": row.id,
                        "due_date": row.due_date,
                        "remaining": remaining,
                        "period_start": row.period_start,
                        "period_end": row.period_end,
                        "contract_id": row.contract_id,
                        "version": row.version,
                    }
                )
        if proposal.clawback_amount > 0 and (
            proposal.deposit_offset_mode == "manual"
            or proposal.effective_date.replace(day=1) <= today.replace(day=1)
        ):
            candidates.append(
                {
                    "ledger_entry_id": "clawback",
                    "due_date": proposal.effective_date,
                    "remaining": proposal.clawback_amount,
                    "period_start": proposal.effective_date,
                    "period_end": proposal.effective_date,
                    "contract_id": contract.id,
                }
            )
        offsets = choose_offsets(
            candidates,
            view.held_amount if entry.collector == "operator" else Decimal(0),
            proposal.deposit_offset_mode,
            [
                {"ledger_entry_id": row.ledger_entry_id, "amount": row.amount}
                for row in proposal.deposit_offsets
            ],
        )
        result.update(
            offsets=[
                {
                    "ledger_entry_id": row["ledger_entry_id"],
                    "amount": str(row["amount"]),
                }
                for row in offsets
            ],
            candidates=[
                {
                    "ledger_entry_id": row["ledger_entry_id"],
                    "remaining": str(row["remaining"]),
                    "period_start": row["period_start"].isoformat(),
                    "period_end": row["period_end"].isoformat(),
                    "contract_id": row["contract_id"],
                    "version": row.get("version"),
                }
                for row in candidates
            ],
            clawback_amount=str(proposal.clawback_amount),
            clawback_basis=proposal.clawback_basis,
            refundable_amount=str(
                view.held_amount - sum((row["amount"] for row in offsets), Decimal(0))
            ),
            additional_due_amount=str(
                max(
                    Decimal(0),
                    sum((row["remaining"] for row in candidates), Decimal(0))
                    - sum((row["amount"] for row in offsets), Decimal(0)),
                )
            ),
        )
        return result

    async def apply(
        self,
        db: AsyncSession,
        *,
        contract: TerminalContract,
        event: ContractLifecycleEvent,
        proposal: TerminalContractTerminationProposal,
        settlement: dict[str, object],
        actor_id: str,
        scope: EffectivePartyScope,
    ) -> None:
        from .deposit_command_service import deposit_command_service

        clawback_id: str | None = None
        if proposal.clawback_amount > 0:
            clawback_id = str(uuid4())
            await asset_ledger_repository.add_entry(
                db,
                entry=RentLedgerEntry(  # type: ignore[call-arg]
                    id=clawback_id,
                    entry_type="terminal_receivable",
                    contract_kind="terminal",
                    contract_id=contract.id,
                    period=event.effective_date.strftime("%Y-%m"),
                    period_start=event.effective_date,
                    period_end=event.effective_date,
                    due_date=event.effective_date,
                    due_amount=proposal.clawback_amount,
                    currency="CNY",
                    origin="clawback",
                    basis_note=proposal.clawback_basis,
                    locked_source={
                        "lifecycle_event_id": event.id,
                        "contract": contract_snapshot(contract),
                    },
                    version=1,
                ),
            )
            await audit(
                db,
                kind="terminal",
                contract_id=contract.id,
                action="rent_clawback_created",
                actor_id=actor_id,
                correlation_id=event.id,
                before={},
                after={
                    "entry_id": clawback_id,
                    "amount": str(proposal.clawback_amount),
                },
                reason=proposal.clawback_basis,
            )
            await db.flush()
        offsets = settlement.get("offsets", [])
        if not isinstance(offsets, list):
            raise ValueError("Invalid settlement allocations")
        for index, row in enumerate(offsets):
            if not isinstance(row, dict):
                raise ValueError("Invalid settlement allocation")
            entry_id = str(settlement["entry_id"])
            view = await deposit_query_service.get(db, entry_id=entry_id, scope=scope)
            target_id = (
                clawback_id
                if row["ledger_entry_id"] == "clawback"
                else str(row["ledger_entry_id"])
            )
            if target_id is not None and target_id.startswith("generated:"):
                period_start = date.fromisoformat(target_id.removeprefix("generated:"))
                entries = await asset_ledger_repository.list_entries(
                    db, contract_kind="terminal", contract_id=contract.id
                )
                resolved = next(
                    (
                        row
                        for row in entries
                        if row.origin == "generated"
                        and row.period_start == period_start
                        and row.voided_at is None
                    ),
                    None,
                )
                if resolved is None:
                    raise ResourceNotFoundError("RentLedgerEntry", target_id)
                target_id = resolved.id
            await deposit_command_service.register(
                db,
                entry_id=entry_id,
                request=DepositRecordRequest(
                    document_id=None,
                    record_type="deduct",
                    amount=Decimal(str(row["amount"])),
                    occurred_on=event.effective_date,
                    offset_ledger_entry_id=target_id,
                    expected_version=view.version,
                ),
                actor_id=actor_id,
                scope=scope,
                idempotency_key=f"termination:{event.id}:{index}",
                commit=False,
                lifecycle_event_id=event.id,
            )

    async def reverse(
        self,
        db: AsyncSession,
        *,
        event_id: str,
        actor_id: str,
        scope: EffectivePartyScope,
        reason: str,
    ) -> None:
        from .deposit_command_service import deposit_command_service

        for record in await deposit_settlement_repository.event_deductions(
            db, event_id=event_id
        ):
            if (
                await deposit_ledger_repository.find_reversal(db, record_id=record.id)
                is not None
            ):
                continue
            view = await deposit_query_service.get(
                db, entry_id=record.deposit_entry_id, scope=scope
            )
            await deposit_command_service.reverse(
                db,
                record_id=record.id,
                request=DepositReversalRequest(
                    reason=reason, expected_version=view.version
                ),
                actor_id=actor_id,
                scope=scope,
                idempotency_key=f"termination-reversal:{record.id}",
                commit=False,
            )


deposit_settlement_service = DepositSettlementService()
