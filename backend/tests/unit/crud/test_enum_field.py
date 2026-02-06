"""
Async unit tests for EnumField CRUDs.
Focus on async-only APIs after migration.
"""

from __future__ import annotations

from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.exception_handler import OperationNotAllowedError
from src.crud.enum_field import (
    EnumFieldHistoryCRUD,
    EnumFieldTypeCRUD,
    EnumFieldUsageCRUD,
    EnumFieldValueCRUD,
    get_enum_field_history_crud,
    get_enum_field_type_crud,
    get_enum_field_usage_crud,
    get_enum_field_value_crud,
)
from src.models.enum_field import (
    EnumFieldHistory,
    EnumFieldType,
    EnumFieldUsage,
    EnumFieldValue,
)
from src.schemas.enum_field import (
    EnumFieldTypeCreate,
    EnumFieldTypeUpdate,
    EnumFieldUsageCreate,
    EnumFieldUsageUpdate,
    EnumFieldValueCreate,
    EnumFieldValueUpdate,
)

pytestmark = pytest.mark.asyncio


def _result_with_scalars(values: list[object] | None = None) -> MagicMock:
    result = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = values or []
    scalars.first.return_value = (values or [None])[0] if values is not None else None
    result.scalars.return_value = scalars
    return result


def _result_with_scalar(value: object | None) -> MagicMock:
    result = MagicMock()
    result.scalar.return_value = value
    return result


