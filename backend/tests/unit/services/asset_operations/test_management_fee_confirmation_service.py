"""Confirmation rejects incomplete statements and freezes exact projections."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace as Row
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.schemas.management_fee_commands import (
    ManagementFeeConfirmationRequest,
    ManagementFeeSuccessorRequest,
)
from src.services.asset_operations import management_fee_confirmation_service as module
from src.services.asset_operations.management_fee_rules import (
    AgreementFact,
    ObligationFact,
    ReceiptFact,
    project_statement,
)
from src.services.party_scope_resolver import EffectivePartyScope

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


@pytest.fixture
def setup(monkeypatch):
    statement = Row(
        id="st",
        owner_party_id="owner",
        period="2026-10",
        status=None,
        version=2,
        stamped_document_id="doc",
        successor_statement_id=None,
    )
    projection = Row(lines=(), base_amount=0, fee_amount=0, upstream_contract_ids=())
    detail = Row(statement=statement, projection=projection)
    monkeypatch.setattr(
        module.management_fee_query_service, "detail", AsyncMock(return_value=detail)
    )
    repo = module.management_fee_statement_repository
    monkeypatch.setattr(repo, "lock_owner", AsyncMock())
    monkeypatch.setattr(repo, "list_statements", AsyncMock(return_value=(statement,)))
    monkeypatch.setattr(repo, "add_lines", AsyncMock())
    monkeypatch.setattr(repo, "add_statement", AsyncMock())
    monkeypatch.setattr(repo, "ensure_draft", AsyncMock())
    monkeypatch.setattr(
        module.asset_contract_repository,
        "get_write_receipt",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(module.business_change_repository, "add", AsyncMock())
    monkeypatch.setattr(module, "receipt", AsyncMock())
    db = MagicMock(flush=AsyncMock(), commit=AsyncMock(), rollback=AsyncMock())
    scope = EffectivePartyScope(
        user_id="actor",
        source="explicit",
        scope_mode="owner",
        owner_party_ids=["owner"],
    )
    return (
        statement,
        projection,
        db,
        dict(statement_id="st", actor_id="actor", scope=scope, idempotency_key="key"),
    )


async def test_confirmation_freezes_totals_and_audit_in_same_transaction(setup):
    statement, projection, db, args = setup
    result = await module.management_fee_confirmation_service.confirm(
        db, request=ManagementFeeConfirmationRequest(expected_version=2), **args
    )
    assert statement.status == "confirmed"
    assert statement.base_amount == 0
    assert result.version == 3
    module.receipt.assert_awaited_once()
    module.business_change_repository.add.assert_awaited_once()
    db.commit.assert_awaited_once()


@pytest.mark.parametrize("failure", ["stamp", "unprocessed", "sequence"])
async def test_confirmation_rejects_incomplete_facts(setup, failure):
    statement, projection, db, args = setup
    if failure == "stamp":
        statement.stamped_document_id = None
    elif failure == "unprocessed":
        projection.lines = (Row(processed=False),)
    else:
        module.management_fee_statement_repository.list_statements.return_value += (
            Row(id="earlier", period="2026-09", status=None),
        )
    with pytest.raises(Exception) as caught:
        await module.management_fee_confirmation_service.confirm(
            db, request=ManagementFeeConfirmationRequest(expected_version=2), **args
        )
    assert caught.value.code in {
        "STAMPED_DOCUMENT_REQUIRED",
        "MANAGEMENT_FEE_LINES_UNRESOLVED",
        "MANAGEMENT_FEE_SEQUENCE_CONFLICT",
    }
    db.rollback.assert_awaited_once()
    db.commit.assert_not_awaited()


async def test_successor_retains_old_snapshot_and_drops_stamp(setup):
    statement, projection, db, args = setup
    statement.status = "confirmed"
    result = await module.management_fee_confirmation_service.supersede(
        db,
        request=ManagementFeeSuccessorRequest(expected_version=2, reason="到账有误"),
        **args,
    )
    assert statement.status == "superseded"
    assert statement.stamped_document_id == "doc"
    new = module.management_fee_statement_repository.add_statement.await_args.kwargs[
        "statement"
    ]
    assert new.period == "2026-10" and new.status is None
    assert new.stamped_document_id is None
    assert new.predecessor_statement_id == "st"
    assert statement.successor_statement_id == result.successor_statement_id


async def test_replay_is_before_version_and_status(setup):
    statement, projection, db, args = setup
    request = ManagementFeeConfirmationRequest(expected_version=2)
    statement.version = 9
    statement.status = "confirmed"
    module.asset_contract_repository.get_write_receipt.return_value = Row(
        request_fingerprint=module.fingerprint(
            "confirm_management_fee_statement", "st", request
        ),
        result_data={"statement_id": "st", "version": 3},
    )
    result = await module.management_fee_confirmation_service.confirm(
        db, request=request, **args
    )
    assert result.version == 3 and result.idempotent
    module.management_fee_statement_repository.add_lines.assert_not_awaited()


async def test_confirmation_snapshots_partial_receipt_and_creates_next_month(setup):
    statement, projection, db, args = setup
    projected = project_statement(
        statement_period="2026-10",
        agreements=(AgreementFact("up", Decimal("0.1")),),
        obligations=(
            ObligationFact(
                "rent", "tm", "up", "2026-10", Decimal("100"), False, "租户", ("unit",)
            ),
        ),
        receipts=(ReceiptFact("receipt", "rent", Decimal("40"), date(2026, 10, 15)),),
        already_counted_record_ids=frozenset(),
        confirmed_periods=frozenset(),
        prior_statement_id=None,
        prior_statement_confirmed=False,
        prior_deferred_rows=(),
        deferral_marks={"rent": "下月补齐"},
        today=date(2026, 10, 16),
    )
    module.management_fee_query_service.detail.return_value = Row(
        statement=statement, projection=projected
    )
    await module.management_fee_confirmation_service.confirm(
        db, request=ManagementFeeConfirmationRequest(expected_version=2), **args
    )
    lines = module.management_fee_statement_repository.add_lines.await_args.kwargs[
        "lines"
    ]
    assert len(lines) == 1
    assert lines[0].counted_record_ids == ["receipt"]
    assert lines[0].deferred_amount == Decimal("60")
    assert statement.base_amount == Decimal("40")
    assert statement.fee_amount == Decimal("4.00")
    module.management_fee_statement_repository.ensure_draft.assert_awaited_once_with(
        db, owner_party_id="owner", period="2026-11"
    )


async def test_confirmed_statement_cannot_confirm_again_under_new_key(setup):
    statement, projection, db, args = setup
    statement.status = "confirmed"
    with pytest.raises(Exception) as caught:
        await module.management_fee_confirmation_service.confirm(
            db, request=ManagementFeeConfirmationRequest(expected_version=2), **args
        )
    assert caught.value.code == "MANAGEMENT_FEE_STATEMENT_LOCKED"


async def test_only_latest_confirmed_statement_can_be_corrected(setup):
    statement, projection, db, args = setup
    statement.status = "confirmed"
    module.management_fee_statement_repository.list_statements.return_value += (
        Row(id="later", period="2026-11", status="confirmed"),
    )
    with pytest.raises(Exception) as caught:
        await module.management_fee_confirmation_service.supersede(
            db,
            request=ManagementFeeSuccessorRequest(expected_version=2, reason="有误"),
            **args,
        )
    assert caught.value.code == "MANAGEMENT_FEE_SEQUENCE_CONFLICT"
    module.management_fee_statement_repository.add_statement.assert_not_awaited()


async def test_correction_requires_reason(setup):
    statement, projection, db, args = setup
    with pytest.raises(Exception) as caught:
        await module.management_fee_confirmation_service.supersede(
            db,
            request=ManagementFeeSuccessorRequest(expected_version=2, reason=" "),
            **args,
        )
    assert caught.value.code == "CORRECTION_REASON_REQUIRED"


async def test_audit_failure_rolls_back_confirmation_and_receipt(setup):
    statement, projection, db, args = setup
    module.business_change_repository.add.side_effect = RuntimeError("audit failed")
    with pytest.raises(RuntimeError, match="audit failed"):
        await module.management_fee_confirmation_service.confirm(
            db, request=ManagementFeeConfirmationRequest(expected_version=2), **args
        )
    db.rollback.assert_awaited_once()
    db.commit.assert_not_awaited()
    module.receipt.assert_not_awaited()


async def test_backfilled_statement_cannot_carry_into_confirmed_next_month(setup):
    statement, projection, db, args = setup
    projection.lines = (Row(processed=True, deferred_amount=60),)
    module.management_fee_statement_repository.list_statements.return_value += (
        Row(id="later", period="2026-11", status="confirmed"),
    )
    with pytest.raises(Exception) as caught:
        await module.management_fee_confirmation_service.confirm(
            db, request=ManagementFeeConfirmationRequest(expected_version=2), **args
        )
    assert caught.value.code == "MANAGEMENT_FEE_SEQUENCE_CONFLICT"
    module.management_fee_statement_repository.add_lines.assert_not_awaited()
    assert statement.status is None
    db.rollback.assert_awaited_once()
