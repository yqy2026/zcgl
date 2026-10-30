"""Fee deferral commands preserve scope, version, audit and replay ordering."""

from types import SimpleNamespace as Row
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.schemas.management_fee_commands import ManagementFeeDeferralRequest
from src.services.asset_operations import management_fee_command_service as module
from src.services.party_scope_resolver import EffectivePartyScope

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


@pytest.fixture
def setup(monkeypatch):
    statement = Row(
        id="st", owner_party_id="owner", period="2026-10", version=2, status=None
    )
    detail = Row(
        statement=statement,
        projection=Row(
            lines=(
                Row(
                    rent_ledger_entry_id="rent",
                    terminal_contract_id="tm",
                    deferred_amount=100,
                ),
            )
        ),
    )
    monkeypatch.setattr(
        module.management_fee_query_service, "detail", AsyncMock(return_value=detail)
    )
    monkeypatch.setattr(
        module.management_fee_statement_repository, "lock_owner", AsyncMock()
    )
    monkeypatch.setattr(
        module.management_fee_statement_repository,
        "get_statement",
        AsyncMock(return_value=statement),
    )
    monkeypatch.setattr(
        module.asset_contract_repository,
        "get_write_receipt",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        module.management_fee_deferral_repository,
        "list_marks",
        AsyncMock(return_value=()),
    )
    monkeypatch.setattr(
        module.management_fee_deferral_repository, "add_mark", AsyncMock()
    )
    monkeypatch.setattr(module, "audit", AsyncMock())
    monkeypatch.setattr(module, "receipt", AsyncMock())
    db = MagicMock(flush=AsyncMock(), commit=AsyncMock(), rollback=AsyncMock())
    scope = EffectivePartyScope(
        user_id="actor",
        source="explicit",
        scope_mode="owner",
        owner_party_ids=["owner"],
    )
    request = ManagementFeeDeferralRequest(
        rent_ledger_entry_id="rent", reason="下月补齐", expected_version=2
    )
    return (
        statement,
        db,
        dict(
            statement_id="st",
            request=request,
            actor_id="actor",
            scope=scope,
            idempotency_key="key",
        ),
    )


async def test_deferral_writes_mark_audit_and_receipt_then_commits(setup):
    statement, db, kwargs = setup
    result = await module.management_fee_command_service.defer_line(db, **kwargs)
    assert result.version == statement.version == 3
    module.management_fee_deferral_repository.add_mark.assert_awaited_once()
    module.audit.assert_awaited_once()
    module.receipt.assert_awaited_once()
    db.commit.assert_awaited_once()


async def test_locked_statement_rolls_back_without_mark(setup):
    statement, db, kwargs = setup
    statement.status = "confirmed"
    with pytest.raises(Exception) as caught:
        await module.management_fee_command_service.defer_line(db, **kwargs)
    assert caught.value.code == "MANAGEMENT_FEE_STATEMENT_LOCKED"
    module.management_fee_deferral_repository.add_mark.assert_not_awaited()
    db.rollback.assert_awaited_once()


async def test_replay_precedes_optimistic_version_and_does_not_write(
    setup, monkeypatch
):
    statement, db, kwargs = setup
    statement.version = 9
    request_fingerprint = module.fingerprint(
        "defer_management_fee_line", "st", kwargs["request"]
    )
    module.asset_contract_repository.get_write_receipt.return_value = Row(
        request_fingerprint=request_fingerprint,
        result_data={"statement_id": "st", "version": 3, "idempotent": False},
    )
    result = await module.management_fee_command_service.defer_line(db, **kwargs)
    assert result.idempotent is True
    assert result.version == 3
    module.management_fee_deferral_repository.add_mark.assert_not_awaited()
    db.commit.assert_not_awaited()


async def test_stale_version_rolls_back_without_mark(setup):
    statement, db, kwargs = setup
    statement.version = 3
    with pytest.raises(module.AssetOperationsVersionConflictError):
        await module.management_fee_command_service.defer_line(db, **kwargs)
    module.management_fee_deferral_repository.add_mark.assert_not_awaited()
    db.rollback.assert_awaited_once()


async def test_same_key_changed_reason_is_an_idempotency_conflict(setup):
    statement, db, kwargs = setup
    module.asset_contract_repository.get_write_receipt.return_value = Row(
        request_fingerprint="different", result_data={}
    )
    with pytest.raises(Exception) as caught:
        await module.management_fee_command_service.defer_line(db, **kwargs)
    assert caught.value.code == "IDEMPOTENCY_CONFLICT"
    module.management_fee_deferral_repository.add_mark.assert_not_awaited()
    db.rollback.assert_awaited_once()


async def test_audit_failure_rolls_back_mark_and_receipt(setup):
    statement, db, kwargs = setup
    module.audit.side_effect = RuntimeError("audit unavailable")
    with pytest.raises(RuntimeError, match="audit unavailable"):
        await module.management_fee_command_service.defer_line(db, **kwargs)
    db.rollback.assert_awaited_once()
    db.commit.assert_not_awaited()
    module.receipt.assert_not_awaited()
