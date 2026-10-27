"""Repository behavior for v5 asset-unit queries."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.crud.asset_unit import AssetUnitRepository
from src.models.asset_unit import AssetUnit
from src.services.party_scope_resolver import EffectivePartyScope


def _execute_results(*, items: list[AssetUnit], total: int) -> list[MagicMock]:
    count_result = MagicMock()
    count_result.scalar_one.return_value = total
    rows_result = MagicMock()
    rows_result.scalars.return_value.all.return_value = items
    return [count_result, rows_result]


@pytest.mark.asyncio
async def test_list_units_returns_only_owner_scoped_rows() -> None:
    expected = AssetUnit(id="unit-owner-a", unit_code="UNIT-SCOPE-A")
    db = MagicMock()
    db.execute = AsyncMock(side_effect=_execute_results(items=[expected], total=1))

    repository = AssetUnitRepository()
    items, total = await repository.list(
        db,
        scope=EffectivePartyScope(
            user_id="user-1",
            source="explicit",
            scope_mode="owner",
            owner_party_ids=["owner-a"],
        ),
    )

    assert items == [expected]
    assert total == 1
    list_statement = db.execute.await_args_list[1].args[0]
    sql = str(list_statement.compile(compile_kwargs={"literal_binds": True}))
    assert "asset_units.owner_party_id IN ('owner-a')" in sql


@pytest.mark.asyncio
async def test_list_units_fails_closed_without_effective_party_scope() -> None:
    db = MagicMock()
    db.execute = AsyncMock()

    items, total = await AssetUnitRepository().list(
        db,
        scope=EffectivePartyScope(
            user_id="user-1",
            source="none",
            scope_mode="none",
            error_code="PARTY_SCOPE_MISSING",
        ),
    )

    assert items == []
    assert total == 0
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_list_units_manager_scope_uses_project_management_assignment() -> None:
    expected = AssetUnit(id="unit-managed", unit_code="UNIT-MANAGED")
    db = MagicMock()
    db.execute = AsyncMock(side_effect=_execute_results(items=[expected], total=1))

    items, total = await AssetUnitRepository().list(
        db,
        scope=EffectivePartyScope(
            user_id="user-1",
            source="explicit",
            scope_mode="manager",
            manager_party_ids=["operator-a"],
        ),
    )

    assert items == [expected]
    assert total == 1
    list_statement = db.execute.await_args_list[1].args[0]
    sql = str(list_statement.compile(compile_kwargs={"literal_binds": True}))
    assert "projects.manager_party_id IN ('operator-a')" in sql
    assert "projects.id = asset_units.project_id" in sql


@pytest.mark.asyncio
async def test_get_unit_applies_scope_before_returning_single_object() -> None:
    expected = AssetUnit(id="unit-owner-a", unit_code="UNIT-SCOPE-A")
    result = MagicMock()
    result.scalars.return_value.one_or_none.return_value = expected
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)

    item = await AssetUnitRepository().get(
        db,
        unit_id=expected.id,
        scope=EffectivePartyScope(
            user_id="user-1",
            source="explicit",
            scope_mode="owner",
            owner_party_ids=["owner-a"],
        ),
    )

    assert item is expected
    statement = db.execute.await_args.args[0]
    sql = str(statement.compile(compile_kwargs={"literal_binds": True}))
    assert "asset_units.id = 'unit-owner-a'" in sql
    assert "asset_units.owner_party_id IN ('owner-a')" in sql


@pytest.mark.asyncio
async def test_lock_for_write_uses_one_scoped_deterministic_row_lock_contract() -> None:
    expected = [
        AssetUnit(id="unit-a", unit_code="UNIT-A"),
        AssetUnit(id="unit-b", unit_code="UNIT-B"),
    ]
    result = MagicMock()
    result.scalars.return_value.all.return_value = expected
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)

    locked = await AssetUnitRepository().lock_for_write(
        db,
        unit_ids=["unit-b", "unit-a", "unit-b"],
        scope=EffectivePartyScope(
            user_id="user-1",
            source="explicit",
            scope_mode="owner",
            owner_party_ids=["owner-a"],
        ),
    )

    assert locked == tuple(expected)
    statement = db.execute.await_args.args[0]
    sql = str(statement.compile(compile_kwargs={"literal_binds": True}))
    assert "asset_units.id IN ('unit-a', 'unit-b')" in sql
    assert "asset_units.owner_party_id IN ('owner-a')" in sql
    assert "ORDER BY asset_units.id" in sql
    assert "FOR UPDATE" in sql
