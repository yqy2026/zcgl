"""Batched fee reads share one membership check, owner facts and mark query.

The whole-owner authorization rule has a single home: the SQL boundary in
crud/business_change_event (fee_statement_ids_for_scope); the query service
no longer keeps a Python twin. Batch reads must not amplify queries per
statement (V2 已知读路径读放大收口).
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace as Row
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.core.exception_handler import ResourceNotFoundError
from src.crud.asset_contract import asset_contract_repository
from src.crud.business_change_event import visible_fee_statement_ids
from src.crud.management_fee_deferral import management_fee_deferral_repository
from src.crud.management_fee_queries import ManagementFeeQueryFacts
from src.models.asset_contract import UpstreamContract
from src.models.management_fee_deferral import ManagementFeeDeferral
from src.models.management_fee_statement import ManagementFeeStatement
from src.services.asset_operations import management_fee_query_service as query_module
from src.services.party_scope_resolver import EffectivePartyScope

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class AsyncSessionFacade:
    def __init__(self, session):
        self.session = session

    async def execute(self, statement):
        return self.session.execute(statement)


def statement_row(id, owner_party_id, period, status=None):
    return Row(
        id=id,
        owner_party_id=owner_party_id,
        period=period,
        status=status,
        version=1,
    )


def facts(owner_statements):
    return ManagementFeeQueryFacts(
        agreements=(
            Row(
                id="up",
                management_fee_rate=Decimal("0.1"),
                operator_party_id="manager",
            ),
        ),
        contracts=(Row(id="tm", upstream_contract_id="up", tenant_party_id="tenant"),),
        obligations=(
            Row(
                id="entry",
                contract_id="tm",
                period="2026-09",
                due_amount=Decimal("100"),
                voided_at=None,
            ),
        ),
        records=(),
        tenant_names={"tenant": "租户"},
        unit_ids={"tm": ("unit",)},
        statements=owner_statements,
        lines=(),
    )


def patch_batch_seams(monkeypatch, *, visible_ids, facts_by_owner, marks=None):
    monkeypatch.setattr(
        query_module,
        "visible_fee_statement_ids",
        AsyncMock(return_value=visible_ids),
    )
    monkeypatch.setattr(
        query_module.management_fee_query_repository,
        "load_facts",
        AsyncMock(side_effect=facts_by_owner),
    )
    monkeypatch.setattr(
        query_module.management_fee_deferral_repository,
        "list_marks_for_statements",
        AsyncMock(return_value={} if marks is None else marks),
    )
    monkeypatch.setattr(
        query_module,
        "business_today",
        lambda: date(2026, 10, 10),
    )


async def test_details_batches_reads_per_distinct_owner(monkeypatch):
    statements = (
        statement_row("s1", "owner-a", "2026-10"),
        statement_row("s2", "owner-a", "2026-09", status="confirmed"),
        statement_row("s3", "owner-b", "2026-10"),
    )
    patch_batch_seams(
        monkeypatch,
        visible_ids={"s1", "s2", "s3"},
        facts_by_owner=[
            facts(
                (
                    Row(id="s2", period="2026-09", status="confirmed"),
                    Row(id="s1", period="2026-10", status=None),
                )
            ),
            facts((Row(id="s3", period="2026-10", status=None),)),
        ],
        marks={"s1": (Row(rent_ledger_entry_id="entry", reason="下月补齐"),)},
    )
    scope = EffectivePartyScope(
        user_id="actor", source="explicit", scope_mode="owner",
        owner_party_ids=["owner-a", "owner-b"],
    )
    result = await query_module.management_fee_query_service.details(
        AsyncSessionFacade(None), statements=statements, scope=scope
    )
    assert set(result) == {"s1", "s2", "s3"}
    assert result["s2"].projection is None
    assert result["s1"].projection is not None
    assert result["s1"].projection.lines[0].deferral_reason == "下月补齐"
    # 意图：读放大收口——每主体一次事实加载、全批一次边界校验与一次标记查询。
    query_module.visible_fee_statement_ids.assert_awaited_once()
    assert query_module.visible_fee_statement_ids.await_args.kwargs[
        "statement_ids"
    ] == ("s1", "s2", "s3")
    assert (
        query_module.management_fee_query_repository.load_facts.await_count == 2
    )
    query_module.management_fee_deferral_repository.list_marks_for_statements.assert_awaited_once()


async def test_details_hidden_statement_fails_whole_batch(monkeypatch):
    statements = (statement_row("s1", "owner-a", "2026-10"),)
    patch_batch_seams(
        monkeypatch,
        visible_ids=set(),
        facts_by_owner=[],
    )
    scope = EffectivePartyScope(
        user_id="actor", source="explicit", scope_mode="manager",
        manager_party_ids=["other-manager"],
    )
    with pytest.raises(ResourceNotFoundError):
        await query_module.management_fee_query_service.details(
            AsyncSessionFacade(None), statements=statements, scope=scope
        )
    # 授权失败不触发任何事实或标记读取。
    query_module.management_fee_query_repository.load_facts.assert_not_awaited()


async def test_manager_visibility_filter_runs_once_per_owner(monkeypatch):
    statements = (
        statement_row("s1", "owner-a", "2026-10"),
        statement_row("s3", "owner-a", "2026-11"),
    )
    data = facts(
        (
            Row(id="s1", period="2026-10", status=None),
            Row(id="s3", period="2026-11", status=None),
        )
    )
    data.contracts[0].upstream_contract_id = None
    data.contracts += (
        Row(id="hidden", upstream_contract_id=None, tenant_party_id="hidden-tenant"),
    )
    data.obligations += (
        Row(
            id="hidden-entry",
            contract_id="hidden",
            period="2026-09",
            due_amount=Decimal("100"),
            voided_at=None,
        ),
    )
    data.tenant_names["hidden-tenant"] = "隐藏租户"
    patch_batch_seams(
        monkeypatch,
        visible_ids={"s1", "s3"},
        facts_by_owner=[data],
    )
    lookup = AsyncMock(return_value={"tm"})
    monkeypatch.setattr(asset_contract_repository, "terminal_ids_in_scope", lookup)
    scope = EffectivePartyScope(
        user_id="actor", source="explicit", scope_mode="manager",
        manager_party_ids=["manager"],
    )
    result = await query_module.management_fee_query_service.details(
        AsyncSessionFacade(None), statements=statements, scope=scope
    )
    assert result["s1"].projection.upstream_missing_entry_ids == ("entry",)
    assert result["s3"].projection.upstream_missing_entry_ids == ("entry",)
    # 意图：同一主体的可见性过滤只算一次，不再逐合同逐单重查。
    lookup.assert_awaited_once()


@pytest.fixture
def boundary_database():
    engine = create_engine("sqlite://")
    for model in (ManagementFeeStatement, UpstreamContract):
        model.__table__.create(engine)
    with Session(engine, expire_on_commit=False) as session:
        session.add_all(
            [
                ManagementFeeStatement(
                    id="a1",
                    owner_party_id="owner-a",
                    period="2026-10",
                    statement_number="MF-A-10",
                    version=1,
                ),
                ManagementFeeStatement(
                    id="a2",
                    owner_party_id="owner-a",
                    period="2026-09",
                    statement_number="MF-A-09",
                    status="confirmed",
                    upstream_contract_ids=["up"],
                    base_amount=Decimal("100"),
                    fee_amount=Decimal("10"),
                    stamped_document_id="doc",
                    confirmed_at=datetime(2026, 10, 1, tzinfo=UTC),
                    confirmed_by="actor",
                    version=1,
                ),
                ManagementFeeStatement(
                    id="b1",
                    owner_party_id="owner-b",
                    period="2026-10",
                    statement_number="MF-B-10",
                    version=1,
                ),
                UpstreamContract(
                    id="agg-a-1",
                    contract_number="AGG-A-1",
                    contract_type="management_agreement",
                    name="A 管理协议一",
                    owner_party_id="owner-a",
                    operator_party_id="m1",
                    start_date=date(2026, 1, 1),
                    end_date=date(2027, 1, 1),
                    management_fee_rate=Decimal("0.1"),
                    scan_document_id="scan",
                    version=1,
                ),
                UpstreamContract(
                    id="agg-a-2",
                    contract_number="AGG-A-2",
                    contract_type="management_agreement",
                    name="A 管理协议二",
                    owner_party_id="owner-a",
                    operator_party_id="other",
                    start_date=date(2026, 1, 1),
                    end_date=date(2027, 1, 1),
                    management_fee_rate=Decimal("0.1"),
                    scan_document_id="scan",
                    version=1,
                ),
                UpstreamContract(
                    id="lease-a",
                    contract_number="LEASE-A",
                    contract_type="lease",
                    name="A 租赁合同",
                    owner_party_id="owner-a",
                    operator_party_id="other",
                    start_date=date(2026, 1, 1),
                    end_date=date(2027, 1, 1),
                    scan_document_id="scan",
                    version=1,
                ),
                UpstreamContract(
                    id="agg-b-1",
                    contract_number="AGG-B-1",
                    contract_type="management_agreement",
                    name="B 管理协议",
                    owner_party_id="owner-b",
                    operator_party_id="m1",
                    start_date=date(2026, 1, 1),
                    end_date=date(2027, 1, 1),
                    management_fee_rate=Decimal("0.1"),
                    scan_document_id="scan",
                    version=1,
                ),
            ]
        )
        session.commit()
        yield session
    engine.dispose()


@pytest.mark.parametrize(
    ("scope_mode", "owner_party_ids", "manager_party_ids", "expected"),
    [
        ("unrestricted", [], [], {"a1", "a2", "b1"}),
        ("owner", ["owner-a"], [], {"a1", "a2"}),
        # A 的两份协议未全被 m1 覆盖，整主体排除；B 全覆盖。
        ("manager", [], ["m1"], {"b1"}),
        ("manager", [], ["m1", "other"], {"a1", "a2", "b1"}),
        # all 模式取两轴并集：owner 轴授予 A，manager 轴全覆盖授予 B。
        ("all", ["owner-a"], ["m1"], {"a1", "a2", "b1"}),
    ],
)
async def test_visible_fee_statement_ids_boundary_semantics(
    boundary_database, scope_mode, owner_party_ids, manager_party_ids, expected
):
    db = AsyncSessionFacade(boundary_database)
    scope = EffectivePartyScope(
        user_id="actor", source="explicit", scope_mode=scope_mode,
        owner_party_ids=owner_party_ids, manager_party_ids=manager_party_ids,
    )
    result = await visible_fee_statement_ids(
        db,
        statement_ids=("a1", "a2", "b1", "missing"),
        scope=scope,
    )
    assert result == expected


async def test_visible_fee_statement_ids_empty_input_skips_query():
    db = Row(execute=AsyncMock())
    result = await visible_fee_statement_ids(
        db, statement_ids=(), scope=EffectivePartyScope(
            user_id="actor", source="explicit", scope_mode="unrestricted"
        )
    )
    assert result == set()
    db.execute.assert_not_awaited()


@pytest.fixture
def marks_database():
    engine = create_engine("sqlite://")
    ManagementFeeDeferral.__table__.create(engine)
    with Session(engine, expire_on_commit=False) as session:
        session.add_all(
            [
                ManagementFeeDeferral(
                    id="mark-1",
                    statement_id="s1",
                    rent_ledger_entry_id="entry-1",
                    reason="下月补齐",
                    created_by="actor",
                ),
                ManagementFeeDeferral(
                    id="mark-2",
                    statement_id="s2",
                    rent_ledger_entry_id="entry-2",
                    reason="争议中",
                    created_by="actor",
                ),
                ManagementFeeDeferral(
                    id="mark-3",
                    statement_id="s2",
                    rent_ledger_entry_id="entry-3",
                    reason="顺延",
                    created_by="actor",
                ),
            ]
        )
        session.commit()
        yield session
    engine.dispose()


async def test_list_marks_for_statements_groups_by_statement(marks_database):
    grouped = await management_fee_deferral_repository.list_marks_for_statements(
        AsyncSessionFacade(marks_database), statement_ids=("s1", "s2")
    )
    assert set(grouped) == {"s1", "s2"}
    assert tuple(mark.id for mark in grouped["s2"]) == ("mark-2", "mark-3")


async def test_list_marks_for_statements_empty_input_skips_query():
    db = Row(execute=AsyncMock())
    assert (
        await management_fee_deferral_repository.list_marks_for_statements(
            db, statement_ids=()
        )
        == {}
    )
    db.execute.assert_not_awaited()
