"""Business audit payloads are scoped and never expose private fields."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from src.core.exception_handler import BaseBusinessError, PartyScopeForbiddenError
from src.services.asset_operations.business_change_service import (
    BusinessChangeService,
    redact_snapshot,
)
from src.services.party_scope_resolver import EffectivePartyScope

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "period", ["2026-13", "2026-00", "invalid", "2026-1", "0000-01"]
)
async def test_invalid_period_is_a_stable_business_error(period):
    with pytest.raises(BaseBusinessError) as error:
        await BusinessChangeService().list_events(
            None,
            scope=EffectivePartyScope(
                user_id="actor",
                source="explicit",
                scope_mode="unrestricted",
            ),
            period=period,
        )
    assert error.value.code == "INVALID_PERIOD"
    assert error.value.status_code == 400


def test_redaction_recurses_without_mutating_input():
    value = {
        "name": "物业",
        "phone": "13812345678",
        "nested": [{"id_card": "secret", "amount": "20"}],
    }
    assert redact_snapshot(value) == {
        "name": "物业",
        "phone": "***",
        "nested": [{"id_card": "***", "amount": "20"}],
    }
    assert value["phone"] == "13812345678"


@pytest.mark.asyncio
async def test_missing_party_scope_fails_before_query():
    with pytest.raises(PartyScopeForbiddenError):
        await BusinessChangeService().list_events(
            None,
            scope=EffectivePartyScope(
                user_id="u", source="explicit", scope_mode="owner"
            ),
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mode,owners,managers", [("owner", [], ["other"]), ("manager", ["other"], [])]
)
async def test_wrong_scope_axis_fails_before_query(mode, owners, managers):
    with pytest.raises(PartyScopeForbiddenError):
        await BusinessChangeService().list_events(
            None,
            scope=EffectivePartyScope(
                user_id="actor",
                source="explicit",
                scope_mode=mode,
                owner_party_ids=owners,
                manager_party_ids=managers,
            ),
        )


@pytest.mark.asyncio
async def test_period_uses_shanghai_month_boundaries(monkeypatch):
    from src.services.asset_operations import business_change_service as module

    query = AsyncMock(return_value=((), 0))
    monkeypatch.setattr(module.business_change_repository, "list_events", query)
    scope = EffectivePartyScope(
        user_id="actor", source="explicit", scope_mode="unrestricted"
    )
    assert await BusinessChangeService().list_events(
        None, scope=scope, period="2026-01"
    ) == ([], 0)
    args = query.call_args.kwargs
    assert args["since"].astimezone(UTC) == datetime(2025, 12, 31, 16, tzinfo=UTC)
    assert args["until"].astimezone(UTC) == datetime(2026, 1, 31, 16, tzinfo=UTC)
