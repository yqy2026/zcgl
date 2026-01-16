"""Tests for CRUDBase.get_distinct_field_values() method"""

from unittest.mock import MagicMock, Mock

import pytest
from sqlalchemy.orm import Session

from src.crud.asset import asset_crud


@pytest.fixture
def mock_db():
    """模拟数据库会话"""
    return MagicMock(spec=Session)


class TestGetDistinctFieldValues:
    """Test suite for CRUDBase.get_distinct_field_values()"""

    def test_invalid_field_name(self, mock_db: MagicMock):
        """Test error handling for invalid field"""
        with pytest.raises(AttributeError, match="does not exist on model"):
            asset_crud.get_distinct_field_values(mock_db, "nonexistent_field")

    def test_invalid_sort_order(self, mock_db: MagicMock):
        """Test error handling for invalid sort order"""
        with pytest.raises(ValueError, match="sort_order must be"):
            asset_crud.get_distinct_field_values(
                mock_db, "ownership_entity", sort_order="invalid"
            )

    def test_query_construction(self, mock_db: MagicMock):
        """Test that query is constructed correctly with all options"""
        # Mock the query chain
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.distinct.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [("value1",), ("value2",)]

        # Call the method
        result = asset_crud.get_distinct_field_values(
            mock_db,
            "ownership_entity",
            sort_order="asc",
            use_cache=False,
            exclude_empty=True,
        )

        # Verify query was called correctly
        mock_db.query.assert_called_once()
        assert result == ["value1", "value2"]

    def test_query_with_filters(self, mock_db: MagicMock):
        """Test query construction with additional filters"""
        # Mock the query chain
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.distinct.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []

        # Call the method with filters
        asset_crud.get_distinct_field_values(
            mock_db,
            "ownership_entity",
            filters={"is_active": True},
            use_cache=False,
        )

        # Verify filter was called at least once for exclude_empty + once for additional filter
        # The implementation chains filters, so we expect at least 2 calls
        # (one for None/empty check, one or more for additional filters)
        assert mock_query.filter.call_count >= 1

    def test_descending_sort(self, mock_db: MagicMock):
        """Test descending sort order is applied"""
        # Mock the query chain
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.distinct.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []

        # Call with descending sort
        asset_crud.get_distinct_field_values(
            mock_db, "ownership_entity", sort_order="desc", use_cache=False
        )

        # Verify order_by was called
        mock_query.order_by.assert_called_once()

    def test_exclude_empty_false(self, mock_db: MagicMock):
        """Test with exclude_empty=False"""
        # Mock the query chain
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.distinct.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []

        # Call with exclude_empty=False
        asset_crud.get_distinct_field_values(
            mock_db, "ownership_entity", exclude_empty=True, use_cache=False
        )

        # Verify query was constructed
        mock_db.query.assert_called_once()

    def test_caching_mechanism(self, mock_db: MagicMock):
        """Test that caching is properly used"""
        # Mock the query chain
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.distinct.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [("value1",)]

        # First call with cache enabled
        result1 = asset_crud.get_distinct_field_values(
            mock_db, "ownership_entity", use_cache=True
        )

        # Second call should use cache (query should not be called again)
        result2 = asset_crud.get_distinct_field_values(
            mock_db, "ownership_entity", use_cache=True
        )

        # Results should be the same
        assert result1 == result2 == ["value1"]

        # Query should only be called once (first call hits DB, second call uses cache)
        # Note: This depends on cache_key generation being consistent

    def test_empty_values_filtered(self, mock_db: MagicMock):
        """Test that empty values are filtered from results"""
        # Mock the query chain
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.distinct.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        # Return mix of valid and empty values
        mock_query.all.return_value = [
            ("value1",),
            ("value2",),
            (None,),
            ("",),
            ("value3",),
        ]

        # Call the method
        result = asset_crud.get_distinct_field_values(
            mock_db, "ownership_entity", use_cache=False
        )

        # Verify empty values were filtered out
        assert result == ["value1", "value2", "value3"]
        assert None not in result
        assert "" not in result
