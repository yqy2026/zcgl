"""Asset-unit list/detail reads derive rental facts from live coverage."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest

from src.core.exception_handler import ResourceNotFoundError
from src.models.asset_contract import ContractLifecycleEvent
from src.models.asset_unit import AssetUnit
from src.schemas.asset_operations import (
    AssetUnitUpdate,
    AssetUnitVacancyNoteUpdate,
)
from src.services.asset_operations.asset_unit_command_service import (
    AssetUnitCommandService,
)
from src.services.asset_operations.query_service import AssetOperationsQueryService
from src.services.party_scope_resolver import EffectivePartyScope

TODAY = date(2026, 10, 25)
SCOPE = EffectivePartyScope(
    user_id="actor-1",
    source="explicit",
    scope_mode="owner",
    owner_party_ids=["owner-1"],
)


def _unit(**overrides: object) -> AssetUnit:
    values: dict[str, object] = {
        "id": "unit-1",
        "unit_code": "U-001",
        "name": "一号商铺",
        "project_id": "project-1",
        "owner_party_id": "owner-1",
        "address": "地址 1 号",
        "usage_type": "commercial",
        "acquisition_mode": "leased",
        "is_operating": True,
        "land_area": Decimal("0"),
        "building_area": Decimal("100"),
        "rentable_area": Decimal("80"),
        "managed_from": date(2026, 1, 1),
        "predecessor_unit_ids": [],
        "version": 2,
        "created_at": datetime(2026, 1, 1),
        "updated_at": datetime(2026, 1, 1),
    }
    values.update(overrides)
    return AssetUnit(**values)  # type: ignore[arg-type]


class _UnitReader:
    def __init__(self, units: list[AssetUnit]) -> None:
        self.units = units
        self.get_calls: list[str] = []

    async def list(self, _db, **kwargs):
        rows = list(self.units)
        if kwargs.get("non_rentable_only"):
            rows = [
                unit
                for unit in rows
                if not unit.is_operating or unit.rentable_area <= 0
            ]
        if kwargs.get("rentable_only"):
            rows = [
                unit
                for unit in rows
                if unit.is_operating and unit.rentable_area > 0
            ]
        exclude = kwargs.get("exclude_unit_ids")
        if exclude:
            rows = [unit for unit in rows if unit.id not in set(exclude)]
        restrict = kwargs.get("unit_ids")
        if restrict is not None:
            rows = [unit for unit in rows if unit.id in set(restrict)]
        return list(rows), len(rows)

    async def get(self, _db, *, unit_id, scope, for_update=False):
        self.get_calls.append(unit_id)
        return next((u for u in self.units if u.id == unit_id), None)

    async def project_names(self, _db, *, project_ids):
        return {}

    async def active_certificate_counts(self, _db, *, unit_ids, as_of):
        return {}

    async def lock_for_write(self, _db, *, unit_ids, scope):
        return tuple(self.units)

    async def update_fields(self, _db, *, unit, fields: dict[str, object]) -> None:
        for key, value in fields.items():
            setattr(unit, key, value)


class _ContractReader:
    def __init__(self, rented_unit_ids: set[str]) -> None:
        self.rented_unit_ids = rented_unit_ids

    async def list_rented_unit_ids(self, _db, *, as_of, scope):
        return self.rented_unit_ids

    async def find_terminal_overlaps(
        self, _db, *, unit_ids, start_date, end_date
    ):
        if set(unit_ids) & self.rented_unit_ids:
            return ("terminal-1",)
        return ()

    async def list_terminal_coverages(self, _db, *, asset_unit_id):
        if asset_unit_id == "unit-1" and "unit-1" in self.rented_unit_ids:
            return ("terminal-1",)
        return ()

    async def list_active_terminals_by_units(self, _db, *, unit_ids, as_of):
        return ()

    async def list_lifecycle_events_by_contract_ids(
        self, _db, *, contract_kind, contract_ids
    ):
        return ()

    async def list_lifecycle_events(self, _db, *, contract_kind, contract_id):
        return ()


class _PartyNameReader:
    async def get_party_names_by_ids(self, _db, *, party_ids):
        return {}


class _DB:
    def __init__(self) -> None:
        self.commits = 0
        self.added: list[object] = []

    def commit_called(self) -> bool:
        return self.commits > 0

    def add(self, obj: object) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        return None


def _query_service(
    units: list[AssetUnit], rented: set[str]
) -> AssetOperationsQueryService:
    return AssetOperationsQueryService(
        asset_unit_repository=_UnitReader(units),  # type: ignore[arg-type]
        asset_contract_repository=_ContractReader(rented),  # type: ignore[arg-type]
        party_name_reader=_PartyNameReader(),  # type: ignore[arg-type]
        business_today=lambda: TODAY,
    )


@pytest.mark.asyncio
async def test_unit_list_derives_rental_status_and_occupancy() -> None:
    rented = _unit()
    vacant = _unit(id="unit-2", unit_code="U-002")
    non_rentable = _unit(
        id="unit-3", unit_code="U-003", is_operating=False
    )
    service = _query_service([rented, vacant, non_rentable], {"unit-1"})

    items, total = await service.list_asset_units(_DB(), scope=SCOPE)

    assert total == 3
    by_id = {item.id: item for item in items}
    assert by_id["unit-1"].rental_status == "rented"
    assert by_id["unit-1"].rented_area == Decimal("80")
    assert by_id["unit-1"].occupancy_rate == Decimal("1")
    assert by_id["unit-2"].rental_status == "vacant"
    assert by_id["unit-2"].rented_area == Decimal("0")
    assert by_id["unit-3"].rental_status == "non_rentable"


@pytest.mark.asyncio
async def test_unit_detail_aggregates_coverage_facts() -> None:
    service = _query_service([_unit()], {"unit-1"})

    detail = await service.get_asset_unit_detail(_DB(), "unit-1", scope=SCOPE)

    assert detail is not None
    assert detail.rental_status == "rented"
    assert detail.terminal_contract_ids == ["terminal-1"]


@pytest.mark.asyncio
async def test_unit_detail_returns_none_for_unknown() -> None:
    service = _query_service([], set())

    assert await service.get_asset_unit_detail(_DB(), "missing", scope=SCOPE) is None


class _Repository(_UnitReader):
    async def list_lifecycle_events(self, _db, *, contract_kind, contract_id):
        return tuple()


def _command_service(
    units: list[AssetUnit], events: list[ContractLifecycleEvent] | None = None
) -> AssetUnitCommandService:
    repository = _Repository(units)
    repository.events = events or []
    return AssetUnitCommandService(
        repository=repository,  # type: ignore[arg-type]
        contract_repository=_ContractReader(set()),  # type: ignore[arg-type]
        business_today=lambda: TODAY,
    )


@pytest.mark.asyncio
async def test_unit_update_applies_fields_under_optimistic_lock() -> None:
    units = [_unit()]
    service = _command_service(units)
    db = _DB()

    response = await service.update_asset_unit(
        db,
        unit_id="unit-1",
        request=AssetUnitUpdate.model_validate(
            {"expected_version": 2, "name": "改名后的商铺"}
        ),
        actor_id="actor-1",
        scope=SCOPE,
    )

    assert response.name == "改名后的商铺"
    assert response.rental_status == "vacant"
    assert db.commit_called() is True


@pytest.mark.asyncio
async def test_unit_update_rejects_version_drift() -> None:
    service = _command_service([_unit()])
    db = _DB()

    from src.services.asset_operations.errors import AssetOperationsVersionConflictError

    with pytest.raises(AssetOperationsVersionConflictError):
        await service.update_asset_unit(
            db,
            unit_id="unit-1",
            request=AssetUnitUpdate.model_validate(
                {"expected_version": 99, "name": "漂移"}
            ),
            actor_id="actor-1",
            scope=SCOPE,
        )


@pytest.mark.asyncio
async def test_unit_update_rejects_rentable_over_building() -> None:
    service = _command_service([_unit()])
    db = _DB()

    from src.services.asset_operations.errors import AssetUnitAreaInvalidError

    with pytest.raises(AssetUnitAreaInvalidError):
        await service.update_asset_unit(
            db,
            unit_id="unit-1",
            request=AssetUnitUpdate.model_validate(
                {"expected_version": 2, "rentable_area": Decimal("200")}
            ),
            actor_id="actor-1",
            scope=SCOPE,
        )


@pytest.mark.asyncio
async def test_unit_update_returns_404_for_unknown() -> None:
    service = _command_service([])
    db = _DB()

    with pytest.raises(ResourceNotFoundError):
        await service.update_asset_unit(
            db,
            unit_id="missing",
            request=AssetUnitUpdate.model_validate(
                {"expected_version": 1, "name": "不存在"}
            ),
            actor_id="actor-1",
            scope=SCOPE,
        )


@pytest.mark.asyncio
async def test_vacancy_note_update_sets_reason_and_expected_start() -> None:
    units = [_unit()]
    service = _command_service(units)
    db = _DB()

    response = await service.update_vacancy_note(
        db,
        unit_id="unit-1",
        request=AssetUnitVacancyNoteUpdate.model_validate(
            {
                "expected_version": 2,
                "vacancy_reason": "renovation",
                "expected_lease_start": "2027-01-01",
            }
        ),
        actor_id="actor-1",
        scope=SCOPE,
    )

    assert response.vacancy_reason == "renovation"
    assert response.expected_lease_start == date(2027, 1, 1)
    assert db.commit_called() is True


@pytest.mark.asyncio
async def test_unit_list_non_rentable_filter_selects_only_non_rentable() -> None:
    rented = _unit()
    non_rentable = _unit(id="unit-3", unit_code="U-003", is_operating=False)
    service = _query_service([rented, non_rentable], {"unit-1"})

    items, total = await service.list_asset_units(
        _DB(), scope=SCOPE, filter="non_rentable"
    )

    assert total == 1
    assert [item.id for item in items] == ["unit-3"]
    assert items[0].rental_status == "non_rentable"


@pytest.mark.asyncio
async def test_unit_list_view_filters_counts_and_assessment_labels() -> None:
    rented = _unit()
    vacant = _unit(id="unit-2", unit_code="U-002")
    non_rentable = _unit(id="unit-3", unit_code="U-003", is_operating=False)
    service = _query_service([rented, vacant, non_rentable], {"unit-1"})

    items, total, counts = await service.list_asset_units_view(
        _DB(),
        scope=SCOPE,
        filter="vacant",
    )

    # 空置筛选：可租且今天无在租终端合同。
    assert total == 1
    assert [item.id for item in items] == ["unit-2"]
    assert items[0].rental_status == "vacant"
    # 分段筛选计数与筛选语义一致。
    assert counts.all == 3
    assert counts.vacant == 1
    assert counts.non_rentable == 1


@pytest.mark.asyncio
async def test_unit_list_assessment_marks_decided_and_pending(monkeypatch) -> None:
    from types import SimpleNamespace as Row
    from unittest.mock import AsyncMock

    from src.crud import assessment_scope as scope_module

    units = [_unit(), _unit(id="unit-2", unit_code="U-002")]
    service = AssetOperationsQueryService(
        asset_unit_repository=_UnitReader(units),  # type: ignore[arg-type]
        asset_contract_repository=_ContractReader(set()),  # type: ignore[arg-type]
        party_name_reader=_PartyNameReader(),  # type: ignore[arg-type]
        business_today=lambda: TODAY,
    )

    item = Row(asset_unit_id="unit-1", included=False)
    monkeypatch.setattr(
        scope_module.assessment_scope_repository,
        "get_active_version",
        AsyncMock(return_value=Row(id="v1")),
    )
    monkeypatch.setattr(
        scope_module.assessment_scope_repository,
        "list_items",
        AsyncMock(return_value=(item,)),
    )
    monkeypatch.setattr(
        scope_module.assessment_scope_repository,
        "list_managed_units",
        AsyncMock(return_value=list(units)),
    )

    items, _total, counts = await service.list_asset_units_view(
        _DB(),
        scope=SCOPE,
        assessment_operator_party_id="op-1",
        assessment_year=2026,
    )

    by_id = {row.id: row for row in items}
    # unit-1 有落库决定（排除）→ 不纳入；unit-2 是经营性候选但无决定 → 待确认。
    assert by_id["unit-1"].assessment == "excluded"
    assert by_id["unit-2"].assessment == "pending"
    assert counts.in_assessment == 0
