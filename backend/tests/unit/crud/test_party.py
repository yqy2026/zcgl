"""Unit tests for party CRUD helpers."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.crud.party import CRUDParty


def _mapping_execute_result(row: dict[str, str] | None) -> MagicMock:
    result = MagicMock()
    result.mappings.return_value.one_or_none.return_value = row
    return result


def _mapping_execute_all_result(rows: list[dict[str, str | None]]) -> MagicMock:
    result = MagicMock()
    result.mappings.return_value.all.return_value = rows
    return result


@pytest.mark.asyncio
async def test_create_party_adds_and_refreshes(mock_db) -> None:
    crud = CRUDParty()

    result = await crud.create_party(
        mock_db,
        obj_in={"party_type": "organization", "name": "总部", "code": "HQ"},
        commit=False,
    )

    assert result.name == "总部"
    mock_db.add.assert_called_once()
    mock_db.flush.assert_awaited_once()
    mock_db.refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_descendants_returns_recursive_ids(mock_db) -> None:
    crud = CRUDParty()
    execute_result = MagicMock()
    execute_result.fetchall.return_value = [("child-1",), ("child-2",)]
    mock_db.execute = AsyncMock(return_value=execute_result)

    descendants = await crud.get_descendants(
        mock_db,
        party_id="root-1",
        include_self=True,
    )

    assert descendants == ["root-1", "child-1", "child-2"]


@pytest.mark.asyncio
async def test_remove_hierarchy_returns_deleted_count(mock_db) -> None:
    crud = CRUDParty()
    mock_db.execute = AsyncMock(return_value=SimpleNamespace(rowcount=1))

    deleted = await crud.remove_hierarchy(
        mock_db,
        parent_party_id="p-1",
        child_party_id="p-2",
        commit=False,
    )

    assert deleted == 1
    mock_db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_parties_applies_search_filter(mock_db) -> None:
    crud = CRUDParty()
    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=execute_result)

    await crud.get_parties(mock_db, search="总部")

    stmt = mock_db.execute.await_args.args[0]
    sql = str(stmt)
    assert "parties.name" in sql
    assert "parties.code" in sql
    assert "LIKE" in sql.upper()


@pytest.mark.asyncio
async def test_get_parties_applies_scoped_party_ids_filter(mock_db) -> None:
    crud = CRUDParty()
    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=execute_result)

    await crud.get_parties(mock_db, scoped_party_ids=["party-1", "party-2"])

    stmt = mock_db.execute.await_args.args[0]
    sql = str(stmt)
    assert "parties.id IN" in sql


@pytest.mark.asyncio
async def test_get_parties_returns_empty_when_scoped_party_ids_is_empty(mock_db) -> None:
    crud = CRUDParty()

    result = await crud.get_parties(mock_db, scoped_party_ids=[])

    assert result == []
    mock_db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_resolve_legal_entity_party_id_should_match_external_ref(mock_db) -> None:
    crud = CRUDParty()
    mock_db.execute = AsyncMock(
        side_effect=[
            _mapping_execute_result(None),
            _mapping_execute_result({"party_id": "party-2"}),
        ]
    )

    resolved = await crud.resolve_legal_entity_party_id(
        mock_db,
        ownership_id="ownership-legacy-1",
    )

    assert resolved == "party-2"
    assert mock_db.execute.await_count == 2


@pytest.mark.asyncio
async def test_resolve_organization_party_id_should_match_external_ref(mock_db) -> None:
    crud = CRUDParty()
    mock_db.execute = AsyncMock(
        side_effect=[
            _mapping_execute_result(None),
            _mapping_execute_result({"party_id": "party-org-2"}),
        ]
    )

    resolved = await crud.resolve_organization_party_id(
        mock_db,
        organization_id="organization-legacy-1",
    )

    assert resolved == "party-org-2"
    assert mock_db.execute.await_count == 2


@pytest.mark.asyncio
async def test_resolve_organization_party_id_should_fallback_to_org_metadata(
    mock_db,
) -> None:
    crud = CRUDParty()
    mock_db.execute = AsyncMock(
        side_effect=[
            _mapping_execute_result(None),
            _mapping_execute_result(None),
            _mapping_execute_result(
                {
                    "organization_code": "ORG-001",
                    "organization_name": "组织一",
                }
            ),
            _mapping_execute_result({"party_id": "party-org-1"}),
        ]
    )

    resolved = await crud.resolve_organization_party_id(
        mock_db,
        organization_id="organization-legacy-1",
    )

    assert resolved == "party-org-1"
    assert mock_db.execute.await_count == 4


@pytest.mark.asyncio
async def test_resolve_legal_entity_party_id_should_return_none_for_blank_identifier(
    mock_db,
) -> None:
    crud = CRUDParty()

    resolved = await crud.resolve_legal_entity_party_id(
        mock_db,
        ownership_id="   ",
    )

    assert resolved is None
    mock_db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_resolve_legacy_organization_scope_ids_by_party_ids_should_map_party_and_external_ref(
    mock_db,
) -> None:
    crud = CRUDParty()
    mock_db.execute = AsyncMock(
        return_value=_mapping_execute_all_result(
            [
                {
                    "party_id": "party-org-1",
                    "external_ref": "org-legacy-1",
                    "party_code": "ORG-001",
                    "party_name": "组织一",
                },
                {
                    "party_id": "party-org-2",
                    "external_ref": "org-legacy-2",
                    "party_code": "ORG-002",
                    "party_name": "组织二",
                },
            ]
        )
    )

    result = await crud.resolve_legacy_organization_scope_ids_by_party_ids(
        mock_db,
        party_ids=["party-org-1", "org-legacy-2", "unknown"],
    )

    assert result == {
        "party-org-1": ["org-legacy-1"],
        "org-legacy-2": ["org-legacy-2"],
    }


@pytest.mark.asyncio
async def test_resolve_legacy_organization_scope_ids_by_party_ids_should_resolve_org_id_via_metadata_lookup(
    mock_db,
) -> None:
    crud = CRUDParty()
    mock_db.execute = AsyncMock(
        side_effect=[
            _mapping_execute_all_result(
                [
                    {
                        "party_id": "party-org-1",
                        "external_ref": None,
                        "party_code": "ORG-001",
                        "party_name": "组织一",
                    }
                ]
            ),
            _mapping_execute_all_result(
                [
                    {
                        "organization_id": "org-legacy-1",
                        "organization_code": "ORG-001",
                        "organization_name": "组织一",
                    }
                ]
            ),
        ]
    )

    result = await crud.resolve_legacy_organization_scope_ids_by_party_ids(
        mock_db,
        party_ids=["party-org-1"],
    )

    assert result == {"party-org-1": ["org-legacy-1"]}


@pytest.mark.asyncio
async def test_resolve_legacy_organization_scope_ids_by_party_ids_should_not_fallback_to_party_id_when_org_lookup_missing(
    mock_db,
) -> None:
    crud = CRUDParty()
    mock_db.execute = AsyncMock(
        side_effect=[
            _mapping_execute_all_result(
                [
                    {
                        "party_id": "party-org-1",
                        "external_ref": None,
                        "party_code": "ORG-001",
                        "party_name": "组织一",
                    }
                ]
            ),
            _mapping_execute_all_result([]),
        ]
    )

    result = await crud.resolve_legacy_organization_scope_ids_by_party_ids(
        mock_db,
        party_ids=["party-org-1"],
    )

    assert result == {}


@pytest.mark.asyncio
async def test_resolve_legacy_organization_scope_ids_by_party_ids_should_skip_blank_input(
    mock_db,
) -> None:
    crud = CRUDParty()

    result = await crud.resolve_legacy_organization_scope_ids_by_party_ids(
        mock_db,
        party_ids=[" ", "", "\t"],
    )

    assert result == {}
    mock_db.execute.assert_not_called()
