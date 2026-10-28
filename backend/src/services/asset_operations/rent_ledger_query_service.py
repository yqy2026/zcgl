"""Build rent-ledger views from batched, current Party-scoped facts."""

from calendar import monthrange
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception_handler import PartyScopeForbiddenError, ResourceNotFoundError
from ...crud.rent_ledger_queries import (
    RentLedgerQueryRepository,
    RentQueryFacts,
    rent_ledger_query_repository,
)
from ...models.asset_contract import (
    ContractLifecycleEvent,
    ContractRentSchedule,
    TerminalContract,
    UpstreamContract,
)
from ...models.asset_ledger import RentLedgerEntry, RentPaymentRecord
from ...schemas.rent_queries import (
    RentContractRow,
    RentEntryView,
    RentMatrixView,
    RentMonthView,
    RentRecordView,
)
from ..party_scope_resolver import EffectivePartyScope
from .rent_ledger_projections import effective_paid, ledger_status
from .rent_obligation_rules import RentStage, generate_obligations


def business_today() -> date:
    return datetime.now(UTC).astimezone(ZoneInfo("Asia/Shanghai")).date()


def require_rent_scope(scope: EffectivePartyScope) -> None:
    if scope.scope_mode == "unrestricted":
        return
    axes = {
        "owner": scope.owner_party_ids,
        "manager": scope.manager_party_ids,
        "all": scope.effective_party_ids,
    }
    if scope.error_code is not None or not axes.get(scope.scope_mode):
        raise PartyScopeForbiddenError(code=scope.error_code or "PARTY_SCOPE_MISSING")


def effective_end(end_date: date, events: tuple[ContractLifecycleEvent, ...]) -> date:
    reversed_ids = {
        event.reversed_event_id for event in events if event.event_type == "reversed"
    }
    return min(
        [
            end_date,
            *[
                event.effective_date - timedelta(days=1)
                for event in events
                if event.event_type in {"terminated", "exited"}
                and event.id not in reversed_ids
            ],
        ]
    )


def stage_facts(schedules: tuple[ContractRentSchedule, ...]) -> list[RentStage]:
    return [
        RentStage(
            stage_start=row.stage_start,
            stage_end=row.stage_end,
            actual_monthly_rent=row.actual_monthly_rent,
            payment_cycle=row.payment_cycle,
            due_day=row.due_day,
            source_id=row.id,
        )
        for row in schedules
    ]


def project_entry(
    entry: RentLedgerEntry,
    records: tuple[RentPaymentRecord, ...],
    *,
    today: date,
    warnings: list[str] | None = None,
) -> RentEntryView:
    paid = effective_paid(records)
    fields = {
        name: getattr(entry, name)
        for name in (
            "id",
            "entry_type",
            "contract_kind",
            "contract_id",
            "period",
            "period_start",
            "period_end",
            "due_date",
            "due_amount",
            "currency",
            "origin",
            "basis_note",
            "locked_source",
            "voided_at",
            "version",
        )
    }
    return RentEntryView.model_validate(
        {
            **fields,
            "effective_paid_amount": paid,
            "remaining_amount": max(entry.due_amount - paid, Decimal("0")),
            "status": ledger_status(
                due_amount=entry.due_amount,
                paid_amount=paid,
                due_date=entry.due_date,
                period_start=entry.period_start,
                voided=entry.voided_at is not None,
                today=today,
            ),
            "warnings": warnings or [],
            "records": [RentRecordView.model_validate(row) for row in records],
        }
    )


