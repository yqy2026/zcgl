"""Fee HTTP projections serialize source identities and immutable snapshots."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace as Row
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.services.asset_operations import management_fee_response_service as module
from src.services.party_scope_resolver import EffectivePartyScope

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


def statement(status=None):
    return Row(
        id="st",
        owner_party_id="owner",
        period="2026-10",
        statement_number="MF-1",
        version=2,
        status=status,
        stamped_document_id=None,
        confirmed_at=None,
        confirmed_by=None,
        predecessor_statement_id=None,
        successor_statement_id=None,
        upstream_contract_ids=["up"],
        base_amount=Decimal("999"),
        fee_amount=Decimal("99"),
    )


def scope():
    return EffectivePartyScope(
        user_id="actor",
        source="explicit",
        scope_mode="owner",
        owner_party_ids=["owner"],
    )


async def test_draft_serializes_projection_without_persisted_derived_values(
    monkeypatch,
):
    projection = Row(
        status="collecting",
        deadline=date(2026, 11, 30),
        upstream_contract_ids=("up",),
        base_amount=Decimal("40"),
        fee_amount=Decimal("4"),
        lines=(),
        carried_waiting_hint=True,
        upstream_missing_entry_ids=("missing",),
        upstream_missing_warning="UPSTREAM_CONTRACT_MISSING",
    )
    monkeypatch.setattr(
        module.management_fee_query_service,
        "detail",
        AsyncMock(
            return_value=Row(
                statement=statement(), projection=projection, snapshot_lines=()
            )
        ),
    )
    result = await module.management_fee_response_service.get(
        MagicMock(), statement_id="st", scope=scope()
    )
    assert result.status == "collecting"
    assert result.fee_amount == Decimal("4")
    assert result.carried_waiting_hint is True
    assert "_sa_instance_state" not in result.model_dump()


async def test_confirmed_uses_snapshot_totals_without_current_projection(monkeypatch):
    monkeypatch.setattr(
        module.management_fee_query_service,
        "detail",
        AsyncMock(
            return_value=Row(
                statement=statement("confirmed"), projection=None, snapshot_lines=()
            )
        ),
    )
    result = await module.management_fee_response_service.get(
        MagicMock(), statement_id="st", scope=scope()
    )
    assert result.fee_amount == Decimal("99")
    assert result.status == "confirmed"
    assert result.deadline == date(2026, 11, 30)


@pytest.mark.parametrize("period", ["2026-13", "2026-1", "0000-01", "invalid"])
async def test_invalid_list_period_fails_before_repository(period, monkeypatch):
    query = AsyncMock()
    monkeypatch.setattr(
        module.management_fee_statement_repository, "list_for_period", query
    )
    with pytest.raises(Exception) as caught:
        await module.management_fee_response_service.list(
            MagicMock(), period=period, scope=scope()
        )
    assert caught.value.code == "INVALID_PERIOD"
    query.assert_not_awaited()


async def test_list_reauthorizes_each_scoped_candidate(monkeypatch):
    monkeypatch.setattr(
        module.management_fee_statement_repository,
        "list_for_period",
        AsyncMock(return_value=(statement("confirmed"),)),
    )
    read = AsyncMock(
        return_value=Row(
            statement=statement("confirmed"), projection=None, snapshot_lines=()
        )
    )
    monkeypatch.setattr(module.management_fee_query_service, "detail", read)
    result = await module.management_fee_response_service.list(
        MagicMock(), period="2026-10", scope=scope()
    )
    assert result.total == 1
    assert result.items[0].id == "st"
    read.assert_awaited_once()


async def test_snapshot_line_defaults_processed_without_exposing_storage_fields(
    monkeypatch,
):
    line = Row(
        id="line",
        statement_id="st",
        line_kind="carried",
        upstream_contract_id="up",
        terminal_contract_id="tm",
        rent_ledger_entry_id="rent",
        asset_unit_ids=["unit"],
        tenant_name_snapshot="租户",
        rent_period="2026-09",
        scheduled_rent=Decimal("40"),
        owner_received_amount=Decimal("20"),
        counted_record_ids=["receipt"],
        received_on=None,
        fee_rate=Decimal("0.1"),
        fee_amount=Decimal("2"),
        deferred_amount=Decimal("20"),
        deferral_reason="下月补齐",
        carried_from_statement_id="previous",
    )
    monkeypatch.setattr(
        module.management_fee_query_service,
        "detail",
        AsyncMock(
            return_value=Row(
                statement=statement("confirmed"),
                projection=None,
                snapshot_lines=(line,),
            )
        ),
    )
    result = await module.management_fee_response_service.get(
        MagicMock(), statement_id="st", scope=scope()
    )
    saved = result.lines[0]
    assert saved.processed is True
    assert saved.fee_amount == Decimal("2")
    assert saved.counted_record_ids == ["receipt"]
    assert "statement_id" not in saved.model_dump()


async def test_repository_list_sql_excludes_superseded_and_filters_whole_owner_scope():
    from sqlalchemy.dialects import postgresql

    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    db = Row(execute=AsyncMock(return_value=result))
    await module.management_fee_statement_repository.list_for_period(
        db, period="2026-10", scope=scope()
    )
    query = db.execute.await_args.args[0]
    sql = str(query.compile(dialect=postgresql.dialect()))
    assert "management_fee_statements.id IN (SELECT" in sql
    assert "management_fee_statements.status IS NULL" in sql
    assert "superseded" in query.compile().params.values()
    assert "2026-10" in query.compile().params.values()
