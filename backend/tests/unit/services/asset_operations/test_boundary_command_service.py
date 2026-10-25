"""Asset-unit boundary preview/commit behavior through the public command seam."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError

from src.core.exception_handler import PartyScopeForbiddenError
from src.models.asset_contract import (
    TerminalContract,
    TerminalContractAssetUnit,
    UpstreamContract,
    UpstreamContractAssetUnit,
)
from src.models.asset_unit import AssetUnit
from src.schemas.asset_operations import (
    AssetUnitSplitCommitRequest,
    AssetUnitSplitPartInput,
    AssetUnitSplitProposal,
)
from src.services.asset_operations.boundary_command_service import (
    AssetUnitBoundaryCommandService,
    AssetUnitBoundaryPreviewStore,
    AssetUnitSplitContext,
)
from src.services.asset_operations.errors import (
    AssetOperationsIdempotencyConflictError,
    AssetOperationsPreviewStaleError,
    AssetOperationsVersionConflictError,
    AssetUnitBoundaryInvalidError,
    AssetUnitPeriodOverlapError,
)
from src.services.party_scope_resolver import EffectivePartyScope


def _source_unit() -> AssetUnit:
    return AssetUnit(
        id="unit-1",
        unit_code="U-001",
        name="一号商铺",
        project_id="project-1",
        owner_party_id="owner-1",
        address="测试地址",
        usage_type="商铺",
        acquisition_mode="leased",
        is_operating=True,
        land_area=Decimal("20.00"),
        building_area=Decimal("100.00"),
        rentable_area=Decimal("80.00"),
        managed_from=date(2026, 1, 1),
        managed_to=None,
        predecessor_unit_ids=[],
        version=3,
    )


def _split_context(
    source: AssetUnit,
    *,
    terminal_conflict_ids: tuple[str, ...] = (),
) -> AssetUnitSplitContext:
    upstream = UpstreamContract(
        id="upstream-1",
        contract_number="UP-001",
        contract_type="lease",
        name="上游合同",
        owner_party_id="owner-1",
        operator_party_id="operator-1",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        payment_cycle="monthly",
        payment_day=1,
        deposit_amount=Decimal("0"),
        scan_document_id="scan-upstream",
    )
    terminal_contracts = tuple(
        TerminalContract(
            id=contract_id,
            contract_number=f"TM-{contract_id}",
            contract_mode="sublease",
            tenant_party_id="tenant-1",
            lessor_party_id="operator-1",
            upstream_contract_id="upstream-1",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            deposit_amount=Decimal("0"),
            rent_collector="operator",
            scan_document_id="scan-terminal",
        )
        for contract_id in terminal_conflict_ids
    )
    return AssetUnitSplitContext(
        source=source,
        upstream_coverages=(
            UpstreamContractAssetUnit(
                upstream_contract_id="upstream-1",
                asset_unit_id=source.id,
                effective_from=date(2026, 1, 1),
            ),
        ),
        upstream_contracts=(upstream,),
        terminal_coverages=tuple(
            TerminalContractAssetUnit(
                terminal_contract_id=contract_id,
                asset_unit_id=source.id,
                effective_from=date(2026, 1, 1),
            )
            for contract_id in terminal_conflict_ids
        ),
        terminal_contracts=terminal_contracts,
    )


class _BoundaryRepository:
    def __init__(
        self,
        context: AssetUnitSplitContext,
        *,
        persist_error: Exception | None = None,
        current_version_override: int | None = None,
    ) -> None:
        self.context = context
        self.persist_error = persist_error
        self.current_version_override = current_version_override
        self.write_count = 0
        self.existing_change = None
        self.persisted_results: list[AssetUnit] = []
        self.load_requests: list[dict[str, object]] = []

    async def load_split_context(self, *args, **kwargs) -> AssetUnitSplitContext:
        self.load_requests.append(kwargs)
        return self.context

    async def get_boundary_change_by_idempotency(self, *args, **kwargs):
        return self.existing_change

    async def get_asset_unit_version(self, *args, **kwargs) -> int | None:
        if self.current_version_override is not None:
            return self.current_version_override
        return self.context.source.version if self.context.source is not None else None

    async def persist_split(
        self,
        *args,
        source: AssetUnit,
        results: list[AssetUnit],
        boundary_change,
        **kwargs,
    ):
        self.write_count += 1
        self.persisted_results = results
        if self.persist_error is not None:
            constraint_name = getattr(
                getattr(getattr(self.persist_error, "orig", None), "diag", None),
                "constraint_name",
                None,
            )
            if isinstance(self.persist_error, IntegrityError) and (
                constraint_name
                not in {
                    "uq_asset_units_unit_code",
                    "uq_asset_unit_boundary_sources_unit",
                }
            ):
                self.existing_change = boundary_change
            raise self.persist_error
        self.existing_change = boundary_change
        self.context = AssetUnitSplitContext(
            source=source,
            existing_boundary_change_id=boundary_change.id,
            upstream_coverages=self.context.upstream_coverages,
            upstream_contracts=self.context.upstream_contracts,
            terminal_coverages=self.context.terminal_coverages,
            terminal_contracts=self.context.terminal_contracts,
            lifecycle_events=self.context.lifecycle_events,
        )
        return boundary_change


class _PreviewStore:
    def __init__(self, now: datetime) -> None:
        self.now = now
        self.payload: dict[str, object] | None = None
        self.deleted = False

    def issue(self, payload: dict[str, object]) -> tuple[str, datetime]:
        self.payload = payload
        return "opaque-split-token", self.now + timedelta(minutes=10)

    def peek(self, raw_token: str) -> dict[str, object] | None:
        if raw_token != "opaque-split-token" or self.deleted:
            return None
        return self.payload

    def delete(self, raw_token: str) -> bool:
        if raw_token != "opaque-split-token" or self.deleted:
            return False
        self.deleted = True
        return True


class _Db:
    def __init__(self, *, commit_error: Exception | None = None) -> None:
        self.commit_count = 0
        self.rollback_count = 0
        self.commit_error = commit_error

    async def commit(self) -> None:
        self.commit_count += 1
        if self.commit_error is not None:
            raise self.commit_error

    async def rollback(self) -> None:
        self.rollback_count += 1


class _ConstraintViolationError(RuntimeError):
    def __init__(self, constraint_name: str) -> None:
        super().__init__(constraint_name)
        self.diag = type("_Diag", (), {"constraint_name": constraint_name})()


def test_boundary_preview_store_peeks_until_successful_delete() -> None:
    now = datetime(2026, 10, 23, 9, 0, tzinfo=UTC).replace(tzinfo=None)
    store = AssetUnitBoundaryPreviewStore(clock=lambda: now)

    token, expires_at = store.issue({"actor_id": "actor-1", "action": "split"})

    assert expires_at == now + timedelta(minutes=10)
    assert store.peek(token) == {
        "actor_id": "actor-1",
        "action": "split",
        "expires_at": "2026-10-23T09:10:00",
    }
    assert store.peek(token) is not None
    assert store.delete(token) is True
    assert store.peek(token) is None


@pytest.mark.asyncio
async def test_split_preview_returns_impact_token_and_versions_without_writing() -> (
    None
):
    now = datetime(2026, 10, 23, 9, 0, tzinfo=UTC).replace(tzinfo=None)
    source = _source_unit()
    repository = _BoundaryRepository(_split_context(source))
    preview_store = _PreviewStore(now)
    service = AssetUnitBoundaryCommandService(
        repository=repository,
        preview_store=preview_store,
        clock=lambda: now,
    )
    proposal = AssetUnitSplitProposal(
        change_type="split",
        source_unit_id="unit-1",
        effective_date=date(2026, 11, 1),
        parts=[
            AssetUnitSplitPartInput(
                unit_code="U-001-A",
                name="一号商铺 A",
                land_area=Decimal("8.00"),
                building_area=Decimal("40.00"),
                rentable_area=Decimal("30.00"),
            ),
            AssetUnitSplitPartInput(
                unit_code="U-001-B",
                name="一号商铺 B",
                land_area=Decimal("12.00"),
                building_area=Decimal("60.00"),
                rentable_area=Decimal("50.00"),
            ),
        ],
    )
    scope = EffectivePartyScope(
        user_id="actor-1",
        source="explicit",
        scope_mode="owner",
        owner_party_ids=["owner-1"],
    )

    result = await service.preview(
        object(),
        proposal=proposal,
        actor_id="actor-1",
        scope=scope,
    )

    assert result.change_type == "split"
    assert result.source_unit_ids == ["unit-1"]
    assert [part.unit_code for part in result.results] == ["U-001-A", "U-001-B"]
    assert result.impact.source_units_stop_on == date(2026, 10, 31)
    assert result.impact.result_units_start_on == date(2026, 11, 1)
    assert result.impact.unit_count_delta == 1
    assert result.versions == {"unit-1": 3}
    assert result.preview_token == "opaque-split-token"
    assert result.expires_at == now.replace(tzinfo=UTC) + timedelta(minutes=10)
    assert result.expires_at.utcoffset() == timedelta(0)
    assert source.managed_to is None
    assert repository.write_count == 0
    assert preview_store.payload is not None
    assert preview_store.payload["actor_id"] == "actor-1"
    assert isinstance(preview_store.payload["state_fingerprint"], str)
    assert len(preview_store.payload["state_fingerprint"]) == 64


@pytest.mark.asyncio
async def test_split_preview_allows_source_without_active_upstream_contract() -> None:
    now = datetime(2026, 10, 23, 9, 0, tzinfo=UTC).replace(tzinfo=None)
    source = _source_unit()
    repository = _BoundaryRepository(AssetUnitSplitContext(source=source))
    preview_store = _PreviewStore(now)
    service = AssetUnitBoundaryCommandService(
        repository=repository,
        preview_store=preview_store,
        clock=lambda: now,
    )

    result = await service.preview(
        object(),
        proposal=AssetUnitSplitProposal(
            source_unit_id=source.id,
            effective_date=date(2026, 11, 1),
            parts=[
                AssetUnitSplitPartInput(
                    unit_code="U-001-A",
                    name="一号商铺 A",
                    land_area=Decimal("8.00"),
                    building_area=Decimal("40.00"),
                    rentable_area=Decimal("30.00"),
                ),
                AssetUnitSplitPartInput(
                    unit_code="U-001-B",
                    name="一号商铺 B",
                    land_area=Decimal("12.00"),
                    building_area=Decimal("60.00"),
                    rentable_area=Decimal("50.00"),
                ),
            ],
        ),
        actor_id="actor-1",
        scope=EffectivePartyScope(
            user_id="actor-1",
            source="explicit",
            scope_mode="owner",
            owner_party_ids=["owner-1"],
        ),
    )

    assert result.source_unit_ids == [source.id]
    assert preview_store.payload is not None


@pytest.mark.asyncio
async def test_split_preview_rejects_scope_resolved_for_another_actor() -> None:
    now = datetime(2026, 10, 23, 9, 0, tzinfo=UTC).replace(tzinfo=None)
    service = AssetUnitBoundaryCommandService(
        repository=_BoundaryRepository(_split_context(_source_unit())),
        preview_store=_PreviewStore(now),
        clock=lambda: now,
    )

    with pytest.raises(PartyScopeForbiddenError) as error:
        await service.preview(
            object(),
            proposal=AssetUnitSplitProposal(
                source_unit_id="unit-1",
                effective_date=date(2026, 11, 1),
                parts=[
                    AssetUnitSplitPartInput(
                        unit_code="U-001-A",
                        name="一号商铺 A",
                        land_area=Decimal("8.00"),
                        building_area=Decimal("40.00"),
                        rentable_area=Decimal("30.00"),
                    ),
                    AssetUnitSplitPartInput(
                        unit_code="U-001-B",
                        name="一号商铺 B",
                        land_area=Decimal("12.00"),
                        building_area=Decimal("60.00"),
                        rentable_area=Decimal("50.00"),
                    ),
                ],
            ),
            actor_id="actor-1",
            scope=EffectivePartyScope(
                user_id="actor-2",
                source="explicit",
                scope_mode="owner",
                owner_party_ids=["owner-1"],
            ),
        )

    assert error.value.status_code == 403
    assert error.value.code == "PARTY_SCOPE_INVALID_BINDING"
    assert error.value.details == {"reason": "scope_actor_mismatch"}


@pytest.mark.asyncio
async def test_split_preview_blocks_terminal_contracts_crossing_effective_date() -> (
    None
):
    now = datetime(2026, 10, 23, 9, 0, tzinfo=UTC).replace(tzinfo=None)
    repository = _BoundaryRepository(
        _split_context(
            _source_unit(),
            terminal_conflict_ids=("terminal-1", "terminal-2"),
        )
    )
    preview_store = _PreviewStore(now)
    service = AssetUnitBoundaryCommandService(
        repository=repository,
        preview_store=preview_store,
        clock=lambda: now,
    )
    proposal = AssetUnitSplitProposal(
        source_unit_id="unit-1",
        effective_date=date(2026, 11, 1),
        parts=[
            AssetUnitSplitPartInput(
                unit_code="U-001-A",
                name="一号商铺 A",
                land_area=Decimal("8.00"),
                building_area=Decimal("40.00"),
                rentable_area=Decimal("30.00"),
            ),
            AssetUnitSplitPartInput(
                unit_code="U-001-B",
                name="一号商铺 B",
                land_area=Decimal("12.00"),
                building_area=Decimal("60.00"),
                rentable_area=Decimal("50.00"),
            ),
        ],
    )

    with pytest.raises(AssetUnitPeriodOverlapError) as error:
        await service.preview(
            object(),
            proposal=proposal,
            actor_id="actor-1",
            scope=EffectivePartyScope(
                user_id="actor-1",
                source="explicit",
                scope_mode="owner",
                owner_party_ids=["owner-1"],
            ),
        )

    assert error.value.status_code == 409
    assert error.value.code == "ASSET_UNIT_PERIOD_OVERLAP"
    assert error.value.details == {
        "asset_unit_ids": ["unit-1"],
        "terminal_contract_ids": ["terminal-1", "terminal-2"],
    }
    assert preview_store.payload is None


@pytest.mark.asyncio
async def test_split_commit_is_atomic_and_replays_first_result_idempotently() -> None:
    now = datetime(2026, 10, 23, 9, 0, tzinfo=UTC).replace(tzinfo=None)
    source = _source_unit()
    repository = _BoundaryRepository(_split_context(source))
    preview_store = _PreviewStore(now)
    service = AssetUnitBoundaryCommandService(
        repository=repository,
        preview_store=preview_store,
        clock=lambda: now,
    )
    proposal = AssetUnitSplitProposal(
        source_unit_id="unit-1",
        effective_date=date(2026, 11, 1),
        parts=[
            AssetUnitSplitPartInput(
                unit_code="U-001-A",
                name="一号商铺 A",
                land_area=Decimal("8.00"),
                building_area=Decimal("40.00"),
                rentable_area=Decimal("30.00"),
            ),
            AssetUnitSplitPartInput(
                unit_code="U-001-B",
                name="一号商铺 B",
                land_area=Decimal("12.00"),
                building_area=Decimal("60.00"),
                rentable_area=Decimal("50.00"),
            ),
        ],
    )
    scope = EffectivePartyScope(
        user_id="actor-1",
        source="explicit",
        scope_mode="owner",
        owner_party_ids=["owner-1"],
    )
    preview = await service.preview(
        object(),
        proposal=proposal,
        actor_id="actor-1",
        scope=scope,
    )
    request = AssetUnitSplitCommitRequest(
        preview_token=preview.preview_token,
        reason="按楼层重新划分",
        expected_version=3,
    )
    db = _Db()

    with pytest.raises(AssetOperationsPreviewStaleError) as path_error:
        await service.commit(
            db,
            source_unit_id="another-unit",
            request=request,
            actor_id="actor-1",
            scope=scope,
            idempotency_key="split-request-1",
        )
    assert path_error.value.details == {"reason": "target_mismatch"}
    assert repository.write_count == 0
    assert preview_store.deleted is False

    result = await service.commit(
        db,
        source_unit_id="unit-1",
        request=request,
        actor_id="actor-1",
        scope=scope,
        idempotency_key="split-request-1",
    )

    assert result.change_type == "split"
    assert result.source_unit_ids == ["unit-1"]
    assert len(result.result_unit_ids) == 2
    assert result.effective_date == date(2026, 11, 1)
    assert result.committed_at.utcoffset() == timedelta(0)
    assert result.idempotent is False
    assert source.managed_to == date(2026, 10, 31)
    assert source.version == 4
    assert [unit.managed_from for unit in repository.persisted_results] == [
        date(2026, 11, 1),
        date(2026, 11, 1),
    ]
    assert all(
        unit.predecessor_unit_ids == ["unit-1"] for unit in repository.persisted_results
    )
    assert repository.existing_change.request_fingerprint != ""
    assert repository.existing_change.created_at.tzinfo is None
    assert repository.existing_change.result_data["result_unit_ids"] == (
        result.result_unit_ids
    )
    assert repository.write_count == 1
    assert db.commit_count == 1
    assert preview_store.deleted is True

    repeated = await service.commit(
        db,
        source_unit_id="unit-1",
        request=request,
        actor_id="actor-1",
        scope=scope,
        idempotency_key="split-request-1",
    )

    assert repeated.model_copy(update={"idempotent": False}) == result
    assert repeated.idempotent is True
    assert repository.write_count == 1
    assert db.commit_count == 1


@pytest.mark.asyncio
async def test_split_preview_rejects_existing_result_unit_code() -> None:
    now = datetime(2026, 10, 23, 9, 0, tzinfo=UTC).replace(tzinfo=None)
    context = _split_context(_source_unit())
    context = AssetUnitSplitContext(
        source=context.source,
        upstream_coverages=context.upstream_coverages,
        upstream_contracts=context.upstream_contracts,
        existing_result_unit_codes=("U-001-B",),
    )
    repository = _BoundaryRepository(context)
    service = AssetUnitBoundaryCommandService(
        repository=repository,
        preview_store=_PreviewStore(now),
        clock=lambda: now,
    )

    with pytest.raises(AssetUnitBoundaryInvalidError) as error:
        await service.preview(
            object(),
            proposal=AssetUnitSplitProposal(
                source_unit_id="unit-1",
                effective_date=date(2026, 11, 1),
                parts=[
                    AssetUnitSplitPartInput(
                        unit_code="U-001-A",
                        name="一号商铺 A",
                        land_area=Decimal("8.00"),
                        building_area=Decimal("40.00"),
                        rentable_area=Decimal("30.00"),
                    ),
                    AssetUnitSplitPartInput(
                        unit_code="U-001-B",
                        name="一号商铺 B",
                        land_area=Decimal("12.00"),
                        building_area=Decimal("60.00"),
                        rentable_area=Decimal("50.00"),
                    ),
                ],
            ),
            actor_id="actor-1",
            scope=EffectivePartyScope(
                user_id="actor-1",
                source="explicit",
                scope_mode="owner",
                owner_party_ids=["owner-1"],
            ),
        )

    assert error.value.code == "ASSET_UNIT_BOUNDARY_INVALID"
    assert error.value.details == {
        "reason": "result_unit_code_conflict",
        "unit_ids": ["unit-1"],
    }
    assert repository.load_requests[0]["result_unit_codes"] == (
        "U-001-A",
        "U-001-B",
    )


@pytest.mark.asyncio
async def test_split_preview_rejects_source_not_effective_on_boundary() -> None:
    now = datetime(2026, 10, 23, 9, 0, tzinfo=UTC).replace(tzinfo=None)
    source = _source_unit()
    source.managed_to = date(2026, 10, 15)
    repository = _BoundaryRepository(_split_context(source))
    service = AssetUnitBoundaryCommandService(
        repository=repository,
        preview_store=_PreviewStore(now),
        clock=lambda: now,
    )

    with pytest.raises(AssetUnitBoundaryInvalidError) as error:
        await service.preview(
            object(),
            proposal=AssetUnitSplitProposal(
                source_unit_id="unit-1",
                effective_date=date(2026, 11, 1),
                parts=[
                    AssetUnitSplitPartInput(
                        unit_code="U-001-A",
                        name="一号商铺 A",
                        land_area=Decimal("8.00"),
                        building_area=Decimal("40.00"),
                        rentable_area=Decimal("30.00"),
                    ),
                    AssetUnitSplitPartInput(
                        unit_code="U-001-B",
                        name="一号商铺 B",
                        land_area=Decimal("12.00"),
                        building_area=Decimal("60.00"),
                        rentable_area=Decimal("50.00"),
                    ),
                ],
            ),
            actor_id="actor-1",
            scope=EffectivePartyScope(
                user_id="actor-1",
                source="explicit",
                scope_mode="owner",
                owner_party_ids=["owner-1"],
            ),
        )

    assert error.value.details == {
        "reason": "source_not_effective_on_boundary",
        "unit_ids": ["unit-1"],
    }


@pytest.mark.asyncio
async def test_split_preview_rejects_source_already_consumed_by_boundary_change() -> (
    None
):
    now = datetime(2026, 10, 23, 9, 0, tzinfo=UTC).replace(tzinfo=None)
    base = _split_context(_source_unit())
    repository = _BoundaryRepository(
        AssetUnitSplitContext(
            source=base.source,
            existing_boundary_change_id="change-existing",
            upstream_coverages=base.upstream_coverages,
            upstream_contracts=base.upstream_contracts,
        )
    )
    service = AssetUnitBoundaryCommandService(
        repository=repository,
        preview_store=_PreviewStore(now),
        clock=lambda: now,
    )

    with pytest.raises(AssetUnitBoundaryInvalidError) as error:
        await service.preview(
            object(),
            proposal=AssetUnitSplitProposal(
                source_unit_id="unit-1",
                effective_date=date(2026, 11, 1),
                parts=[
                    AssetUnitSplitPartInput(
                        unit_code="U-001-A",
                        name="一号商铺 A",
                        land_area=Decimal("8.00"),
                        building_area=Decimal("40.00"),
                        rentable_area=Decimal("30.00"),
                    ),
                    AssetUnitSplitPartInput(
                        unit_code="U-001-B",
                        name="一号商铺 B",
                        land_area=Decimal("12.00"),
                        building_area=Decimal("60.00"),
                        rentable_area=Decimal("50.00"),
                    ),
                ],
            ),
            actor_id="actor-1",
            scope=EffectivePartyScope(
                user_id="actor-1",
                source="explicit",
                scope_mode="owner",
                owner_party_ids=["owner-1"],
            ),
        )

    assert error.value.details == {
        "reason": "source_boundary_already_changed",
        "unit_ids": ["unit-1"],
    }


@pytest.mark.asyncio
async def test_split_commit_consumes_source_even_if_end_date_was_already_boundary_day() -> (
    None
):
    now = datetime(2026, 10, 23, 9, 0, tzinfo=UTC).replace(tzinfo=None)
    source = _source_unit()
    source.managed_to = date(2026, 10, 31)
    repository = _BoundaryRepository(AssetUnitSplitContext(source=source))
    first_store = _PreviewStore(now)
    first_service = AssetUnitBoundaryCommandService(
        repository=repository,
        preview_store=first_store,
        clock=lambda: now,
    )
    scope = EffectivePartyScope(
        user_id="actor-1",
        source="explicit",
        scope_mode="owner",
        owner_party_ids=["owner-1"],
    )
    proposal = AssetUnitSplitProposal(
        source_unit_id=source.id,
        effective_date=date(2026, 11, 1),
        parts=[
            AssetUnitSplitPartInput(
                unit_code="U-001-A",
                name="一号商铺 A",
                land_area=Decimal("8.00"),
                building_area=Decimal("40.00"),
                rentable_area=Decimal("30.00"),
            ),
            AssetUnitSplitPartInput(
                unit_code="U-001-B",
                name="一号商铺 B",
                land_area=Decimal("12.00"),
                building_area=Decimal("60.00"),
                rentable_area=Decimal("50.00"),
            ),
        ],
    )
    preview = await first_service.preview(
        object(),
        proposal=proposal,
        actor_id="actor-1",
        scope=scope,
    )

    await first_service.commit(
        _Db(),
        source_unit_id="unit-1",
        request=AssetUnitSplitCommitRequest(
            preview_token=preview.preview_token,
            reason="按楼层重新划分",
            expected_version=3,
        ),
        actor_id="actor-1",
        scope=scope,
        idempotency_key="first-boundary",
    )

    assert source.version == 4
    assert repository.context.existing_boundary_change_id is not None

    second_service = AssetUnitBoundaryCommandService(
        repository=repository,
        preview_store=_PreviewStore(now),
        clock=lambda: now,
    )
    with pytest.raises(AssetUnitBoundaryInvalidError) as error:
        await second_service.preview(
            object(),
            proposal=proposal.model_copy(
                update={
                    "parts": [
                        proposal.parts[0].model_copy(update={"unit_code": "U-001-C"}),
                        proposal.parts[1].model_copy(update={"unit_code": "U-001-D"}),
                    ]
                }
            ),
            actor_id="actor-1",
            scope=scope,
        )

    assert error.value.details["reason"] == "source_boundary_already_changed"


@pytest.mark.asyncio
async def test_split_commit_rejects_stale_expected_version_without_consuming_preview() -> (
    None
):
    now = datetime(2026, 10, 23, 9, 0, tzinfo=UTC).replace(tzinfo=None)
    repository = _BoundaryRepository(_split_context(_source_unit()))
    preview_store = _PreviewStore(now)
    service = AssetUnitBoundaryCommandService(
        repository=repository,
        preview_store=preview_store,
        clock=lambda: now,
    )
    scope = EffectivePartyScope(
        user_id="actor-1",
        source="explicit",
        scope_mode="owner",
        owner_party_ids=["owner-1"],
    )
    preview = await service.preview(
        object(),
        proposal=AssetUnitSplitProposal(
            source_unit_id="unit-1",
            effective_date=date(2026, 11, 1),
            parts=[
                AssetUnitSplitPartInput(
                    unit_code="U-001-A",
                    name="一号商铺 A",
                    land_area=Decimal("8.00"),
                    building_area=Decimal("40.00"),
                    rentable_area=Decimal("30.00"),
                ),
                AssetUnitSplitPartInput(
                    unit_code="U-001-B",
                    name="一号商铺 B",
                    land_area=Decimal("12.00"),
                    building_area=Decimal("60.00"),
                    rentable_area=Decimal("50.00"),
                ),
            ],
        ),
        actor_id="actor-1",
        scope=scope,
    )

    with pytest.raises(AssetOperationsVersionConflictError) as error:
        await service.commit(
            _Db(),
            source_unit_id="unit-1",
            request=AssetUnitSplitCommitRequest(
                preview_token=preview.preview_token,
                reason="按楼层重新划分",
                expected_version=2,
            ),
            actor_id="actor-1",
            scope=scope,
            idempotency_key="split-stale-version",
        )

    assert error.value.code == "VERSION_CONFLICT"
    assert repository.write_count == 0
    assert preview_store.deleted is False


@pytest.mark.asyncio
async def test_split_commit_rejects_changed_request_for_same_idempotency_key() -> None:
    now = datetime(2026, 10, 23, 9, 0, tzinfo=UTC).replace(tzinfo=None)
    repository = _BoundaryRepository(_split_context(_source_unit()))
    preview_store = _PreviewStore(now)
    service = AssetUnitBoundaryCommandService(
        repository=repository,
        preview_store=preview_store,
        clock=lambda: now,
    )
    scope = EffectivePartyScope(
        user_id="actor-1",
        source="explicit",
        scope_mode="owner",
        owner_party_ids=["owner-1"],
    )
    preview = await service.preview(
        object(),
        proposal=AssetUnitSplitProposal(
            source_unit_id="unit-1",
            effective_date=date(2026, 11, 1),
            parts=[
                AssetUnitSplitPartInput(
                    unit_code="U-001-A",
                    name="一号商铺 A",
                    land_area=Decimal("8.00"),
                    building_area=Decimal("40.00"),
                    rentable_area=Decimal("30.00"),
                ),
                AssetUnitSplitPartInput(
                    unit_code="U-001-B",
                    name="一号商铺 B",
                    land_area=Decimal("12.00"),
                    building_area=Decimal("60.00"),
                    rentable_area=Decimal("50.00"),
                ),
            ],
        ),
        actor_id="actor-1",
        scope=scope,
    )
    db = _Db()
    original = AssetUnitSplitCommitRequest(
        preview_token=preview.preview_token,
        reason="首次原因",
        expected_version=3,
    )
    await service.commit(
        db,
        source_unit_id="unit-1",
        request=original,
        actor_id="actor-1",
        scope=scope,
        idempotency_key="same-key",
    )

    with pytest.raises(AssetOperationsIdempotencyConflictError) as error:
        await service.commit(
            db,
            source_unit_id="unit-1",
            request=original.model_copy(update={"reason": "改变后的原因"}),
            actor_id="actor-1",
            scope=scope,
            idempotency_key="same-key",
        )

    assert error.value.code == "IDEMPOTENCY_CONFLICT"
    assert repository.write_count == 1
    assert db.commit_count == 1


@pytest.mark.asyncio
async def test_split_commit_rejects_changed_upstream_coverage_period() -> None:
    now = datetime(2026, 10, 23, 9, 0, tzinfo=UTC).replace(tzinfo=None)
    repository = _BoundaryRepository(_split_context(_source_unit()))
    preview_store = _PreviewStore(now)
    service = AssetUnitBoundaryCommandService(
        repository=repository,
        preview_store=preview_store,
        clock=lambda: now,
    )
    scope = EffectivePartyScope(
        user_id="actor-1",
        source="explicit",
        scope_mode="owner",
        owner_party_ids=["owner-1"],
    )
    preview = await service.preview(
        object(),
        proposal=AssetUnitSplitProposal(
            source_unit_id="unit-1",
            effective_date=date(2026, 11, 1),
            parts=[
                AssetUnitSplitPartInput(
                    unit_code="U-001-A",
                    name="一号商铺 A",
                    land_area=Decimal("8.00"),
                    building_area=Decimal("40.00"),
                    rentable_area=Decimal("30.00"),
                ),
                AssetUnitSplitPartInput(
                    unit_code="U-001-B",
                    name="一号商铺 B",
                    land_area=Decimal("12.00"),
                    building_area=Decimal("60.00"),
                    rentable_area=Decimal("50.00"),
                ),
            ],
        ),
        actor_id="actor-1",
        scope=scope,
    )
    repository.context.upstream_coverages[0].effective_to = date(2027, 12, 31)

    with pytest.raises(AssetOperationsPreviewStaleError) as error:
        await service.commit(
            _Db(),
            source_unit_id="unit-1",
            request=AssetUnitSplitCommitRequest(
                preview_token=preview.preview_token,
                reason="按楼层重新划分",
                expected_version=3,
            ),
            actor_id="actor-1",
            scope=scope,
            idempotency_key="changed-coverage",
        )

    assert error.value.details == {"reason": "state_changed"}
    assert repository.write_count == 0
    assert preview_store.deleted is False


@pytest.mark.asyncio
async def test_split_commit_retains_preview_when_database_commit_conflicts() -> None:
    now = datetime(2026, 10, 23, 9, 0, tzinfo=UTC).replace(tzinfo=None)
    repository = _BoundaryRepository(
        _split_context(_source_unit()),
        persist_error=StaleDataError("concurrent update"),
        current_version_override=4,
    )
    preview_store = _PreviewStore(now)
    service = AssetUnitBoundaryCommandService(
        repository=repository,
        preview_store=preview_store,
        clock=lambda: now,
    )
    scope = EffectivePartyScope(
        user_id="actor-1",
        source="explicit",
        scope_mode="owner",
        owner_party_ids=["owner-1"],
    )
    preview = await service.preview(
        object(),
        proposal=AssetUnitSplitProposal(
            source_unit_id="unit-1",
            effective_date=date(2026, 11, 1),
            parts=[
                AssetUnitSplitPartInput(
                    unit_code="U-001-A",
                    name="一号商铺 A",
                    land_area=Decimal("8.00"),
                    building_area=Decimal("40.00"),
                    rentable_area=Decimal("30.00"),
                ),
                AssetUnitSplitPartInput(
                    unit_code="U-001-B",
                    name="一号商铺 B",
                    land_area=Decimal("12.00"),
                    building_area=Decimal("60.00"),
                    rentable_area=Decimal("50.00"),
                ),
            ],
        ),
        actor_id="actor-1",
        scope=scope,
    )
    db = _Db()

    with pytest.raises(AssetOperationsVersionConflictError) as error:
        await service.commit(
            db,
            source_unit_id="unit-1",
            request=AssetUnitSplitCommitRequest(
                preview_token=preview.preview_token,
                reason="按楼层重新划分",
                expected_version=3,
            ),
            actor_id="actor-1",
            scope=scope,
            idempotency_key="commit-conflict",
        )

    assert db.rollback_count == 1
    assert error.value.details["actual_version"] == 4
    assert preview_store.deleted is False


@pytest.mark.asyncio
async def test_split_commit_replays_concurrent_idempotent_insert() -> None:
    now = datetime(2026, 10, 23, 9, 0, tzinfo=UTC).replace(tzinfo=None)
    repository = _BoundaryRepository(
        _split_context(_source_unit()),
        persist_error=IntegrityError(
            "insert asset_unit_boundary_changes",
            {},
            RuntimeError("duplicate actor/idempotency key"),
        ),
    )
    preview_store = _PreviewStore(now)
    service = AssetUnitBoundaryCommandService(
        repository=repository,
        preview_store=preview_store,
        clock=lambda: now,
    )
    scope = EffectivePartyScope(
        user_id="actor-1",
        source="explicit",
        scope_mode="owner",
        owner_party_ids=["owner-1"],
    )
    preview = await service.preview(
        object(),
        proposal=AssetUnitSplitProposal(
            source_unit_id="unit-1",
            effective_date=date(2026, 11, 1),
            parts=[
                AssetUnitSplitPartInput(
                    unit_code="U-001-A",
                    name="一号商铺 A",
                    land_area=Decimal("8.00"),
                    building_area=Decimal("40.00"),
                    rentable_area=Decimal("30.00"),
                ),
                AssetUnitSplitPartInput(
                    unit_code="U-001-B",
                    name="一号商铺 B",
                    land_area=Decimal("12.00"),
                    building_area=Decimal("60.00"),
                    rentable_area=Decimal("50.00"),
                ),
            ],
        ),
        actor_id="actor-1",
        scope=scope,
    )
    request = AssetUnitSplitCommitRequest(
        preview_token=preview.preview_token,
        reason="按楼层重新划分",
        expected_version=3,
    )
    db = _Db()

    result = await service.commit(
        db,
        source_unit_id="unit-1",
        request=request,
        actor_id="actor-1",
        scope=scope,
        idempotency_key="concurrent-key",
    )

    assert result.idempotent is True
    assert db.rollback_count == 1
    assert preview_store.deleted is True


@pytest.mark.asyncio
async def test_split_commit_maps_concurrent_result_code_collision_to_stable_409() -> (
    None
):
    now = datetime(2026, 10, 23, 9, 0, tzinfo=UTC).replace(tzinfo=None)
    repository = _BoundaryRepository(
        _split_context(_source_unit()),
        persist_error=IntegrityError(
            "insert asset_units",
            {},
            _ConstraintViolationError("uq_asset_units_unit_code"),
        ),
    )
    preview_store = _PreviewStore(now)
    service = AssetUnitBoundaryCommandService(
        repository=repository,
        preview_store=preview_store,
        clock=lambda: now,
    )
    scope = EffectivePartyScope(
        user_id="actor-1",
        source="explicit",
        scope_mode="owner",
        owner_party_ids=["owner-1"],
    )
    preview = await service.preview(
        object(),
        proposal=AssetUnitSplitProposal(
            source_unit_id="unit-1",
            effective_date=date(2026, 11, 1),
            parts=[
                AssetUnitSplitPartInput(
                    unit_code="U-001-A",
                    name="一号商铺 A",
                    land_area=Decimal("8.00"),
                    building_area=Decimal("40.00"),
                    rentable_area=Decimal("30.00"),
                ),
                AssetUnitSplitPartInput(
                    unit_code="U-001-B",
                    name="一号商铺 B",
                    land_area=Decimal("12.00"),
                    building_area=Decimal("60.00"),
                    rentable_area=Decimal("50.00"),
                ),
            ],
        ),
        actor_id="actor-1",
        scope=scope,
    )
    db = _Db()

    with pytest.raises(AssetUnitBoundaryInvalidError) as error:
        await service.commit(
            db,
            source_unit_id="unit-1",
            request=AssetUnitSplitCommitRequest(
                preview_token=preview.preview_token,
                reason="按楼层重新划分",
                expected_version=3,
            ),
            actor_id="actor-1",
            scope=scope,
            idempotency_key="code-collision",
        )

    assert error.value.code == "ASSET_UNIT_BOUNDARY_INVALID"
    assert error.value.details == {
        "reason": "result_unit_code_conflict",
        "unit_ids": ["unit-1"],
    }
    assert db.rollback_count == 1
    assert preview_store.deleted is False


@pytest.mark.asyncio
async def test_split_commit_maps_concurrent_source_consumption_to_stable_409() -> None:
    now = datetime(2026, 10, 23, 9, 0, tzinfo=UTC).replace(tzinfo=None)
    repository = _BoundaryRepository(
        _split_context(_source_unit()),
        persist_error=IntegrityError(
            "insert asset_unit_boundary_sources",
            {},
            _ConstraintViolationError("uq_asset_unit_boundary_sources_unit"),
        ),
    )
    preview_store = _PreviewStore(now)
    service = AssetUnitBoundaryCommandService(
        repository=repository,
        preview_store=preview_store,
        clock=lambda: now,
    )
    scope = EffectivePartyScope(
        user_id="actor-1",
        source="explicit",
        scope_mode="owner",
        owner_party_ids=["owner-1"],
    )
    preview = await service.preview(
        object(),
        proposal=AssetUnitSplitProposal(
            source_unit_id="unit-1",
            effective_date=date(2026, 11, 1),
            parts=[
                AssetUnitSplitPartInput(
                    unit_code="U-001-A",
                    name="一号商铺 A",
                    land_area=Decimal("8.00"),
                    building_area=Decimal("40.00"),
                    rentable_area=Decimal("30.00"),
                ),
                AssetUnitSplitPartInput(
                    unit_code="U-001-B",
                    name="一号商铺 B",
                    land_area=Decimal("12.00"),
                    building_area=Decimal("60.00"),
                    rentable_area=Decimal("50.00"),
                ),
            ],
        ),
        actor_id="actor-1",
        scope=scope,
    )
    db = _Db()

    with pytest.raises(AssetUnitBoundaryInvalidError) as error:
        await service.commit(
            db,
            source_unit_id="unit-1",
            request=AssetUnitSplitCommitRequest(
                preview_token=preview.preview_token,
                reason="按楼层重新划分",
                expected_version=3,
            ),
            actor_id="actor-1",
            scope=scope,
            idempotency_key="source-collision",
        )

    assert error.value.details == {
        "reason": "source_boundary_already_changed",
        "unit_ids": ["unit-1"],
    }
    assert db.rollback_count == 1
    assert preview_store.deleted is False


@pytest.mark.asyncio
async def test_split_commit_rejects_preview_from_another_actor() -> None:
    now = datetime(2026, 10, 23, 9, 0, tzinfo=UTC).replace(tzinfo=None)
    repository = _BoundaryRepository(_split_context(_source_unit()))
    preview_store = _PreviewStore(now)
    service = AssetUnitBoundaryCommandService(
        repository=repository,
        preview_store=preview_store,
        clock=lambda: now,
    )
    owner_scope = EffectivePartyScope(
        user_id="actor-1",
        source="explicit",
        scope_mode="owner",
        owner_party_ids=["owner-1"],
    )
    preview = await service.preview(
        object(),
        proposal=AssetUnitSplitProposal(
            source_unit_id="unit-1",
            effective_date=date(2026, 11, 1),
            parts=[
                AssetUnitSplitPartInput(
                    unit_code="U-001-A",
                    name="一号商铺 A",
                    land_area=Decimal("8.00"),
                    building_area=Decimal("40.00"),
                    rentable_area=Decimal("30.00"),
                ),
                AssetUnitSplitPartInput(
                    unit_code="U-001-B",
                    name="一号商铺 B",
                    land_area=Decimal("12.00"),
                    building_area=Decimal("60.00"),
                    rentable_area=Decimal("50.00"),
                ),
            ],
        ),
        actor_id="actor-1",
        scope=owner_scope,
    )

    with pytest.raises(AssetOperationsPreviewStaleError) as error:
        await service.commit(
            _Db(),
            source_unit_id="unit-1",
            request=AssetUnitSplitCommitRequest(
                preview_token=preview.preview_token,
                reason="按楼层重新划分",
                expected_version=3,
            ),
            actor_id="actor-2",
            scope=EffectivePartyScope(
                user_id="actor-2",
                source="explicit",
                scope_mode="owner",
                owner_party_ids=["owner-1"],
            ),
            idempotency_key="other-actor",
        )

    assert error.value.code == "PREVIEW_STALE"
    assert error.value.details == {"reason": "actor_mismatch"}
    assert preview_store.deleted is False
