"""
Unit tests for enum data initialization.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from src.services.enum_data_init import STANDARD_ENUMS, init_enum_data


class _ExecuteResult:
    def __init__(self, values):
        self._values = values

    def scalars(self):
        return self

    def all(self):
        return self._values

    def first(self):
        if isinstance(self._values, list):
            return self._values[0] if self._values else None
        return self._values


@pytest.fixture
def mock_db():
    db = AsyncMock()
    added_objects: list[object] = []

    def _add(obj: object) -> None:
        added_objects.append(obj)

    async def _flush() -> None:
        for obj in added_objects:
            if getattr(obj, "id", None) is None and getattr(obj, "code", None) is not None:
                obj.id = f"type-{obj.code}"

    db.add = Mock(side_effect=_add)
    db.execute = AsyncMock()
    db.flush = AsyncMock(side_effect=_flush)
    db.commit = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_init_enum_data_creates_all_types_and_values(mock_db):
    total_values = sum(len(config["values"]) for config in STANDARD_ENUMS.values())
    mock_db.execute.side_effect = [_ExecuteResult([])]

    result = await init_enum_data(mock_db, created_by="tester")

    assert result["types_created"] == len(STANDARD_ENUMS)
    assert result["types_updated"] == 0
    assert result["values_created"] == total_values
    assert result["values_updated"] == 0
    assert result["errors"] == []
    assert mock_db.flush.await_count == len(STANDARD_ENUMS)
    assert mock_db.execute.await_count == 1
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_init_enum_data_updates_existing_types_and_values(mock_db):
    total_values = sum(len(config["values"]) for config in STANDARD_ENUMS.values())
    existing_types = []
    existing_values = []
    for enum_code, config in STANDARD_ENUMS.items():
        enum_type_id = f"type-{enum_code}"
        existing_types.append(
            SimpleNamespace(
                id=enum_type_id,
                code=enum_code,
                category="old-category",
                description="old-description",
            )
        )
        for value_config in config["values"]:
            existing_values.append(
                SimpleNamespace(
                    enum_type_id=enum_type_id,
                    value=value_config["value"],
                    sort_order=1,
                )
            )

    mock_db.execute.side_effect = [
        _ExecuteResult(existing_types),
        _ExecuteResult(existing_values),
    ]

    result = await init_enum_data(mock_db, created_by="tester")

    assert result["types_created"] == 0
    assert result["types_updated"] == len(STANDARD_ENUMS)
    assert result["values_created"] == 0
    assert result["values_updated"] == total_values
    assert result["errors"] == []
    mock_db.flush.assert_not_awaited()
    assert mock_db.execute.await_count == 2
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_init_enum_data_collects_errors_without_crashing(mock_db):
    mock_db.execute.side_effect = Exception("db boom")

    result = await init_enum_data(mock_db, created_by="tester")

    assert result["types_created"] == 0
    assert result["types_updated"] == 0
    assert result["values_created"] == 0
    assert result["values_updated"] == 0
    assert len(result["errors"]) == len(STANDARD_ENUMS)
    assert all("db boom" in error for error in result["errors"])
    mock_db.commit.assert_awaited_once()
