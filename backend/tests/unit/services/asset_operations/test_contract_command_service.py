"""Contract confirmation writes through one scoped, idempotent command seam."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from src.core.exception_handler import ResourceNotFoundError
from src.models.asset_contract import (
    AssetContractWriteReceipt,
    UpstreamContract,
    UpstreamContractAssetUnit,
)
from src.models.asset_unit import AssetUnit
from src.schemas.asset_operations import TerminalContractCreate, UpstreamContractCreate
from src.services.asset_operations.contract_command_service import (
    AssetContractCommandService,
)
from src.services.asset_operations.errors import (
    AssetContractCoverageInvalidError,
    AssetOperationsIdempotencyConflictError,
    AssetUnitPeriodOverlapError,
    ScanDocumentAlreadyBoundError,
)
from src.services.party_scope_resolver import EffectivePartyScope

NOW = datetime(2026, 10, 24, 4, 0, tzinfo=UTC)
SCOPE = EffectivePartyScope(
    user_id="user-1",
    source="explicit",
    scope_mode="all",
    owner_party_ids=["owner-1"],
    manager_party_ids=["operator-1"],
)


def _unit(unit_id: str = "unit-1") -> AssetUnit:
    return AssetUnit(
        id=unit_id,
        unit_code=f"U-{unit_id}",
        name="测试物业",
        project_id="project-1",
        owner_party_id="owner-1",
        address="测试地址",
        usage_type="商铺",
        acquisition_mode="leased",
        is_operating=True,
        land_area=Decimal("0"),
        building_area=Decimal("100"),
        rentable_area=Decimal("80"),
        managed_from=date(2026, 1, 1),
        predecessor_unit_ids=[],
        version=1,
    )


def _upstream_request() -> UpstreamContractCreate:
    return UpstreamContractCreate.model_validate(
        {
            "contract_number": "UP-001",
            "contract_type": "lease",
            "name": "测试承租合同",
            "owner_party_id": "owner-1",
            "operator_party_id": "operator-1",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "payment_cycle": "monthly",
            "payment_day": 15,
            "deposit_amount": "1000",
            "scan_document_id": "scan-1",
            "asset_unit_ids": ["unit-1"],
            "rent_schedules": [],
        }
    )


def _terminal_request(
    *, upstream_contract_id: str | None = None
) -> TerminalContractCreate:
    return TerminalContractCreate.model_validate(
        {
            "contract_number": "TM-001",
            "contract_mode": "sublease",
            "tenant_party_id": "tenant-1",
            "lessor_party_id": "operator-1",
            "upstream_contract_id": upstream_contract_id,
            "start_date": "2026-02-01",
            "end_date": "2027-03-31",
            "deposit_months": "2",
            "deposit_amount": "2000",
            "rent_collector": "operator",
            "scan_document_id": "scan-2",
            "asset_unit_ids": ["unit-1"],
            "rent_schedules": [],
        }
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "changes",
    [
        {"contract_type": "lease", "management_fee_rate": "0.08"},
        {
            "contract_type": "management_agreement",
            "payment_cycle": None,
            "payment_day": None,
            "management_fee_rate": "0.08",
            "deposit_amount": "1",
        },
        {
            "contract_type": "management_agreement",
            "payment_cycle": None,
            "payment_day": None,
            "management_fee_rate": "0.08",
            "deposit_amount": "0",
            "rent_schedules": [
                {
                    "stage_start": "2026-01-01",
                    "stage_end": "2026-12-31",
                    "base_monthly_rent": "100",
                    "actual_monthly_rent": "100",
                    "payment_cycle": "monthly",
                    "due_day": 25,
                }
            ],
        },
    ],
)
async def test_upstream_confirmation_rejects_inapplicable_fields(changes) -> None:
    from src.core.exception_handler import BaseBusinessError

    request = UpstreamContractCreate.model_validate(
        {**_upstream_request().model_dump(), **changes}
    )
    repository = _Repository()
    db = _DB()
    with pytest.raises(BaseBusinessError) as error:
        await _service(repository, _UnitLocker((_unit(),))).create_upstream(
            db,
            request=request,
            actor_id="user-1",
            scope=SCOPE,
            idempotency_key="invalid-field",
            attachment_owner_id="intake-1",
        )
    assert error.value.code == "CONTRACT_FIELD_NOT_APPLICABLE"
    assert error.value.status_code == 422
    assert repository.writes == 0
    assert db.commits == 0


class _UnitLocker:
    def __init__(
        self,
        units: tuple[AssetUnit, ...],
        *,
        manager_party_ids: dict[str, str | None] | None = None,
    ) -> None:
        self.units = units
        self.manager_party_ids = manager_party_ids or {"project-1": "operator-1"}
        self.calls: list[tuple[str, ...]] = []

    async def lock_for_write(self, _db, *, unit_ids, scope):
        assert scope is SCOPE
        self.calls.append(tuple(unit_ids))
        return self.units

    async def get_project_manager_party_ids(self, _db, *, project_ids):
        return {
            project_id: self.manager_party_ids.get(project_id)
            for project_id in project_ids
        }


class _Repository:
    def __init__(self) -> None:
        self.receipt: AssetContractWriteReceipt | None = None
        self.upstream: UpstreamContract | None = None
        self.upstream_coverages: tuple[UpstreamContractAssetUnit, ...] = ()
        self.overlap_ids: tuple[str, ...] = ()
        self.bind_allowed = True
        self.writes = 0

    async def get_write_receipt(self, _db, *, actor_id, idempotency_key):
        return self.receipt

    async def require_contract_attachment(self, _db, *, attachment_id):
        if attachment_id not in {"scan-1", "scan-2"}:
            return None
        return object()

    async def bind_contract_attachment(
        self,
        _db,
        *,
        attachment_id: str,
        contract_id: str,
        expected_owner_id: str,
    ) -> bool:
        assert expected_owner_id == "intake-1"
        return self.bind_allowed

    async def get_upstream_for_terminal(self, _db, *, contract_id, unit_ids, scope):
        assert unit_ids == ("unit-1",)
        assert scope is SCOPE
        return self.upstream

    async def list_upstream_coverages(self, _db, *, contract_id):
        return self.upstream_coverages

    async def find_terminal_overlaps(self, _db, *, unit_ids, start_date, end_date):
        return self.overlap_ids

    async def add_upstream(self, db, *, contract, coverages, schedules):
        self.writes += 1
        contract.created_at = NOW.replace(tzinfo=None)
        contract.updated_at = NOW.replace(tzinfo=None)
        contract.version = 1

    async def add_terminal(self, db, *, contract, coverages, schedules):
        self.writes += 1
        contract.created_at = NOW.replace(tzinfo=None)
        contract.updated_at = NOW.replace(tzinfo=None)
        contract.version = 1

    async def add_write_receipt(self, db, *, receipt):
        self.receipt = receipt


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


def _service(
    repository: _Repository, locker: _UnitLocker
) -> AssetContractCommandService:
    ids = iter(["contract-1", "receipt-1"])
    return AssetContractCommandService(
        repository=repository,
        unit_repository=locker,
        clock=lambda: NOW,
        business_today=lambda: date(2026, 10, 24),
        id_factory=lambda: next(ids),
    )


@pytest.mark.asyncio
async def test_create_upstream_locks_units_and_persists_one_atomic_aggregate() -> None:
    repository = _Repository()
    locker = _UnitLocker((_unit(),))
    db = _DB()

    response = await _service(repository, locker).create_upstream(
        db,
        request=_upstream_request(),
        actor_id="user-1",
        scope=SCOPE,
        idempotency_key="request-1",
        attachment_owner_id="intake-1",
    )

    assert locker.calls == [("unit-1",)]
    assert repository.writes == 1
    assert db.commits == 1
    assert response.id == "contract-1"
    assert response.status == "expiring"
    assert response.idempotent is False


@pytest.mark.asyncio
async def test_create_contract_fails_closed_when_any_scoped_unit_is_missing() -> None:
    repository = _Repository()
    db = _DB()

    with pytest.raises(ResourceNotFoundError):
        await _service(repository, _UnitLocker(())).create_upstream(
            db,
            request=_upstream_request(),
            actor_id="user-1",
            scope=SCOPE,
            idempotency_key="request-1",
            attachment_owner_id="intake-1",
        )

    assert repository.writes == 0
    assert db.commits == 0


@pytest.mark.asyncio
async def test_terminal_without_upstream_is_saved_with_warning() -> None:
    repository = _Repository()
    db = _DB()

    response = await _service(repository, _UnitLocker((_unit(),))).create_terminal(
        db,
        request=_terminal_request(),
        actor_id="user-1",
        scope=SCOPE,
        idempotency_key="request-2",
        attachment_owner_id="intake-1",
    )

    assert repository.writes == 1
    assert response.warnings[0].code == "UPSTREAM_CONTRACT_MISSING"


@pytest.mark.asyncio
async def test_unlinked_direct_lease_must_use_the_units_single_owner() -> None:
    request = TerminalContractCreate.model_validate(
        {
            "contract_number": "TM-DIRECT-001",
            "contract_mode": "direct_lease",
            "tenant_party_id": "tenant-1",
            "lessor_party_id": "owner-other",
            "upstream_contract_id": None,
            "start_date": "2026-02-01",
            "end_date": "2026-12-31",
            "deposit_amount": "0",
            "rent_collector": "owner",
            "scan_document_id": "scan-2",
            "asset_unit_ids": ["unit-1"],
            "rent_schedules": [],
        }
    )

    with pytest.raises(AssetContractCoverageInvalidError) as exc_info:
        await _service(_Repository(), _UnitLocker((_unit(),))).create_terminal(
            _DB(),
            request=request,
            actor_id="user-1",
            scope=SCOPE,
            idempotency_key="request-direct-lessor",
            attachment_owner_id="intake-1",
        )

    assert exc_info.value.details["reason"] == "lessor_party_mismatch"


@pytest.mark.asyncio
async def test_unlinked_sublease_must_use_the_projects_single_manager() -> None:
    locker = _UnitLocker(
        (_unit(),),
        manager_party_ids={"project-1": "operator-other"},
    )

    with pytest.raises(AssetContractCoverageInvalidError) as exc_info:
        await _service(_Repository(), locker).create_terminal(
            _DB(),
            request=_terminal_request(),
            actor_id="user-1",
            scope=SCOPE,
            idempotency_key="request-sublease-lessor",
            attachment_owner_id="intake-1",
        )

    assert exc_info.value.details["reason"] == "lessor_party_mismatch"


@pytest.mark.asyncio
async def test_terminal_exceeding_selected_upstream_is_saved_with_warning() -> None:
    repository = _Repository()
    repository.upstream = UpstreamContract(
        id="upstream-1",
        contract_number="UP-001",
        contract_type="lease",
        name="上游合同",
        owner_party_id="owner-1",
        operator_party_id="operator-1",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        payment_cycle="monthly",
        deposit_amount=0,
        scan_document_id="scan-1",
    )
    repository.upstream_coverages = (
        UpstreamContractAssetUnit(
            upstream_contract_id="upstream-1",
            asset_unit_id="unit-1",
            effective_from=date(2026, 1, 1),
            effective_to=date(2026, 12, 31),
        ),
    )

    response = await _service(repository, _UnitLocker((_unit(),))).create_terminal(
        _DB(),
        request=_terminal_request(upstream_contract_id="upstream-1"),
        actor_id="user-1",
        scope=SCOPE,
        idempotency_key="request-3",
        attachment_owner_id="intake-1",
    )

    assert response.warnings[0].code == "TERMINAL_TERM_EXCEEDS_UPSTREAM"


@pytest.mark.asyncio
async def test_selected_upstream_mode_mismatch_returns_stable_conflict() -> None:
    repository = _Repository()
    repository.upstream = UpstreamContract(
        id="upstream-1",
        contract_number="UP-001",
        contract_type="lease",
        name="上游合同",
        owner_party_id="owner-1",
        operator_party_id="operator-1",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        payment_cycle="monthly",
        deposit_amount=0,
        scan_document_id="scan-1",
    )
    request = _terminal_request(upstream_contract_id="upstream-1").model_copy(
        update={
            "contract_mode": "direct_lease",
            "lessor_party_id": "owner-1",
            "rent_collector": "owner",
        }
    )

    with pytest.raises(AssetContractCoverageInvalidError) as exc_info:
        await _service(repository, _UnitLocker((_unit(),))).create_terminal(
            _DB(),
            request=request,
            actor_id="user-1",
            scope=SCOPE,
            idempotency_key="request-mode-mismatch",
            attachment_owner_id="intake-1",
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.details["reason"] == "upstream_type_mismatch"


@pytest.mark.asyncio
async def test_terminal_period_overlap_is_rejected_before_write() -> None:
    repository = _Repository()
    repository.overlap_ids = ("terminal-existing",)

    with pytest.raises(AssetUnitPeriodOverlapError):
        await _service(repository, _UnitLocker((_unit(),))).create_terminal(
            _DB(),
            request=_terminal_request(),
            actor_id="user-1",
            scope=SCOPE,
            idempotency_key="request-4",
            attachment_owner_id="intake-1",
        )

    assert repository.writes == 0


@pytest.mark.asyncio
async def test_same_idempotency_key_replays_response_and_conflicts_on_other_body() -> (
    None
):
    repository = _Repository()
    service = _service(repository, _UnitLocker((_unit(),)))
    db = _DB()
    first = await service.create_upstream(
        db,
        request=_upstream_request(),
        actor_id="user-1",
        scope=SCOPE,
        idempotency_key="request-5",
        attachment_owner_id="intake-1",
    )
    replay = await service.create_upstream(
        db,
        request=_upstream_request(),
        actor_id="user-1",
        scope=SCOPE,
        idempotency_key="request-5",
        attachment_owner_id="intake-1",
    )

    assert replay.id == first.id
    assert replay.idempotent is True
    assert repository.writes == 1

    changed = _upstream_request().model_copy(update={"name": "另一份合同"})
    with pytest.raises(AssetOperationsIdempotencyConflictError):
        await service.create_upstream(
            db,
            request=changed,
            actor_id="user-1",
            scope=SCOPE,
            idempotency_key="request-5",
            attachment_owner_id="intake-1",
        )


@pytest.mark.asyncio
async def test_scan_owned_by_another_intake_cannot_be_consumed() -> None:
    repository = _Repository()
    repository.bind_allowed = False
    db = _DB()

    with pytest.raises(ScanDocumentAlreadyBoundError):
        await _service(repository, _UnitLocker((_unit(),))).create_upstream(
            db,
            request=_upstream_request(),
            actor_id="user-1",
            scope=SCOPE,
            idempotency_key="request-6",
            attachment_owner_id="intake-1",
        )

    assert db.commits == 0
    assert db.rollbacks == 1
