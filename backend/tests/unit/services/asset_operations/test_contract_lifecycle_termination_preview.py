"""Termination preview binds the impact model before any event is written."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from src.core.exception_handler import PartyScopeForbiddenError
from src.models.asset_contract import (
    ContractLifecycleEvent,
    TerminalContract,
    TerminalContractAssetUnit,
)
from src.schemas.asset_operations import (
    TerminalContractTerminationCommitRequest,
    TerminalContractTerminationProposal,
)
from src.services.asset_operations.contract_lifecycle_command_service import (
    ContractLifecycleCommandService,
)
from src.services.asset_operations.errors import (
    AssetOperationsIdempotencyConflictError,
    AssetOperationsPreviewStaleError,
    AssetOperationsVersionConflictError,
    TerminalContractAlreadyTerminatedError,
)
from src.services.party_scope_resolver import EffectivePartyScope

NOW = datetime(2026, 10, 25, 1, 0, tzinfo=UTC)
EXPIRES_AT = NOW + timedelta(minutes=10)
SCOPE = EffectivePartyScope(
    user_id="actor-1",
    source="explicit",
    scope_mode="owner",
    owner_party_ids=["owner-1"],
)
OTHER_SCOPE = EffectivePartyScope(
    user_id="actor-1",
    source="explicit",
    scope_mode="manager",
    manager_party_ids=["manager-1"],
)


class _PreviewStore:
    def __init__(self) -> None:
        self.payloads: dict[str, dict[str, object]] = {}

    def issue(self, payload: dict[str, object]) -> tuple[str, datetime]:
        token = f"preview-token-{len(self.payloads)}"
        self.payloads[token] = dict(payload)
        return token, EXPIRES_AT

    def peek(self, raw_token: str) -> dict[str, object] | None:
        return self.payloads.get(raw_token)

    def delete(self, raw_token: str) -> bool:
        return self.payloads.pop(raw_token, None) is not None


class _Repository:
    def __init__(self) -> None:
        self.events: list[ContractLifecycleEvent] = []
        self.writes = 0
        self.truncations: list[tuple[str, date]] = []
        self.coverages = [
            TerminalContractAssetUnit(
                terminal_contract_id="terminal-1",
                asset_unit_id="unit-1",
                effective_from=date(2026, 1, 1),
                effective_to=date(2026, 12, 31),
            )
        ]
        self.terminal = TerminalContract(
            id="terminal-1",
            contract_number="TM-001",
            contract_mode="direct_lease",
            tenant_party_id="tenant-1",
            lessor_party_id="owner-1",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            deposit_amount=Decimal("20000"),
            rent_collector="owner",
            scan_document_id="scan-1",
        )
        self.terminal.version = 3

    async def get_lifecycle_event_by_idempotency_key(
        self, _db, *, idempotency_key: str
    ) -> ContractLifecycleEvent | None:
        for event in self.events:
            if event.idempotency_key == idempotency_key:
                return event
        return None

    async def get_terminal(
        self, _db, *, contract_id: str, scope: EffectivePartyScope, for_update: bool
    ) -> TerminalContract | None:
        if contract_id != "terminal-1" or scope is not SCOPE:
            return None
        return self.terminal

    async def list_lifecycle_events(
        self, _db, *, contract_kind: str, contract_id: str
    ) -> tuple[ContractLifecycleEvent, ...]:
        return tuple(
            event
            for event in self.events
            if event.contract_kind == contract_kind and event.contract_id == contract_id
        )

    async def list_terminal_coverages(
        self, _db, *, contract_id: str
    ) -> tuple[TerminalContractAssetUnit, ...]:
        return tuple(
            coverage
            for coverage in self.coverages
            if coverage.terminal_contract_id == contract_id
        )

    async def truncate_terminal_coverages(
        self, _db, *, contract_id: str, effective_date: date
    ) -> int:
        self.truncations.append((contract_id, effective_date))
        cutoff = effective_date - timedelta(days=1)
        for coverage in self.coverages:
            if coverage.terminal_contract_id == contract_id and (
                coverage.effective_to is None or coverage.effective_to > cutoff
            ):
                coverage.effective_to = cutoff
        return 1

    async def add_lifecycle_event(self, _db, *, event: ContractLifecycleEvent) -> None:
        self.writes += 1
        self.events.append(event)


class _DB:
    def add(self, event) -> None:
        if not hasattr(self, "audit_events"):
            self.audit_events = []
        self.audit_events.append(event)

    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


def _proposal() -> TerminalContractTerminationProposal:
    return TerminalContractTerminationProposal.model_validate(
        {
            "effective_date": "2026-06-30",
            "termination_type": "early",
            "handover_status": "pending",
            "deposit_settlement_status": "pending",
            "reason": "提前退租",
        }
    )


def _service(
    repository: _Repository, store: _PreviewStore
) -> ContractLifecycleCommandService:
    return ContractLifecycleCommandService(
        repository=repository,
        preview_store=store,
        clock=lambda: NOW,
        id_factory=lambda: "event-1",
    )


@pytest.mark.asyncio
async def test_preview_reports_coverage_impact_without_writes() -> None:
    repository = _Repository()
    store = _PreviewStore()
    service = _service(repository, store)
    db = _DB()

    preview = await service.preview_terminal_termination(
        db,
        contract_id="terminal-1",
        proposal=_proposal(),
        actor_id="actor-1",
        scope=SCOPE,
    )

    assert preview.contract_version == 3
    assert preview.effective_date == date(2026, 6, 30)
    assert preview.last_valid_day == date(2026, 6, 29)
    assert len(preview.coverage_impact) == 1
    impact = preview.coverage_impact[0]
    assert impact.asset_unit_id == "unit-1"
    assert impact.current_effective_to == date(2026, 12, 31)
    assert impact.new_effective_to == date(2026, 6, 29)
    assert list(preview.warnings) == ["deposit_unsettled"]
    assert repository.writes == 0
    assert repository.truncations == []
    assert db.commits == 0

    token_payload = store.payloads[preview.preview_token]
    assert token_payload["actor_id"] == "actor-1"
    assert token_payload["action"] == "terminal_termination"
    assert token_payload["contract_id"] == "terminal-1"
    assert token_payload["versions"] == {"terminal-1": 3}


@pytest.mark.asyncio
async def test_preview_rejects_contract_with_active_termination() -> None:
    repository = _Repository()
    repository.events.append(
        ContractLifecycleEvent(  # type: ignore[call-arg]
            id="event-existing",
            contract_kind="terminal",
            contract_id="terminal-1",
            event_type="terminated",
            effective_date=date(2026, 5, 31),
            termination_type="early",
            handover_status="completed",
            deposit_settlement_status="settled",
            reason="既有终止",
            created_by="actor-1",
            created_at=datetime(2026, 6, 1),
            idempotency_key="terminate-previous",
        )
    )
    store = _PreviewStore()
    service = _service(repository, store)
    db = _DB()

    with pytest.raises(TerminalContractAlreadyTerminatedError):
        await service.preview_terminal_termination(
            db,
            contract_id="terminal-1",
            proposal=_proposal(),
            actor_id="actor-1",
            scope=SCOPE,
        )
    assert store.payloads == {}


@pytest.mark.asyncio
async def test_commit_consumes_token_and_truncates_coverage() -> None:
    repository = _Repository()
    store = _PreviewStore()
    service = _service(repository, store)
    db = _DB()
    preview = await service.preview_terminal_termination(
        db,
        contract_id="terminal-1",
        proposal=_proposal(),
        actor_id="actor-1",
        scope=SCOPE,
    )
    request = TerminalContractTerminationCommitRequest.model_validate(
        {"preview_token": preview.preview_token, "expected_version": 3}
    )

    response = await service.commit_terminal_termination(
        db,
        contract_id="terminal-1",
        request=request,
        actor_id="actor-1",
        scope=SCOPE,
        idempotency_key="terminate-commit-1",
    )

    assert response.idempotent is False
    assert response.event_type == "terminated"
    assert repository.truncations == [("terminal-1", date(2026, 6, 30))]
    assert repository.coverages[0].effective_to == date(2026, 6, 29)
    assert store.payloads == {}
    assert db.commits == 1


@pytest.mark.asyncio
async def test_commit_replays_first_result_after_token_consumed() -> None:
    repository = _Repository()
    store = _PreviewStore()
    service = _service(repository, store)
    db = _DB()
    preview = await service.preview_terminal_termination(
        db,
        contract_id="terminal-1",
        proposal=_proposal(),
        actor_id="actor-1",
        scope=SCOPE,
    )
    request = TerminalContractTerminationCommitRequest.model_validate(
        {"preview_token": preview.preview_token, "expected_version": 3}
    )

    first = await service.commit_terminal_termination(
        db,
        contract_id="terminal-1",
        request=request,
        actor_id="actor-1",
        scope=SCOPE,
        idempotency_key="terminate-commit-1",
    )
    replay = await service.commit_terminal_termination(
        db,
        contract_id="terminal-1",
        request=request,
        actor_id="actor-1",
        scope=SCOPE,
        idempotency_key="terminate-commit-1",
    )

    assert first.idempotent is False
    assert replay.idempotent is True
    assert replay.id == first.id
    assert repository.writes == 1
    assert repository.truncations == [("terminal-1", date(2026, 6, 30))]


@pytest.mark.asyncio
async def test_commit_rejects_missing_token_without_receipt() -> None:
    repository = _Repository()
    store = _PreviewStore()
    service = _service(repository, store)
    db = _DB()
    request = TerminalContractTerminationCommitRequest.model_validate(
        {"preview_token": "unknown-token", "expected_version": 3}
    )

    with pytest.raises(AssetOperationsPreviewStaleError):
        await service.commit_terminal_termination(
            db,
            contract_id="terminal-1",
            request=request,
            actor_id="actor-1",
            scope=SCOPE,
            idempotency_key="terminate-commit-1",
        )
    assert repository.writes == 0


@pytest.mark.asyncio
async def test_commit_rejects_version_drift() -> None:
    repository = _Repository()
    store = _PreviewStore()
    service = _service(repository, store)
    db = _DB()
    preview = await service.preview_terminal_termination(
        db,
        contract_id="terminal-1",
        proposal=_proposal(),
        actor_id="actor-1",
        scope=SCOPE,
    )
    repository.terminal.version = 4
    request = TerminalContractTerminationCommitRequest.model_validate(
        {"preview_token": preview.preview_token, "expected_version": 3}
    )

    with pytest.raises(AssetOperationsVersionConflictError):
        await service.commit_terminal_termination(
            db,
            contract_id="terminal-1",
            request=request,
            actor_id="actor-1",
            scope=SCOPE,
            idempotency_key="terminate-commit-1",
        )
    assert repository.writes == 0
    assert repository.truncations == []
    assert preview.preview_token in store.payloads


@pytest.mark.asyncio
async def test_commit_rejects_state_change_after_preview() -> None:
    repository = _Repository()
    store = _PreviewStore()
    service = _service(repository, store)
    db = _DB()
    preview = await service.preview_terminal_termination(
        db,
        contract_id="terminal-1",
        proposal=_proposal(),
        actor_id="actor-1",
        scope=SCOPE,
    )
    repository.coverages[0].effective_to = date(2026, 11, 30)
    request = TerminalContractTerminationCommitRequest.model_validate(
        {"preview_token": preview.preview_token, "expected_version": 3}
    )

    with pytest.raises(AssetOperationsPreviewStaleError):
        await service.commit_terminal_termination(
            db,
            contract_id="terminal-1",
            request=request,
            actor_id="actor-1",
            scope=SCOPE,
            idempotency_key="terminate-commit-1",
        )
    assert repository.writes == 0
    assert preview.preview_token in store.payloads


@pytest.mark.asyncio
async def test_commit_rejects_actor_and_scope_mismatch() -> None:
    repository = _Repository()
    store = _PreviewStore()
    service = _service(repository, store)
    db = _DB()
    preview = await service.preview_terminal_termination(
        db,
        contract_id="terminal-1",
        proposal=_proposal(),
        actor_id="actor-1",
        scope=SCOPE,
    )
    request = TerminalContractTerminationCommitRequest.model_validate(
        {"preview_token": preview.preview_token, "expected_version": 3}
    )

    with pytest.raises(PartyScopeForbiddenError):
        await service.commit_terminal_termination(
            db,
            contract_id="terminal-1",
            request=request,
            actor_id="actor-2",
            scope=SCOPE,
            idempotency_key="terminate-commit-actor",
        )

    with pytest.raises(AssetOperationsPreviewStaleError) as scope_error:
        await service.commit_terminal_termination(
            db,
            contract_id="terminal-1",
            request=request,
            actor_id="actor-1",
            scope=OTHER_SCOPE,
            idempotency_key="terminate-commit-scope",
        )
    assert scope_error.value.details["reason"] == "scope_changed"
    assert repository.writes == 0


@pytest.mark.asyncio
async def test_commit_replay_with_different_live_token_conflicts() -> None:
    repository = _Repository()
    store = _PreviewStore()
    service = _service(repository, store)
    db = _DB()
    first_preview = await service.preview_terminal_termination(
        db,
        contract_id="terminal-1",
        proposal=_proposal(),
        actor_id="actor-1",
        scope=SCOPE,
    )
    changed_proposal = _proposal().model_copy(update={"reason": "改写后的原因"})
    second_preview = await service.preview_terminal_termination(
        db,
        contract_id="terminal-1",
        proposal=changed_proposal,
        actor_id="actor-1",
        scope=SCOPE,
    )
    assert second_preview.preview_token != first_preview.preview_token

    first_request = TerminalContractTerminationCommitRequest.model_validate(
        {"preview_token": first_preview.preview_token, "expected_version": 3}
    )
    await service.commit_terminal_termination(
        db,
        contract_id="terminal-1",
        request=first_request,
        actor_id="actor-1",
        scope=SCOPE,
        idempotency_key="terminate-commit-1",
    )

    second_request = TerminalContractTerminationCommitRequest.model_validate(
        {"preview_token": second_preview.preview_token, "expected_version": 3}
    )

    with pytest.raises(AssetOperationsIdempotencyConflictError):
        await service.commit_terminal_termination(
            db,
            contract_id="terminal-1",
            request=second_request,
            actor_id="actor-1",
            scope=SCOPE,
            idempotency_key="terminate-commit-1",
        )
    assert repository.writes == 1
