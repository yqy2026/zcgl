"""Preview and atomic commit behavior for asset-unit merges."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.crud.asset_unit_boundary import AssetUnitMergeContext
from src.models.asset_contract import UpstreamContract, UpstreamContractAssetUnit
from src.models.asset_unit import AssetUnit, AssetUnitBoundaryChange
from src.schemas.asset_operations import (
    AssetUnitMergeCommitRequest,
    AssetUnitMergeProposal,
    AssetUnitMergeResultInput,
)
from src.services.asset_operations.boundary_command_service import (
    AssetUnitBoundaryCommandService,
)
from src.services.asset_operations.errors import (
    AssetOperationsPreviewStaleError,
    AssetOperationsVersionConflictError,
    AssetUnitBoundaryInvalidError,
)
from src.services.party_scope_resolver import EffectivePartyScope


def _unit(unit_id: str, code: str, building: str, rentable: str) -> AssetUnit:
    return AssetUnit(
        id=unit_id,
        unit_code=code,
        name=f"{code} 商铺",
        project_id="project-1",
        owner_party_id="owner-1",
        address="测试路 1 号",
        usage_type="commercial",
        acquisition_mode="leased",
        is_operating=True,
        land_area=Decimal("0"),
        building_area=Decimal(building),
        rentable_area=Decimal(rentable),
        managed_from=date(2026, 1, 1),
        predecessor_unit_ids=[],
        version=1,
    )


def _context() -> AssetUnitMergeContext:
    sources = (
        _unit("unit-1", "U-001", "40", "30"),
        _unit("unit-2", "U-002", "60", "50"),
    )
    coverages = tuple(
        UpstreamContractAssetUnit(
            upstream_contract_id="upstream-1",
            asset_unit_id=source.id,
            effective_from=date(2026, 1, 1),
            effective_to=date(2026, 12, 31),
        )
        for source in sources
    )
    upstream = UpstreamContract(
        id="upstream-1",
        contract_number="UP-001",
        contract_type="lease",
        name="测试上游合同",
        owner_party_id="owner-1",
        operator_party_id="operator-1",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        payment_cycle="monthly",
        payment_day=1,
        deposit_amount=Decimal("0"),
        scan_document_id="scan-1",
    )
    return AssetUnitMergeContext(
        sources=sources,
        upstream_coverages=coverages,
        upstream_contracts=(upstream,),
    )


def _scope() -> EffectivePartyScope:
    return EffectivePartyScope(
        user_id="actor-1",
        source="explicit",
        scope_mode="owner",
        owner_party_ids=["owner-1"],
    )


def _proposal() -> AssetUnitMergeProposal:
    return AssetUnitMergeProposal(
        source_unit_ids=["unit-2", "unit-1"],
        effective_date=date(2026, 11, 1),
        result=AssetUnitMergeResultInput(
            unit_code="U-001+002",
            name="一二号合并商铺",
        ),
    )


class _PreviewStore:
    def __init__(self) -> None:
        self.payload: dict[str, object] | None = None
        self.deleted: list[str] = []

    def issue(self, payload: dict[str, object]) -> tuple[str, datetime]:
        self.payload = payload
        return "merge-token", datetime(2026, 10, 24, 9, 10)

    def peek(self, raw_token: str) -> dict[str, object] | None:
        return self.payload if raw_token == "merge-token" else None

    def delete(self, raw_token: str) -> bool:
        self.deleted.append(raw_token)
        return True


class _Repository:
    def __init__(self, context: AssetUnitMergeContext) -> None:
        self.context = context
        self.persisted: dict[str, object] | None = None
        self.existing: AssetUnitBoundaryChange | None = None

    async def load_merge_context(
        self, _db: object, **_kwargs: object
    ) -> AssetUnitMergeContext:
        return self.context

    async def get_boundary_change_by_idempotency(
        self, _db: object, **_kwargs: object
    ) -> AssetUnitBoundaryChange | None:
        return self.existing

    async def get_asset_unit_version(self, _db: object, *, unit_id: str) -> int | None:
        source = next(
            (item for item in self.context.sources if item.id == unit_id), None
        )
        return source.version if source is not None else None

    async def persist_merge(
        self, _db: object, **kwargs: object
    ) -> AssetUnitBoundaryChange:
        self.persisted = kwargs
        boundary_change = kwargs["boundary_change"]
        assert isinstance(boundary_change, AssetUnitBoundaryChange)
        self.existing = boundary_change
        return boundary_change


@pytest.mark.asyncio
async def test_merge_preview_normalizes_sources_and_computes_result_areas() -> None:
    store = _PreviewStore()
    service = AssetUnitBoundaryCommandService(
        repository=_Repository(_context()),
        preview_store=store,
        clock=lambda: datetime(2026, 10, 24, 9, 0),
    )

    preview = await service.preview_merge(
        SimpleNamespace(),
        proposal=_proposal(),
        actor_id="actor-1",
        scope=_scope(),
    )

    assert preview.change_type == "merge"
    assert preview.source_unit_ids == ["unit-1", "unit-2"]
    assert preview.results[0].model_dump(mode="json") == {
        "unit_code": "U-001+002",
        "name": "一二号合并商铺",
        "land_area": "0",
        "building_area": "100",
        "rentable_area": "80",
    }
    assert preview.versions == {"unit-1": 1, "unit-2": 1}
    assert preview.impact.unit_count_delta == -1
    assert store.payload is not None
    assert store.payload["action"] == "merge"
    assert store.payload["source_unit_ids"] == ["unit-1", "unit-2"]


@pytest.mark.asyncio
async def test_merge_commit_ends_all_sources_and_replays_idempotently() -> None:
    repository = _Repository(_context())
    store = _PreviewStore()
    db = SimpleNamespace(
        commit=AsyncMock(),
        rollback=AsyncMock(),
    )
    service = AssetUnitBoundaryCommandService(
        repository=repository,
        preview_store=store,
        clock=lambda: datetime(2026, 10, 24, 9, 0),
    )
    preview = await service.preview_merge(
        db,
        proposal=_proposal(),
        actor_id="actor-1",
        scope=_scope(),
    )
    request = AssetUnitMergeCommitRequest(
        preview_token=preview.preview_token,
        reason="恢复完整经营边界",
        expected_versions=preview.versions,
    )

    committed = await service.commit_merge(
        db,
        request=request,
        actor_id="actor-1",
        scope=_scope(),
        idempotency_key="merge-request-1",
    )
    replayed = await service.commit_merge(
        db,
        request=request,
        actor_id="actor-1",
        scope=_scope(),
        idempotency_key="merge-request-1",
    )

    assert committed.change_type == "merge"
    assert committed.source_unit_ids == ["unit-1", "unit-2"]
    assert replayed.idempotent is True
    assert replayed.boundary_change_id == committed.boundary_change_id
    assert repository.persisted is not None
    sources = repository.persisted["sources"]
    assert all(source.managed_to == date(2026, 10, 31) for source in sources)
    assert all(source.version == 2 for source in sources)
    result = repository.persisted["result"]
    assert result.predecessor_unit_ids == ["unit-1", "unit-2"]
    assert result.building_area == Decimal("100")
    assert store.deleted == ["merge-token"]


@pytest.mark.asyncio
async def test_merge_commit_requires_exact_token_version_set() -> None:
    repository = _Repository(_context())
    store = _PreviewStore()
    service = AssetUnitBoundaryCommandService(
        repository=repository,
        preview_store=store,
        clock=lambda: datetime(2026, 10, 24, 9, 0),
    )
    preview = await service.preview_merge(
        SimpleNamespace(),
        proposal=_proposal(),
        actor_id="actor-1",
        scope=_scope(),
    )

    with pytest.raises(AssetOperationsPreviewStaleError) as missing:
        await service.commit_merge(
            SimpleNamespace(),
            request=AssetUnitMergeCommitRequest(
                preview_token=preview.preview_token,
                reason="恢复完整经营边界",
                expected_versions={"unit-1": 1, "different-unit": 1},
            ),
            actor_id="actor-1",
            scope=_scope(),
            idempotency_key="merge-request-missing-version",
        )

    assert missing.value.details["reason"] == "version_set_mismatch"
    assert repository.persisted is None


@pytest.mark.asyncio
async def test_merge_rejects_metadata_drift_before_issuing_token() -> None:
    context = _context()
    context.sources[1].project_id = "project-2"
    store = _PreviewStore()
    service = AssetUnitBoundaryCommandService(
        repository=_Repository(context),
        preview_store=store,
        clock=lambda: datetime(2026, 10, 24, 9, 0),
    )

    with pytest.raises(AssetUnitBoundaryInvalidError) as error:
        await service.preview_merge(
            SimpleNamespace(),
            proposal=_proposal(),
            actor_id="actor-1",
            scope=_scope(),
        )

    assert error.value.details["reason"] == "merge_source_metadata_mismatch"
    assert store.payload is None


@pytest.mark.asyncio
async def test_merge_rejects_different_future_upstream_coverage_boundaries() -> None:
    context = _context()
    context.upstream_coverages[1].effective_to = date(2027, 6, 30)
    store = _PreviewStore()
    service = AssetUnitBoundaryCommandService(
        repository=_Repository(context),
        preview_store=store,
        clock=lambda: datetime(2026, 10, 24, 9, 0),
    )

    with pytest.raises(AssetUnitBoundaryInvalidError) as error:
        await service.preview_merge(
            SimpleNamespace(),
            proposal=_proposal(),
            actor_id="actor-1",
            scope=_scope(),
        )

    assert error.value.details["reason"] == (
        "merge_upstream_coverage_boundary_mismatch"
    )
    assert store.payload is None


@pytest.mark.asyncio
async def test_merge_rejects_upstream_coverage_scheduled_after_boundary() -> None:
    context = _context()
    future_contract = UpstreamContract(
        id="upstream-future",
        contract_number="UP-FUTURE",
        contract_type="lease",
        name="未来上游合同",
        owner_party_id="owner-1",
        operator_party_id="operator-1",
        start_date=date(2026, 12, 1),
        end_date=date(2027, 12, 31),
        payment_cycle="monthly",
        payment_day=1,
        deposit_amount=Decimal("0"),
        scan_document_id="scan-future",
    )
    future_coverages = tuple(
        UpstreamContractAssetUnit(
            upstream_contract_id=future_contract.id,
            asset_unit_id=source.id,
            effective_from=date(2026, 12, 1),
            effective_to=date(2027, 12, 31),
        )
        for source in context.sources
    )
    context = replace(
        context,
        upstream_coverages=(*context.upstream_coverages, *future_coverages),
        upstream_contracts=(*context.upstream_contracts, future_contract),
    )
    store = _PreviewStore()
    service = AssetUnitBoundaryCommandService(
        repository=_Repository(context),
        preview_store=store,
        clock=lambda: datetime(2026, 10, 24, 9, 0),
    )

    with pytest.raises(AssetUnitBoundaryInvalidError) as error:
        await service.preview_merge(
            SimpleNamespace(),
            proposal=_proposal(),
            actor_id="actor-1",
            scope=_scope(),
        )

    assert error.value.details["reason"] == "source_has_future_upstream_coverage"
    assert error.value.details["unit_ids"] == ["unit-1", "unit-2"]
    assert store.payload is None


@pytest.mark.asyncio
async def test_merge_detects_changed_source_version_after_preview() -> None:
    repository = _Repository(_context())
    store = _PreviewStore()
    service = AssetUnitBoundaryCommandService(
        repository=repository,
        preview_store=store,
        clock=lambda: datetime(2026, 10, 24, 9, 0),
    )
    preview = await service.preview_merge(
        SimpleNamespace(),
        proposal=_proposal(),
        actor_id="actor-1",
        scope=_scope(),
    )
    repository.context.sources[1].version = 2

    with pytest.raises(AssetOperationsVersionConflictError) as error:
        await service.commit_merge(
            SimpleNamespace(),
            request=AssetUnitMergeCommitRequest(
                preview_token=preview.preview_token,
                reason="恢复完整经营边界",
                expected_versions=preview.versions,
            ),
            actor_id="actor-1",
            scope=_scope(),
            idempotency_key="merge-request-version-conflict",
        )

    assert error.value.details["unit_id"] == "unit-2"
    assert error.value.details["actual_version"] == 2


@pytest.mark.asyncio
async def test_merge_effective_date_uses_asia_shanghai_business_day() -> None:
    service = AssetUnitBoundaryCommandService(
        repository=_Repository(_context()),
        preview_store=_PreviewStore(),
        clock=lambda: datetime(2026, 10, 24, 16, 30),
    )
    proposal = _proposal().model_copy(update={"effective_date": date(2026, 10, 25)})

    with pytest.raises(AssetUnitBoundaryInvalidError) as error:
        await service.preview_merge(
            SimpleNamespace(),
            proposal=proposal,
            actor_id="actor-1",
            scope=_scope(),
        )

    assert error.value.details["reason"] == "effective_date_not_future"
