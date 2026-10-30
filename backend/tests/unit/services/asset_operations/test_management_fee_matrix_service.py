"""Annual fee totals count confirmed snapshots only."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace as Row
from unittest.mock import AsyncMock

import pytest

from src.services.asset_operations.management_fee_matrix_service import (
    management_fee_matrix_service as service,
)
from src.services.party_scope_resolver import EffectivePartyScope

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_matrix_statuses_and_confirmed_only_totals(monkeypatch):
    scope = EffectivePartyScope(
        user_id="actor", source="explicit", scope_mode="unrestricted"
    )
    facts = [
        (Row(id="a", owner_party_id="owner", period="2026-01"), "产权方"),
        (Row(id="b", owner_party_id="owner", period="2026-02"), "产权方"),
        (Row(id="c", owner_party_id="owner2", period="2026-03"), "产权方二"),
    ]
    repository = AsyncMock(return_value=facts)
    monkeypatch.setattr(service.repository, "list_year", repository)
    detail = AsyncMock(
        side_effect=[
            Row(status="confirmed", fee_amount=Decimal("12.34")),
            Row(status="pending_stamp", fee_amount=Decimal("99.99")),
            Row(status="confirmed", fee_amount=Decimal("7.77")),
        ]
    )
    monkeypatch.setattr(service.responses, "get", detail)
    result = await service.matrix(
        None, scope=scope, year=2026, today=date(2026, 10, 29)
    )
    assert result.total_confirmed_amount == Decimal("20.11")
    row = result.rows[0]
    assert row.owner_name == "产权方"
    assert len(row.months) == 12
    assert row.months[0].status == "confirmed"
    assert row.months[1].status == "pending_stamp"
    assert row.months[9].status == "missing"
    assert row.months[10].status == "upcoming"
    assert row.months[9].fee_amount is None
    assert row.total_confirmed_amount == Decimal("12.34")
    assert result.rows[1].total_confirmed_amount == Decimal("7.77")
    # V2-T24: the matrix total must equal the sum of its confirmed months.
    assert result.total_confirmed_amount == sum(
        (
            month.fee_amount or Decimal("0")
            for owner_row in result.rows
            for month in owner_row.months
            if month.status == "confirmed"
        ),
        Decimal("0"),
    )
    detail.assert_any_await(None, statement_id="a", scope=scope)
    repository.assert_awaited_once_with(None, scope=scope, year=2026)


@pytest.mark.asyncio
async def test_empty_scope_fails_before_query(monkeypatch):
    scope = EffectivePartyScope(user_id="actor", source="explicit", scope_mode="owner")
    repository = AsyncMock()
    monkeypatch.setattr(service.repository, "list_year", repository)
    with pytest.raises(Exception) as error:
        await service.matrix(None, scope=scope, year=2026)
    assert error.value.code == "PARTY_SCOPE_MISSING"
    repository.assert_not_awaited()


@pytest.mark.asyncio
async def test_empty_year_is_empty_without_fabricated_owners(monkeypatch):
    scope = EffectivePartyScope(
        user_id="actor", source="explicit", scope_mode="unrestricted"
    )
    monkeypatch.setattr(service.repository, "list_year", AsyncMock(return_value=[]))
    result = await service.matrix(
        None, scope=scope, year=2027, today=date(2026, 10, 29)
    )
    assert result.rows == []
    assert result.total_confirmed_amount == Decimal("0")
