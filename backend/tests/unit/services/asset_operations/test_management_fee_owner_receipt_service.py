"""Statement receipt writes delegate to the single rent fact writer."""

from datetime import date
from types import SimpleNamespace as Row
from unittest.mock import AsyncMock

import pytest

from src.schemas.management_fee_commands import ManagementFeeOwnerReceiptRequest
from src.services.asset_operations import management_fee_owner_receipt_service as module
from src.services.party_scope_resolver import EffectivePartyScope

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


async def test_owner_receipt_uses_rent_service_with_fixed_record_type_and_context(
    monkeypatch,
):
    scope = EffectivePartyScope(
        user_id="actor",
        source="explicit",
        scope_mode="owner",
        owner_party_ids=["owner"],
    )
    detail = Row(
        projection=Row(lines=(Row(rent_ledger_entry_id="rent"),)), snapshot_lines=()
    )
    monkeypatch.setattr(
        module.management_fee_query_service, "detail", AsyncMock(return_value=detail)
    )
    register = AsyncMock(return_value="result")
    monkeypatch.setattr(module.rent_payment_command_service, "register", register)
    request = ManagementFeeOwnerReceiptRequest(
        rent_ledger_entry_id="rent",
        amount="100",
        occurred_on=date(2026, 10, 29),
        expected_version=2,
    )
    result = await module.management_fee_owner_receipt_service.register(
        None,
        statement_id="st",
        request=request,
        actor_id="actor",
        scope=scope,
        idempotency_key="key",
    )
    assert result == "result"
    assert register.await_args.kwargs["management_fee_statement_id"] == "st"
    assert register.await_args.kwargs["request"].record_type == "owner_reported_receipt"
    assert register.await_args.kwargs["request"].expected_version == 2


async def test_replay_can_reach_rent_receipt_after_line_disappears(monkeypatch):
    scope = EffectivePartyScope(
        user_id="actor",
        source="explicit",
        scope_mode="owner",
        owner_party_ids=["owner"],
    )
    monkeypatch.setattr(
        module.management_fee_query_service,
        "detail",
        AsyncMock(return_value=Row(projection=Row(lines=()), snapshot_lines=())),
    )
    register = AsyncMock(return_value=Row(idempotent=True, id="first-receipt"))
    monkeypatch.setattr(module.rent_payment_command_service, "register", register)
    request = ManagementFeeOwnerReceiptRequest(
        rent_ledger_entry_id="rent",
        amount="100",
        occurred_on=date(2026, 10, 29),
        expected_version=2,
    )
    result = await module.management_fee_owner_receipt_service.register(
        None,
        statement_id="st",
        request=request,
        actor_id="actor",
        scope=scope,
        idempotency_key="key",
    )
    assert result.idempotent is True
    assert result.id == "first-receipt"
    assert register.await_args.kwargs["management_fee_statement_id"] == "st"
