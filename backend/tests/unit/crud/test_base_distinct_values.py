"""Tests for CRUDBase.get_distinct_field_values()."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.exception_handler import InvalidRequestError
from src.crud.asset import asset_crud


@pytest.fixture(autouse=True)
def clear_asset_crud_cache():
    asset_crud.clear_cache()
    yield
    asset_crud.clear_cache()


class TestGetDistinctFieldValues:
    """Test suite for CRUDBase.get_distinct_field_values()."""

    @pytest.mark.asyncio
    async def test_invalid_field_name(self, mock_db: MagicMock):
        with pytest.raises(AttributeError, match="does not exist on model"):
            await asset_crud.get_distinct_field_values(mock_db, "nonexistent_field")

    @pytest.mark.asyncio
    async def test_invalid_sort_order(self, mock_db: MagicMock):
        with pytest.raises(InvalidRequestError, match="sort_order must be"):
            await asset_crud.get_distinct_field_values(
                mock_db,
                "ownership_id",
                sort_order="invalid",
            )

    @pytest.mark.asyncio
    async def test_query_execution_and_result_mapping(self, mock_db: MagicMock):
        mock_result = MagicMock()
        mock_result.all.return_value = [("value1",), ("value2",)]
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await asset_crud.get_distinct_field_values(
            mock_db,
            "ownership_id",
            sort_order="asc",
            use_cache=False,
            exclude_empty=True,
        )

        assert result == ["value1", "value2"]
        mock_db.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_query_with_filters(self, mock_db: MagicMock):
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        await asset_crud.get_distinct_field_values(
            mock_db,
            "ownership_id",
            filters={"is_active": True},
            use_cache=False,
        )

        mock_db.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_descending_sort_generates_desc_statement(self, mock_db: MagicMock):
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        await asset_crud.get_distinct_field_values(
            mock_db,
            "ownership_id",
            sort_order="desc",
            use_cache=False,
        )

        stmt = mock_db.execute.await_args.args[0]
        assert "DESC" in str(stmt)

    @pytest.mark.asyncio
    async def test_exclude_empty_false_still_executes(self, mock_db: MagicMock):
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        await asset_crud.get_distinct_field_values(
            mock_db,
            "ownership_id",
            exclude_empty=False,
            use_cache=False,
        )

        mock_db.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_caching_mechanism(self, mock_db: MagicMock):
        mock_result = MagicMock()
        mock_result.all.return_value = [("value1",)]
        mock_db.execute = AsyncMock(return_value=mock_result)

        result1 = await asset_crud.get_distinct_field_values(
            mock_db,
            "ownership_id",
            use_cache=True,
        )
        result2 = await asset_crud.get_distinct_field_values(
            mock_db,
            "ownership_id",
            use_cache=True,
        )

        assert result1 == result2 == ["value1"]
        mock_db.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_empty_values_filtered(self, mock_db: MagicMock):
        mock_result = MagicMock()
        mock_result.all.return_value = [
            ("value1",),
            ("value2",),
            (None,),
            ("",),
            ("value3",),
        ]
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await asset_crud.get_distinct_field_values(
            mock_db,
            "ownership_id",
            use_cache=False,
        )

        assert result == ["value1", "value2", "value3"]
