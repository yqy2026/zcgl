"""Monthly workbench aggregation: cards, carry-over and progress math."""

import importlib
from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace as Row
from unittest.mock import AsyncMock

import pytest

from src.models.asset_contract import TerminalContract, UpstreamContract
from src.services.asset_operations.errors import (
    OccupancyReportAlreadySubmittedError,
    OccupancyReportPeriodInvalidError,
    OccupancyReportScopeMissingError,
)
from src.services.party_scope_resolver import EffectivePartyScope

# 包 __init__ 把同名单例绑到包属性上，import a.b as c 会拿到单例；
# 这里要的是模块本身（便于按命名空间打桩）。
module = importlib.import_module(
    "src.services.asset_operations.monthly_workbench_service"
)

pytestmark = pytest.mark.unit

TODAY = date(2026, 11, 17)


def _scope() -> EffectivePartyScope:
    return EffectivePartyScope(
        user_id="actor", source="explicit", scope_mode="unrestricted"
    )


def _entry(
    entry_id,
    contract_id,
    *,
    period,
    status,
    due=Decimal("100"),
    paid=Decimal("0"),
    remaining=None,
    due_date=date(2026, 11, 25),
):
    return Row(
        id=entry_id,
        contract_id=contract_id,
        period=period,
        status=status,
        due_amount=due,
        effective_paid_amount=paid,
        remaining_amount=remaining
        if remaining is not None
        else max(due - paid, Decimal("0")),
        due_date=due_date,
    )


def _upstream(cid, number, *, kind="lease", end=date(2027, 6, 30), owner="owner-1"):
    return UpstreamContract(
        id=cid,
        contract_number=number,
        contract_type=kind,
        name=f"物业{number}",
        owner_party_id=owner,
        operator_party_id="operator-1",
        start_date=date(2023, 1, 1),
        end_date=end,
        deposit_amount=Decimal("0"),
        renewed_from_id=None,
        scan_document_id="scan-up",
        version=1,
        created_at=datetime(2026, 1, 1),
        updated_at=datetime(2026, 1, 1),
    )


def _terminal(cid, number, *, collector="operator", tenant="tenant-1"):
    return TerminalContract(
        id=cid,
        contract_number=number,
        contract_mode="sublease",
        tenant_party_id=tenant,
        lessor_party_id="operator-1",
        upstream_contract_id=None,
        start_date=date(2024, 1, 1),
        end_date=date(2028, 1, 31),
        deposit_amount=Decimal("0"),
        rent_collector=collector,
        renewed_from_id=None,
        scan_document_id="scan-tm",
        version=1,
        created_at=datetime(2026, 1, 1),
        updated_at=datetime(2026, 1, 1),
    )


