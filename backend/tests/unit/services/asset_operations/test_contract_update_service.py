"""Contract updates mutate editable terms and resync coverage end dates."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.models.asset_contract import (
    TerminalContract,
    TerminalContractAssetUnit,
    UpstreamContract,
    UpstreamContractAssetUnit,
)
from src.models.asset_unit import AssetUnit
from src.schemas.asset_operations import (
    TerminalContractUpdate,
    UpstreamContractUpdate,
)
from src.services.asset_operations.contract_command_service import (
    AssetContractCommandService,
)
from src.services.asset_operations.errors import (
    AssetContractCoverageInvalidError,
    AssetOperationsVersionConflictError,
)
from src.services.party_scope_resolver import EffectivePartyScope

NOW = datetime(2026, 10, 25, 1, 0)
SCOPE = EffectivePartyScope(
    user_id="actor-1",
    source="explicit",
    scope_mode="owner",
    owner_party_ids=["owner-1"],
)


class _UnitRepository:
    def __init__(self) -> None:
        self.locked: list[tuple[str, ...]] = []
        self.units = (
            AssetUnit(
                id="unit-1",
                managed_from=date(2026, 1, 1),
                managed_to=None,
            ),
        )

    async def lock_for_write(self, _db, *, unit_ids, scope):
        self.locked.append(tuple(sorted(unit_ids)))
        return self.units


class _Repository:
    def __init__(self) -> None:
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
            scan_document_id="scan-up",
            version=3,
            created_at=datetime(2026, 1, 1),
            updated_at=datetime(2026, 1, 1),
        )
        self.upstream.version = 3
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
            scan_document_id="scan-tm",
            version=2,
            created_at=datetime(2026, 1, 1),
            updated_at=datetime(2026, 1, 1),
        )
        self.terminal.version = 2
        self.terminal_coverages = [
            TerminalContractAssetUnit(
                terminal_contract_id="terminal-1",
                asset_unit_id="unit-1",
                effective_from=date(2026, 1, 1),
                effective_to=date(2026, 12, 31),
            )
        ]
        self.upstream_for_terminal: object | None = None
        self.retargets: list[tuple[str, str, date, date]] = []
        self.events: list[object] = []

    async def list_lifecycle_events(self, _db, *, contract_kind, contract_id):
        return tuple(event for event in self.events if event.contract_id == contract_id)

    async def list_rent_schedules(self, _db, *, contract_kind, contract_ids):
        return ()

    async def get_upstream(self, _db, *, contract_id, scope, for_update=False):
        if contract_id != "upstream-1" or scope is not SCOPE:
            return None
        return self.upstream

    async def get_terminal(self, _db, *, contract_id, scope, for_update=False):
        if contract_id != "terminal-1" or scope is not SCOPE:
            return None
        return self.terminal

    async def get_upstream_for_terminal(self, _db, **kwargs):
        return self.upstream_for_terminal

    async def list_terminal_coverages(self, _db, *, contract_id):
        return tuple(
            c for c in self.terminal_coverages if c.terminal_contract_id == contract_id
        )

    async def list_upstream_coverages(self, _db, *, contract_id):
        return tuple(
            c for c in self.upstream_coverages if c.upstream_contract_id == contract_id
        )

    async def retarget_upstream_coverage_ends(
        self, _db, *, contract_id, old_end, new_end
    ):
        self.retargets.append(("upstream", contract_id, old_end, new_end))
        changed = 0
        for coverage in self.upstream_coverages:
            if (
                coverage.upstream_contract_id == contract_id
                and coverage.effective_to == old_end
            ):
                coverage.effective_to = new_end
                changed += 1
        return changed

    async def retarget_terminal_coverage_ends(
        self, _db, *, contract_id, old_end, new_end
    ):
        self.retargets.append(("terminal", contract_id, old_end, new_end))
        changed = 0
        for coverage in self.terminal_coverages:
            if (
                coverage.terminal_contract_id == contract_id
                and coverage.effective_to == old_end
            ):
                coverage.effective_to = new_end
                changed += 1
        return changed


class _DB:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0
        self.added: list[object] = []

    def add(self, value: object) -> None:
        self.added.append(value)

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


def _service(repository: _Repository) -> AssetContractCommandService:
    return AssetContractCommandService(
        repository=repository,  # type: ignore[arg-type]
        unit_repository=_UnitRepository(),  # type: ignore[arg-type]
        clock=lambda: datetime(2026, 10, 25, 1, 0),
        business_today=lambda: date(2026, 10, 25),
    )


def _upstream_update(**overrides: object) -> UpstreamContractUpdate:
    values: dict[str, object] = {"expected_version": 3}
    values.update(overrides)
    return UpstreamContractUpdate.model_validate(values)


def _terminal_update(**overrides: object) -> TerminalContractUpdate:
    values: dict[str, object] = {"expected_version": 2}
    values.update(overrides)
    return TerminalContractUpdate.model_validate(values)


@pytest.mark.parametrize(
    "field,value", [("payment_cycle", "quarterly"), ("payment_day", 25)]
)
def test_upstream_patch_rejects_contract_payment_defaults(field, value) -> None:
    with pytest.raises(ValidationError, match="extra_forbidden"):
        _upstream_update(**{field: value})


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "contract_type,field,value",
    [
        ("lease", "management_fee_rate", Decimal("0.08")),
        ("lease", "management_fee_rate", None),
        ("management_agreement", "deposit_amount", Decimal("1")),
    ],
)
async def test_upstream_update_rejects_inapplicable_fields(
    contract_type, field, value
) -> None:
    from src.core.exception_handler import BaseBusinessError

    repository = _Repository()
    repository.upstream.contract_type = contract_type
    db = _DB()
    with pytest.raises(BaseBusinessError) as error:
        await _service(repository).update_upstream(
            db,
            contract_id="upstream-1",
            request=_upstream_update(**{field: value}),
            actor_id="actor-1",
            scope=SCOPE,
        )
    assert error.value.code == "CONTRACT_FIELD_NOT_APPLICABLE"
    assert error.value.status_code == 422
    assert db.commits == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["upstream", "terminal"])
async def test_contract_extension_rejects_coverage_outside_unit_managed_period(
    kind: str,
) -> None:
    repository = _Repository()
    service = _service(repository)
    service.unit_repository.units[0].managed_to = date(2026, 12, 31)
    db = _DB()
    request = (
        _upstream_update(end_date=date(2027, 6, 30))
        if kind == "upstream"
        else _terminal_update(end_date=date(2027, 6, 30))
    )

    with pytest.raises(AssetContractCoverageInvalidError) as error:
        await getattr(service, f"update_{kind}")(
            db,
            contract_id=f"{kind}-1",
            request=request,
            actor_id="actor-1",
            scope=SCOPE,
        )

    assert error.value.details["reason"] == "outside_asset_unit_managed_period"
    assert repository.retargets == []
    assert db.commits == 0


@pytest.mark.asyncio
async def test_upstream_extension_preserves_retired_source_coverage() -> None:
    repository = _Repository()
    repository.upstream_coverages[0].effective_to = date(2026, 6, 30)
    repository.upstream_coverages.append(
        UpstreamContractAssetUnit(
            upstream_contract_id="upstream-1",
            asset_unit_id="unit-2",
            effective_from=date(2026, 7, 1),
            effective_to=date(2026, 12, 31),
        )
    )
    service = _service(repository)
    service.unit_repository.units = (
        AssetUnit(
            id="unit-1",
            managed_from=date(2026, 1, 1),
            managed_to=date(2026, 6, 30),
        ),
        AssetUnit(
            id="unit-2",
            managed_from=date(2026, 7, 1),
            managed_to=date(2027, 6, 30),
        ),
    )
    db = _DB()

    response = await service.update_upstream(
        db,
        contract_id="upstream-1",
        request=_upstream_update(end_date=date(2027, 6, 30)),
        actor_id="actor-1",
        scope=SCOPE,
    )

    assert response.end_date == date(2027, 6, 30)
    assert repository.upstream_coverages[0].effective_to == date(2026, 6, 30)
    assert repository.upstream_coverages[1].effective_to == date(2027, 6, 30)
    assert db.commits == 1


@pytest.mark.asyncio
async def test_upstream_update_mutates_terms_and_resyncs_coverage() -> None:
    repository = _Repository()
    service = _service(repository)
    db = _DB()

    response = await service.update_upstream(
        db,
        contract_id="upstream-1",
        request=_upstream_update(
            name="续订后的上游合同",
            end_date=date(2027, 6, 30),
            deposit_amount=Decimal("60000"),
            oa_reference="OA-26-0901",
        ),
        actor_id="actor-1",
        scope=SCOPE,
    )

    assert response.name == "续订后的上游合同"
    assert response.end_date == date(2027, 6, 30)
    assert response.deposit_amount == Decimal("60000")
    assert response.oa_reference == "OA-26-0901"
    assert response.payment_day == 15
    assert repository.upstream_coverages[0].effective_to == date(2027, 6, 30)
    assert repository.retargets == [
        ("upstream", "upstream-1", date(2026, 12, 31), date(2027, 6, 30))
    ]
    assert response.status == "active"
    assert db.commits == 1


@pytest.mark.asyncio
async def test_upstream_update_rejects_version_drift() -> None:
    repository = _Repository()
    service = _service(repository)
    db = _DB()

    with pytest.raises(AssetOperationsVersionConflictError):
        await service.update_upstream(
            db,
            contract_id="upstream-1",
            request=_upstream_update(expected_version=2),
            actor_id="actor-1",
            scope=SCOPE,
        )
    assert db.commits == 0


@pytest.mark.asyncio
async def test_upstream_update_rejects_end_before_start() -> None:
    repository = _Repository()
    service = _service(repository)
    db = _DB()

    with pytest.raises(AssetContractCoverageInvalidError) as error:
        await service.update_upstream(
            db,
            contract_id="upstream-1",
            request=_upstream_update(end_date=date(2025, 12, 31)),
            actor_id="actor-1",
            scope=SCOPE,
        )
    assert error.value.details["reason"] == "end_date_before_start"
    assert db.commits == 0


@pytest.mark.asyncio
async def test_terminal_update_attaches_upstream_with_consistency_checks() -> None:
    repository = _Repository()
    repository.terminal.upstream_contract_id = None
    repository.upstream_for_terminal = repository.upstream
    service = _service(repository)
    db = _DB()

    response = await service.update_terminal(
        db,
        contract_id="terminal-1",
        request=_terminal_update(upstream_contract_id="upstream-1"),
        actor_id="actor-1",
        scope=SCOPE,
    )

    assert response.upstream_contract_id == "upstream-1"
    assert [warning.code for warning in response.warnings] == []
    assert db.commits == 1


@pytest.mark.asyncio
async def test_terminal_update_rejects_mode_type_mismatch() -> None:
    repository = _Repository()
    repository.terminal.upstream_contract_id = None
    repository.upstream.contract_type = "management_agreement"
    repository.upstream_for_terminal = repository.upstream
    service = _service(repository)
    db = _DB()

    with pytest.raises(AssetContractCoverageInvalidError) as error:
        await service.update_terminal(
            db,
            contract_id="terminal-1",
            request=_terminal_update(upstream_contract_id="upstream-1"),
            actor_id="actor-1",
            scope=SCOPE,
        )
    assert error.value.details["reason"] == "upstream_type_mismatch"
    assert db.commits == 0


@pytest.mark.asyncio
async def test_terminal_update_resyncs_coverage_on_extension() -> None:
    repository = _Repository()
    service = _service(repository)
    db = _DB()

    response = await service.update_terminal(
        db,
        contract_id="terminal-1",
        request=_terminal_update(end_date=date(2027, 3, 31)),
        actor_id="actor-1",
        scope=SCOPE,
    )

    assert response.end_date == date(2027, 3, 31)
    assert repository.terminal_coverages[0].effective_to == date(2027, 3, 31)
    assert repository.retargets == [
        ("terminal", "terminal-1", date(2026, 12, 31), date(2027, 3, 31))
    ]


@pytest.mark.asyncio
async def test_update_returns_404_for_unknown_contract() -> None:
    from src.core.exception_handler import ResourceNotFoundError

    repository = _Repository()
    service = _service(repository)
    db = _DB()

    with pytest.raises(ResourceNotFoundError):
        await service.update_upstream(
            db,
            contract_id="missing",
            request=_upstream_update(),
            actor_id="actor-1",
            scope=SCOPE,
        )
    assert db.commits == 0


@pytest.mark.asyncio
async def test_terminal_update_blocked_after_termination() -> None:
    from src.models.asset_contract import ContractLifecycleEvent

    repository = _Repository()
    repository.events.append(
        ContractLifecycleEvent(  # type: ignore[call-arg]
            id="event-term",
            contract_kind="terminal",
            contract_id="terminal-1",
            event_type="terminated",
            effective_date=date(2026, 6, 30),
            termination_type="early",
            handover_status="completed",
            deposit_settlement_status="settled",
            reason="已终止",
            created_by="actor-1",
            created_at=datetime(2026, 7, 1),
            idempotency_key="term-1",
        )
    )
    service = _service(repository)
    db = _DB()

    from src.services.asset_operations.errors import (
        TerminalContractAlreadyTerminatedError,
    )

    with pytest.raises(TerminalContractAlreadyTerminatedError):
        await service.update_terminal(
            db,
            contract_id="terminal-1",
            request=_terminal_update(end_date=date(2027, 6, 30)),
            actor_id="actor-1",
            scope=SCOPE,
        )
    assert repository.retargets == []
    assert db.commits == 0


@pytest.mark.asyncio
async def test_terminal_update_recomputes_warnings_from_real_upstream() -> None:
    repository = _Repository()
    repository.upstream.end_date = date(2026, 11, 30)
    service = _service(repository)
    db = _DB()

    response = await service.update_terminal(
        db,
        contract_id="terminal-1",
        request=_terminal_update(deposit_amount=Decimal("26000")),
        actor_id="actor-1",
        scope=SCOPE,
    )

    warning_codes = [warning.code for warning in response.warnings]
    assert "UPSTREAM_CONTRACT_MISSING" not in warning_codes
    assert "TERMINAL_TERM_EXCEEDS_UPSTREAM" in warning_codes
