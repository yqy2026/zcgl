"""Stateless monthly workbench aggregation (本月).

The prototype's monthly task list is derived, never stored: pending
payments, uncollected rent, management-fee reconciliation states and the
occupancy-report gate are recomputed from the single source of truth on
every read. Overdue lines from earlier months surface naturally with
their overdue-day counts, which is the carry-over the v5 spec asks for.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Callable
from datetime import date, timedelta
from decimal import Decimal
from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception_handler import ResourceNotFoundError
from ...crud.asset_contract import asset_contract_repository
from ...crud.deposit_queries import deposit_query_repository
from ...crud.management_fee_matrix import management_fee_matrix_repository
from ...crud.party import CRUDParty
from ...crud.rent_ledger_queries import (
    RentQueryFacts,
    rent_ledger_query_repository,
)
from ...models.asset_contract import (
    ContractLifecycleEvent,
    TerminalContract,
    UpstreamContract,
    UpstreamContractAssetUnit,
)
from ...schemas.monthly_workbench import (
    MonthlyWorkbenchView,
    WorkbenchArchiveGapItem,
    WorkbenchDepositItem,
    WorkbenchExpiredUpstreamItem,
    WorkbenchExpiringUpstreamItem,
    WorkbenchManagementFeeCard,
    WorkbenchManagementFeeItem,
    WorkbenchMoneyCard,
    WorkbenchMoneyTask,
    WorkbenchOccupancyReportCard,
    WorkbenchPendingScopeUnit,
    WorkbenchProgress,
)
from ..party_scope_resolver import EffectivePartyScope
from .archive_matrix_service import archive_matrix_service
from .contract_projections import derive_upstream_contract_status
from .deposit_query_service import project_deposit_facts
from .errors import (
    AssessmentScopeOperatorForbiddenError,
    OccupancyReportAlreadySubmittedError,
    OccupancyReportPeriodInvalidError,
    OccupancyReportScopeMissingError,
)
from .management_fee_query_service import management_fee_query_service
from .occupancy_report_draft_service import occupancy_report_draft_service
from .query_service import asset_operations_query_service
from .rent_ledger_query_service import business_today, rent_ledger_query_service

_MONTH_PATTERN = re.compile(r"^[0-9]{4}-(0[1-9]|1[0-2])$")
_PARTY_CRUD = CRUDParty()


def _previous_month(month: str) -> str:
    year, mon = int(month[:4]), int(month[5:7])
    if mon == 1:
        return f"{year - 1:04d}-12"
    return f"{year:04d}-{mon - 1:02d}"


def _month_bounds(month: str) -> tuple[date, date]:
    year, mon = int(month[:4]), int(month[5:7])
    start = date(year, mon, 1)
    end = (
        date(year, 12, 31) if mon == 12 else date(year, mon + 1, 1) - timedelta(days=1)
    )
    return start, end


def _effective_terminal_end(
    terminal: TerminalContract,
    events: tuple[ContractLifecycleEvent, ...],
) -> date:
    reversed_ids = {
        event.reversed_event_id for event in events if event.event_type == "reversed"
    }
    ends = [
        event.effective_date - timedelta(days=1)
        for event in events
        if event.event_type in {"terminated", "exited"} and event.id not in reversed_ids
    ]
    return min([terminal.end_date, *ends])


def _merge_facts(
    batches: tuple[RentQueryFacts, ...],
) -> RentQueryFacts:
    """Union per-year facts, deduplicating every identity by id.

    Contracts, schedules and events are year-independent in the
    repository reads, so a naive concatenation would duplicate rent
    stages and double-generate obligations; identities dedupe by id.
    """
    from typing import Any

    contracts: dict[str, UpstreamContract | TerminalContract] = {}
    entries: dict[str, Any] = {}
    records: dict[str, Any] = {}
    schedules: dict[str, Any] = {}
    events: dict[str, Any] = {}
    for facts in batches:
        for contract in facts.contracts:
            contracts[contract.id] = contract
        for entry_row in facts.entries:
            entries[entry_row.id] = entry_row
        for record_row in facts.records:
            records[record_row.id] = record_row
        for schedule_row in facts.schedules:
            schedules[schedule_row.id] = schedule_row
        for event_row in facts.events:
            events[event_row.id] = event_row
    return RentQueryFacts(
        tuple(contracts.values()),
        tuple(entries.values()),
        tuple(records.values()),
        tuple(schedules.values()),
        tuple(events.values()),
    )


class MonthlyWorkbenchService:
    """Compose the four deadline cards plus the anytime list."""

    def __init__(self, *, business_today_fn: Callable[[], date] = business_today):
        self._business_today = business_today_fn

    async def overview(
        self,
        db: AsyncSession,
        *,
        scope: EffectivePartyScope,
        operator_party_id: str,
        actor_id: str,
        month: str | None = None,
    ) -> MonthlyWorkbenchView:
        today = self._business_today()
        resolved = month or today.strftime("%Y-%m")
        if not _MONTH_PATTERN.match(resolved):
            raise OccupancyReportPeriodInvalidError(
                period=resolved, reason="统计月必须是 YYYY-MM"
            )
        year = int(resolved[:4])
        _, month_end = _month_bounds(resolved)
        is_current_month = resolved == today.strftime("%Y-%m")
        days_left = max((month_end - today).days, 0) if is_current_month else 0

        upstreams, _ = await asset_contract_repository.list_upstream(
            db, scope=scope, offset=0, limit=500
        )
        upstream_events = (
            await asset_contract_repository.list_lifecycle_events_by_contract_ids(
                db,
                contract_kind="upstream",
                contract_ids=tuple(sorted(c.id for c in upstreams)),
            )
        )
        events_by_upstream: dict[str, tuple[ContractLifecycleEvent, ...]] = defaultdict(
            tuple
        )
        grouped: dict[str, list[ContractLifecycleEvent]] = defaultdict(list)
        for event in upstream_events:
            grouped[event.contract_id].append(event)
        events_by_upstream = {key: tuple(value) for key, value in grouped.items()}

        rent_facts = _merge_facts(
            tuple(
                [
                    await rent_ledger_query_repository.matrix_facts(
                        db, scope=scope, ledger_type="upstream_rent", year=fetch_year
                    )
                    for fetch_year in (year - 1, year)
                ]
            )
        )
        terminal_facts = _merge_facts(
            tuple(
                [
                    await rent_ledger_query_repository.matrix_facts(
                        db, scope=scope, ledger_type="terminal_rent", year=fetch_year
                    )
                    for fetch_year in (year - 1, year)
                ]
            )
        )
        party_ids = {contract.owner_party_id for contract in upstreams}
        party_ids.update(
            contract.tenant_party_id
            for contract in terminal_facts.contracts
            if isinstance(contract, TerminalContract)
        )
        party_names = await _PARTY_CRUD.get_party_names_by_ids(
            db, party_ids=tuple(sorted(party_ids))
        )

        rent_payments = self._money_card(
            facts=rent_facts,
            ledger_type="upstream_rent",
            month=resolved,
            today=today,
            party_names=party_names,
            unit_labels={},
        )
        operator_ids = tuple(
            contract.id
            for contract in terminal_facts.contracts
            if isinstance(contract, TerminalContract)
            and contract.rent_collector == "operator"
        )
        terminal_unit_labels = (
            await asset_contract_repository.list_terminal_unit_labels(
                db, contract_ids=operator_ids
            )
            if operator_ids
            else {}
        )
        rent_collections = self._money_card(
            facts=terminal_facts,
            ledger_type="terminal_rent",
            month=resolved,
            today=today,
            party_names=party_names,
            unit_labels=terminal_unit_labels,
        )
        management_fees = await self._management_fee_card(
            db,
            scope=scope,
            month=resolved,
            today=today,
            party_names=party_names,
            upstreams=upstreams,
            events_by_upstream=events_by_upstream,
        )
        occupancy = await self._occupancy_card(
            db,
            scope=scope,
            operator_party_id=operator_party_id,
            actor_id=actor_id,
            month=resolved,
        )
        expired, expiring = self._upstream_watchlists(
            upstreams=upstreams,
            events_by_upstream=events_by_upstream,
            today=today,
        )
        coverage_counts = await self._upstream_terminal_facts(
            db, expired + expiring, today=today
        )
        expired_items = [
            WorkbenchExpiredUpstreamItem(
                contract_id=contract.id,
                contract_number=contract.contract_number,
                name=contract.name or contract.contract_number,
                contract_type=contract.contract_type,  # type: ignore[arg-type]
                end_date=contract.end_date,
                days_past=(today - contract.end_date).days,
                unit_count=coverage_counts[contract.id]["unit_count"],
                active_terminal_count=coverage_counts[contract.id][
                    "active_terminal_count"
                ],
                has_pending_renewal=has_renewal,
            )
            for contract, has_renewal in expired
        ]
        expiring_items = [
            WorkbenchExpiringUpstreamItem(
                contract_id=contract.id,
                contract_number=contract.contract_number,
                name=contract.name or contract.contract_number,
                contract_type=contract.contract_type,  # type: ignore[arg-type]
                owner_party_name=party_names.get(contract.owner_party_id, ""),
                end_date=contract.end_date,
                days_left=(contract.end_date - today).days,
                overrun_terminal_count=coverage_counts[contract.id][
                    "overrun_terminal_count"
                ],
            )
            for contract, _ in expiring
        ]

        completion = await archive_matrix_service.completion(db, scope=scope)
        archive_gaps = [
            WorkbenchArchiveGapItem(
                document_type=category.document_type,
                label=category.label,
                missing=category.missing or 0,
            )
            for category in completion.categories
            if category.supported and category.required and (category.missing or 0) > 0
        ]
        deposits = await self._pending_deposits(db, scope=scope)
        pending_scope_units = await self._pending_scope_units(
            db,
            scope=scope,
            operator_party_id=operator_party_id,
            actor_id=actor_id,
            year=year,
        )

        fee_undone = len(
            [item for item in management_fees.items if item.status != "confirmed"]
        )
        progress = WorkbenchProgress(
            total=(
                rent_payments.pending_count
                + rent_collections.pending_count
                + fee_undone
                + 1
            ),
            done=(
                rent_payments.done_count
                + rent_collections.done_count
                + (len(management_fees.items) - fee_undone)
                + (1 if occupancy.status == "submitted" else 0)
            ),
        )
        return MonthlyWorkbenchView(
            month=resolved,
            today=today,
            days_left_in_month=days_left,
            progress=progress,
            rent_payments=rent_payments,
            rent_collections=rent_collections,
            management_fees=management_fees,
            occupancy_report=occupancy,
            expired_upstream=expired_items,
            expiring_upstream=expiring_items,
            archive_gaps=archive_gaps,
            unlinked_unit_count=completion.unlinked_unit_count,
            deposits_pending=deposits,
            pending_scope_units=pending_scope_units,
        )

    # ---- deadline cards -------------------------------------------------

    def _money_card(
        self,
        *,
        facts: RentQueryFacts,
        ledger_type: str,
        month: str,
        today: date,
        party_names: dict[str, str],
        unit_labels: dict[str, tuple[str, ...]],
    ) -> WorkbenchMoneyCard:
        views, _ = rent_ledger_query_service._views(facts, today=today)
        contracts_by_id = {contract.id: contract for contract in facts.contracts}
        is_upstream = ledger_type == "upstream_rent"
        if is_upstream:
            involved_ids = set(contracts_by_id)
        else:
            involved_ids = {
                contract.id
                for contract in facts.contracts
                if isinstance(contract, TerminalContract)
                and contract.rent_collector == "operator"
            }

        items: list[WorkbenchMoneyTask] = []
        done_count = 0
        done_amount = Decimal("0")
        pending_amount = Decimal("0")
        for entry_id, view in views.items():
            if view.contract_id not in involved_ids:
                continue
            contract = contracts_by_id[view.contract_id]
            if view.status == "void":
                continue
            if view.period == month and view.status == "paid":
                done_count += 1
                done_amount += view.effective_paid_amount
                continue
            if view.remaining_amount <= 0 or view.period > month:
                continue
            if is_upstream:
                counterparty = party_names.get(
                    cast(UpstreamContract, contract).owner_party_id, ""
                )
            else:
                counterparty = party_names.get(
                    cast(TerminalContract, contract).tenant_party_id, ""
                )
            labels = unit_labels.get(contract.id, ())
            items.append(
                WorkbenchMoneyTask(
                    contract_kind="upstream" if is_upstream else "terminal",
                    contract_id=contract.id,
                    contract_number=contract.contract_number,
                    contract_name=(
                        cast(UpstreamContract, contract).name
                        if is_upstream
                        else cast(TerminalContract, contract).contract_number
                    ),
                    counterparty_name=counterparty,
                    unit_label=(
                        labels[0]
                        if len(labels) == 1
                        else f"{labels[0]} 等 {len(labels)} 个单元"
                        if labels
                        else None
                    ),
                    period=view.period,
                    ledger_entry_id=entry_id,
                    due_amount=view.due_amount,
                    paid_amount=view.effective_paid_amount,
                    remaining_amount=view.remaining_amount,
                    due_date=view.due_date,
                    days_overdue=max((today - view.due_date).days, 0),
                    status=view.status,  # type: ignore[arg-type]
                    record_type_hint="payment" if is_upstream else "receipt",
                )
            )
            pending_amount += view.remaining_amount
        items.sort(key=lambda t: (-t.days_overdue, t.due_date, t.contract_number))
        subtitle = (
            "月付 25 日前 · 季付 15 日前"
            if ledger_type == "upstream_rent"
            else "转租单元 · 本公司收取"
        )
        return WorkbenchMoneyCard(
            period=month,
            subtitle=subtitle,
            pending_count=len(items),
            pending_amount=pending_amount,
            done_count=done_count,
            done_amount=done_amount,
            items=items,
        )

    async def _management_fee_card(
        self,
        db: AsyncSession,
        *,
        scope: EffectivePartyScope,
        month: str,
        today: date,
        party_names: dict[str, str],
        upstreams: list[UpstreamContract],
        events_by_upstream: dict[str, tuple[ContractLifecycleEvent, ...]],
    ) -> WorkbenchManagementFeeCard:
        prev = _previous_month(month)
        _, prev_end = _month_bounds(prev)
        facts = await management_fee_matrix_repository.list_year(
            db, scope=scope, year=int(prev[:4])
        )
        statements = tuple(row for row, _ in facts if row.period == prev)
        owner_names = {statement.owner_party_id: name for statement, name in facts}
        details = (
            await management_fee_query_service.details(
                db, statements=statements, scope=scope
            )
            if statements
            else {}
        )
        items_by_owner: dict[str, WorkbenchManagementFeeItem] = {}
        covered_upstream_ids: set[str] = set()
        for statement in statements:
            detail = details[statement.id]
            current_lines = [
                line for line in detail.snapshot_lines if line.line_kind == "current"
            ]
            status = detail.status or statement.status or "collecting"
            if status == "superseded":
                continue
            covered_upstream_ids.update(statement.upstream_contract_ids or [])
            items_by_owner[statement.owner_party_id] = WorkbenchManagementFeeItem(
                owner_party_id=statement.owner_party_id,
                owner_party_name=owner_names.get(
                    statement.owner_party_id,
                    party_names.get(statement.owner_party_id, ""),
                ),
                statement_id=statement.id,
                statement_number=statement.statement_number,
                status=status,  # type: ignore[arg-type]
                base_amount=statement.base_amount,
                fee_amount=detail.fee_amount,
                received_line_count=len(
                    [line for line in current_lines if line.owner_received_amount > 0]
                ),
                line_count=len(current_lines),
            )

        for contract in upstreams:
            if contract.contract_type != "management_agreement":
                continue
            if contract.start_date > prev_end:
                continue
            events = events_by_upstream.get(contract.id, ())
            _, successor_from = asset_operations_query_service._active_successor(
                events, as_of=prev_end
            )
            status_at_prev = derive_upstream_contract_status(
                contract,
                as_of=prev_end,
                lifecycle_events=events,
                successor_effective_from=successor_from,
            )
            if status_at_prev in {"scheduled", "exited", "historical"}:
                continue
            if contract.id in covered_upstream_ids:
                continue
            items_by_owner.setdefault(
                contract.owner_party_id,
                WorkbenchManagementFeeItem(
                    owner_party_id=contract.owner_party_id,
                    owner_party_name=party_names.get(contract.owner_party_id, ""),
                    statement_id=None,
                    statement_number=None,
                    status="missing",
                    base_amount=None,
                    fee_amount=None,
                    received_line_count=0,
                    line_count=0,
                ),
            )
        return WorkbenchManagementFeeCard(
            period=prev,
            items=sorted(
                items_by_owner.values(), key=lambda item: item.owner_party_name
            ),
        )

    async def _occupancy_card(
        self,
        db: AsyncSession,
        *,
        scope: EffectivePartyScope,
        operator_party_id: str,
        actor_id: str,
        month: str,
    ) -> WorkbenchOccupancyReportCard:
        try:
            draft = await occupancy_report_draft_service.get_draft(
                db,
                operator_party_id=operator_party_id,
                period=month,
                actor_id=actor_id,
                scope=scope,
            )
        except OccupancyReportAlreadySubmittedError:
            from ...crud.occupancy_report import occupancy_report_repository

            report = await occupancy_report_repository.get_active_chain_report(
                db, operator_party_id=operator_party_id, period=month
            )
            return WorkbenchOccupancyReportCard(
                operator_party_id=operator_party_id,
                period=month,
                status="submitted",
                unit_count=report.unit_count if report else None,
                rented_unit_count=report.rented_unit_count if report else None,
                occupancy_rate=report.occupancy_rate if report else None,
            )
        except OccupancyReportScopeMissingError:
            return WorkbenchOccupancyReportCard(
                operator_party_id=operator_party_id,
                period=month,
                status="missing_scope",
                unavailable_reason="缺少生效考核范围，请先在报送页保存考核范围",
            )
        rate_delta = None
        for change in draft.changes:
            if change.field_name == "occupancy_rate":
                try:
                    rate_delta = Decimal(str(change.current)) - Decimal(
                        str(change.previous)
                    )
                except Exception:  # noqa: BLE001 - degrade to no delta
                    rate_delta = None
                break
        return WorkbenchOccupancyReportCard(
            operator_party_id=operator_party_id,
            period=month,
            status="draft",
            unit_count=draft.totals.unit_count,
            rented_unit_count=draft.totals.rented_unit_count,
            occupancy_rate=draft.totals.occupancy_rate,
            rate_delta=rate_delta,
            gate_reasons=list(draft.gate_reasons),
            can_submit=draft.can_submit,
        )

    # ---- anytime sections -----------------------------------------------

    def _upstream_watchlists(
        self,
        *,
        upstreams: list[UpstreamContract],
        events_by_upstream: dict[str, tuple[ContractLifecycleEvent, ...]],
        today: date,
    ) -> tuple[
        list[tuple[UpstreamContract, bool]],
        list[tuple[UpstreamContract, bool]],
    ]:
        expired: list[tuple[UpstreamContract, bool]] = []
        expiring: list[tuple[UpstreamContract, bool]] = []
        for contract in upstreams:
            events = events_by_upstream.get(contract.id, ())
            successor_id, successor_from = (
                asset_operations_query_service._active_successor(events, as_of=today)
            )
            status = derive_upstream_contract_status(
                contract,
                as_of=today,
                lifecycle_events=events,
                successor_effective_from=successor_from,
            )
            if status == "expired_pending_action":
                expired.append((contract, successor_id is not None))
            elif status == "expiring":
                expiring.append((contract, successor_id is not None))
        expired.sort(key=lambda pair: pair[0].end_date)
        expiring.sort(key=lambda pair: pair[0].end_date)
        return expired, expiring

    async def _upstream_terminal_facts(
        self,
        db: AsyncSession,
        flagged: list[tuple[UpstreamContract, bool]],
        *,
        today: date,
    ) -> dict[str, dict[str, int]]:
        """Unit counts plus active/overrun terminal counts per contract."""
        terminals_by_upstream: dict[str, list[TerminalContract]] = defaultdict(list)
        for (
            upstream_id,
            terminal,
        ) in await asset_contract_repository.list_terminals_by_upstream_batched(
            db,
            upstream_contract_ids=tuple(sorted(contract.id for contract, _ in flagged)),
        ):
            terminals_by_upstream[upstream_id].append(terminal)
        terminal_ids = tuple(
            sorted(
                terminal.id
                for items in terminals_by_upstream.values()
                for terminal in items
            )
        )
        terminal_events: dict[str, tuple[ContractLifecycleEvent, ...]] = {}
        if terminal_ids:
            rows = (
                await asset_contract_repository.list_lifecycle_events_by_contract_ids(
                    db, contract_kind="terminal", contract_ids=terminal_ids
                )
            )
            grouped_events: dict[str, list[ContractLifecycleEvent]] = defaultdict(list)
            for row in rows:
                grouped_events[row.contract_id].append(row)
            terminal_events = {
                key: tuple(value) for key, value in grouped_events.items()
            }
        coverages_by_contract: dict[str, list[UpstreamContractAssetUnit]] = defaultdict(
            list
        )
        for (
            upstream_id,
            link,
        ) in await asset_contract_repository.list_upstream_coverages_batched(
            db,
            contract_ids=tuple(sorted(contract.id for contract, _ in flagged)),
        ):
            coverages_by_contract[upstream_id].append(link)
        counts: dict[str, dict[str, int]] = {}
        for contract, _ in flagged:
            coverages = coverages_by_contract.get(contract.id, ())
            active = 0
            overrun = 0
            for terminal in terminals_by_upstream.get(contract.id, ()):
                t_events = terminal_events.get(terminal.id, ())
                # 与终端页状态机同口径：存在未撤销且已生效的 renewed 事件，
                # 前驱即为 historical，不进在租/越界计数（避免前驱+后继双计）。
                successor_id, _successor_from = (
                    asset_operations_query_service._active_successor(
                        t_events, as_of=today
                    )
                )
                if successor_id is not None:
                    continue
                end = _effective_terminal_end(terminal, t_events)
                if end > contract.end_date:
                    overrun += 1
                if end >= today:
                    active += 1
            counts[contract.id] = {
                "unit_count": len(coverages),
                "active_terminal_count": active,
                "overrun_terminal_count": overrun,
            }
        return counts

    async def _pending_deposits(
        self, db: AsyncSession, *, scope: EffectivePartyScope
    ) -> list[WorkbenchDepositItem]:
        items: list[WorkbenchDepositItem] = []
        upstream_ids: set[str] = set()
        terminal_ids: set[str] = set()
        today = self._business_today()
        for kind in ("upstream", "terminal"):
            facts = await deposit_query_repository.load_facts(
                db, scope=scope, contract_kind=kind
            )
            for view in project_deposit_facts(facts, today=today):
                if view.status == "settled":
                    continue
                if kind == "upstream":
                    upstream_ids.add(view.contract_id)
                else:
                    terminal_ids.add(view.contract_id)
                items.append(
                    WorkbenchDepositItem(
                        deposit_id=view.id,
                        contract_kind=view.contract_kind,
                        contract_id=view.contract_id,
                        contract_number="",
                        counterparty_name="",
                        collector=view.collector,
                        status=view.status,
                        direction=view.direction,
                        agreed_amount=view.agreed_amount,
                        held_amount=view.held_amount,
                        outstanding_amount=view.outstanding_amount,
                    )
                )
        if not items:
            return []
        upstreams = await asset_contract_repository.get_upstreams_by_ids(
            db, contract_ids=tuple(sorted(upstream_ids)), scope=scope
        )
        terminals: list[TerminalContract] = []
        if terminal_ids:
            rows, _ = await asset_contract_repository.list_terminal(
                db,
                scope=scope,
                contract_ids=set(terminal_ids),
                offset=0,
                limit=len(terminal_ids),
            )
            terminals = list(rows)
        numbers = {contract.id: contract.contract_number for contract in upstreams}
        numbers.update(
            {contract.id: contract.contract_number for contract in terminals}
        )
        owners = {contract.id: contract.owner_party_id for contract in upstreams}
        tenants = {contract.id: contract.tenant_party_id for contract in terminals}
        names = await _PARTY_CRUD.get_party_names_by_ids(
            db,
            party_ids=tuple(sorted(set(owners.values()) | set(tenants.values()))),
        )
        for item in items:
            item.contract_number = numbers.get(item.contract_id, item.contract_id)
            if item.contract_kind == "upstream":
                item.counterparty_name = names.get(owners.get(item.contract_id, ""), "")
            else:
                item.counterparty_name = names.get(
                    tenants.get(item.contract_id, ""), ""
                )
        items.sort(
            key=lambda item: (
                item.contract_kind,
                item.contract_number,
                item.deposit_id,
            )
        )
        return items

    async def _pending_scope_units(
        self,
        db: AsyncSession,
        *,
        scope: EffectivePartyScope,
        operator_party_id: str,
        actor_id: str,
        year: int,
    ) -> list[WorkbenchPendingScopeUnit]:
        from .assessment_scope_command_service import (
            assessment_scope_command_service,
        )

        try:
            overview = await assessment_scope_command_service.get_overview(
                db,
                operator_party_id=operator_party_id,
                year=year,
                actor_id=actor_id,
                scope=scope,
            )
        except (
            AssessmentScopeOperatorForbiddenError,
            OccupancyReportScopeMissingError,
            ResourceNotFoundError,
        ):
            # 待确认宗地是 advisory 区块：无范围/越权/单元不可见时静默降级，
            # 其余异常（DB 故障等）照常上抛，失败要响（红线 11）。
            return []
        return [
            WorkbenchPendingScopeUnit(
                asset_unit_id=pending.asset_unit_id,
                unit_code=pending.unit_snapshot.unit_code,
                unit_name=pending.unit_snapshot.name,
                reason=pending.reason,
            )
            for pending in overview.pending
        ]


monthly_workbench_service = MonthlyWorkbenchService()


__all__ = ["MonthlyWorkbenchService", "monthly_workbench_service"]