@pytest.fixture
def repos(monkeypatch):
    upstreams = [
        _upstream("u1", "CZ-2026-001"),
        _upstream("u2", "WT-2026-002", kind="management_agreement", owner="owner-2"),
        _upstream("u3", "CZ-2025-003", end=date(2026, 10, 31)),
        _upstream("u4", "WT-2026-004", kind="management_agreement", owner="owner-1"),
    ]
    monkeypatch.setattr(
        module.asset_contract_repository,
        "list_upstream",
        AsyncMock(return_value=(upstreams, len(upstreams))),
    )
    monkeypatch.setattr(
        module.asset_contract_repository,
        "list_lifecycle_events_by_contract_ids",
        AsyncMock(return_value=()),
    )
    monkeypatch.setattr(
        module.asset_contract_repository,
        "list_terminal_by_upstream",
        AsyncMock(return_value=()),
    )
    monkeypatch.setattr(
        module.asset_contract_repository,
        "list_upstream_coverages",
        AsyncMock(return_value=()),
    )
    monkeypatch.setattr(
        module.asset_contract_repository,
        "list_terminal_unit_labels",
        AsyncMock(
            return_value={"t2": ("101 室", "102 室", "103 室"), "t1": ("201 室",)}
        ),
    )

    upstream_entries = {
        "e1": _entry(
            "e1",
            "u1",
            period="2026-11",
            status="unpaid",
            due=Decimal("60000"),
            due_date=date(2026, 11, 25),
        ),
        "e2": _entry(
            "e2",
            "u1",
            period="2026-10",
            status="overdue",
            due=Decimal("60000"),
            due_date=date(2026, 10, 25),
        ),
        "e3": _entry(
            "e3",
            "u1",
            period="2026-11",
            status="paid",
            due=Decimal("0"),
            paid=Decimal("58000"),
            remaining=Decimal("0"),
        ),
    }
    terminal_entries = {
        "t1e": _entry(
            "t1e",
            "t1",
            period="2026-11",
            status="partial",
            due=Decimal("8000"),
            paid=Decimal("3000"),
            due_date=date(2026, 11, 10),
        ),
        "t2e": _entry(
            "t2e",
            "t2",
            period="2026-11",
            status="upcoming",
            due=Decimal("12000"),
            due_date=date(2026, 11, 20),
        ),
        "t3e": _entry("t3e", "t3", period="2026-11", status="unpaid"),
    }

    def fake_views(facts, *, today):
        _ = today
        if any(
            getattr(contract, "rent_collector", None) for contract in facts.contracts
        ):
            return dict(terminal_entries), {}
        return dict(upstream_entries), {}

    monkeypatch.setattr(
        module.rent_ledger_query_service, "_views", staticmethod(fake_views)
    )

    async def fake_matrix_facts(db, *, scope, ledger_type, year):
        _ = db, scope, year

        def _facts(contracts):
            return Row(
                contracts=contracts,
                entries=(),
                records=(),
                schedules=(),
                events=(),
            )

        if ledger_type == "upstream_rent":
            return _facts((_upstream("u1", "CZ-2026-001"),))
        return _facts(
            (
                _terminal("t1", "ZZ-1"),
                _terminal("t2", "ZZ-2"),
                _terminal("t3", "ZZ-3", collector="owner", tenant="tenant-2"),
            )
        )

    monkeypatch.setattr(
        module.rent_ledger_query_repository,
        "matrix_facts",
        fake_matrix_facts,
    )

    statement = Row(
        id="st-1",
        owner_party_id="owner-2",
        period="2026-10",
        statement_number="DF-2026-10-01",
        base_amount=Decimal("50000"),
        upstream_contract_ids=["u2"],
    )
    monkeypatch.setattr(
        module.management_fee_matrix_repository,
        "list_year",
        AsyncMock(return_value=((statement, "业主二"),)),
    )
    monkeypatch.setattr(
        module.management_fee_query_service,
        "details",
        AsyncMock(
            return_value={
                "st-1": Row(
                    status="collecting",
                    fee_amount=Decimal("3000"),
                    snapshot_lines=(
                        Row(line_kind="current", owner_received_amount=Decimal("1")),
                        Row(line_kind="current", owner_received_amount=Decimal("0")),
                        Row(
                            line_kind="carried",
                            owner_received_amount=Decimal("1"),
                        ),
                    ),
                )
            }
        ),
    )
    monkeypatch.setattr(
        module._PARTY_CRUD,
        "get_party_names_by_ids",
        AsyncMock(
            return_value={
                "owner-1": "国资物业",
                "owner-2": "城投资产",
                "tenant-1": "凤凰创意",
                "tenant-2": "直签租户",
            }
        ),
    )
    monkeypatch.setattr(
        module.archive_matrix_service,
        "completion",
        AsyncMock(
            return_value=Row(
                categories=(
                    Row(
                        document_type="terminal_contract",
                        label="终端合同",
                        supported=True,
                        required=True,
                        missing=3,
                    ),
                    Row(
                        document_type="upstream_contract",
                        label="上游合同",
                        supported=True,
                        required=True,
                        missing=0,
                    ),
                ),
                unlinked_unit_count=2,
            )
        ),
    )
    monkeypatch.setattr(
        module.deposit_query_repository, "load_facts", AsyncMock(return_value=())
    )
    monkeypatch.setattr(module, "project_deposit_facts", lambda facts, *, today: ())

    scope_module = importlib.import_module(
        "src.services.asset_operations.assessment_scope_command_service"
    )
    monkeypatch.setattr(
        scope_module.assessment_scope_command_service,
        "get_overview",
        AsyncMock(return_value=Row(pending=())),
    )
    return upstreams


