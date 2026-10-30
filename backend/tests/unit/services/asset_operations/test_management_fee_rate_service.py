"""Rate changes invalidate open fee projections in the contract transaction."""

from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace as Row
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.asset_contract import UpstreamContract
from src.schemas.asset_operations import UpstreamContractUpdate
from src.services.asset_operations import contract_command_service as module
from src.services.asset_operations.contract_command_service import (
    AssetContractCommandService,
)
from src.services.asset_operations.management_fee_rate_service import (
    ManagementFeeRateService,
)
from src.services.party_scope_resolver import EffectivePartyScope

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


async def test_rate_change_invalidates_all_owner_drafts_only():
    rows = [
        Row(status=None, version=2),
        Row(status=None, version=5),
        Row(status="confirmed", version=3),
        Row(status="superseded", version=4),
    ]
    repo = MagicMock(
        lock_owner=AsyncMock(), list_statements=AsyncMock(return_value=rows)
    )
    db = MagicMock()
    await ManagementFeeRateService(repository=repo).invalidate(
        db, owner_party_id="owner"
    )
    assert [row.version for row in rows] == [3, 6, 3, 4]
    repo.lock_owner.assert_awaited_once_with(db, owner_party_id="owner")
    repo.list_statements.assert_awaited_once_with(
        db, owner_party_id="owner", for_update=True
    )
    db.commit.assert_not_called()
    db.flush.assert_not_called()


@pytest.mark.parametrize(
    "new_rate,expected", [(Decimal("0.2"), 1), (Decimal("0.1"), 0), (None, 0)]
)
async def test_upstream_update_invalidates_only_an_actual_rate_change(
    monkeypatch, new_rate, expected
):
    await exercise(monkeypatch, new_rate=new_rate, expected=expected)


async def test_invalidation_failure_rolls_back_contract_update(monkeypatch):
    await exercise(monkeypatch, new_rate=Decimal("0.2"), expected=1, fail=True)


async def exercise(monkeypatch, *, new_rate, expected, fail=False):
    now = datetime(2026, 10, 29, tzinfo=UTC)
    contract = UpstreamContract(
        id="up",
        contract_number="UP-1",
        contract_type="management_agreement",
        name="委托协议",
        owner_party_id="owner",
        operator_party_id="manager",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        payment_cycle="monthly",
        payment_day=15,
        management_fee_rate=Decimal("0.1"),
        deposit_amount=Decimal("0"),
        version=1,
        scan_document_id="scan",
        created_at=now,
        updated_at=now,
    )
    repo = MagicMock(
        get_upstream=AsyncMock(return_value=contract),
        list_upstream_coverages=AsyncMock(return_value=()),
        list_lifecycle_events=AsyncMock(return_value=()),
        list_rent_schedules=AsyncMock(return_value=()),
    )
    service = AssetContractCommandService(repository=repo)
    monkeypatch.setattr(service, "_lock_exact_units", AsyncMock(return_value=()))
    monkeypatch.setattr(module, "record_contract_change", AsyncMock())
    monkeypatch.setattr(
        module, "UpstreamContractResponse", Row(model_validate=lambda value: value)
    )
    invalidation = AsyncMock(
        side_effect=RuntimeError("fee invalidation failed") if fail else None
    )
    monkeypatch.setattr(module.management_fee_rate_service, "invalidate", invalidation)
    db = MagicMock(flush=AsyncMock(), commit=AsyncMock(), rollback=AsyncMock())
    scope = EffectivePartyScope(
        user_id="actor",
        source="explicit",
        scope_mode="owner",
        owner_party_ids=["owner"],
    )
    payload = {"expected_version": 1}
    if new_rate is not None:
        payload["management_fee_rate"] = new_rate
    call = service.update_upstream(
        db,
        contract_id="up",
        request=UpstreamContractUpdate(**payload),
        actor_id="actor",
        scope=scope,
    )
    if fail:
        with pytest.raises(RuntimeError, match="fee invalidation failed"):
            await call
        db.rollback.assert_awaited_once()
        db.commit.assert_not_awaited()
    else:
        await call
        db.commit.assert_awaited_once()
    assert invalidation.await_count == expected
