"""Binding an existing direct lease creates fee identities in the same transaction."""

from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.asset_contract import TerminalContract
from src.schemas.asset_operations import TerminalContractUpdate
from src.services.asset_operations import contract_command_service as module
from src.services.asset_operations.contract_command_service import (
    AssetContractCommandService,
)
from src.services.asset_operations.management_fee_entry_service import (
    management_fee_entry_service,
)
from src.services.party_scope_resolver import EffectivePartyScope

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


@pytest.mark.parametrize(
    "previous,mode,expected",
    [(None, "direct_lease", 1), ("up-1", "direct_lease", 0), (None, "sublease", 0)],
)
async def test_binding_without_date_edit_ensures_fee_identities(
    monkeypatch, previous, mode, expected
):
    await exercise(monkeypatch, previous=previous, mode=mode, expected=expected)


async def test_fee_identity_failure_rolls_back_binding_transaction(monkeypatch):
    await exercise(
        monkeypatch, previous=None, mode="direct_lease", expected=1, fail=True
    )


async def exercise(monkeypatch, *, previous, mode, expected, fail=False):
    now = datetime(2026, 10, 29, tzinfo=UTC)
    contract = TerminalContract(
        id="terminal",
        contract_number="TM-1",
        contract_mode=mode,
        tenant_party_id="tenant",
        lessor_party_id="owner",
        upstream_contract_id=previous,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        deposit_months=Decimal("0"),
        deposit_amount=Decimal("0"),
        rent_collector="owner",
        version=1,
        scan_document_id="scan",
        created_at=now,
        updated_at=now,
    )
    repo = MagicMock(
        get_terminal=AsyncMock(return_value=contract),
        list_terminal_coverages=AsyncMock(return_value=()),
        list_lifecycle_events=AsyncMock(return_value=()),
        list_rent_schedules=AsyncMock(return_value=()),
    )
    service = AssetContractCommandService(repository=repo)
    monkeypatch.setattr(service, "_lock_exact_units", AsyncMock(return_value=()))
    monkeypatch.setattr(
        service, "_validate_upstream_link", AsyncMock(return_value=SimpleNamespace())
    )
    monkeypatch.setattr(module, "record_contract_change", AsyncMock())
    monkeypatch.setattr(
        module, "derive_terminal_contract_warnings", lambda *a, **kw: ()
    )
    monkeypatch.setattr(
        module,
        "TerminalContractResponse",
        SimpleNamespace(model_validate=lambda value: value),
    )
    ensure = AsyncMock(side_effect=RuntimeError("fee failure") if fail else None)
    monkeypatch.setattr(
        management_fee_entry_service, "ensure_bound_contract", ensure, raising=False
    )
    db = MagicMock(flush=AsyncMock(), commit=AsyncMock(), rollback=AsyncMock())
    scope = EffectivePartyScope(
        user_id="actor",
        source="explicit",
        scope_mode="owner",
        owner_party_ids=["owner"],
    )
    call = service.update_terminal(
        db,
        contract_id="terminal",
        request=TerminalContractUpdate(expected_version=1, upstream_contract_id="up-1"),
        actor_id="actor",
        scope=scope,
    )
    if fail:
        with pytest.raises(RuntimeError, match="fee failure"):
            await call
        db.commit.assert_not_awaited()
        db.rollback.assert_awaited_once()
    else:
        await call
        db.commit.assert_awaited_once()
        db.rollback.assert_not_awaited()
    assert ensure.await_count == expected
    if expected:
        ensure.assert_awaited_once_with(db, terminal_contract_id="terminal")
