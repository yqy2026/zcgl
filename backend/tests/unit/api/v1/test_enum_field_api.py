from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Depends

from src.api.v1.system.enum_field import (
    _resolve_service,
    _strip_enum_children,
    create_enum_field_value,
    delete_enum_field_value,
    get_enum_field_type_history,
    get_enum_field_types,
    get_enum_field_value_history,
)
from src.schemas.enum_field import EnumFieldValueCreate

pytestmark = pytest.mark.api


def test_strip_enum_children_uses_set_committed_value():
    enum_value = MagicMock()

    with patch("src.api.v1.system.enum_field.set_committed_value") as mock_set:
        _strip_enum_children([enum_value])

    mock_set.assert_called_once_with(enum_value, "children", [])


def test_strip_enum_children_falls_back_to_setattr():
    class DummyValue:
        def __init__(self) -> None:
            self.children = ["legacy"]

    enum_value = DummyValue()

    with patch(
        "src.api.v1.system.enum_field.set_committed_value",
        side_effect=RuntimeError("db session missing"),
    ):
        _strip_enum_children([enum_value])

    assert enum_value.children == []


def test_resolve_service_from_depends_param():
    resolved_service = object()

    with patch(
        "src.api.v1.system.enum_field.get_enum_field_service",
        return_value=resolved_service,
    ):
        result = _resolve_service(Depends(lambda: None))

    assert result is resolved_service


@pytest.mark.asyncio
async def test_get_enum_field_types_delegates_to_service(mock_db):
    expected = [MagicMock(id="type_001")]
    mock_service = MagicMock()
    mock_service.get_enum_field_types = AsyncMock(return_value=expected)

    result = await get_enum_field_types(
        page=2,
        page_size=50,
        category="asset",
        status="active",
        is_system=False,
        keyword="面积",
        db=mock_db,
        service=mock_service,
    )

    assert result == expected
    mock_service.get_enum_field_types.assert_awaited_once_with(
        db=mock_db,
        page=2,
        page_size=50,
        category="asset",
        status="active",
        is_system=False,
        keyword="面积",
    )


@pytest.mark.asyncio
async def test_create_enum_field_value_delegates_to_service(mock_db):
    payload = EnumFieldValueCreate(
        enum_type_id="type_001",
        label="商业",
        value="commercial",
        code="COMMERCIAL",
    )
    expected = MagicMock(id="value_001")
    mock_service = MagicMock()
    mock_service.create_enum_field_value = AsyncMock(return_value=expected)

    result = await create_enum_field_value(
        type_id="type_001",
        enum_value=payload,
        db=mock_db,
        service=mock_service,
    )

    assert result == expected
    mock_service.create_enum_field_value.assert_awaited_once_with(
        db=mock_db,
        type_id="type_001",
        enum_value=payload,
    )


@pytest.mark.asyncio
async def test_delete_enum_field_value_delegates_to_service(mock_db):
    expected = {"message": "删除成功"}
    mock_service = MagicMock()
    mock_service.delete_enum_field_value = AsyncMock(return_value=expected)

    result = await delete_enum_field_value(
        value_id="value_001",
        deleted_by="tester",
        db=mock_db,
        service=mock_service,
    )

    assert result == expected
    mock_service.delete_enum_field_value.assert_awaited_once_with(
        db=mock_db,
        value_id="value_001",
        deleted_by="tester",
    )


@pytest.mark.asyncio
async def test_get_history_endpoints_delegate_to_service(mock_db):
    type_history = [MagicMock(id="history_type_001")]
    value_history = [MagicMock(id="history_value_001")]
    mock_service = MagicMock()
    mock_service.get_enum_field_type_history = AsyncMock(return_value=type_history)
    mock_service.get_enum_field_value_history = AsyncMock(return_value=value_history)

    type_result = await get_enum_field_type_history(
        type_id="type_001",
        page=3,
        page_size=20,
        db=mock_db,
        service=mock_service,
    )
    value_result = await get_enum_field_value_history(
        value_id="value_001",
        page=4,
        page_size=10,
        db=mock_db,
        service=mock_service,
    )

    assert type_result == type_history
    assert value_result == value_history
    mock_service.get_enum_field_type_history.assert_awaited_once_with(
        db=mock_db,
        type_id="type_001",
        page=3,
        page_size=20,
    )
    mock_service.get_enum_field_value_history.assert_awaited_once_with(
        db=mock_db,
        value_id="value_001",
        page=4,
        page_size=10,
    )