@pytest.fixture
def sample_enum_type() -> EnumFieldType:
    enum_type = EnumFieldType(
        id="enum_type_123",
        name="Asset Type",
        code="asset_type",
        category="asset",
        description="Asset category",
        is_system=False,
        is_multiple=True,
        is_hierarchical=True,
        status="active",
        is_deleted=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    enum_type.enum_values = []
    return enum_type


@pytest.fixture
def sample_enum_value() -> EnumFieldValue:
    return EnumFieldValue(
        id="enum_value_123",
        enum_type_id="enum_type_123",
        label="Office",
        value="office",
        code="OFFICE",
        level=1,
        path="",
        sort_order=1,
        is_active=True,
        is_deleted=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_usage() -> EnumFieldUsage:
    return EnumFieldUsage(
        id="usage_123",
        enum_type_id="enum_type_123",
        table_name="assets",
        field_name="asset_type",
        field_label="Asset Type",
        module_name="asset",
        is_required=True,
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_type_create() -> EnumFieldTypeCreate:
    return EnumFieldTypeCreate(
        name="New Asset Type",
        code="new_asset_type",
        category="asset",
        description="New asset category",
        is_system=False,
        is_multiple=False,
        is_hierarchical=False,
        status="active",
        created_by="admin",
    )


@pytest.fixture
def sample_value_create() -> EnumFieldValueCreate:
    return EnumFieldValueCreate(
        enum_type_id="enum_type_123",
        label="Commercial",
        value="commercial",
        code="COMMERCIAL",
        sort_order=2,
        is_active=True,
        created_by="admin",
    )


class TestEnumFieldTypeCRUD:
    async def test_get_async_loads_values(self, mock_db, sample_enum_type, sample_enum_value):
        mock_db.execute = AsyncMock(
            side_effect=[
                _result_with_scalars([sample_enum_type]),
                _result_with_scalars([sample_enum_value]),
            ]
        )

        crud = EnumFieldTypeCRUD()
        result = await crud.get_async(mock_db, "enum_type_123")

        assert result is not None
        assert result.id == "enum_type_123"
        assert getattr(result, "enum_values") == [sample_enum_value]

    async def test_get_by_code_async_not_found(self, mock_db):
        mock_db.execute = AsyncMock(return_value=_result_with_scalars([]))

        crud = EnumFieldTypeCRUD()
        result = await crud.get_by_code_async(mock_db, "missing")

        assert result is None

    async def test_get_multi_async_with_filters(self, mock_db, sample_enum_type):
        mock_db.execute = AsyncMock(
            side_effect=[
                _result_with_scalars([sample_enum_type]),
                _result_with_scalars([]),
            ]
        )

        crud = EnumFieldTypeCRUD()
        result = await crud.get_multi_async(
            mock_db,
            skip=0,
            limit=10,
            category="asset",
            status="active",
            is_system=False,
            keyword="asset",
        )

        assert len(result) == 1
        assert result[0].code == "asset_type"

    async def test_create_async_records_history(self, mock_db, sample_type_create):
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock(side_effect=lambda obj: setattr(obj, "id", "new_id"))
        mock_db.flush = AsyncMock()

        crud = EnumFieldTypeCRUD()
        result = await crud.create_async(mock_db, sample_type_create)

        assert result.id == "new_id"
        assert mock_db.add.called
        mock_db.commit.assert_awaited()
        mock_db.flush.assert_awaited()

    async def test_delete_async_blocks_with_values(self, mock_db, sample_enum_type):
        mock_db.execute = AsyncMock(
            side_effect=[
                _result_with_scalars([sample_enum_type]),
                _result_with_scalars([]),
                _result_with_scalar(1),
            ]
        )

        crud = EnumFieldTypeCRUD()
        with pytest.raises(OperationNotAllowedError):
            await crud.delete_async(mock_db, "enum_type_123")

    async def test_get_statistics_async(self, mock_db):
        mock_db.execute = AsyncMock(
            side_effect=[
                _result_with_scalar(5),
                _result_with_scalar(3),
                _result_with_scalars([]),
            ]
        )

        crud = EnumFieldTypeCRUD()
        stats = await crud.get_statistics_async(mock_db)

        assert stats["total_types"] == 5
        assert stats["active_types"] == 3


class TestEnumFieldValueCRUD:
    async def test_get_by_type_and_value_async(self, mock_db, sample_enum_value):
        mock_db.execute = AsyncMock(return_value=_result_with_scalars([sample_enum_value]))

        crud = EnumFieldValueCRUD()
        result = await crud.get_by_type_and_value_async(
            mock_db, "enum_type_123", "office"
        )

        assert result is not None
        assert result.value == "office"

    async def test_get_tree_async(self, mock_db, sample_enum_value):
        crud = EnumFieldValueCRUD()
        crud.get_by_type_async = AsyncMock(side_effect=[[sample_enum_value], []])

        tree = await crud.get_tree_async(mock_db, "enum_type_123")

        assert tree
        assert tree[0].children == []

    async def test_create_async_sets_level_and_path(self, mock_db, sample_value_create):
        parent = EnumFieldValue(
            id="parent",
            enum_type_id="enum_type_123",
            label="Parent",
            value="parent",
            code="PARENT",
            level=1,
            path="root",
            sort_order=1,
            is_active=True,
            is_deleted=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_db.flush = AsyncMock()

        crud = EnumFieldValueCRUD()
        crud.get_async = AsyncMock(return_value=parent)

        obj_in = EnumFieldValueCreate(
            enum_type_id="enum_type_123",
            label="Child",
            value="child",
            code="CHILD",
            sort_order=1,
            is_active=True,
            created_by="admin",
            parent_id="parent",
        )

        result = await crud.create_async(mock_db, obj_in)

        assert result.level == 2
        assert result.path == "root/parent"

    async def test_delete_async_blocks_with_children(self, mock_db, sample_enum_value):
        mock_db.execute = AsyncMock(
            side_effect=[
                _result_with_scalars([sample_enum_value]),
                _result_with_scalar(2),
            ]
        )

        crud = EnumFieldValueCRUD()
        with pytest.raises(OperationNotAllowedError):
            await crud.delete_async(mock_db, "enum_value_123")


class TestEnumFieldUsageCRUD:
    async def test_create_update_delete_async(self, mock_db, sample_usage):
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_db.delete = AsyncMock()

        crud = EnumFieldUsageCRUD()
        created = await crud.create_async(
            mock_db,
            EnumFieldUsageCreate(
                enum_type_id=sample_usage.enum_type_id,
                table_name=sample_usage.table_name,
                field_name=sample_usage.field_name,
                field_label=sample_usage.field_label,
                module_name=sample_usage.module_name,
                is_required=True,
                is_active=True,
                created_by="admin",
            ),
        )

        updated = await crud.update_async(
            mock_db,
            created,
            EnumFieldUsageUpdate(is_active=False, updated_by="admin"),
        )

        assert updated.is_active is False

        mock_db.execute = AsyncMock(return_value=_result_with_scalars([created]))
        deleted = await crud.delete_async(mock_db, created.id)
        assert deleted is True


class TestEnumFieldHistoryCRUD:
    async def test_get_multi_async(self, mock_db):
        history = EnumFieldHistory(
            id="hist_1",
            enum_type_id="enum_type_123",
            enum_value_id=None,
            action="create",
            target_type="type",
            created_at=datetime.now(UTC),
            created_by="admin",
        )
        mock_db.execute = AsyncMock(return_value=_result_with_scalars([history]))

        crud = EnumFieldHistoryCRUD()
        result = await crud.get_multi_async(mock_db, enum_type_id="enum_type_123")

        assert len(result) == 1
        assert result[0].id == "hist_1"


class TestEnumFieldCrudFactories:
    async def test_factory_functions(self, mock_db):
        assert isinstance(get_enum_field_type_crud(mock_db), EnumFieldTypeCRUD)
        assert isinstance(get_enum_field_value_crud(mock_db), EnumFieldValueCRUD)
        assert isinstance(get_enum_field_usage_crud(mock_db), EnumFieldUsageCRUD)
        assert isinstance(get_enum_field_history_crud(mock_db), EnumFieldHistoryCRUD)
