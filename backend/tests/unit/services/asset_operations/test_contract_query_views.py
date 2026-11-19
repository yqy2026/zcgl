"""Contract list and detail reads derive status from replayed events."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest

from src.models.asset_contract import (
    ContractLifecycleEvent,
    ContractRentSchedule,
    TerminalContract,
    TerminalContractAssetUnit,
    UpstreamContract,
    UpstreamContractAssetUnit,
)
from src.services.asset_operations.query_service import AssetOperationsQueryService
from src.services.party_scope_resolver import EffectivePartyScope

TODAY = date(2026, 10, 25)
SCOPE = EffectivePartyScope(
    user_id="actor-1",
    source="explicit",
    scope_mode="owner",
    owner_party_ids=["owner-1"],
)


def _upstream(**overrides: object) -> UpstreamContract:
    values: dict[str, object] = {
        "id": "upstream-1",
        "contract_number": "UP-001",
        "contract_type": "lease",
        "name": "上游合同",
        "owner_party_id": "owner-1",
        "operator_party_id": "operator-1",
        "start_date": date(2026, 1, 1),
        "end_date": date(2026, 12, 20),
        "payment_cycle": "monthly",
        "payment_day": 15,
        "deposit_amount": Decimal("50000"),
        "scan_document_id": "scan-up",
        "version": 1,
        "created_at": datetime(2026, 1, 1),
        "updated_at": datetime(2026, 1, 1),
    }
    values.update(overrides)
    return UpstreamContract(**values)  # type: ignore[arg-type]


def _terminal(**overrides: object) -> TerminalContract:
    values: dict[str, object] = {
        "id": "terminal-1",
        "contract_number": "TM-001",
        "contract_mode": "sublease",
        "tenant_party_id": "tenant-1",
        "lessor_party_id": "operator-1",
        "upstream_contract_id": "upstream-1",
        "start_date": date(2026, 1, 1),
        "end_date": date(2026, 12, 31),
        "deposit_amount": Decimal("20000"),
        "rent_collector": "operator",
        "scan_document_id": "scan-tm",
        "version": 1,
        "created_at": datetime(2026, 1, 1),
        "updated_at": datetime(2026, 1, 1),
    }
    values.update(overrides)
    return TerminalContract(**values)  # type: ignore[arg-type]


def _event(**overrides: object) -> ContractLifecycleEvent:
    values: dict[str, object] = {
        "id": "event-1",
        "contract_kind": "terminal",
        "contract_id": "terminal-1",
        "event_type": "terminated",
        "effective_date": date(2026, 6, 30),
        "termination_type": "early",
        "handover_status": "completed",
        "deposit_settlement_status": "settled",
        "reason": "提前退租",
        "created_by": "actor-1",
        "created_at": datetime(2026, 7, 1),
        "idempotency_key": "event-key-1",
    }
    values.update(overrides)
    return ContractLifecycleEvent(**values)  # type: ignore[arg-type]


class _Reader:
    def __init__(self) -> None:
        self.upstreams = [_upstream()]
        self.terminals = [_terminal()]
        self.events: list[ContractLifecycleEvent] = []
        self.schedules: list[ContractRentSchedule] = [
            ContractRentSchedule(  # type: ignore[call-arg]
                id="schedule-1",
                contract_kind="terminal",
                contract_id="terminal-1",
                stage_start=date(2026, 1, 1),
                stage_end=date(2026, 12, 31),
                base_monthly_rent=Decimal("10000"),
                actual_monthly_rent=Decimal("10000"),
                payment_cycle="monthly",
                due_day=15,
            )
        ]
        self.upstream_coverages = [
            UpstreamContractAssetUnit(
                upstream_contract_id="upstream-1",
                asset_unit_id="unit-1",
                effective_from=date(2026, 1, 1),
                effective_to=date(2026, 12, 20),
            )
        ]
        self.terminal_coverages = [
            TerminalContractAssetUnit(
                terminal_contract_id="terminal-1",
                asset_unit_id="unit-1",
                effective_from=date(2026, 1, 1),
                effective_to=date(2026, 6, 29),
            )
        ]

    async def list_upstream(self, _db, **kwargs):
        return list(self.upstreams), len(self.upstreams)

    async def get_upstream(self, _db, *, contract_id, scope, for_update=False):
        return next((c for c in self.upstreams if c.id == contract_id), None)

    async def get_upstreams_by_ids(self, _db, *, contract_ids, scope=None):
        return tuple(c for c in self.upstreams if c.id in set(contract_ids))

    async def list_terminal(self, _db, **kwargs):
        return list(self.terminals), len(self.terminals)

    async def get_terminal(self, _db, *, contract_id, scope, for_update=False):
        return next((c for c in self.terminals if c.id == contract_id), None)

    async def list_lifecycle_events_by_contract_ids(
        self, _db, *, contract_kind, contract_ids
    ):
        return tuple(
            event
            for event in self.events
            if event.contract_kind == contract_kind
            and event.contract_id in set(contract_ids)
        )

    async def list_rent_schedules(self, _db, *, contract_kind, contract_ids):
        return tuple(
            schedule
            for schedule in self.schedules
            if schedule.contract_kind == contract_kind
            and schedule.contract_id in set(contract_ids)
        )

    async def list_upstream_coverages(self, _db, *, contract_id):
        return tuple(
            c for c in self.upstream_coverages if c.upstream_contract_id == contract_id
        )

    async def list_terminal_coverages(self, _db, *, contract_id):
        return tuple(
            c for c in self.terminal_coverages if c.terminal_contract_id == contract_id
        )

    async def list_terminal_by_upstream(self, _db, *, upstream_contract_id):
        return tuple(
            c for c in self.terminals if c.upstream_contract_id == upstream_contract_id
        )

    async def list_terminal_unit_labels(self, _db, *, contract_ids):
        return {}

    async def list_terminal_coverages_by_ids(self, _db, *, contract_ids):
        return tuple(
            (link.terminal_contract_id, link)
            for link in self.terminal_coverages
            if link.terminal_contract_id in set(contract_ids)
        )

    async def list_terminals_by_upstream_batched(self, _db, *, upstream_contract_ids):
        wanted = set(upstream_contract_ids)
        return tuple(
            (c.upstream_contract_id, c)
            for c in self.terminals
            if c.upstream_contract_id in wanted
        )

    async def list_upstream_coverages_batched(self, _db, *, contract_ids):
        return tuple(
            (link.upstream_contract_id, link)
            for link in self.upstream_coverages
            if link.upstream_contract_id in set(contract_ids)
        )


class _DB:
    pass


class _PartyNames:
    async def get_party_names_by_ids(self, _db, *, party_ids):
        return {}


class _UnitReaderLite:
    async def get_units_by_ids(self, _db, *, unit_ids, scope):
        return ()


def _service(reader: _Reader) -> AssetOperationsQueryService:
    return AssetOperationsQueryService(
        asset_contract_repository=reader,  # type: ignore[arg-type]
        asset_unit_repository=_UnitReaderLite(),  # type: ignore[arg-type]
        party_name_reader=_PartyNames(),  # type: ignore[arg-type]
        business_today=lambda: TODAY,
    )


@pytest.fixture
def terminal_ledger_boundary(monkeypatch):
    """终端列表的计数/本月到账聚合依赖台账与押金单例，这里整体旁路。"""
    from unittest.mock import AsyncMock

    from src.crud.deposit_queries import deposit_query_repository
    from src.crud.rent_ledger_queries import rent_ledger_query_repository
    from src.services.asset_operations.rent_ledger_query_service import (
        rent_ledger_query_service,
    )

    monkeypatch.setattr(
        rent_ledger_query_service,
        "unpaid_contract_ids",
        AsyncMock(return_value=set()),
    )
    monkeypatch.setattr(
        rent_ledger_query_service,
        "_views",
        staticmethod(lambda facts, *, today: ({}, {})),
    )
    from src.services.asset_operations import deposit_query_service as dep_mod

    monkeypatch.setattr(dep_mod, "project_deposit_facts", lambda facts, *, today: [])
    monkeypatch.setattr(
        deposit_query_repository,
        "load_facts",
        AsyncMock(return_value=object()),
    )
    monkeypatch.setattr(
        rent_ledger_query_repository,
        "matrix_facts",
        AsyncMock(return_value=None),
    )


@pytest.mark.asyncio
async def test_upstream_list_derives_expiring_status_from_events() -> None:
    reader = _Reader()
    service = _service(reader)

    items, total = await service.list_upstream_contracts(_DB(), scope=SCOPE)

    assert total == 1
    assert items[0].status == "expiring"
    assert items[0].contract_number == "UP-001"


@pytest.mark.asyncio
async def test_upstream_list_marks_exited_after_replayed_event() -> None:
    reader = _Reader()
    reader.events.append(
        _event(
            contract_kind="upstream",
            contract_id="upstream-1",
            event_type="exited",
            effective_date=date(2026, 6, 30),
            termination_type=None,
            handover_status=None,
            deposit_settlement_status=None,
            reason="提前解除",
        )
    )
    service = _service(reader)

    items, _ = await service.list_upstream_contracts(_DB(), scope=SCOPE)

    assert items[0].status == "exited"


@pytest.mark.asyncio
async def test_terminal_list_derives_ended_and_warnings(
    terminal_ledger_boundary,
) -> None:
    reader = _Reader()
    reader.events.append(
        _event(
            contract_kind="terminal",
            contract_id="terminal-1",
            event_type="terminated",
            effective_date=date(2026, 6, 30),
        )
    )
    service = _service(reader)

    items, total = await service.list_terminal_contracts(_DB(), scope=SCOPE)

    assert total == 1
    assert items[0].status == "ended"
    warning_codes = [warning.code for warning in items[0].warnings]
    assert "TERMINAL_TERM_EXCEEDS_UPSTREAM" in warning_codes


@pytest.mark.asyncio
async def test_terminal_list_flags_missing_upstream(
    terminal_ledger_boundary,
) -> None:
    reader = _Reader()
    reader.terminals = [_terminal(upstream_contract_id=None)]
    service = _service(reader)

    items, _ = await service.list_terminal_contracts(_DB(), scope=SCOPE)

    assert [warning.code for warning in items[0].warnings] == [
        "UPSTREAM_CONTRACT_MISSING"
    ]


@pytest.mark.asyncio
async def test_upstream_detail_aggregates_coverages_schedules_and_chain() -> None:
    reader = _Reader()
    reader.upstreams.append(
        _upstream(
            id="upstream-2",
            contract_number="UP-002",
            renewed_from_id="upstream-1",
            start_date=date(2027, 1, 1),
            end_date=date(2029, 12, 31),
        )
    )
    reader.events.append(
        _event(
            contract_kind="upstream",
            contract_id="upstream-1",
            event_type="renewed",
            effective_date=date(2026, 7, 1),
            termination_type=None,
            handover_status=None,
            deposit_settlement_status=None,
            reason=None,
            successor_contract_id="upstream-2",
        )
    )
    service = _service(reader)

    detail = await service.get_upstream_contract(_DB(), "upstream-1", scope=SCOPE)

    assert detail is not None
    assert detail.status == "historical"
    assert len(detail.coverages) == 1
    assert detail.coverages[0].asset_unit_id == "unit-1"
    assert [item.relation for item in detail.renewal_chain] == [
        "current",
        "successor",
    ]
    assert detail.renewal_chain[1].contract_number == "UP-002"
    assert detail.terminal_contract_ids == ["terminal-1"]
    assert len(detail.lifecycle_events) == 1


@pytest.mark.asyncio
async def test_upstream_detail_hides_future_successor_until_effective() -> None:
    reader = _Reader()
    reader.upstreams.append(
        _upstream(
            id="upstream-2",
            contract_number="UP-002",
            renewed_from_id="upstream-1",
            start_date=date(2027, 1, 1),
            end_date=date(2029, 12, 31),
        )
    )
    reader.events.append(
        _event(
            contract_kind="upstream",
            contract_id="upstream-1",
            event_type="renewed",
            effective_date=date(2027, 1, 1),
            termination_type=None,
            handover_status=None,
            deposit_settlement_status=None,
            reason=None,
            successor_contract_id="upstream-2",
        )
    )
    service = _service(reader)

    detail = await service.get_upstream_contract(_DB(), "upstream-1", scope=SCOPE)

    assert detail is not None
    assert detail.status == "expiring"
    assert [item.relation for item in detail.renewal_chain] == ["current"]


@pytest.mark.asyncio
async def test_terminal_detail_includes_predecessor_chain_and_schedules() -> None:
    reader = _Reader()
    reader.terminals.append(
        _terminal(
            id="terminal-2",
            contract_number="TM-002",
            renewed_from_id="terminal-1",
            start_date=date(2026, 7, 1),
            end_date=date(2026, 12, 31),
        )
    )
    service = _service(reader)

    detail = await service.get_terminal_contract(_DB(), "terminal-2", scope=SCOPE)

    assert detail is not None
    assert [item.relation for item in detail.renewal_chain] == [
        "predecessor",
        "current",
    ]
    assert detail.renewal_chain[0].contract_number == "TM-001"
    assert len(detail.rent_schedules) == 0
    assert detail.coverages == []


@pytest.mark.asyncio
async def test_detail_returns_none_for_unknown_contract() -> None:
    service = _service(_Reader())

    assert await service.get_upstream_contract(_DB(), "missing", scope=SCOPE) is None
    assert await service.get_terminal_contract(_DB(), "missing", scope=SCOPE) is None


@pytest.mark.asyncio
async def test_terminal_view_counts_and_page_enrichment(
    terminal_ledger_boundary, monkeypatch
) -> None:
    from unittest.mock import AsyncMock

    from src.crud.rent_ledger_queries import rent_ledger_query_repository
    from src.services.asset_operations.rent_ledger_query_service import (
        rent_ledger_query_service,
    )

    reader = _Reader()
    reader.terminals = [
        _terminal(),
        _terminal(
            id="terminal-2",
            contract_number="TM-002",
            scan_document_id=None,
        ),
    ]
    reader.events = [
        _event(
            contract_id="terminal-2",
            event_type="terminated",
            effective_date=date(2026, 5, 31),
        )
    ]

    class _Names:
        async def get_party_names_by_ids(self, _db, *, party_ids):
            return {"tenant-1": "凤凰创意"}

    service = AssetOperationsQueryService(
        asset_contract_repository=reader,  # type: ignore[arg-type]
        party_name_reader=_Names(),  # type: ignore[arg-type]
        business_today=lambda: TODAY,
    )

    unpaid = {"terminal-1"}
    monkeypatch.setattr(
        rent_ledger_query_service,
        "unpaid_contract_ids",
        AsyncMock(return_value=unpaid),
    )

    # 默认终端合同止日 2026-12-31，距今 67 天 → 180 天内到期而非生效中。
    items, total, counts = await service.list_terminal_contracts_view(
        _DB(), scope=SCOPE, filter_value="expiring_180"
    )

    assert total == 1
    assert items[0].id == "terminal-1"
    assert items[0].tenant_party_name == "凤凰创意"
    assert items[0].upstream_contract_number == "UP-001"
    assert items[0].has_scan is True
    # 计数按派生状态与事实集合统计，而不是按当前筛选。
    assert counts.active == 0
    assert counts.expiring_180 == 1
    assert counts.ended == 1
    assert counts.missing_scan == 1
    assert counts.rent_unpaid == 1
    _ = rent_ledger_query_repository


@pytest.mark.asyncio
async def test_upstream_detail_builds_payment_plan_and_units_matrix(
    terminal_ledger_boundary,
) -> None:
    reader = _Reader()
    reader.schedules.append(
        ContractRentSchedule(  # type: ignore[call-arg]
            id="schedule-up",
            contract_kind="upstream",
            contract_id="upstream-1",
            stage_start=date(2026, 1, 1),
            stage_end=date(2026, 12, 31),
            base_monthly_rent=Decimal("10000"),
            actual_monthly_rent=Decimal("10000"),
            increase_rate=Decimal("0"),
            free_rent_months=Decimal("0"),
            discount_amount=Decimal("0"),
            payment_cycle="monthly",
            due_day=15,
        )
    )

    class _Units:
        async def get_units_by_ids(self, _db, *, unit_ids, scope):
            from types import SimpleNamespace

            return (
                SimpleNamespace(
                    id="unit-1",
                    unit_code="U-001",
                    name="一号商铺",
                    rentable_area=Decimal("80"),
                ),
            )

    service = AssetOperationsQueryService(
        asset_contract_repository=reader,  # type: ignore[arg-type]
        asset_unit_repository=_Units(),  # type: ignore[arg-type]
        party_name_reader=_PartyNames(),  # type: ignore[arg-type]
        business_today=lambda: TODAY,
    )

    detail = await service.get_upstream_contract(_DB(), "upstream-1", scope=SCOPE)

    assert detail is not None
    # 默认上游止日 2026-12-20 → 剩余 56 天。
    assert detail.days_to_expiry == (date(2026, 12, 20) - TODAY).days
    # 付款计划：单阶段，期数按月计，合计 = 月租 × 12。
    assert len(detail.payment_plan) == 1
    plan = detail.payment_plan[0]
    assert plan.stage_start == date(2026, 1, 1)
    assert plan.stage_end == date(2026, 12, 20)
    assert plan.period_count == 12
    assert plan.total_amount == Decimal("120000")
    assert plan.note == "首期租金"
    # 单元矩阵：覆盖单元带出当前终端合同与当期月租。
    assert len(detail.units_matrix) == 1
    row = detail.units_matrix[0]
    assert row.asset_unit_id == "unit-1"
    assert row.terminal_contract_number == "TM-001"
    assert row.monthly_rent == Decimal("10000")
    assert row.has_scan is True
