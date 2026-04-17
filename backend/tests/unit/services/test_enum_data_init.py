"""
Unit tests for enum data initialization.
"""

from collections.abc import Callable
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.exc import IntegrityError

from src.services.enum_data_init import STANDARD_ENUMS, init_enum_data


class _AsyncNullTransaction:
    async def __aenter__(self) -> None:
        return None

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


@pytest.fixture
def mock_db():
    db = AsyncMock()
    added_objects: list[object] = []

    def _add(obj: object) -> None:
        added_objects.append(obj)

    async def _flush() -> None:
        for index, obj in enumerate(added_objects, start=1):
            if getattr(obj, "id", None) is None:
                code = getattr(obj, "code", None)
                value = getattr(obj, "value", None)
                if code is not None:
                    obj.id = f"type-{code}"
                elif value is not None:
                    obj.id = f"value-{index}"

    db.add = Mock(side_effect=_add)
    db.flush = AsyncMock(side_effect=_flush)
    db.commit = AsyncMock()
    db.begin_nested = Mock(side_effect=lambda: _AsyncNullTransaction())
    return db


def _build_existing_type(enum_code: str) -> SimpleNamespace:
    config = STANDARD_ENUMS[enum_code]
    return SimpleNamespace(
        id=f"type-{enum_code}",
        code=enum_code,
        name=config["name"],
        category=config["category"],
        description=config["description"],
        is_system=True,
        status="active",
        is_deleted=False,
        updated_by=None,
    )


def _build_existing_value(enum_code: str, value_config: dict[str, object]) -> SimpleNamespace:
    return SimpleNamespace(
        id=f"value-{enum_code}-{value_config['value']}",
        enum_type_id=f"type-{enum_code}",
        value=value_config["value"],
        label=value_config["label"],
        sort_order=value_config["sort_order"],
        is_active=True,
        is_deleted=False,
        updated_by=None,
    )


def _patch_crud(
    monkeypatch: pytest.MonkeyPatch,
    *,
    get_type: Callable[[str], object | None],
    get_values: Callable[[list[str]], list[object]],
) -> None:
    from src.services import enum_data_init as module

    monkeypatch.setattr(
        module.enum_field_type_crud,
        "get_by_code_async",
        AsyncMock(side_effect=lambda _db, code: get_type(code)),
    )
    monkeypatch.setattr(
        module.enum_field_value_crud,
        "get_by_type_ids_async",
        AsyncMock(side_effect=lambda _db, enum_type_ids: get_values(enum_type_ids)),
    )


@pytest.mark.asyncio
async def test_init_enum_data_creates_all_types_and_values(
    mock_db, monkeypatch: pytest.MonkeyPatch
):
    total_values = sum(len(config["values"]) for config in STANDARD_ENUMS.values())

    _patch_crud(
        monkeypatch,
        get_type=lambda _code: None,
        get_values=lambda _type_ids: [],
    )

    result = await init_enum_data(mock_db, created_by="tester")

    assert result["types_created"] == len(STANDARD_ENUMS)
    assert result["types_updated"] == 0
    assert result["values_created"] == total_values
    assert result["values_updated"] == 0
    assert result["errors"] == []
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_init_enum_data_updates_existing_types_and_values(
    mock_db, monkeypatch: pytest.MonkeyPatch
):
    total_values = sum(len(config["values"]) for config in STANDARD_ENUMS.values())
    existing_types = {
        enum_code: _build_existing_type(enum_code) for enum_code in STANDARD_ENUMS
    }
    existing_values = {
        enum_type.id: [
            _build_existing_value(enum_code, value_config)
            for value_config in STANDARD_ENUMS[enum_code]["values"]
        ]
        for enum_code, enum_type in existing_types.items()
    }

    _patch_crud(
        monkeypatch,
        get_type=lambda code: existing_types.get(code),
        get_values=lambda type_ids: [
            value
            for type_id in type_ids
            for value in existing_values.get(type_id, [])
        ],
    )

    result = await init_enum_data(mock_db, created_by="tester")

    assert result["types_created"] == 0
    assert result["types_updated"] == len(STANDARD_ENUMS)
    assert result["values_created"] == 0
    assert result["values_updated"] == total_values
    assert result["errors"] == []
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_init_enum_data_recovers_from_duplicate_type_flush(
    mock_db, monkeypatch: pytest.MonkeyPatch
):
    ownership_type = _build_existing_type("ownership_status")
    retry_state = {"ownership_status": 0}

    def _get_type(enum_code: str) -> object | None:
        if enum_code == "ownership_status":
            retry_state[enum_code] += 1
            if retry_state[enum_code] == 1:
                return None
            return ownership_type
        return None

    _patch_crud(
        monkeypatch,
        get_type=_get_type,
        get_values=lambda _type_ids: [],
    )

    original_flush = mock_db.flush.side_effect
    conflict_raised = {"value": False}

    async def _flush_with_conflict() -> None:
        if not conflict_raised["value"]:
            ownership_inserts = [
                obj
                for obj in mock_db.add.call_args_list
                if getattr(obj.args[0], "code", None) == "ownership_status"
            ]
            if ownership_inserts:
                conflict_raised["value"] = True
                raise IntegrityError("duplicate enum type", None, None)
        await original_flush()

    mock_db.flush.side_effect = _flush_with_conflict

    result = await init_enum_data(mock_db, created_by="tester")

    assert conflict_raised["value"] is True
    assert result["errors"] == []
    assert result["types_updated"] >= 1
    assert result["values_created"] == sum(
        len(config["values"]) for config in STANDARD_ENUMS.values()
    )
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_init_enum_data_collects_errors_without_crashing(
    mock_db, monkeypatch: pytest.MonkeyPatch
):
    from src.services import enum_data_init as module

    monkeypatch.setattr(
        module.enum_field_type_crud,
        "get_by_code_async",
        AsyncMock(side_effect=Exception("db boom")),
    )
    monkeypatch.setattr(
        module.enum_field_value_crud,
        "get_by_type_ids_async",
        AsyncMock(return_value=[]),
    )

    result = await init_enum_data(mock_db, created_by="tester")

    assert result["types_created"] == 0
    assert result["types_updated"] == 0
    assert result["values_created"] == 0
    assert result["values_updated"] == 0
    assert len(result["errors"]) == len(STANDARD_ENUMS)
    assert all("db boom" in error for error in result["errors"])
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_init_enum_data_uses_advisory_lock(
    mock_db, monkeypatch: pytest.MonkeyPatch
):
    _patch_crud(
        monkeypatch,
        get_type=lambda _code: None,
        get_values=lambda _type_ids: [],
    )

    await init_enum_data(mock_db, created_by="tester")

    execute_sqls = [
        str(call.args[0])
        for call in mock_db.execute.await_args_list
        if call.args
    ]
    assert any("pg_advisory_lock" in sql for sql in execute_sqls)
    assert any("pg_advisory_unlock" in sql for sql in execute_sqls)
