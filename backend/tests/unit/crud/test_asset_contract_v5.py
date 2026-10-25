"""Repository behavior for v5 signed-contract queries."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.crud.asset_contract import AssetContractRepository
from src.models.asset_contract import TerminalContract, UpstreamContract
from src.services.party_scope_resolver import EffectivePartyScope


def _execute_results(*, items: list[object], total: int) -> list[MagicMock]:
    count_result = MagicMock()
    count_result.scalar_one.return_value = total
    rows_result = MagicMock()
    rows_result.scalars.return_value.all.return_value = items
    return [count_result, rows_result]


@pytest.mark.asyncio
async def test_list_upstream_contracts_maps_owner_and_manager_scope_to_roles() -> None:
    expected = UpstreamContract(id="upstream-1", contract_number="UP-001")
    db = MagicMock()
    db.execute = AsyncMock(side_effect=_execute_results(items=[expected], total=1))

    items, total = await AssetContractRepository().list_upstream(
        db,
        scope=EffectivePartyScope(
            user_id="user-1",
            source="explicit",
            scope_mode="all",
            owner_party_ids=["owner-a"],
            manager_party_ids=["operator-a"],
        ),
    )

    assert items == [expected]
    assert total == 1
    list_statement = db.execute.await_args_list[1].args[0]
    sql = str(list_statement.compile(compile_kwargs={"literal_binds": True}))
    assert "upstream_contracts.owner_party_id IN ('owner-a')" in sql
    assert "upstream_contracts.operator_party_id IN ('operator-a')" in sql


@pytest.mark.asyncio
async def test_list_terminal_contracts_scopes_through_covered_asset_units() -> None:
    expected = TerminalContract(id="terminal-1", contract_number="TM-001")
    db = MagicMock()
    db.execute = AsyncMock(side_effect=_execute_results(items=[expected], total=1))

    items, total = await AssetContractRepository().list_terminal(
        db,
        scope=EffectivePartyScope(
            user_id="user-1",
            source="explicit",
            scope_mode="all",
            owner_party_ids=["owner-a"],
            manager_party_ids=["operator-a"],
        ),
    )

    assert items == [expected]
    assert total == 1
    list_statement = db.execute.await_args_list[1].args[0]
    sql = str(list_statement.compile(compile_kwargs={"literal_binds": True}))
    assert "terminal_contract_asset_units" in sql
    assert "asset_units.owner_party_id IN ('owner-a')" in sql
    assert "projects.manager_party_id IN ('operator-a')" in sql
    assert "terminal_contracts.lessor_party_id IN" not in sql


@pytest.mark.asyncio
async def test_get_terminal_contract_reuses_covered_unit_scope() -> None:
    expected = TerminalContract(id="terminal-1", contract_number="TM-001")
    result = MagicMock()
    result.scalars.return_value.one_or_none.return_value = expected
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)

    item = await AssetContractRepository().get_terminal(
        db,
        contract_id=expected.id,
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
    assert "terminal_contracts.id = 'terminal-1'" in sql
    assert "asset_units.owner_party_id IN ('owner-a')" in sql


@pytest.mark.asyncio
async def test_get_upstream_contract_reuses_role_scope() -> None:
    expected = UpstreamContract(id="upstream-1", contract_number="UP-001")
    result = MagicMock()
    result.scalars.return_value.one_or_none.return_value = expected
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)

    item = await AssetContractRepository().get_upstream(
        db,
        contract_id=expected.id,
        scope=EffectivePartyScope(
            user_id="user-1",
            source="explicit",
            scope_mode="manager",
            manager_party_ids=["operator-a"],
        ),
    )

    assert item is expected
    statement = db.execute.await_args.args[0]
    sql = str(statement.compile(compile_kwargs={"literal_binds": True}))
    assert "upstream_contracts.id = 'upstream-1'" in sql
    assert "upstream_contracts.operator_party_id IN ('operator-a')" in sql
