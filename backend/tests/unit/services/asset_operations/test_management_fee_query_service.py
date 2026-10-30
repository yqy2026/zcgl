"""Management fee reads keep confirmed snapshots immutable and late rows unique."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace as Row
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.exception_handler import ResourceNotFoundError
from src.crud.management_fee_queries import (
    ManagementFeeQueryFacts,
    management_fee_query_repository,
)
from src.services.asset_operations import management_fee_query_service as query_module
from src.services.asset_operations.management_fee_query_service import project_fee_facts
from src.services.party_scope_resolver import EffectivePartyScope

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def deferral_marks(monkeypatch):
    monkeypatch.setattr(
        query_module.management_fee_deferral_repository,
        "list_marks",
        AsyncMock(return_value=()),
    )


@pytest.mark.asyncio
async def test_query_contracts_require_owner_lessor_and_receipt_kind():
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    db = Row(execute=AsyncMock(return_value=result))
    await management_fee_query_repository.load_facts(db, owner_party_id="owner")
    contract_query = db.execute.await_args_list[1].args[0]
    sql = str(contract_query)
    assert "terminal_contracts.lessor_party_id =" in sql
    assert "terminal_contracts.contract_mode =" in sql
    assert "terminal_contracts.rent_collector =" in sql
    assert "owner" in contract_query.compile().params.values()
    assert contract_query.get_execution_options()["populate_existing"] is True
    assert (
        db.execute.await_args_list[0]
        .args[0]
        .get_execution_options()["populate_existing"]
        is True
    )


@pytest.mark.asyncio
async def test_manager_missing_upstream_warnings_respect_terminal_scope(monkeypatch):
    data = facts()
    data.contracts[0].upstream_contract_id = None
    data.contracts += (
        Row(id="hidden", upstream_contract_id=None, tenant_party_id="hidden-tenant"),
    )
    data.obligations += (
        Row(
            id="hidden-entry",
            contract_id="hidden",
            period="2026-10",
            due_amount=Decimal("100"),
            voided_at=None,
        ),
    )
    data.tenant_names["hidden-tenant"] = "隐藏租户"
    statement = Row(id="first", owner_party_id="owner", period="2026-10", status=None)
    monkeypatch.setattr(
        query_module.management_fee_statement_repository,
        "get_statement",
        AsyncMock(return_value=statement),
    )
    monkeypatch.setattr(
        query_module.management_fee_query_repository,
        "load_facts",
        AsyncMock(return_value=data),
    )
    lookup = AsyncMock(side_effect=[data.contracts[0], None])
    monkeypatch.setattr(query_module.asset_contract_repository, "get_terminal", lookup)
    scope = EffectivePartyScope(
        user_id="actor",
        source="explicit",
        scope_mode="manager",
        manager_party_ids=["manager"],
    )
    result = await query_module.management_fee_query_service.detail(
        Row(), statement_id="first", scope=scope
    )
    assert result.projection.upstream_missing_entry_ids == ("entry",)
    assert lookup.await_count == 2


@pytest.mark.asyncio
async def test_confirmed_snapshot_is_not_reprojected(monkeypatch):
    data = facts()
    saved = Row(id="saved", statement_id="old")
    data.lines = (saved,)
    statement = Row(
        id="old", owner_party_id="owner", period="2026-09", status="confirmed"
    )
    monkeypatch.setattr(
        query_module.management_fee_statement_repository,
        "get_statement",
        AsyncMock(return_value=statement),
    )
    monkeypatch.setattr(
        query_module.management_fee_query_repository,
        "load_facts",
        AsyncMock(return_value=data),
    )
    monkeypatch.setattr(
        query_module,
        "project_fee_facts",
        lambda *args, **kwargs: pytest.fail("confirmed snapshot was recomputed"),
    )
    scope = EffectivePartyScope(
        user_id="actor",
        source="explicit",
        scope_mode="owner",
        owner_party_ids=["owner"],
    )
    result = await query_module.management_fee_query_service.detail(
        Row(), statement_id="old", scope=scope
    )
    assert result.snapshot_lines == (saved,)
    assert result.projection is None


@pytest.mark.asyncio
async def test_partial_manager_scope_cannot_read_whole_owner_statement(monkeypatch):
    data = facts()
    data.agreements += (Row(id="other", operator_party_id="other-manager"),)
    statement = Row(
        id="old", owner_party_id="owner", period="2026-09", status="confirmed"
    )
    monkeypatch.setattr(
        query_module.management_fee_statement_repository,
        "get_statement",
        AsyncMock(return_value=statement),
    )
    monkeypatch.setattr(
        query_module.management_fee_query_repository,
        "load_facts",
        AsyncMock(return_value=data),
    )
    scope = EffectivePartyScope(
        user_id="actor",
        source="explicit",
        scope_mode="manager",
        manager_party_ids=["manager"],
    )
    with pytest.raises(ResourceNotFoundError):
        await query_module.management_fee_query_service.detail(
            Row(), statement_id="old", scope=scope
        )


def facts():
    return ManagementFeeQueryFacts(
        agreements=(
            Row(
                id="up", management_fee_rate=Decimal("0.1"), operator_party_id="manager"
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
        statements=(
            Row(id="old", period="2026-09", status="confirmed"),
            Row(id="first", period="2026-10", status=None),
            Row(id="later", period="2026-11", status=None),
        ),
        lines=(),
    )


def test_late_obligation_enters_only_earliest_open_statement():
    data = facts()
    first = project_fee_facts(
        data, statement=data.statements[1], today=date(2026, 10, 10)
    )
    later = project_fee_facts(
        data, statement=data.statements[2], today=date(2026, 10, 10)
    )
    assert len(first.lines) == 1
    assert later.lines == ()


def test_earlier_missing_month_draft_does_not_swallow_later_late_rent():
    data = facts()
    data.statements = (
        Row(id="backfill", period="2026-08", status=None),
        *data.statements,
    )
    result = project_fee_facts(
        data, statement=data.statements[2], today=date(2026, 10, 10)
    )
    assert len(result.lines) == 1
    assert result.lines[0].rent_period == "2026-09"


@pytest.mark.asyncio
async def test_persisted_deferral_is_applied_to_open_projection(monkeypatch):
    data = facts()
    statement = Row(id="first", owner_party_id="owner", period="2026-10", status=None)
    monkeypatch.setattr(
        query_module.management_fee_statement_repository,
        "get_statement",
        AsyncMock(return_value=statement),
    )
    monkeypatch.setattr(
        query_module.management_fee_query_repository,
        "load_facts",
        AsyncMock(return_value=data),
    )
    monkeypatch.setattr(query_module, "business_today", lambda: date(2026, 10, 10))
    query_module.management_fee_deferral_repository.list_marks.return_value = (
        Row(rent_ledger_entry_id="entry", reason="下月补齐"),
    )
    scope = EffectivePartyScope(
        user_id="actor",
        source="explicit",
        scope_mode="owner",
        owner_party_ids=["owner"],
    )
    result = await query_module.management_fee_query_service.detail(
        Row(), statement_id="first", scope=scope
    )
    assert result.projection.status == "pending_stamp"
    assert result.projection.lines[0].deferral_reason == "下月补齐"


def test_unbound_owner_obligation_is_warning_only():
    data = facts()
    data.contracts[0].upstream_contract_id = None
    result = project_fee_facts(
        data, statement=data.statements[1], today=date(2026, 10, 10)
    )
    assert result.lines == ()
    assert result.upstream_missing_entry_ids == ("entry",)


def test_prior_snapshot_receipts_are_subtracted_and_remaining_carried():
    data = facts()
    data.lines = (
        Row(
            statement_id="old",
            rent_ledger_entry_id="entry",
            counted_record_ids=["paid"],
            deferred_amount=Decimal("60"),
        ),
    )
    data.records = (
        Row(
            id="paid",
            record_type="owner_reported_receipt",
            ledger_entry_id="entry",
            amount=Decimal("40"),
            occurred_on=date(2026, 9, 15),
        ),
    )
    result = project_fee_facts(
        data, statement=data.statements[1], today=date(2026, 10, 10)
    )
    assert result.lines[0].scheduled_rent == Decimal("60")
    assert result.base_amount == 0
    assert result.lines[0].carried_from_statement_id == "old"


def test_reversed_owner_receipts_are_not_counted():
    data = facts()
    data.records = (
        Row(
            id="r",
            record_type="owner_reported_receipt",
            ledger_entry_id="entry",
            amount=Decimal("100"),
            occurred_on=date(2026, 10, 1),
            reverses_record_id=None,
        ),
        Row(id="rev", record_type="reversal", reverses_record_id="r"),
    )
    result = project_fee_facts(
        data, statement=data.statements[1], today=date(2026, 10, 10)
    )
    assert result.base_amount == 0