class RentLedgerQueryService:
    def __init__(
        self, *, repository: RentLedgerQueryRepository = rent_ledger_query_repository
    ) -> None:
        self.repository = repository

    async def contract_summary(
        self,
        db: AsyncSession,
        *,
        contract: UpstreamContract | TerminalContract,
        contract_kind: str,
        schedules: tuple[ContractRentSchedule, ...],
        events: tuple[ContractLifecycleEvent, ...],
        today: date,
    ) -> dict[str, object]:
        if (
            isinstance(contract, UpstreamContract)
            and contract.contract_type == "management_agreement"
        ):
            return {}
        entries, records = await self.repository.contract_entries(
            db, contract_kind=contract_kind, contract_id=contract.id
        )
        facts = RentQueryFacts((contract,), entries, records, schedules, events)
        views, warnings = self._views(facts, today=today)
        active = [row for row in views.values() if row.status != "void"]
        month = today.strftime("%Y-%m")
        current = [row for row in active if row.period == month]
        pending = [row for row in active if row.remaining_amount > 0]
        return {
            "current_period": month,
            "due_amount_this_month": sum(
                (row.due_amount for row in current), Decimal("0")
            ),
            "paid_amount_this_month": sum(
                (row.effective_paid_amount for row in current), Decimal("0")
            ),
            "remaining_amount_this_month": sum(
                (row.remaining_amount for row in current), Decimal("0")
            ),
            "total_remaining_amount": sum(
                (row.remaining_amount for row in active), Decimal("0")
            ),
            "paid_period_count": len([row for row in active if row.status == "paid"]),
            "period_count": len(active),
            "next_due_date": min((row.due_date for row in pending), default=None),
            "warnings": warnings[contract.id],
            "entries": [row.model_dump(mode="json") for row in views.values()],
        }

    @staticmethod
    def _views(
        facts: RentQueryFacts, *, today: date
    ) -> tuple[dict[str, RentEntryView], dict[str, list[str]]]:
        records: dict[str, list[RentPaymentRecord]] = defaultdict(list)
        for record in facts.records:
            records[record.ledger_entry_id].append(record)
        views: dict[str, RentEntryView] = {}
        warnings: dict[str, list[str]] = defaultdict(list)
        for contract in facts.contracts:
            schedules = tuple(
                row for row in facts.schedules if row.contract_id == contract.id
            )
            events = tuple(
                row for row in facts.events if row.contract_id == contract.id
            )
            end = effective_end(contract.end_date, events)
            targets, gaps = generate_obligations(
                start_date=contract.start_date,
                end_date=end,
                stages=stage_facts(schedules),
            )
            if gaps:
                warnings[contract.id].append("RENT_SCHEDULE_GAP")
            by_start = {target.period_start: target for target in targets}
            for entry in facts.entries:
                if entry.contract_id != contract.id:
                    continue
                entry_records = tuple(records[entry.id])
                issues: list[str] = []
                target = by_start.get(entry.period_start)
                if (
                    entry.origin == "generated"
                    and effective_paid(entry_records) > 0
                    and (
                        target is None
                        or target.due_amount != entry.due_amount
                        or target.period_end != entry.period_end
                        or target.due_date != entry.due_date
                    )
                ):
                    issues.append("RENT_LEDGER_PLAN_MISMATCH")
                    if "RENT_LEDGER_PLAN_MISMATCH" not in warnings[contract.id]:
                        warnings[contract.id].append("RENT_LEDGER_PLAN_MISMATCH")
                views[entry.id] = project_entry(
                    entry, entry_records, today=today, warnings=issues
                )
        return views, warnings

    async def matrix(
        self,
        db: AsyncSession,
        *,
        scope: EffectivePartyScope,
        ledger_type: str,
        year: int,
        today: date | None = None,
    ) -> RentMatrixView:
        require_rent_scope(scope)
        current = today or business_today()
        facts = await self.repository.matrix_facts(
            db, scope=scope, ledger_type=ledger_type, year=year
        )
        views, warnings = self._views(facts, today=current)
        rows: list[RentContractRow] = []
        for contract in facts.contracts:
            contract_views = [
                views[entry.id]
                for entry in facts.entries
                if entry.contract_id == contract.id
            ]
            end = effective_end(
                contract.end_date,
                tuple(row for row in facts.events if row.contract_id == contract.id),
            )
            schedules = tuple(
                row for row in facts.schedules if row.contract_id == contract.id
            )
            months: list[RentMonthView] = []
            for month in range(1, 13):
                first, last = (
                    date(year, month, 1),
                    date(year, month, monthrange(year, month)[1]),
                )
                entries = [
                    entry
                    for entry in contract_views
                    if entry.period == f"{year:04d}-{month:02d}"
                ]
                active = [entry for entry in entries if entry.status != "void"]
                label = None
                if not active:
                    stages = [
                        row
                        for row in schedules
                        if row.stage_start <= min(last, end)
                        and row.stage_end >= max(first, contract.start_date)
                    ]
                    if last < contract.start_date or first > end:
                        label = "不在租期"
                    elif not stages:
                        label = "租金阶段缺口"
                    elif all(row.actual_monthly_rent == 0 for row in stages):
                        label = "免租"
                    elif any(row.payment_cycle == "custom" for row in stages):
                        label = "待手工登记"
                    else:
                        label = "非付款月"
                months.append(
                    RentMonthView(
                        month=month,
                        entries=entries,
                        due_amount=sum(
                            (entry.due_amount for entry in active), Decimal("0")
                        ),
                        paid_amount=sum(
                            (entry.effective_paid_amount for entry in active),
                            Decimal("0"),
                        ),
                        remaining_amount=sum(
                            (entry.remaining_amount for entry in active), Decimal("0")
                        ),
                        label=label,
                    )
                )
            rows.append(
                RentContractRow(
                    contract_kind="upstream"
                    if ledger_type == "upstream_rent"
                    else "terminal",
                    contract_id=contract.id,
                    contract_number=contract.contract_number,
                    contract_name=getattr(contract, "name", contract.contract_number),
                    months=months,
                    warnings=warnings[contract.id],
                    total_due_amount=sum(
                        (month.due_amount for month in months), Decimal("0")
                    ),
                    total_paid_amount=sum(
                        (month.paid_amount for month in months), Decimal("0")
                    ),
                    total_remaining_amount=sum(
                        (month.remaining_amount for month in months), Decimal("0")
                    ),
                )
            )
        return RentMatrixView(
            ledger_type=ledger_type,
            year=year,
            current_month=current.month,
            rows=rows,
            total_due_amount=sum((row.total_due_amount for row in rows), Decimal("0")),
            total_paid_amount=sum(
                (row.total_paid_amount for row in rows), Decimal("0")
            ),
            total_remaining_amount=sum(
                (row.total_remaining_amount for row in rows), Decimal("0")
            ),
        )

    async def detail(
        self, db: AsyncSession, *, scope: EffectivePartyScope, entry_id: str
    ) -> RentEntryView:
        require_rent_scope(scope)
        facts = await self.repository.detail_facts(db, scope=scope, entry_id=entry_id)
        if facts is None:
            raise ResourceNotFoundError("RentLedgerEntry", entry_id)
        views, _ = self._views(facts, today=business_today())
        return views[entry_id]

    async def unpaid_contract_ids(self, db: AsyncSession, *, today: date) -> set[str]:
        entries, records = await self.repository.terminal_outstanding_facts(
            db, today=today
        )
        records_by_entry: dict[str, list[RentPaymentRecord]] = defaultdict(list)
        for record in records:
            records_by_entry[record.ledger_entry_id].append(record)
        period = today.strftime("%Y-%m")
        return {
            entry.contract_id
            for entry in entries
            if (entry.entry_type != "owner_receipt_expected" or entry.period < period)
            and entry.due_amount > effective_paid(records_by_entry[entry.id])
        }


rent_ledger_query_service = RentLedgerQueryService()
