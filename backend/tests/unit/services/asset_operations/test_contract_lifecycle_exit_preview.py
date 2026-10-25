"""Upstream-exit preview binds the impact model before any event is written."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest

from src.models.asset_contract import (
    ContractLifecycleEvent,
    UpstreamContract,
    UpstreamContractAssetUnit,
)
from src.schemas.asset_operations import (
    UpstreamContractExitCommitRequest,
    UpstreamContractExitProposal,
)
from src.services.asset_operations.contract_lifecycle_command_service import (
    ContractLifecycleCommandService,
)
from src.services.asset_operations.errors import (
    AssetOperationsPreviewStaleError,
    AssetOperationsVersionConflictError,
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


class _PreviewStore:
    def __init__(self) -> None:
        self.payloads: dict[str, dict[str, object]] = {}

    def issue(self, payload: dict[str, object]) -> tuple[str, datetime]:
        token = f"exit-preview-token-{len(self.payloads)}"
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
            UpstreamContractAssetUnit(
                upstream_contract_id="upstream-1",
                asset_unit_id="unit-1",
                effective_from=date(2026, 1, 1),
                effective_to=date(2026, 12, 31),
            )
        ]
        self.upstream = UpstreamContract(
            id="upstream-1",
            contract_number="UP-001",
            contract_type="lease",
            name="上游合同",
            owner_party_id="owner-1",
            operator_party_id="operator-1",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            deposit_amount=0,
            scan_document_id="scan-2",
        )
        self.upstream.version = 3

    async def get_lifecycle_event_by_idempotency_key(
        self, _db, *, idempotency_key: str
    ) -> ContractLifecycleEvent | None:
        for event in self.events:
            if event.idempotency_key == idempotency_key:
                return event
        return None

    async def get_upstream(
        self, _db, *, contract_id: str, scope: EffectivePartyScope, for_update: bool
    ) -> UpstreamContract | None:
        if contract_id != "upstream-1" or scope is not SCOPE:
            return None
        return self.upstream

    async def list_lifecycle_events(
        self, _db, *, contract_kind: str, contract_id: str
    ) -> tuple[ContractLifecycleEvent, ...]:
        return tuple(
            event
            for event in self.events
            if event.contract_kind == contract_kind
            and event.contract_id == contract_id
        )

    async def list_upstream_coverages(
        self, _db, *, contract_id: str
    ) -> tuple[UpstreamContractAssetUnit, ...]:
        return tuple(
            coverage
            for coverage in self.coverages
            if coverage.upstream_contract_id == contract_id
        )

    async def list_terminal_by_upstream(self, _db, *, upstream_contract_id: str):
        return ()

    async def list_terminal_lifecycle_events(self, _db, *, contract_ids):
        return ()

    async def truncate_upstream_coverages(
        self, _db, *, contract_id: str, effective_date: date
    ) -> int:
        self.truncations.append((contract_id, effective_date))
        cutoff = effective_date - timedelta(days=1)
        for coverage in self.coverages:
            if coverage.upstream_contract_id == contract_id and (
                coverage.effective_to is None or coverage.effective_to > cutoff
            ):
                coverage.effective_to = cutoff
        return 1

    async def add_lifecycle_event(
        self, _db, *, event: ContractLifecycleEvent
    ) -> None:
        self.writes += 1
        self.events.append(event)


class _DB:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


def _proposal() -> UpstreamContractExitProposal:
    return UpstreamContractExitProposal.model_validate(
        {"effective_date": "2026-06-30", "reason": "提前解除承租合同"}
    )


def _service(
    repository: _Repository, store: _PreviewStore
) -> ContractLifecycleCommandService:
    return ContractLifecycleCommandService(
        repository=repository,
        preview_store=store,
        clock=lambda: NOW,
        id_factory=lambda: "event-exit-1",
    )


@pytest.mark.asyncio
async def test_exit_preview_reports_impact_without_writes() -> None:
    repository = _Repository()
    store = _PreviewStore()
    service = _service(repository, store)
    db = _DB()

    preview = await service.preview_upstream_exit(
        db,
        contract_id="upstream-1",
        proposal=_proposal(),
        actor_id="actor-1",
        scope=SCOPE,
    )

    assert preview.contract_version == 3
    assert preview.last_valid_day == date(2026, 6, 29)
    assert len(preview.coverage_impact) == 1
    assert preview.coverage_impact[0].new_effective_to == date(2026, 6, 29)
    assert repository.writes == 0
    assert repository.truncations == []
    assert db.commits == 0

    token_payload = store.payloads[preview.preview_token]
    assert token_payload["actor_id"] == "actor-1"
    assert token_payload["action"] == "upstream_exit"
    assert token_payload["contract_id"] == "upstream-1"
    assert token_payload["versions"] == {"upstream-1": 3}


@pytest.mark.asyncio
async def test_exit_commit_consumes_token_and_truncates_coverage() -> None:
    repository = _Repository()
    store = _PreviewStore()
    service = _service(repository, store)
    db = _DB()
    preview = await service.preview_upstream_exit(
        db,
        contract_id="upstream-1",
        proposal=_proposal(),
        actor_id="actor-1",
        scope=SCOPE,
    )
    request = UpstreamContractExitCommitRequest.model_validate(
        {"preview_token": preview.preview_token, "expected_version": 3}
    )

    response = await service.commit_upstream_exit(
        db,
        contract_id="upstream-1",
        request=request,
        actor_id="actor-1",
        scope=SCOPE,
        idempotency_key="exit-commit-1",
    )

    assert response.idempotent is False
    assert response.event_type == "exited"
    assert repository.truncations == [("upstream-1", date(2026, 6, 30))]
    assert repository.coverages[0].effective_to == date(2026, 6, 29)
    assert store.payloads == {}
    assert db.commits == 1


@pytest.mark.asyncio
async def test_exit_commit_rejects_version_drift_and_keeps_token() -> None:
    repository = _Repository()
    store = _PreviewStore()
    service = _service(repository, store)
    db = _DB()
    preview = await service.preview_upstream_exit(
        db,
        contract_id="upstream-1",
        proposal=_proposal(),
        actor_id="actor-1",
        scope=SCOPE,
    )
    repository.upstream.version = 4
    request = UpstreamContractExitCommitRequest.model_validate(
        {"preview_token": preview.preview_token, "expected_version": 3}
    )

    with pytest.raises(AssetOperationsVersionConflictError):
        await service.commit_upstream_exit(
            db,
            contract_id="upstream-1",
            request=request,
            actor_id="actor-1",
            scope=SCOPE,
            idempotency_key="exit-commit-1",
        )
    assert repository.writes == 0
    assert repository.truncations == []
    assert preview.preview_token in store.payloads


@pytest.mark.asyncio
async def test_exit_commit_rejects_state_change_and_keeps_token() -> None:
    repository = _Repository()
    store = _PreviewStore()
    service = _service(repository, store)
    db = _DB()
    preview = await service.preview_upstream_exit(
        db,
        contract_id="upstream-1",
        proposal=_proposal(),
        actor_id="actor-1",
        scope=SCOPE,
    )
    repository.coverages[0].effective_to = date(2026, 11, 30)
    request = UpstreamContractExitCommitRequest.model_validate(
        {"preview_token": preview.preview_token, "expected_version": 3}
    )

    with pytest.raises(AssetOperationsPreviewStaleError) as error:
        await service.commit_upstream_exit(
            db,
            contract_id="upstream-1",
            request=request,
            actor_id="actor-1",
            scope=SCOPE,
            idempotency_key="exit-commit-1",
        )
    assert error.value.details["reason"] == "state_changed"
    assert repository.writes == 0
    assert preview.preview_token in store.payloads


@pytest.mark.asyncio
async def test_exit_commit_rejects_missing_token_without_receipt() -> None:
    repository = _Repository()
    store = _PreviewStore()
    service = _service(repository, store)
    db = _DB()
    request = UpstreamContractExitCommitRequest.model_validate(
        {"preview_token": "unknown-token", "expected_version": 3}
    )

    with pytest.raises(AssetOperationsPreviewStaleError):
        await service.commit_upstream_exit(
            db,
            contract_id="upstream-1",
            request=request,
            actor_id="actor-1",
            scope=SCOPE,
            idempotency_key="exit-commit-1",
        )
    assert repository.writes == 0
