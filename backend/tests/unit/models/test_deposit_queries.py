"""Deposit queries batch sources and keep ancestor visibility separate."""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.dialects import postgresql

from src.crud.deposit_queries import deposit_query_repository
from src.services.party_scope_resolver import EffectivePartyScope


def result(rows):
    value = MagicMock()
    value.scalars.return_value.all.return_value = rows
    value.all.return_value = rows
    return value


@pytest.mark.asyncio
async def test_empty_visible_contracts_do_not_read_hidden_ancestor_facts():
    db = MagicMock(execute=AsyncMock(return_value=result([])))
    facts = await deposit_query_repository.load_facts(
        db,
        scope=EffectivePartyScope(
            user_id="user", source="explicit", scope_mode="unrestricted"
        ),
        contract_kind="terminal",
    )
    assert facts.visible_contract_ids == frozenset()
    assert facts.contracts == facts.entries == facts.records == facts.events == ()
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["upstream", "terminal"])
async def test_recursive_ancestors_are_loaded_once_without_becoming_visible(kind):
    child = SimpleNamespace(id="child")
    parent = SimpleNamespace(id="parent")
    entry = SimpleNamespace(id="deposit", contract_id="child")
    db = MagicMock(
        execute=AsyncMock(
            side_effect=[
                result([child]),
                result([parent, child]),
                result([entry]),
                result([]),
                result([]),
                result([("deposit", Decimal("100"), Decimal("20"))]),
            ]
        )
    )
    facts = await deposit_query_repository.load_facts(
        db,
        scope=EffectivePartyScope(
            user_id="user", source="explicit", scope_mode="unrestricted"
        ),
        contract_kind=kind,
        contract_id="child",
        party_id="party",
        project_id="project",
    )
    assert facts.visible_contract_ids == frozenset({"child"})
    assert facts.contracts == (parent, child)
    assert db.execute.await_count == 6
    assert facts.totals == {"deposit": (Decimal("100"), Decimal("20"))}
    statements = [
        str(
            call.args[0].compile(
                dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
            )
        )
        for call in db.execute.await_args_list
    ]
    assert (
        "EXISTS" in statements[0]
        and "project" in statements[0]
        and "party" in statements[0]
    )
    assert "WITH RECURSIVE" in statements[1]
    assert "UNION ALL" not in statements[1]
    assert "renewed_from_id" in statements[1]
    assert "effective_date" not in statements[-2].split("WHERE")[-1]
    assert "sum(CASE" in statements[-1]
    assert "NOT (EXISTS" in statements[-1]
    if kind == "upstream":
        assert "lease" in statements[0]


@pytest.mark.asyncio
async def test_offset_candidates_query_filters_ancestor_scope_before_loading_rent_records():
    rent = SimpleNamespace(id="rent")
    db = MagicMock(execute=AsyncMock(side_effect=[result([rent]), result([])]))
    entries, records = await deposit_query_repository.load_offset_candidates(
        db,
        scope=EffectivePartyScope(
            user_id="user",
            source="explicit",
            scope_mode="owner",
            owner_party_ids=("owner",),
        ),
        contract_ids=frozenset({"current", "ancestor"}),
    )
    assert entries == (rent,) and records == ()
    sql = str(
        db.execute.await_args_list[0]
        .args[0]
        .compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})
    )
    assert "owner" in sql and "ancestor" in sql
    assert "terminal_receivable" in sql and "voided_at IS NULL" in sql
    assert "terminal_contracts" in sql
