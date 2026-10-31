"""Persistence behavior for v5 asset-unit boundary commands."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.crud.asset_unit_boundary import AssetUnitBoundaryRepository
from src.models.asset_contract import (
    TerminalContract,
    TerminalContractAssetUnit,
    UpstreamContract,
    UpstreamContractAssetUnit,
)
from src.models.asset_unit import (
    AssetUnit,
    AssetUnitBoundaryChange,
    AssetUnitBoundarySource,
)
from src.services.party_scope_resolver import EffectivePartyScope


def _scalar_result(items: list[object]) -> MagicMock:
    result = MagicMock()
    result.scalars.return_value.all.return_value = items
    return result


def _first_scalar_result(item: object | None) -> MagicMock:
    result = MagicMock()
    result.scalars.return_value.first.return_value = item
    return result


def _source() -> AssetUnit:
    return AssetUnit(
        id="unit-1",
        unit_code="U-001",
        name="一号商铺",
        project_id="project-1",
        owner_party_id="owner-1",
        land_area=Decimal("20.00"),
        building_area=Decimal("100.00"),
        rentable_area=Decimal("80.00"),
        managed_from=date(2026, 1, 1),
        version=3,
    )


@pytest.mark.asyncio
async def test_get_asset_unit_version_reads_fresh_value_after_rollback() -> None:
    result = MagicMock()
    result.scalar_one_or_none.return_value = 4
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)

    version = await AssetUnitBoundaryRepository().get_asset_unit_version(
        db,
        unit_id="unit-1",
    )

    assert version == 4
    statement = db.execute.await_args.args[0]
    sql = str(statement.compile(compile_kwargs={"literal_binds": True}))
    assert "asset_units.version" in sql
    assert "asset_units.id = 'unit-1'" in sql


@pytest.mark.asyncio
async def test_load_split_context_locks_and_returns_all_boundary_facts() -> None:
    source = _source()
    upstream_coverage = UpstreamContractAssetUnit(
        upstream_contract_id="upstream-1",
        asset_unit_id=source.id,
        effective_from=date(2026, 1, 1),
    )
    terminal_coverage = TerminalContractAssetUnit(
        terminal_contract_id="terminal-1",
        asset_unit_id=source.id,
        effective_from=date(2026, 1, 1),
    )
    upstream = UpstreamContract(id="upstream-1", contract_number="UP-001")
    terminal = TerminalContract(id="terminal-1", contract_number="TM-001")
    no_boundary_source = MagicMock()
    no_boundary_source.scalars.return_value.one_or_none.return_value = None
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            no_boundary_source,
            _scalar_result(["U-001-B"]),
            _scalar_result([upstream_coverage]),
            _scalar_result([terminal_coverage]),
            _scalar_result([upstream]),
            _scalar_result([terminal]),
            _scalar_result([]),
        ]
    )
    scope = EffectivePartyScope(
        user_id="actor-1",
        source="explicit",
        scope_mode="owner",
        owner_party_ids=["owner-1"],
    )

    with patch(
        "src.crud.asset_unit_boundary.asset_unit_repository.lock_for_write",
        new=AsyncMock(return_value=(source,)),
    ) as lock_units:
        context = await AssetUnitBoundaryRepository().load_split_context(
            db,
            unit_id=source.id,
            scope=scope,
            effective_date=date(2026, 11, 1),
            result_unit_codes=("U-001-A", "U-001-B"),
            for_update=True,
        )

    assert context.source is source
    assert context.existing_result_unit_codes == ("U-001-B",)
    assert context.upstream_coverages == (upstream_coverage,)
    assert context.upstream_contracts == (upstream,)
    assert context.terminal_coverages == (terminal_coverage,)
    assert context.terminal_contracts == (terminal,)
    assert lock_units.await_args.kwargs["unit_ids"] == (source.id,)
    sql_statements = [
        str(call.args[0].compile(compile_kwargs={"literal_binds": True}))
        for call in db.execute.await_args_list
    ]
    assert all("FOR UPDATE" in sql for sql in sql_statements)
    assert "asset_unit_boundary_sources.asset_unit_id = 'unit-1'" in sql_statements[0]
    assert "asset_units.unit_code IN ('U-001-A', 'U-001-B')" in sql_statements[1]


@pytest.mark.asyncio
async def test_persist_split_rebinds_upstream_coverage_to_every_result() -> None:
    source = _source()
    source.managed_to = date(2026, 10, 31)
    original_coverage = UpstreamContractAssetUnit(
        upstream_contract_id="upstream-1",
        asset_unit_id=source.id,
        effective_from=date(2026, 1, 1),
        effective_to=date(2027, 12, 31),
    )
    results = [
        AssetUnit(
            id="unit-a",
            unit_code="U-001-A",
            managed_from=date(2026, 11, 1),
        ),
        AssetUnit(
            id="unit-b",
            unit_code="U-001-B",
            managed_from=date(2026, 11, 1),
        ),
    ]
    boundary_change = AssetUnitBoundaryChange(
        id="change-1",
        change_type="split",
        effective_date=date(2026, 11, 1),
        source_unit_ids=[source.id],
        result_unit_ids=[unit.id for unit in results],
        area_check={},
        reason="按楼层重新划分",
        created_by="actor-1",
        created_at=datetime(2026, 10, 23, 9, 0),
        idempotency_key="request-1",
        request_fingerprint="f" * 64,
        result_data={},
    )
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalar_result([original_coverage]))
    db.flush = AsyncMock()

    await AssetUnitBoundaryRepository().persist_split(
        db,
        source=source,
        results=results,
        boundary_change=boundary_change,
        active_upstream_contract_ids=("upstream-1",),
        effective_date=date(2026, 11, 1),
    )

    assert original_coverage.effective_to == date(2026, 10, 31)
    added = db.add_all.call_args.args[0]
    new_coverages = [
        item for item in added if isinstance(item, UpstreamContractAssetUnit)
    ]
    boundary_sources = [
        item for item in added if isinstance(item, AssetUnitBoundarySource)
    ]
    assert {
        (item.upstream_contract_id, item.asset_unit_id) for item in new_coverages
    } == {
        ("upstream-1", "unit-a"),
        ("upstream-1", "unit-b"),
    }
    assert all(item.effective_from == date(2026, 11, 1) for item in new_coverages)
    assert all(item.effective_to == date(2027, 12, 31) for item in new_coverages)
    assert len(boundary_sources) == 1
    assert boundary_sources[0].asset_unit_id == source.id
    assert boundary_sources[0].boundary_change_id == boundary_change.id
    await_args = db.execute.await_args.args[0]
    sql = str(await_args.compile(compile_kwargs={"literal_binds": True}))
    assert "FOR UPDATE" in sql
    assert db.flush.await_count == 2


@pytest.mark.asyncio
async def test_persist_split_moves_same_day_upstream_coverage_without_empty_range() -> (
    None
):
    source = _source()
    results = [
        AssetUnit(id="unit-a", unit_code="U-001-A"),
        AssetUnit(id="unit-b", unit_code="U-001-B"),
    ]
    same_day_coverage = UpstreamContractAssetUnit(
        upstream_contract_id="upstream-1",
        asset_unit_id=source.id,
        effective_from=date(2026, 11, 1),
        effective_to=date(2027, 12, 31),
    )
    boundary_change = AssetUnitBoundaryChange(
        id="change-same-day",
        change_type="split",
        effective_date=date(2026, 11, 1),
        source_unit_ids=[source.id],
        result_unit_ids=[unit.id for unit in results],
        area_check={},
        reason="同日迁移上游覆盖",
        created_by="actor-1",
        created_at=datetime(2026, 10, 24, 9, 0),
        idempotency_key="split-same-day",
        request_fingerprint="f" * 64,
        result_data={},
    )
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalar_result([same_day_coverage]))
    db.delete = AsyncMock()
    db.flush = AsyncMock()

    await AssetUnitBoundaryRepository().persist_split(
        db,
        source=source,
        results=results,
        boundary_change=boundary_change,
        active_upstream_contract_ids=("upstream-1",),
        effective_date=date(2026, 11, 1),
    )

    db.delete.assert_awaited_once_with(same_day_coverage)
    added = db.add_all.call_args.args[0]
    new_coverages = [
        item for item in added if isinstance(item, UpstreamContractAssetUnit)
    ]
    assert len(new_coverages) == 2
    assert all(
        coverage.effective_from == date(2026, 11, 1)
        and coverage.effective_to == date(2027, 12, 31)
        for coverage in new_coverages
    )


@pytest.mark.asyncio
async def test_load_merge_context_locks_sources_in_one_sorted_batch() -> None:
    source_1 = _source()
    source_2 = _source()
    source_2.id = "unit-2"
    source_2.unit_code = "U-002"
    upstream_coverage_1 = UpstreamContractAssetUnit(
        upstream_contract_id="upstream-1",
        asset_unit_id=source_1.id,
        effective_from=date(2026, 1, 1),
    )
    upstream_coverage_2 = UpstreamContractAssetUnit(
        upstream_contract_id="upstream-1",
        asset_unit_id=source_2.id,
        effective_from=date(2026, 1, 1),
    )
    upstream = UpstreamContract(id="upstream-1", contract_number="UP-001")
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalar_result([]),
            _first_scalar_result(None),
            _scalar_result([upstream_coverage_1, upstream_coverage_2]),
            _scalar_result([]),
            _scalar_result([upstream]),
            _scalar_result([]),
        ]
    )
    scope = EffectivePartyScope(
        user_id="actor-1",
        source="explicit",
        scope_mode="owner",
        owner_party_ids=["owner-1"],
    )

    with patch(
        "src.crud.asset_unit_boundary.asset_unit_repository.lock_for_write",
        new=AsyncMock(return_value=(source_1, source_2)),
    ) as lock_units:
        context = await AssetUnitBoundaryRepository().load_merge_context(
            db,
            unit_ids=(source_2.id, source_1.id),
            scope=scope,
            effective_date=date(2026, 11, 1),
            result_unit_code="U-001+002",
            for_update=True,
        )

    assert context.sources == (source_1, source_2)
    assert context.result_unit_code_exists is False
    assert context.upstream_coverages == (
        upstream_coverage_1,
        upstream_coverage_2,
    )
    assert lock_units.await_args.kwargs["unit_ids"] == ("unit-1", "unit-2")
    sql_statements = [
        str(call.args[0].compile(compile_kwargs={"literal_binds": True}))
        for call in db.execute.await_args_list
    ]
    assert all("FOR UPDATE" in sql for sql in sql_statements)
    assert "asset_unit_boundary_sources.asset_unit_id IN" in sql_statements[0]
    assert "asset_units.unit_code = 'U-001+002'" in sql_statements[1]


@pytest.mark.asyncio
async def test_persist_merge_ends_all_coverages_and_creates_one_result_scope() -> None:
    source_1 = _source()
    source_2 = _source()
    source_2.id = "unit-2"
    source_2.unit_code = "U-002"
    result = AssetUnit(
        id="unit-merged",
        unit_code="U-001+002",
        managed_from=date(2026, 11, 1),
    )
    source_coverages = [
        UpstreamContractAssetUnit(
            upstream_contract_id="upstream-1",
            asset_unit_id=source.id,
            effective_from=date(2026, 1, 1),
            effective_to=date(2027, 12, 31),
        )
        for source in (source_1, source_2)
    ]
    boundary_change = AssetUnitBoundaryChange(
        id="change-merge-1",
        change_type="merge",
        effective_date=date(2026, 11, 1),
        source_unit_ids=[source_1.id, source_2.id],
        result_unit_ids=[result.id],
        area_check={},
        reason="恢复完整经营边界",
        created_by="actor-1",
        created_at=datetime(2026, 10, 24, 9, 0),
        idempotency_key="merge-request-1",
        request_fingerprint="f" * 64,
        result_data={},
    )
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalar_result(source_coverages))
    db.flush = AsyncMock()

    await AssetUnitBoundaryRepository().persist_merge(
        db,
        sources=(source_1, source_2),
        result=result,
        boundary_change=boundary_change,
        active_upstream_contract_ids=("upstream-1",),
        effective_date=date(2026, 11, 1),
    )

    assert all(
        coverage.effective_to == date(2026, 10, 31) for coverage in source_coverages
    )
    added = db.add_all.call_args.args[0]
    new_coverages = [
        item for item in added if isinstance(item, UpstreamContractAssetUnit)
    ]
    boundary_sources = [
        item for item in added if isinstance(item, AssetUnitBoundarySource)
    ]
    assert len(new_coverages) == 1
    assert new_coverages[0].upstream_contract_id == "upstream-1"
    assert new_coverages[0].asset_unit_id == result.id
    assert new_coverages[0].effective_from == date(2026, 11, 1)
    assert new_coverages[0].effective_to == date(2027, 12, 31)
    assert {item.asset_unit_id for item in boundary_sources} == {
        source_1.id,
        source_2.id,
    }
    statement = db.execute.await_args.args[0]
    assert "FOR UPDATE" in str(statement.compile())
    assert db.flush.await_count == 2