@pytest.mark.asyncio
async def test_overview_cards_progress_and_anytime(monkeypatch, repos):
    _ = repos
    draft = Row(
        totals=Row(
            unit_count=10,
            rented_unit_count=7,
            occupancy_rate=Decimal("0.7000"),
        ),
        changes=(
            Row(field_name="occupancy_rate", previous="0.6500", current="0.7000"),
        ),
        gate_reasons=["change_note_required"],
        can_submit=False,
    )
    monkeypatch.setattr(
        module.occupancy_report_draft_service,
        "get_draft",
        AsyncMock(return_value=draft),
    )
    service = module.MonthlyWorkbenchService(business_today_fn=lambda: TODAY)
    view = await service.overview(
        None,
        scope=_scope(),
        operator_party_id="op",
        actor_id="actor",
        month="2026-11",
    )

    # 支付卡：往月逾期排前、当月未付随后，部分付款金额可辨。
    payments = view.rent_payments
    assert [item.period for item in payments.items] == ["2026-10", "2026-11"]
    assert payments.items[0].days_overdue == (TODAY - date(2026, 10, 25)).days
    assert payments.items[0].counterparty_name == "国资物业"
    assert payments.done_count == 1
    assert payments.pending_count == 2

    # 收租卡：只含本公司收取的转租合同；直签合同不出现在卡里。
    collections = view.rent_collections
    assert {item.contract_id for item in collections.items} == {"t1", "t2"}
    merged = next(item for item in collections.items if item.contract_id == "t2")
    assert merged.unit_label == "101 室 等 3 个单元"
    partial = next(item for item in collections.items if item.contract_id == "t1")
    assert partial.paid_amount == Decimal("3000")
    assert partial.remaining_amount == Decimal("5000")

    # 管理费卡：出单物业为收租中（含 1/2 户），未出单协议标记 missing。
    fees = view.management_fees
    assert fees.period == "2026-10"
    assert [item.status for item in fees.items] == ["collecting", "missing"]
    collecting = fees.items[0]
    assert collecting.owner_party_name == "业主二"
    assert collecting.received_line_count == 1
    assert collecting.line_count == 2
    missing = fees.items[1]
    assert missing.statement_id is None
    assert missing.owner_party_name == "国资物业"

    # 报送卡：草稿态、门槛与较上月变化透出。
    report = view.occupancy_report
    assert report.status == "draft"
    assert report.unit_count == 10
    assert report.rate_delta == Decimal("0.0500")
    assert report.gate_reasons == ["change_note_required"]

    # 随时处理：到期未处理上游、档案缺漏、押金/待确认清单。
    assert [item.contract_number for item in view.expired_upstream] == ["CZ-2025-003"]
    assert view.expired_upstream[0].days_past == (TODAY - date(2026, 10, 31)).days
    assert [gap.label for gap in view.archive_gaps] == ["终端合同"]
    assert view.unlinked_unit_count == 2
    assert view.deposits_pending == []
    assert view.pending_scope_units == []

    # 进度 = 支付 2 + 收租 2 + 管理费 2（未确认）+ 报送 1。
    assert view.progress.total == 7
    assert view.progress.done == 1  # 支付已完成 1 笔
    assert view.days_left_in_month == (date(2026, 11, 30) - TODAY).days


