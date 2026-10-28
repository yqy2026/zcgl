"""Lifecycle commands append one scoped, idempotent contract event."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from src.models.asset_contract import (
    ContractLifecycleEvent,
    TerminalContract,
    TerminalContractAssetUnit,
    UpstreamContract,
    UpstreamContractAssetUnit,
)
from src.schemas.asset_operations import (
    TerminalContractTerminationProposal,
    TerminalContractTerminationReversalProposal,
    UpstreamContractExitProposal,
    UpstreamContractExitReversalProposal,
)
from src.services.asset_operations.contract_lifecycle_command_service import (
    ContractLifecycleCommandService,
)
from src.services.asset_operations.errors import (
    ActiveTerminalContractsBlockExitError,
    AssetContractCoverageInvalidError,
    AssetOperationsIdempotencyConflictError,
    TerminalContractAlreadyTerminatedError,
    TerminationReversalBlockedError,
    TerminationReversalTargetInvalidError,
    UpstreamContractAlreadyExitedError,
    UpstreamExitReversalBlockedError,
    UpstreamExitReversalTargetInvalidError,
)
from src.services.party_scope_resolver import EffectivePartyScope

NOW = datetime(2026, 10, 25, 1, 0, tzinfo=UTC)
SCOPE = EffectivePartyScope(
    user_id="actor-1",
    source="explicit",
    scope_mode="owner",
    owner_party_ids=["owner-1"],
)


class _Repository:
    def __init__(self) -> None:
        self.event: ContractLifecycleEvent | None = None
        self.events: list[ContractLifecycleEvent] = []
        self.writes = 0
        self.truncations: list[tuple[str, date]] = []
        self.restorations: list[tuple[str, date, date]] = []
        self.overlapping_contract_ids: tuple[str, ...] = ()
        self.upstream_truncations: list[tuple[str, date]] = []
        self.upstream_restorations: list[tuple[str, date, date]] = []
        self.upstream_overlapping_contract_ids: tuple[str, ...] = ()
        self.terminal_contracts: list[TerminalContract] = []
        self.terminal_events: list[ContractLifecycleEvent] = []
        self.upstream = UpstreamContract(
            id="upstream-1",
            contract_number="UP-001",
            contract_type="lease",
            name="上游合同",
            owner_party_id="owner-1",
            operator_party_id="operator-1",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            deposit_amount=Decimal("50000"),
            scan_document_id="scan-2",
        )
        self.upstream_coverages = [
            UpstreamContractAssetUnit(
                upstream_contract_id="upstream-1",
                asset_unit_id="unit-1",
                effective_from=date(2026, 1, 1),
                effective_to=date(2026, 12, 31),
            )
        ]
        self.coverages = [
            TerminalContractAssetUnit(
                terminal_contract_id="terminal-1",
                asset_unit_id="unit-1",
                effective_from=date(2026, 1, 1),
                effective_to=date(2026, 12, 31),
            ),
            TerminalContractAssetUnit(
                terminal_contract_id="terminal-1",
                asset_unit_id="unit-2",
                effective_from=date(2026, 1, 1),
                effective_to=date(2026, 6, 15),
            ),
        ]
        self.terminal = TerminalContract(
            id="terminal-1",
            contract_number="TM-001",
            contract_mode="direct_lease",
            tenant_party_id="tenant-1",
            lessor_party_id="owner-1",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            deposit_amount=0,
            rent_collector="owner",
            scan_document_id="scan-1",
        )

    async def get_lifecycle_event_by_idempotency_key(
        self, _db, *, idempotency_key: str
    ):
        for event in self.events:
            if event.idempotency_key == idempotency_key:
                return event
        return None

    async def get_terminal(
        self, _db, *, contract_id: str, scope: EffectivePartyScope, for_update: bool
    ):
        assert contract_id == "terminal-1"
        assert scope is SCOPE
        self.read_lock_modes = [*getattr(self, "read_lock_modes", []), for_update]
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
        changed = 0
        for coverage in self.coverages:
            if coverage.terminal_contract_id != contract_id:
                continue
            if coverage.effective_to is None or coverage.effective_to > cutoff:
                coverage.effective_to = cutoff
                changed += 1
        return changed

    async def restore_terminal_coverages(
        self, _db, *, contract_id: str, cutoff: date, until: date
    ) -> int:
        self.restorations.append((contract_id, cutoff, until))
        changed = 0
        for coverage in self.coverages:
            if (
                coverage.terminal_contract_id == contract_id
                and coverage.effective_to == cutoff
            ):
                coverage.effective_to = until
                changed += 1
        return changed

    async def get_lifecycle_event_by_id(
        self, _db, *, event_id: str
    ) -> ContractLifecycleEvent | None:
        for event in self.events:
            if event.id == event_id:
                return event
        return None

    async def get_upstream(
        self, _db, *, contract_id: str, scope: EffectivePartyScope, for_update: bool
    ) -> UpstreamContract | None:
        if contract_id != "upstream-1" or scope is not SCOPE:
            return None
        self.read_lock_modes = [*getattr(self, "read_lock_modes", []), for_update]
        return self.upstream

    async def list_upstream_coverages(
        self, _db, *, contract_id: str
    ) -> tuple[UpstreamContractAssetUnit, ...]:
        return tuple(
            coverage
            for coverage in self.upstream_coverages
            if coverage.upstream_contract_id == contract_id
        )

    async def truncate_upstream_coverages(
        self, _db, *, contract_id: str, effective_date: date
    ) -> int:
        self.upstream_truncations.append((contract_id, effective_date))
        cutoff = effective_date - timedelta(days=1)
        changed = 0
        for coverage in self.upstream_coverages:
            if coverage.upstream_contract_id != contract_id:
                continue
            if coverage.effective_to is None or coverage.effective_to > cutoff:
                coverage.effective_to = cutoff
                changed += 1
        return changed

    async def restore_upstream_coverages(
        self, _db, *, contract_id: str, cutoff: date, until: date
    ) -> int:
        self.upstream_restorations.append((contract_id, cutoff, until))
        changed = 0
        for coverage in self.upstream_coverages:
            if (
                coverage.upstream_contract_id == contract_id
                and coverage.effective_to == cutoff
            ):
                coverage.effective_to = until
                changed += 1
        return changed

    async def find_upstream_overlaps(
        self,
        _db,
        *,
        unit_ids: tuple[str, ...],
        start_date: date,
        end_date: date,
    ) -> tuple[str, ...]:
        return self.upstream_overlapping_contract_ids

    async def list_terminal_by_upstream(
        self, _db, *, upstream_contract_id: str
    ) -> tuple[TerminalContract, ...]:
        return tuple(self.terminal_contracts)

    async def list_terminal_lifecycle_events(
        self, _db, *, contract_ids: tuple[str, ...]
    ) -> tuple[ContractLifecycleEvent, ...]:
        return tuple(
            event for event in self.terminal_events if event.contract_id in contract_ids
        )

    async def find_terminal_overlaps(
        self,
        _db,
        *,
        unit_ids: tuple[str, ...],
        start_date: date,
        end_date: date,
    ) -> tuple[str, ...]:
        return self.overlapping_contract_ids

    async def add_lifecycle_event(self, _db, *, event: ContractLifecycleEvent):
        self.writes += 1
        self.event = event
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


def _service(repository: _Repository) -> ContractLifecycleCommandService:
    return ContractLifecycleCommandService(
        repository=repository,
        clock=lambda: NOW,
        id_factory=lambda: "event-1",
    )


def _proposal(*, reason: str = "提前退租") -> TerminalContractTerminationProposal:
    return TerminalContractTerminationProposal.model_validate(
        {
            "effective_date": "2026-06-30",
            "termination_type": "early",
            "handover_status": "pending",
            "deposit_settlement_status": "pending",
            "reason": reason,
        }
    )


@pytest.mark.asyncio
async def test_terminal_termination_replays_same_key_without_second_event() -> None:
    repository = _Repository()
    service = _service(repository)
    db = _DB()

    first = await service.terminate_terminal(
        db,
        contract_id="terminal-1",
        proposal=_proposal(),
        actor_id="actor-1",
        scope=SCOPE,
        idempotency_key="terminate-1",
    )
    replay = await service.terminate_terminal(
        db,
        contract_id="terminal-1",
        proposal=_proposal(),
        actor_id="actor-1",
        scope=SCOPE,
        idempotency_key="terminate-1",
    )

    assert first.id == "event-1"
    assert first.idempotent is False
    assert replay.id == first.id
    assert replay.idempotent is True
    assert repository.writes == 1
    assert db.commits == 1

    with pytest.raises(AssetOperationsIdempotencyConflictError):
        await service.terminate_terminal(
            db,
            contract_id="terminal-1",
            proposal=_proposal(reason="协商退租"),
            actor_id="actor-1",
            scope=SCOPE,
            idempotency_key="terminate-1",
        )


@pytest.mark.asyncio
async def test_terminal_termination_truncates_coverage_to_day_before() -> None:
    repository = _Repository()
    service = _service(repository)
    db = _DB()

    await service.terminate_terminal(
        db,
        contract_id="terminal-1",
        proposal=_proposal(),
        actor_id="actor-1",
        scope=SCOPE,
        idempotency_key="terminate-truncate-1",
    )
    await service.terminate_terminal(
        db,
        contract_id="terminal-1",
        proposal=_proposal(),
        actor_id="actor-1",
        scope=SCOPE,
        idempotency_key="terminate-truncate-1",
    )

    unit_one, unit_two = repository.coverages
    assert unit_one.asset_unit_id == "unit-1"
    assert unit_two.asset_unit_id == "unit-2"
    assert unit_one.effective_to == date(2026, 6, 29)
    assert unit_two.effective_to == date(2026, 6, 15)
    assert repository.truncations == [("terminal-1", date(2026, 6, 30))]
    assert repository.writes == 1


@pytest.mark.asyncio
async def test_terminal_termination_rejects_date_covering_no_valid_period() -> None:
    repository = _Repository()
    service = _service(repository)
    db = _DB()
    proposal = TerminalContractTerminationProposal.model_validate(
        {
            "effective_date": "2026-01-01",
            "termination_type": "early",
            "handover_status": "pending",
            "deposit_settlement_status": "pending",
            "reason": "生效日不晚于开始日",
        }
    )

    with pytest.raises(AssetContractCoverageInvalidError):
        await service.terminate_terminal(
            db,
            contract_id="terminal-1",
            proposal=proposal,
            actor_id="actor-1",
            scope=SCOPE,
            idempotency_key="terminate-invalid-date-1",
        )
    assert repository.writes == 0
    assert repository.truncations == []


@pytest.mark.asyncio
async def test_terminal_termination_rejects_second_active_termination() -> None:
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
    service = _service(repository)
    db = _DB()

    with pytest.raises(TerminalContractAlreadyTerminatedError):
        await service.terminate_terminal(
            db,
            contract_id="terminal-1",
            proposal=_proposal(),
            actor_id="actor-1",
            scope=SCOPE,
            idempotency_key="terminate-second-1",
        )
    assert repository.writes == 0
    assert repository.truncations == []


@pytest.mark.asyncio
async def test_terminal_termination_allows_new_termination_after_reversal() -> None:
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
            reason="已撤销的终止",
            created_by="actor-1",
            created_at=datetime(2026, 6, 1),
            idempotency_key="terminate-previous",
        )
    )
    repository.events.append(
        ContractLifecycleEvent(  # type: ignore[call-arg]
            id="event-reversal",
            contract_kind="terminal",
            contract_id="terminal-1",
            event_type="reversed",
            effective_date=date(2026, 6, 2),
            reversed_event_id="event-existing",
            reason="终止日期录入错误",
            created_by="actor-1",
            created_at=datetime(2026, 6, 2),
            idempotency_key="terminate-previous-reversal",
        )
    )
    service = _service(repository)
    db = _DB()

    response = await service.terminate_terminal(
        db,
        contract_id="terminal-1",
        proposal=_proposal(),
        actor_id="actor-1",
        scope=SCOPE,
        idempotency_key="terminate-after-reversal-1",
    )

    assert response.idempotent is False
    assert repository.writes == 1
    assert repository.truncations == [("terminal-1", date(2026, 6, 30))]


def _reversal(
    *, target_event_id: str = "event-1", reason: str = "终止日期录入错误"
) -> TerminalContractTerminationReversalProposal:
    return TerminalContractTerminationReversalProposal.model_validate(
        {
            "target_event_id": target_event_id,
            "effective_date": "2026-07-01",
            "reason": reason,
        }
    )


async def _terminate_once(
    service: ContractLifecycleCommandService, repository: _Repository
) -> None:
    await service.terminate_terminal(
        _DB(),
        contract_id="terminal-1",
        proposal=_proposal(),
        actor_id="actor-1",
        scope=SCOPE,
        idempotency_key="terminate-before-reversal-1",
    )
    assert repository.truncations == [("terminal-1", date(2026, 6, 30))]


@pytest.mark.asyncio
async def test_termination_reversal_restores_coverage_truncated_by_target() -> None:
    repository = _Repository()
    service = _service(repository)
    await _terminate_once(service, repository)
    db = _DB()

    reversal = await service.reverse_terminal_termination(
        db,
        contract_id="terminal-1",
        proposal=_reversal(),
        actor_id="actor-1",
        scope=SCOPE,
        idempotency_key="reverse-1",
    )
    replay = await service.reverse_terminal_termination(
        db,
        contract_id="terminal-1",
        proposal=_reversal(),
        actor_id="actor-1",
        scope=SCOPE,
        idempotency_key="reverse-1",
    )

    assert reversal.event_type == "reversed"
    assert reversal.reversed_event_id == "event-1"
    assert reversal.idempotent is False
    assert replay.id == reversal.id
    assert replay.idempotent is True
    unit_one, unit_two = repository.coverages
    assert unit_one.effective_to == date(2026, 12, 31)
    assert unit_two.effective_to == date(2026, 6, 15)
    assert repository.restorations == [
        ("terminal-1", date(2026, 6, 29), date(2026, 12, 31))
    ]
    assert repository.writes == 2
    assert db.commits == 1

    with pytest.raises(AssetOperationsIdempotencyConflictError):
        await service.reverse_terminal_termination(
            db,
            contract_id="terminal-1",
            proposal=_reversal(reason="另一个原因"),
            actor_id="actor-1",
            scope=SCOPE,
            idempotency_key="reverse-1",
        )


@pytest.mark.asyncio
async def test_termination_reversal_rejects_unknown_target() -> None:
    repository = _Repository()
    service = _service(repository)
    await _terminate_once(service, repository)
    db = _DB()

    with pytest.raises(TerminationReversalTargetInvalidError):
        await service.reverse_terminal_termination(
            db,
            contract_id="terminal-1",
            proposal=_reversal(target_event_id="missing-event"),
            actor_id="actor-1",
            scope=SCOPE,
            idempotency_key="reverse-unknown-1",
        )
    assert repository.writes == 1
    assert repository.restorations == []


@pytest.mark.asyncio
async def test_termination_reversal_rejects_already_reversed_target() -> None:
    repository = _Repository()
    service = _service(repository)
    await _terminate_once(service, repository)
    await service.reverse_terminal_termination(
        _DB(),
        contract_id="terminal-1",
        proposal=_reversal(),
        actor_id="actor-1",
        scope=SCOPE,
        idempotency_key="reverse-first-1",
    )
    db = _DB()

    with pytest.raises(TerminationReversalTargetInvalidError) as error:
        await service.reverse_terminal_termination(
            db,
            contract_id="terminal-1",
            proposal=_reversal(),
            actor_id="actor-1",
            scope=SCOPE,
            idempotency_key="reverse-second-1",
        )
    assert error.value.details["reason"] == "target_already_reversed"
    assert repository.writes == 2


@pytest.mark.asyncio
async def test_termination_reversal_blocked_by_successor_coverage() -> None:
    repository = _Repository()
    repository.overlapping_contract_ids = ("terminal-2",)
    service = _service(repository)
    await _terminate_once(service, repository)
    db = _DB()

    with pytest.raises(TerminationReversalBlockedError) as error:
        await service.reverse_terminal_termination(
            db,
            contract_id="terminal-1",
            proposal=_reversal(),
            actor_id="actor-1",
            scope=SCOPE,
            idempotency_key="reverse-blocked-1",
        )
    assert error.value.details["blocking_contract_ids"] == ["terminal-2"]
    assert repository.writes == 1
    assert repository.restorations == []


@pytest.mark.asyncio
async def test_termination_reversal_blocked_by_renewed_event() -> None:
    repository = _Repository()
    service = _service(repository)
    await _terminate_once(service, repository)
    repository.events.append(
        ContractLifecycleEvent(  # type: ignore[call-arg]
            id="event-renewed",
            contract_kind="terminal",
            contract_id="terminal-1",
            event_type="renewed",
            effective_date=date(2026, 7, 1),
            successor_contract_id="terminal-2",
            reason=None,
            created_by="actor-1",
            created_at=datetime(2026, 7, 1),
            idempotency_key="renew-1",
        )
    )
    db = _DB()

    with pytest.raises(TerminationReversalBlockedError) as error:
        await service.reverse_terminal_termination(
            db,
            contract_id="terminal-1",
            proposal=_reversal(),
            actor_id="actor-1",
            scope=SCOPE,
            idempotency_key="reverse-blocked-2",
        )
    assert error.value.details["renewed_event_ids"] == ["event-renewed"]
    assert repository.writes == 1
    assert repository.restorations == []


def _exit_proposal(*, reason: str = "提前解除承租合同") -> UpstreamContractExitProposal:
    return UpstreamContractExitProposal.model_validate(
        {"effective_date": "2026-06-30", "reason": reason}
    )


@pytest.mark.asyncio
async def test_upstream_exit_blocks_active_terminal_contracts() -> None:
    repository = _Repository()
    repository.terminal_contracts.append(
        TerminalContract(
            id="terminal-active",
            contract_number="TM-ACTIVE",
            contract_mode="sublease",
            tenant_party_id="tenant-1",
            lessor_party_id="operator-1",
            upstream_contract_id="upstream-1",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            deposit_amount=0,
            rent_collector="operator",
            scan_document_id="scan-1",
        )
    )
    service = _service(repository)
    db = _DB()

    with pytest.raises(ActiveTerminalContractsBlockExitError):
        await service.exit_upstream(
            db,
            contract_id="upstream-1",
            proposal=_exit_proposal(),
            actor_id="actor-1",
            scope=SCOPE,
            idempotency_key="exit-blocked-1",
        )
    assert repository.writes == 0
    assert repository.upstream_truncations == []


@pytest.mark.asyncio
async def test_upstream_exit_terminated_terminal_does_not_block() -> None:
    repository = _Repository()
    repository.terminal_contracts.append(
        TerminalContract(
            id="terminal-ended",
            contract_number="TM-ENDED",
            contract_mode="sublease",
            tenant_party_id="tenant-1",
            lessor_party_id="operator-1",
            upstream_contract_id="upstream-1",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            deposit_amount=0,
            rent_collector="operator",
            scan_document_id="scan-1",
        )
    )
    repository.terminal_events.append(
        ContractLifecycleEvent(  # type: ignore[call-arg]
            id="event-terminal-ended",
            contract_kind="terminal",
            contract_id="terminal-ended",
            event_type="terminated",
            effective_date=date(2026, 6, 15),
            termination_type="early",
            handover_status="completed",
            deposit_settlement_status="settled",
            reason="先行终止",
            created_by="actor-1",
            created_at=datetime(2026, 6, 15),
            idempotency_key="terminal-ended-1",
        )
    )
    service = _service(repository)
    db = _DB()

    response = await service.exit_upstream(
        db,
        contract_id="upstream-1",
        proposal=_exit_proposal(),
        actor_id="actor-1",
        scope=SCOPE,
        idempotency_key="exit-allowed-1",
    )

    assert response.event_type == "exited"
    assert response.idempotent is False
    assert repository.upstream_truncations == [("upstream-1", date(2026, 6, 30))]
    assert repository.upstream_coverages[0].effective_to == date(2026, 6, 29)
    assert repository.writes == 1


@pytest.mark.asyncio
async def test_upstream_exit_replays_same_key_and_conflicts_on_change() -> None:
    repository = _Repository()
    service = _service(repository)
    db = _DB()

    first = await service.exit_upstream(
        db,
        contract_id="upstream-1",
        proposal=_exit_proposal(),
        actor_id="actor-1",
        scope=SCOPE,
        idempotency_key="exit-1",
    )
    replay = await service.exit_upstream(
        db,
        contract_id="upstream-1",
        proposal=_exit_proposal(),
        actor_id="actor-1",
        scope=SCOPE,
        idempotency_key="exit-1",
    )

    assert first.idempotent is False
    assert replay.idempotent is True
    assert replay.id == first.id
    assert repository.writes == 1
    assert repository.upstream_truncations == [("upstream-1", date(2026, 6, 30))]

    with pytest.raises(AssetOperationsIdempotencyConflictError):
        await service.exit_upstream(
            db,
            contract_id="upstream-1",
            proposal=_exit_proposal(reason="改写原因"),
            actor_id="actor-1",
            scope=SCOPE,
            idempotency_key="exit-1",
        )


@pytest.mark.asyncio
async def test_upstream_exit_rejects_second_active_exit() -> None:
    repository = _Repository()
    repository.events.append(
        ContractLifecycleEvent(  # type: ignore[call-arg]
            id="event-exited",
            contract_kind="upstream",
            contract_id="upstream-1",
            event_type="exited",
            effective_date=date(2026, 5, 31),
            reason="既有退出",
            created_by="actor-1",
            created_at=datetime(2026, 6, 1),
            idempotency_key="exit-previous",
        )
    )
    service = _service(repository)
    db = _DB()

    with pytest.raises(UpstreamContractAlreadyExitedError):
        await service.exit_upstream(
            db,
            contract_id="upstream-1",
            proposal=_exit_proposal(),
            actor_id="actor-1",
            scope=SCOPE,
            idempotency_key="exit-second-1",
        )
    assert repository.writes == 0
    assert repository.upstream_truncations == []


@pytest.mark.asyncio
async def test_upstream_exit_rejects_date_covering_no_valid_period() -> None:
    repository = _Repository()
    service = _service(repository)
    db = _DB()
    proposal = UpstreamContractExitProposal.model_validate(
        {"effective_date": "2026-01-01", "reason": "生效日不晚于开始日"}
    )

    with pytest.raises(AssetContractCoverageInvalidError):
        await service.exit_upstream(
            db,
            contract_id="upstream-1",
            proposal=proposal,
            actor_id="actor-1",
            scope=SCOPE,
            idempotency_key="exit-invalid-1",
        )
    assert repository.writes == 0
    assert repository.upstream_truncations == []


def _exit_reversal(
    *, target_event_id: str = "event-1", reason: str = "退出日期录入错误"
) -> UpstreamContractExitReversalProposal:
    return UpstreamContractExitReversalProposal.model_validate(
        {
            "target_event_id": target_event_id,
            "effective_date": "2026-07-01",
            "reason": reason,
        }
    )


async def _exit_once(
    service: ContractLifecycleCommandService, repository: _Repository
) -> None:
    await service.exit_upstream(
        _DB(),
        contract_id="upstream-1",
        proposal=_exit_proposal(),
        actor_id="actor-1",
        scope=SCOPE,
        idempotency_key="exit-before-reversal-1",
    )
    assert repository.upstream_truncations == [("upstream-1", date(2026, 6, 30))]


@pytest.mark.asyncio
async def test_upstream_exit_reversal_restores_coverage() -> None:
    repository = _Repository()
    service = _service(repository)
    await _exit_once(service, repository)
    db = _DB()

    reversal = await service.reverse_upstream_exit(
        db,
        contract_id="upstream-1",
        proposal=_exit_reversal(),
        actor_id="actor-1",
        scope=SCOPE,
        idempotency_key="exit-reverse-1",
    )
    replay = await service.reverse_upstream_exit(
        db,
        contract_id="upstream-1",
        proposal=_exit_reversal(),
        actor_id="actor-1",
        scope=SCOPE,
        idempotency_key="exit-reverse-1",
    )

    assert reversal.event_type == "reversed"
    assert reversal.reversed_event_id == "event-1"
    assert replay.id == reversal.id
    assert replay.idempotent is True
    assert repository.upstream_coverages[0].effective_to == date(2026, 12, 31)
    assert repository.upstream_restorations == [
        ("upstream-1", date(2026, 6, 29), date(2026, 12, 31))
    ]
    assert repository.writes == 2

    with pytest.raises(AssetOperationsIdempotencyConflictError):
        await service.reverse_upstream_exit(
            db,
            contract_id="upstream-1",
            proposal=_exit_reversal(reason="另一个原因"),
            actor_id="actor-1",
            scope=SCOPE,
            idempotency_key="exit-reverse-1",
        )


@pytest.mark.asyncio
async def test_upstream_exit_reversal_rejects_unknown_target() -> None:
    repository = _Repository()
    service = _service(repository)
    await _exit_once(service, repository)
    db = _DB()

    with pytest.raises(UpstreamExitReversalTargetInvalidError):
        await service.reverse_upstream_exit(
            db,
            contract_id="upstream-1",
            proposal=_exit_reversal(target_event_id="missing"),
            actor_id="actor-1",
            scope=SCOPE,
            idempotency_key="exit-reverse-unknown-1",
        )
    assert repository.writes == 1
    assert repository.upstream_restorations == []


@pytest.mark.asyncio
async def test_upstream_exit_reversal_blocked_by_successor_facts() -> None:
    repository = _Repository()
    service = _service(repository)
    await _exit_once(service, repository)
    repository.upstream_overlapping_contract_ids = ("upstream-2",)
    db = _DB()

    with pytest.raises(UpstreamExitReversalBlockedError) as error:
        await service.reverse_upstream_exit(
            db,
            contract_id="upstream-1",
            proposal=_exit_reversal(),
            actor_id="actor-1",
            scope=SCOPE,
            idempotency_key="exit-reverse-blocked-1",
        )
    assert error.value.details["blocking_contract_ids"] == ["upstream-2"]

    repository.upstream_overlapping_contract_ids = ()
    repository.events.append(
        ContractLifecycleEvent(  # type: ignore[call-arg]
            id="event-renewed",
            contract_kind="upstream",
            contract_id="upstream-1",
            event_type="renewed",
            effective_date=date(2026, 7, 1),
            successor_contract_id="upstream-2",
            reason=None,
            created_by="actor-1",
            created_at=datetime(2026, 7, 1),
            idempotency_key="upstream-renew-1",
        )
    )
    with pytest.raises(UpstreamExitReversalBlockedError) as renewed_error:
        await service.reverse_upstream_exit(
            db,
            contract_id="upstream-1",
            proposal=_exit_reversal(),
            actor_id="actor-1",
            scope=SCOPE,
            idempotency_key="exit-reverse-blocked-2",
        )
    assert renewed_error.value.details["renewed_event_ids"] == ["event-renewed"]
    assert repository.writes == 1
    assert repository.upstream_restorations == []
