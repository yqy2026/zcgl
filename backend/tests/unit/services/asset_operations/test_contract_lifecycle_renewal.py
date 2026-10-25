"""Renewal commands carry predecessor facts into one successor transaction."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from src.core.exception_handler import PartyScopeForbiddenError, ResourceNotFoundError
from src.models.asset_contract import (
    ContractLifecycleEvent,
    TerminalContract,
    TerminalContractAssetUnit,
    UpstreamContract,
    UpstreamContractAssetUnit,
)
from src.schemas.asset_operations import (
    TerminalContractRenewalRequest,
    TerminalContractResponse,
    UpstreamContractRenewalRequest,
    UpstreamContractResponse,
)
from src.services.asset_operations.contract_lifecycle_command_service import (
    ContractLifecycleCommandService,
)
from src.services.asset_operations.errors import (
    AssetContractCoverageInvalidError,
    ContractAlreadyRenewedError,
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
        self.events: list[ContractLifecycleEvent] = []
        self.receipts: dict[tuple[str, str], object] = {}
        self.upstream = UpstreamContract(
            id="upstream-1",
            contract_number="UP-001",
            contract_type="lease",
            name="原上游合同",
            owner_party_id="owner-1",
            operator_party_id="operator-1",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            payment_cycle="monthly",
            payment_day=15,
            deposit_amount=Decimal("50000"),
            scan_document_id="scan-old",
        )
        self.upstream_coverages = [
            UpstreamContractAssetUnit(
                upstream_contract_id="upstream-1",
                asset_unit_id="unit-1",
                effective_from=date(2026, 1, 1),
                effective_to=date(2026, 12, 31),
            )
        ]
        self.terminal = TerminalContract(
            id="terminal-1",
            contract_number="TM-001",
            contract_mode="sublease",
            tenant_party_id="tenant-1",
            lessor_party_id="operator-1",
            upstream_contract_id="upstream-1",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            deposit_amount=Decimal("20000"),
            rent_collector="operator",
            scan_document_id="scan-old-terminal",
        )
        self.terminal_coverages = [
            TerminalContractAssetUnit(
                terminal_contract_id="terminal-1",
                asset_unit_id="unit-1",
                effective_from=date(2026, 1, 1),
                effective_to=date(2026, 12, 31),
            )
        ]

    async def get_write_receipt(self, _db, *, actor_id: str, idempotency_key: str):
        return self.receipts.get((actor_id, idempotency_key))

    async def get_upstream(self, _db, *, contract_id, scope, for_update):
        if contract_id != "upstream-1" or scope is not SCOPE:
            return None
        return self.upstream

    async def get_terminal(self, _db, *, contract_id, scope, for_update):
        if contract_id != "terminal-1" or scope is not SCOPE:
            return None
        return self.terminal

    async def list_upstream_coverages(self, _db, *, contract_id):
        return tuple(
            coverage
            for coverage in self.upstream_coverages
            if coverage.upstream_contract_id == contract_id
        )

    async def list_terminal_coverages(self, _db, *, contract_id):
        return tuple(
            coverage
            for coverage in self.terminal_coverages
            if coverage.terminal_contract_id == contract_id
        )

    async def list_lifecycle_events(self, _db, *, contract_kind, contract_id):
        return tuple(
            event
            for event in self.events
            if event.contract_kind == contract_kind
            and event.contract_id == contract_id
        )


class _ContractCommand:
    def __init__(self) -> None:
        self.upstream_calls: list[dict[str, object]] = []
        self.terminal_calls: list[dict[str, object]] = []

    async def create_upstream(self, _db, **kwargs):
        self.upstream_calls.append(kwargs)
        return UpstreamContractResponse.model_validate(
            {
                **kwargs["request"].model_dump(mode="json"),
                "id": "upstream-2",
                "version": 1,
                "created_at": NOW,
                "updated_at": NOW,
                "status": "scheduled",
                "warnings": [],
                "idempotent": False,
            }
        )

    async def create_terminal(self, _db, **kwargs):
        self.terminal_calls.append(kwargs)
        return TerminalContractResponse.model_validate(
            {
                **kwargs["request"].model_dump(mode="json"),
                "id": "terminal-2",
                "version": 1,
                "created_at": NOW,
                "updated_at": NOW,
                "status": "scheduled",
                "warnings": [],
                "idempotent": False,
            }
        )


class _DB:
    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


def _service(
    repository: _Repository, command: _ContractCommand
) -> ContractLifecycleCommandService:
    return ContractLifecycleCommandService(
        repository=repository,
        contract_command=command,
        clock=lambda: NOW,
        id_factory=lambda: "event-renewed-1",
    )


def _upstream_request() -> UpstreamContractRenewalRequest:
    return UpstreamContractRenewalRequest.model_validate(
        {
            "contract_number": "UP-002",
            "name": "续签上游合同",
            "start_date": "2027-01-01",
            "end_date": "2029-12-31",
            "payment_cycle": "monthly",
            "payment_day": 15,
            "deposit_amount": "50000",
            "scan_document_id": "scan-new",
            "scan_owner_id": "intake-session-1",
        }
    )


def _terminal_request() -> TerminalContractRenewalRequest:
    return TerminalContractRenewalRequest.model_validate(
        {
            "contract_number": "TM-002",
            "upstream_contract_id": "upstream-2",
            "start_date": "2027-01-01",
            "end_date": "2027-12-31",
            "deposit_amount": "20000",
            "scan_document_id": "scan-new-terminal",
            "scan_owner_id": "intake-session-2",
        }
    )


@pytest.mark.asyncio
async def test_renew_upstream_carries_predecessor_facts() -> None:
    repository = _Repository()
    command = _ContractCommand()
    service = _service(repository, command)
    db = _DB()

    response = await service.renew_upstream(
        db,
        contract_id="upstream-1",
        request=_upstream_request(),
        actor_id="actor-1",
        scope=SCOPE,
        idempotency_key="renew-upstream-1",
    )

    assert response.id == "upstream-2"
    assert len(command.upstream_calls) == 1
    call = command.upstream_calls[0]
    create = call["request"]
    assert create.contract_type == "lease"
    assert create.owner_party_id == "owner-1"
    assert create.operator_party_id == "operator-1"
    assert create.renewed_from_id == "upstream-1"
    assert create.asset_unit_ids == ["unit-1"]
    assert create.start_date == date(2027, 1, 1)
    assert call["attachment_owner_id"] == "intake-session-1"
    event = call["lifecycle_event"]
    assert event.event_type == "renewed"
    assert event.contract_id == "upstream-1"
    assert event.effective_date == date(2027, 1, 1)
    assert event.idempotency_key == "renew-upstream-1"


@pytest.mark.asyncio
async def test_renew_terminal_carries_parties_and_named_upstream() -> None:
    repository = _Repository()
    command = _ContractCommand()
    service = _service(repository, command)
    db = _DB()

    await service.renew_terminal(
        db,
        contract_id="terminal-1",
        request=_terminal_request(),
        actor_id="actor-1",
        scope=SCOPE,
        idempotency_key="renew-terminal-1",
    )

    assert len(command.terminal_calls) == 1
    create = command.terminal_calls[0]["request"]
    assert create.contract_mode == "sublease"
    assert create.tenant_party_id == "tenant-1"
    assert create.lessor_party_id == "operator-1"
    assert create.rent_collector == "operator"
    assert create.upstream_contract_id == "upstream-2"
    assert create.renewed_from_id == "terminal-1"
    assert create.asset_unit_ids == ["unit-1"]


@pytest.mark.asyncio
async def test_renew_upstream_rejects_second_successor() -> None:
    repository = _Repository()
    repository.events.append(
        ContractLifecycleEvent(  # type: ignore[call-arg]
            id="event-renewed-old",
            contract_kind="upstream",
            contract_id="upstream-1",
            event_type="renewed",
            effective_date=date(2027, 1, 1),
            successor_contract_id="upstream-0",
            reason=None,
            created_by="actor-1",
            created_at=datetime(2026, 11, 1),
            idempotency_key="renew-previous",
        )
    )
    command = _ContractCommand()
    service = _service(repository, command)
    db = _DB()

    with pytest.raises(ContractAlreadyRenewedError):
        await service.renew_upstream(
            db,
            contract_id="upstream-1",
            request=_upstream_request(),
            actor_id="actor-1",
            scope=SCOPE,
            idempotency_key="renew-upstream-2",
        )
    assert command.upstream_calls == []


@pytest.mark.asyncio
async def test_renew_rejects_successor_overlapping_predecessor() -> None:
    repository = _Repository()
    command = _ContractCommand()
    service = _service(repository, command)
    db = _DB()
    overlapping = _upstream_request().model_copy(
        update={"start_date": date(2026, 12, 31)}
    )

    with pytest.raises(AssetContractCoverageInvalidError) as error:
        await service.renew_upstream(
            db,
            contract_id="upstream-1",
            request=overlapping,
            actor_id="actor-1",
            scope=SCOPE,
            idempotency_key="renew-upstream-overlap-1",
        )
    assert error.value.details["reason"] == "renewal_overlaps_predecessor"
    assert command.upstream_calls == []


@pytest.mark.asyncio
async def test_renew_replay_skips_guards_and_passes_no_event() -> None:
    repository = _Repository()
    repository.receipts[("actor-1", "renew-upstream-1")] = object()
    repository.events.append(
        ContractLifecycleEvent(  # type: ignore[call-arg]
            id="event-renewed-old",
            contract_kind="upstream",
            contract_id="upstream-1",
            event_type="renewed",
            effective_date=date(2027, 1, 1),
            successor_contract_id="upstream-2",
            reason=None,
            created_by="actor-1",
            created_at=datetime(2026, 11, 1),
            idempotency_key="renew-upstream-1",
        )
    )
    command = _ContractCommand()
    service = _service(repository, command)
    db = _DB()

    await service.renew_upstream(
        db,
        contract_id="upstream-1",
        request=_upstream_request(),
        actor_id="actor-1",
        scope=SCOPE,
        idempotency_key="renew-upstream-1",
    )

    assert len(command.upstream_calls) == 1
    call = command.upstream_calls[0]
    assert call.get("lifecycle_event") is None


@pytest.mark.asyncio
async def test_renew_rejects_unknown_contract() -> None:
    repository = _Repository()
    command = _ContractCommand()
    service = _service(repository, command)
    db = _DB()

    with pytest.raises(ResourceNotFoundError):
        await service.renew_upstream(
            db,
            contract_id="upstream-missing",
            request=_upstream_request(),
            actor_id="actor-1",
            scope=SCOPE,
            idempotency_key="renew-upstream-404",
        )
    assert command.upstream_calls == []


@pytest.mark.asyncio
async def test_renew_rejects_predecessor_without_coverage() -> None:
    repository = _Repository()
    repository.upstream_coverages = []
    command = _ContractCommand()
    service = _service(repository, command)
    db = _DB()

    with pytest.raises(AssetContractCoverageInvalidError) as error:
        await service.renew_upstream(
            db,
            contract_id="upstream-1",
            request=_upstream_request(),
            actor_id="actor-1",
            scope=SCOPE,
            idempotency_key="renew-upstream-empty-1",
        )
    assert error.value.details["reason"] == "renewal_without_coverage"
    assert command.upstream_calls == []


@pytest.mark.asyncio
async def test_renew_rejects_actor_scope_mismatch() -> None:
    repository = _Repository()
    command = _ContractCommand()
    service = _service(repository, command)
    db = _DB()

    with pytest.raises(PartyScopeForbiddenError):
        await service.renew_upstream(
            db,
            contract_id="upstream-1",
            request=_upstream_request(),
            actor_id="actor-2",
            scope=SCOPE,
            idempotency_key="renew-upstream-actor-1",
        )
    assert command.upstream_calls == []


@pytest.mark.asyncio
async def test_renew_allows_second_successor_after_renewal_reversed() -> None:
    repository = _Repository()
    repository.events.append(
        ContractLifecycleEvent(  # type: ignore[call-arg]
            id="event-renewed-old",
            contract_kind="upstream",
            contract_id="upstream-1",
            event_type="renewed",
            effective_date=date(2027, 1, 1),
            successor_contract_id="upstream-0",
            reason=None,
            created_by="actor-1",
            created_at=datetime(2026, 11, 1),
            idempotency_key="renew-previous",
        )
    )
    repository.events.append(
        ContractLifecycleEvent(  # type: ignore[call-arg]
            id="event-renewal-reversal",
            contract_kind="upstream",
            contract_id="upstream-1",
            event_type="reversed",
            effective_date=date(2026, 11, 2),
            reversed_event_id="event-renewed-old",
            reason="续签链登记错误",
            created_by="actor-1",
            created_at=datetime(2026, 11, 2),
            idempotency_key="renew-previous-reversal",
        )
    )
    command = _ContractCommand()
    service = _service(repository, command)
    db = _DB()

    response = await service.renew_upstream(
        db,
        contract_id="upstream-1",
        request=_upstream_request(),
        actor_id="actor-1",
        scope=SCOPE,
        idempotency_key="renew-upstream-after-reversal-1",
    )

    assert response.id == "upstream-2"
    assert len(command.upstream_calls) == 1