@pytest.mark.asyncio
async def test_overview_counts_report_done_when_submitted(monkeypatch, repos):
    _ = repos
    monkeypatch.setattr(
        module.occupancy_report_draft_service,
        "get_draft",
        AsyncMock(
            side_effect=OccupancyReportAlreadySubmittedError(
                report_id="r1", period="2026-11"
            )
        ),
    )
    from src.crud.occupancy_report import occupancy_report_repository

    monkeypatch.setattr(
        occupancy_report_repository,
        "get_active_chain_report",
        AsyncMock(
            return_value=Row(
                unit_count=10,
                rented_unit_count=8,
                occupancy_rate=Decimal("0.8"),
                status="submitted",
            )
        ),
    )
    service = module.MonthlyWorkbenchService(business_today_fn=lambda: TODAY)
    view = await service.overview(
        None, scope=_scope(), operator_party_id="op", actor_id="actor"
    )
    assert view.occupancy_report.status == "submitted"
    assert view.occupancy_report.rented_unit_count == 8
    assert view.progress.done == 2  # 支付完成 1 + 报送已完成


@pytest.mark.asyncio
async def test_overview_degrades_when_scope_missing(monkeypatch, repos):
    _ = repos
    monkeypatch.setattr(
        module.occupancy_report_draft_service,
        "get_draft",
        AsyncMock(
            side_effect=OccupancyReportScopeMissingError(
                operator_party_id="op", year=2026
            )
        ),
    )
    service = module.MonthlyWorkbenchService(business_today_fn=lambda: TODAY)
    view = await service.overview(
        None, scope=_scope(), operator_party_id="op", actor_id="actor"
    )
    assert view.occupancy_report.status == "missing_scope"
    assert view.occupancy_report.unavailable_reason is not None


@pytest.mark.asyncio
async def test_overview_rejects_invalid_month(monkeypatch, repos):
    _ = repos
    service = module.MonthlyWorkbenchService(business_today_fn=lambda: TODAY)
    with pytest.raises(OccupancyReportPeriodInvalidError):
        await service.overview(
            None,
            scope=_scope(),
            operator_party_id="op",
            actor_id="actor",
            month="2026-13",
        )


@pytest.mark.asyncio
async def test_overview_deposits_carry_names_and_numbers(monkeypatch, repos):
    _ = repos
    views = [
        Row(
            id="d1",
            contract_kind="terminal",
            contract_id="t1",
            collector="operator",
            status="refundable_unreturned",
            direction="refundable",
            agreed_amount=Decimal("16000"),
            held_amount=Decimal("16000"),
            outstanding_amount=Decimal("16000"),
        )
    ]

    async def load_facts(db, *, scope, contract_kind, **kwargs):
        _ = db, scope, kwargs
        return ("facts",) if contract_kind == "terminal" else ()

    monkeypatch.setattr(module.deposit_query_repository, "load_facts", load_facts)
    monkeypatch.setattr(
        module,
        "project_deposit_facts",
        lambda facts, *, today: views if facts else (),
    )
    terminals = [_terminal("t1", "ZZ-1")]
    monkeypatch.setattr(
        module.asset_contract_repository,
        "list_terminal",
        AsyncMock(return_value=(terminals, 1)),
    )
    monkeypatch.setattr(
        module.asset_contract_repository,
        "get_upstreams_by_ids",
        AsyncMock(return_value=()),
    )
    monkeypatch.setattr(
        module.occupancy_report_draft_service,
        "get_draft",
        AsyncMock(
            side_effect=OccupancyReportScopeMissingError(
                operator_party_id="op", year=2026
            )
        ),
    )
    service = module.MonthlyWorkbenchService(business_today_fn=lambda: TODAY)
    view = await service.overview(
        None, scope=_scope(), operator_party_id="op", actor_id="actor"
    )
    assert len(view.deposits_pending) == 1
    deposit = view.deposits_pending[0]
    assert deposit.contract_number == "ZZ-1"
    assert deposit.counterparty_name == "凤凰创意"
    assert deposit.status == "refundable_unreturned"
