"""Transaction-local reconciliation of generated rent obligations."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception_handler import ResourceNotFoundError
from ...crud.asset_ledger import AssetLedgerRepository, asset_ledger_repository
from ...crud.management_fee_statement import management_fee_statement_repository
from ...models.asset_contract import (
    ContractLifecycleEvent,
    ContractRentSchedule,
    TerminalContract,
    UpstreamContract,
)
from ...models.asset_ledger import RentLedgerEntry
from .business_change_service import contract_snapshot, record_contract_change
from .management_fee_entry_service import management_fee_entry_service
from .rent_ledger_projections import effective_paid
from .rent_obligation_rules import ObligationTarget, RentStage, generate_obligations


@dataclass
class RentObligationPlan:
    created: list[ObligationTarget] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    voided: list[str] = field(default_factory=list)
    restored: list[str] = field(default_factory=list)
    mismatched: list[str] = field(default_factory=list)
    gaps: list[tuple[date, date]] = field(default_factory=list)
    targets: dict[date, ObligationTarget] = field(default_factory=dict)

    @property
    def warnings(self) -> list[str]:
        warnings = []
        if self.gaps:
            warnings.append("RENT_SCHEDULE_GAP")
        if self.mismatched:
            warnings.append("RENT_LEDGER_PLAN_MISMATCH")
        return warnings

    def summary(self) -> dict[str, object]:
        return {
            "created_count": len(self.created),
            "updated_count": len(self.updated),
            "voided_count": len(self.voided),
            "restored_count": len(self.restored),
            "mismatched_entry_ids": self.mismatched,
            "warnings": self.warnings,
        }


def active_closures(
    events: Sequence[ContractLifecycleEvent],
) -> list[ContractLifecycleEvent]:
    reversed_ids = {
        event.reversed_event_id for event in events if event.event_type == "reversed"
    }
    return [
        event
        for event in events
        if event.event_type in {"terminated", "exited"} and event.id not in reversed_ids
    ]


def contract_entry_type(contract: UpstreamContract | TerminalContract) -> str | None:
    if isinstance(contract, UpstreamContract):
        return "upstream_payable" if contract.contract_type == "lease" else None
    return (
        "terminal_receivable"
        if contract.contract_mode == "sublease"
        else "owner_receipt_expected"
    )


def rent_stages(schedules: Sequence[ContractRentSchedule]) -> list[RentStage]:
    return [
        RentStage(
            row.stage_start,
            row.stage_end,
            row.actual_monthly_rent,
            row.payment_cycle,
            row.due_day,
            row.id,
        )
        for row in schedules
    ]


def target_differs(entry: RentLedgerEntry, target: ObligationTarget) -> bool:
    return (
        entry.period_end != target.period_end
        or entry.due_date != target.due_date
        or entry.due_amount != target.due_amount
    )


class RentObligationService:
    def __init__(self, *, repository: AssetLedgerRepository | None = None) -> None:
        self.repository = repository or asset_ledger_repository

    async def fingerprint(
        self, db: AsyncSession, *, contract_kind: str, contract_id: str
    ) -> str:
        entries = await self.repository.list_entries(
            db, contract_kind=contract_kind, contract_id=contract_id
        )
        records = await self.repository.list_records(
            db, entry_ids=[entry.id for entry in entries]
        )
        data = {
            "entries": sorted((entry.id, entry.version) for entry in entries),
            "records": sorted(
                (record.id, record.reverses_record_id) for record in records
            ),
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    async def preview(
        self,
        db: AsyncSession,
        *,
        contract_kind: str,
        contract_id: str,
        effective_end: date | None = None,
        schedules: Sequence[ContractRentSchedule] | None = None,
        replan_from: date | None = None,
        supplemental_ranges: Sequence[tuple[date, date]] = (),
        period_starts: Sequence[date] | None = None,
    ) -> RentObligationPlan:
        (
            contract,
            existing_schedules,
            events,
        ) = await self.repository.load_contract_facts(
            db, contract_kind=contract_kind, contract_id=contract_id
        )
        if contract is None:
            raise ResourceNotFoundError("Contract", contract_id)
        entries = await self.repository.list_entries(
            db, contract_kind=contract_kind, contract_id=contract_id
        )
        records = await self.repository.list_records(
            db, entry_ids=[entry.id for entry in entries]
        )
        target_end = effective_end
        if target_end is None:
            target_end = min(
                [
                    contract.end_date,
                    *(
                        event.effective_date - timedelta(days=1)
                        for event in active_closures(events)
                    ),
                ]
            )
        target_end = min(contract.end_date, target_end)
        generated: list[ObligationTarget]
        gaps: list[tuple[date, date]]
        if contract_entry_type(contract) is None:
            generated, gaps = [], []
        else:
            generated, gaps = generate_obligations(
                start_date=contract.start_date,
                end_date=target_end,
                stages=rent_stages(
                    existing_schedules if schedules is None else schedules
                ),
            )
        locked = [
            entry
            for entry in entries
            if effective_paid(
                [record for record in records if record.ledger_entry_id == entry.id]
            )
            > 0
        ]
        overlap_ids: set[str] = set()
        eligible: list[ObligationTarget] = []
        for candidate in generated:
            overlapping = [
                entry
                for entry in locked
                if entry.period_start != candidate.period_start
                and entry.period_start <= candidate.period_end
                and entry.period_end >= candidate.period_start
            ]
            if overlapping:
                overlap_ids.update(entry.id for entry in overlapping)
            else:
                eligible.append(candidate)
        generated = eligible
        source: dict[str, object] = {
            "contract": contract_snapshot(contract),
            "rent_schedules": [
                contract_snapshot(row)
                for row in (existing_schedules if schedules is None else schedules)
            ],
        }
        plan = RentObligationPlan(
            gaps=gaps, targets={target.period_start: target for target in generated}
        )
        existing = {
            entry.period_start: entry
            for entry in entries
            if entry.origin == "generated"
        }
        cancelled_ids = {
            event.reversed_event_id
            for event in events
            if event.event_type == "reversed"
        }
        closed = active_closures(events)
        cutoff = min((event.effective_date for event in closed), default=None)
        active_early_ids = {
            event.id for event in closed if event.termination_type == "early"
        }

        def affected(start: date, end: date) -> bool:
            if period_starts is not None:
                return start in period_starts
            return (
                replan_from is None
                or start >= replan_from
                or any(
                    start <= right and end >= left
                    for left, right in supplemental_ranges
                )
            )

        for candidate in generated:
            if candidate.period_start not in existing and affected(
                candidate.period_start, candidate.period_end
            ):
                plan.created.append(candidate)
        for entry in entries:
            if not affected(entry.period_start, entry.period_end):
                continue
            paid = effective_paid(
                [record for record in records if record.ledger_entry_id == entry.id]
            )
            if entry.origin == "generated":
                target = plan.targets.get(entry.period_start)
                differs = (
                    target is None
                    or target_differs(entry, target)
                    or entry.voided_at is not None
                )
                if paid > 0:
                    if differs:
                        plan.mismatched.append(entry.id)
                elif target is None:
                    if entry.voided_at is None:
                        plan.voided.append(entry.id)
                elif entry.voided_at is not None:
                    plan.restored.append(entry.id)
                elif target_differs(entry, target) or entry.locked_source != source:
                    plan.updated.append(entry.id)
            elif entry.origin == "manual":
                if (
                    cutoff is not None
                    and entry.period_start >= cutoff
                    and entry.voided_at is None
                ):
                    if paid > 0:
                        plan.mismatched.append(entry.id)
                    else:
                        plan.voided.append(entry.id)
                elif (
                    cutoff is None
                    and entry.voided_at is not None
                    and entry.void_correlation_id in cancelled_ids
                    and paid == 0
                ):
                    plan.restored.append(entry.id)
            elif (
                entry.origin == "clawback"
                and entry.locked_source.get("lifecycle_event_id")
                not in active_early_ids
                and entry.voided_at is None
            ):
                if paid > 0:
                    plan.mismatched.append(entry.id)
                else:
                    plan.voided.append(entry.id)
        plan.mismatched = sorted(set(plan.mismatched) | overlap_ids)
        return plan

    async def replan(
        self,
        db: AsyncSession,
        *,
        contract_kind: str,
        contract_id: str,
        actor_id: str,
        correlation_id: str,
        effective_end: date | None = None,
        schedules: Sequence[ContractRentSchedule] | None = None,
        replan_from: date | None = None,
        supplemental_ranges: Sequence[tuple[date, date]] = (),
        period_starts: Sequence[date] | None = None,
    ) -> RentObligationPlan:
        entries = await self.repository.list_entries(
            db, contract_kind=contract_kind, contract_id=contract_id, for_update=True
        )
        (
            contract,
            existing_schedules,
            events,
        ) = await self.repository.load_contract_facts(
            db, contract_kind=contract_kind, contract_id=contract_id
        )
        if contract is None:
            raise ResourceNotFoundError("Contract", contract_id)
        plan = await self.preview(
            db,
            contract_kind=contract_kind,
            contract_id=contract_id,
            effective_end=effective_end,
            schedules=schedules,
            replan_from=replan_from,
            supplemental_ranges=supplemental_ranges,
            period_starts=period_starts,
        )
        source_schedules = existing_schedules if schedules is None else schedules
        now = datetime.now(UTC)
        source: dict[str, object] = {
            "contract": contract_snapshot(contract),
            "rent_schedules": [contract_snapshot(row) for row in source_schedules],
        }
        entry_type = contract_entry_type(contract)
        for target in plan.created:
            await self.repository.add_entry(
                db,
                entry=RentLedgerEntry(  # type: ignore[call-arg]
                    id=str(uuid4()),
                    entry_type=entry_type,
                    contract_kind=contract_kind,
                    contract_id=contract_id,
                    period=target.period,
                    period_start=target.period_start,
                    period_end=target.period_end,
                    due_date=target.due_date,
                    due_amount=target.due_amount,
                    currency="CNY",
                    origin="generated",
                    locked_source=source,
                    version=1,
                ),
            )
        by_id = {entry.id: entry for entry in entries}
        for entry_id in [*plan.updated, *plan.restored]:
            entry = by_id[entry_id]
            if entry.origin == "generated":
                target = plan.targets[entry.period_start]
                entry.period = target.period
                entry.period_end, entry.due_date, entry.due_amount = (
                    target.period_end,
                    target.due_date,
                    target.due_amount,
                )
                entry.locked_source = source
            entry.voided_at = None
            entry.void_correlation_id = None
        for entry_id in plan.voided:
            entry = by_id[entry_id]
            entry.voided_at = now
            entry.void_correlation_id = correlation_id
        changed_ids = [*plan.updated, *plan.restored, *plan.voided]
        if entry_type == "owner_receipt_expected" and (plan.created or changed_ids):
            owner_party_id = await management_fee_statement_repository.bound_owner(
                db, terminal_contract_id=contract_id
            )
            if owner_party_id is not None:
                await management_fee_entry_service.reconcile(
                    db,
                    owner_party_id=owner_party_id,
                    new_periods=tuple(
                        sorted(
                            {target.period for target in plan.created}
                            | {
                                by_id[entry_id].period
                                for entry_id in [*plan.updated, *plan.restored]
                            }
                        )
                    ),
                    changed_periods=tuple(
                        sorted({by_id[entry_id].period for entry_id in changed_ids})
                    ),
                )
        await record_contract_change(
            db,
            contract=contract,
            contract_kind=contract_kind,
            action="rent_obligations_replanned",
            actor_id=actor_id,
            after=plan.summary(),
            correlation_id=correlation_id,
        )
        await db.flush()
        return plan


rent_obligation_service = RentObligationService()
