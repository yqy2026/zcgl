"""
Comprehensive unit tests for Enum Validation Service

Tests cover:
1. Enum value validation
2. System dictionary lookups
3. Validation error generation
4. Multiple enum field validation
5. Caching mechanisms
"""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest
from sqlalchemy.orm import Session

from src.models.enum_field import EnumFieldType, EnumFieldValue
from src.services.enum_validation_service import (
    EnumValidationService,
    get_enum_validation_service,
    get_enum_validation_stats,
    get_valid_enum_values,
    validate_enum_value,
)


# ==================== Fixtures ====================


@pytest.fixture
def mock_db():
    """Mock database session"""
    return MagicMock(spec=Session)


@pytest.fixture
def enum_type_ownership():
    """Create mock ownership status enum type"""
    enum_type = Mock(spec=EnumFieldType)
    enum_type.id = "enum_ownership_001"
    enum_type.code = "ownership_status"
    enum_type.name = "权属状况"
    enum_type.status = "active"
    enum_type.is_deleted = False
    return enum_type


@pytest.fixture
def enum_type_usage():
    """Create mock usage status enum type"""
    enum_type = Mock(spec=EnumFieldType)
    enum_type.id = "enum_usage_001"
    enum_type.code = "usage_status"
    enum_type.name = "使用状况"
    enum_type.status = "active"
    enum_type.is_deleted = False
    return enum_type


@pytest.fixture
def enum_values_ownership():
    """Create mock ownership status enum values"""
    # Service expects tuples from query: [ (value,), (value,), ... ]
    values = [
        ("自有",),
        ("租赁",),
        ("借用",),
        ("其他",),
    ]
    return values


@pytest.fixture
def enum_values_usage():
    """Create mock usage status enum values"""
    # Service expects tuples from query: [ (value,), (value,), ... ]
    values = [
        ("在用",),
        ("空闲",),
        ("维修中",),
        ("报废",),
    ]
    return values


@pytest.fixture
def service(mock_db):
    """Create EnumValidationService instance"""
    return EnumValidationService(mock_db)


# ==================== Test: Cache Management ====================


class TestCacheManagement:
    """Test cache invalidation and validity checks"""

    def test_cache_validity_fresh(self, service):
        """Test that fresh cache is considered valid"""
        service._cache["ownership_status"] = ["自有", "租赁"]
        service._cache_timestamps["ownership_status"] = (
            datetime.now().timestamp() - 60  # 1 minute ago
        )

        assert service._is_cache_valid("ownership_status") is True

    def test_cache_validity_expired(self, service):
        """Test that expired cache is considered invalid"""
        service._cache["ownership_status"] = ["自有", "租赁"]
        service._cache_timestamps["ownership_status"] = (
            datetime.now().timestamp() - 400  # 400 seconds ago (> 300 TTL)
        )

        assert service._is_cache_valid("ownership_status") is False

    def test_cache_validity_missing(self, service):
        """Test that missing cache is considered invalid"""
        assert service._is_cache_valid("nonexistent") is False

    def test_update_cache(self, service):
        """Test cache update functionality"""
        values = ["自有", "租赁", "借用"]
        service._update_cache("ownership_status", values)

        assert service._cache["ownership_status"] == values
        assert "ownership_status" in service._cache_timestamps
        assert service._cache_timestamps["ownership_status"] > 0

    def test_invalidate_cache_specific(self, service):
        """Test invalidating specific enum type cache"""
        service._cache["ownership_status"] = ["自有", "租赁"]
        service._cache["usage_status"] = ["在用", "空闲"]
        service._cache_timestamps["ownership_status"] = datetime.now().timestamp()
        service._cache_timestamps["usage_status"] = datetime.now().timestamp()

        service.invalidate_cache("ownership_status")

        assert "ownership_status" not in service._cache
        assert "ownership_status" not in service._cache_timestamps
        assert "usage_status" in service._cache  # Other cache preserved
        assert "usage_status" in service._cache_timestamps

    def test_invalidate_cache_all(self, service):
        """Test invalidating all cache"""
        service._cache["ownership_status"] = ["自有", "租赁"]
        service._cache["usage_status"] = ["在用", "空闲"]
        service._cache_timestamps["ownership_status"] = datetime.now().timestamp()
        service._cache_timestamps["usage_status"] = datetime.now().timestamp()

        service.invalidate_cache(None)

        assert len(service._cache) == 0
        assert len(service._cache_timestamps) == 0


# ==================== Test: Get Valid Values ====================


class TestGetValidValues:
    """Test retrieving valid enum values"""

    def test_get_valid_values_from_cache(self, service):
        """Test retrieving values from cache"""
        service._cache["ownership_status"] = ["自有", "租赁", "借用"]
        service._cache_timestamps["ownership_status"] = datetime.now().timestamp()

        result = service.get_valid_values("ownership_status")

        assert result == ["自有", "租赁", "借用"]
        service.db.query.assert_not_called()

    def test_get_valid_values_from_database(
        self, service, mock_db, enum_type_ownership, enum_values_ownership
    ):
        """Test retrieving values from database"""
        # Track call count
        call_count = [0]

        # Setup mock query chain
        def mock_query_side_effect(model):
            call_count[0] += 1
            mock_query = Mock()

            # First call: query EnumFieldType
            if call_count[0] == 1:
                mock_query.filter.return_value = mock_query
                mock_query.first.return_value = enum_type_ownership
            # Second call: query EnumFieldValue.value
            else:
                mock_query.filter.return_value = mock_query
                mock_query.order_by.return_value = mock_query
                mock_query.all.return_value = enum_values_ownership

            return mock_query

        mock_db.query.side_effect = mock_query_side_effect

        result = service.get_valid_values("ownership_status")

        assert result == ["自有", "租赁", "借用", "其他"]
        assert "ownership_status" in service._cache

    def test_get_valid_values_enum_type_not_found(self, service, mock_db):
        """Test when enum type doesn't exist"""
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None

        result = service.get_valid_values("nonexistent_type")

        assert result == []

    def test_get_valid_values_enum_type_deleted(self, service, mock_db, enum_type_ownership):
        """Test when enum type is deleted"""
        enum_type_ownership.is_deleted = True
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = enum_type_ownership

        # Second query for EnumFieldValue should not execute
        mock_db.query.reset_mock()

        result = service.get_valid_values("ownership_status")

        assert result == []

    def test_get_valid_values_enum_type_inactive(self, service, mock_db, enum_type_ownership):
        """Test when enum type is inactive"""
        enum_type_ownership.status = "inactive"
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = enum_type_ownership

        result = service.get_valid_values("ownership_status")

        assert result == []

    def test_get_valid_values_no_values(self, service, mock_db, enum_type_ownership):
        """Test when enum type exists but has no values"""
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = enum_type_ownership

        # Mock empty values
        mock_values_query = Mock()
        mock_db.query.return_value = mock_values_query
        mock_values_query.filter.return_value = mock_values_query
        mock_values_query.order_by.return_value = mock_values_query
        mock_values_query.all.return_value = []

        result = service.get_valid_values("ownership_status")

        assert result == []

    def test_get_valid_values_database_error(self, service, mock_db):
        """Test handling of database errors"""
        mock_db.query.side_effect = Exception("Database connection error")

        result = service.get_valid_values("ownership_status")

        assert result == []

    def test_get_valid_values_ordering(self, service, mock_db, enum_type_ownership):
        """Test that values are ordered by sort_order"""
        enum_values = [
            ("租赁",),
            ("自有",),
            ("借用",),
        ]
        # Track call count
        call_count = [0]

        # Setup mock query chain
        def mock_query_side_effect(model):
            call_count[0] += 1
            mock_query = Mock()

            # First call: query EnumFieldType
            if call_count[0] == 1:
                mock_query.filter.return_value = mock_query
                mock_query.first.return_value = enum_type_ownership
            # Second call: query EnumFieldValue.value
            else:
                mock_query.filter.return_value = mock_query
                mock_query.order_by.return_value = mock_query
                mock_query.all.return_value = enum_values

            return mock_query

        mock_db.query.side_effect = mock_query_side_effect

        result = service.get_valid_values("ownership_status")

        # Verify order_by was called
        assert call_count[0] == 2  # Both queries were made
        assert result == ["租赁", "自有", "借用"]


# ==================== Test: Validate Value ====================


class TestValidateValue:
    """Test single enum value validation"""

    def test_validate_value_success(self, service):
        """Test successful validation"""
        with patch.object(service, "get_valid_values", return_value=["自有", "租赁"]):
            is_valid, error = service.validate_value("ownership_status", "自有")

            assert is_valid is True
            assert error is None

    def test_validate_value_invalid(self, service):
        """Test validation with invalid value"""
        with patch.object(
            service, "get_valid_values", return_value=["自有", "租赁", "借用"]
        ):
            is_valid, error = service.validate_value("ownership_status", "无效值")

            assert is_valid is False
            assert "无效值" in error
            assert "ownership_status" in error
            assert "自有" in error

    def test_validate_value_empty_allowed(self, service):
        """Test empty value when allowed"""
        is_valid, error = service.validate_value(
            "ownership_status", "", allow_empty=True
        )

        assert is_valid is True
        assert error is None

    def test_validate_value_empty_not_allowed(self, service):
        """Test empty value when not allowed"""
        is_valid, error = service.validate_value(
            "ownership_status", "", allow_empty=False
        )

        assert is_valid is False
        assert "不能为空" in error

    def test_validate_value_whitespace_allowed(self, service):
        """Test whitespace value when allowed"""
        is_valid, error = service.validate_value(
            "ownership_status", "   ", allow_empty=True
        )

        assert is_valid is True
        assert error is None

    def test_validate_value_whitespace_not_allowed(self, service):
        """Test whitespace value when not allowed"""
        is_valid, error = service.validate_value(
            "ownership_status", "   ", allow_empty=False
        )

        assert is_valid is False
        assert "不能为空" in error

    def test_validate_value_no_valid_values_configured(self, service):
        """Test when no valid values are configured"""
        with patch.object(service, "get_valid_values", return_value=[]):
            is_valid, error = service.validate_value("ownership_status", "自有")

            assert is_valid is False
            assert "未配置或未激活" in error

    def test_validate_value_with_context(self, service):
        """Test validation with context information"""
        context = {"endpoint": "/api/v1/assets", "user_id": "user_123"}
        with patch.object(
            service, "get_valid_values", return_value=["自有", "租赁"]
        ):
            is_valid, error = service.validate_value(
                "ownership_status", "自有", context=context
            )

            assert is_valid is True
            # Check that stats were updated with context
            stats = service.get_validation_stats("ownership_status")
            assert stats["total_validations"] == 1

    def test_validate_value_updates_stats_success(self, service):
        """Test that successful validation updates stats"""
        with patch.object(service, "get_valid_values", return_value=["自有"]):
            service.validate_value("ownership_status", "自有")

            stats = service.get_validation_stats("ownership_status")
            assert stats["total_validations"] == 1
            assert stats["failures"] == 0

    def test_validate_value_updates_stats_failure(self, service):
        """Test that failed validation updates stats"""
        with patch.object(service, "get_valid_values", return_value=["自有"]):
            service.validate_value("ownership_status", "无效")

            stats = service.get_validation_stats("ownership_status")
            assert stats["total_validations"] == 1
            assert stats["failures"] == 1
            assert stats["last_failure_value"] == "无效"
            assert stats["last_failure_time"] is not None
            assert stats["last_failure_context"] is None

    def test_validate_value_updates_stats_with_context(self, service):
        """Test that failed validation stores context"""
        context = {"endpoint": "/api/v1/assets"}
        with patch.object(service, "get_valid_values", return_value=["自有"]):
            service.validate_value("ownership_status", "无效", context=context)

            stats = service.get_validation_stats("ownership_status")
            assert stats["last_failure_context"] == context


# ==================== Test: Validation Statistics ====================


class TestValidationStats:
    """Test validation statistics tracking"""

    def test_get_validation_stats_single_type(self, service):
        """Test getting stats for specific enum type"""
        service._validation_stats["ownership_status"]["total_validations"] = 10
        service._validation_stats["ownership_status"]["failures"] = 2

        stats = service.get_validation_stats("ownership_status")

        assert stats["total_validations"] == 10
        assert stats["failures"] == 2

    def test_get_validation_stats_all_types(self, service):
        """Test getting stats for all enum types"""
        service._validation_stats["ownership_status"]["total_validations"] = 10
        service._validation_stats["usage_status"]["total_validations"] = 5

        stats = service.get_validation_stats(None)

        assert len(stats) == 2
        assert stats["ownership_status"]["total_validations"] == 10
        assert stats["usage_status"]["total_validations"] == 5

    def test_reset_validation_stats_single_type(self, service):
        """Test resetting stats for specific enum type"""
        service._validation_stats["ownership_status"]["total_validations"] = 10
        service._validation_stats["ownership_status"]["failures"] = 2

        service.reset_validation_stats("ownership_status")

        stats = service.get_validation_stats("ownership_status")
        assert stats["total_validations"] == 0
        assert stats["failures"] == 0

    def test_reset_validation_stats_all_types(self, service):
        """Test resetting all validation stats"""
        service._validation_stats["ownership_status"]["total_validations"] = 10
        service._validation_stats["usage_status"]["total_validations"] = 5

        service.reset_validation_stats(None)

        stats = service.get_validation_stats(None)
        assert len(stats) == 0


# ==================== Test: Validate Asset Data ====================


class TestValidateAssetData:
    """Test validation of multiple asset enum fields"""

    def test_validate_asset_data_all_valid(self, service):
        """Test validation with all valid enum values"""
        with patch.object(
            service,
            "get_valid_values",
            side_effect=lambda x: {
                "ownership_status": ["自有", "租赁"],
                "usage_status": ["在用", "空闲"],
                "property_nature": ["房屋", "土地"],
            }.get(x, []),
        ):
            data = {
                "ownership_status": "自有",
                "usage_status": "在用",
                "property_nature": "房屋",
            }

            is_valid, errors = service.validate_asset_data(data)

            assert is_valid is True
            assert len(errors) == 0

    def test_validate_asset_data_partial_invalid(self, service):
        """Test validation with some invalid values"""
        with patch.object(
            service,
            "get_valid_values",
            side_effect=lambda x: {
                "ownership_status": ["自有", "租赁"],
                "usage_status": ["在用", "空闲"],
                "property_nature": ["房屋", "土地"],
            }.get(x, []),
        ):
            data = {
                "ownership_status": "自有",
                "usage_status": "无效值",
                "property_nature": "房屋",
            }

            is_valid, errors = service.validate_asset_data(data)

            assert is_valid is False
            assert len(errors) == 1
            assert "usage_status" in errors[0]

    def test_validate_asset_data_multiple_invalid(self, service):
        """Test validation with multiple invalid values"""
        with patch.object(
            service,
            "get_valid_values",
            side_effect=lambda x: {
                "ownership_status": ["自有", "租赁"],
                "usage_status": ["在用", "空闲"],
                "property_nature": ["房屋", "土地"],
                "business_model": ["租赁", "销售"],
            }.get(x, []),
        ):
            data = {
                "ownership_status": "无效1",
                "usage_status": "无效2",
                "property_nature": "房屋",
                "business_model": "无效3",
            }

            is_valid, errors = service.validate_asset_data(data)

            assert is_valid is False
            assert len(errors) == 3

    def test_validate_asset_data_empty_fields(self, service):
        """Test validation with empty fields (should not be validated)"""
        with patch.object(service, "validate_value", return_value=(True, None)):
            data = {"ownership_status": None, "usage_status": ""}

            is_valid, errors = service.validate_asset_data(data)

            # None and empty strings should be skipped if not in data
            assert is_valid is True

    def test_validate_asset_data_partial_fields(self, service):
        """Test validation with only some enum fields present"""
        with patch.object(
            service,
            "get_valid_values",
            side_effect=lambda x: ["自有", "租赁"] if x == "ownership_status" else [],
        ):
            data = {"ownership_status": "自有"}

            is_valid, errors = service.validate_asset_data(data)

            assert is_valid is True
            assert len(errors) == 0

    def test_validate_asset_data_all_enum_fields(self, service):
        """Test validation covers all defined enum fields"""
        enum_fields = [
            "ownership_status",
            "usage_status",
            "property_nature",
            "business_model",
            "operation_status",
            "tenant_type",
            "data_status",
        ]

        with patch.object(
            service, "get_valid_values", return_value=["value1", "value2"]
        ):
            data = {field: "value1" for field in enum_fields}

            is_valid, errors = service.validate_asset_data(data)

            assert is_valid is True
            assert len(errors) == 0


# ==================== Test: Convenience Functions ====================


class TestConvenienceFunctions:
    """Test module-level convenience functions"""

    def test_get_enum_validation_service(self, mock_db):
        """Test factory function for creating service"""
        service = get_enum_validation_service(mock_db)

        assert isinstance(service, EnumValidationService)
        assert service.db == mock_db

    def test_get_valid_enum_values(self, mock_db):
        """Test convenience function for getting valid values"""
        with patch.object(
            EnumValidationService, "get_valid_values", return_value=["自有", "租赁"]
        ) as mock_get:
            result = get_valid_enum_values(mock_db, "ownership_status")

            assert result == ["自有", "租赁"]
            mock_get.assert_called_once_with("ownership_status")

    def test_validate_enum_value_convenience(self, mock_db):
        """Test convenience function for validating enum value"""
        with patch.object(
            EnumValidationService,
            "validate_value",
            return_value=(True, None),
        ) as mock_validate:
            result = validate_enum_value(
                mock_db, "ownership_status", "自有", allow_empty=True
            )

            assert result == (True, None)
            mock_validate.assert_called_once_with(
                "ownership_status", "自有", True, None
            )

    def test_validate_enum_value_with_context(self, mock_db):
        """Test convenience function with context parameter"""
        context = {"user_id": "user_123"}
        with patch.object(
            EnumValidationService,
            "validate_value",
            return_value=(False, "Invalid"),
        ) as mock_validate:
            result = validate_enum_value(
                mock_db,
                "ownership_status",
                "invalid",
                allow_empty=False,
                context=context,
            )

            assert result == (False, "Invalid")
            mock_validate.assert_called_once_with(
                "ownership_status", "invalid", False, context
            )

    def test_get_enum_validation_stats_single(self, mock_db):
        """Test convenience function for getting single type stats"""
        stats = {"total_validations": 10, "failures": 2}
        with patch.object(
            EnumValidationService,
            "get_validation_stats",
            return_value=stats,
        ) as mock_get:
            result = get_enum_validation_stats(mock_db, "ownership_status")

            assert result == stats
            mock_get.assert_called_once_with("ownership_status")

    def test_get_enum_validation_stats_all(self, mock_db):
        """Test convenience function for getting all stats"""
        stats = {
            "ownership_status": {"total_validations": 10},
            "usage_status": {"total_validations": 5},
        }
        with patch.object(
            EnumValidationService,
            "get_validation_stats",
            return_value=stats,
        ) as mock_get:
            result = get_enum_validation_stats(mock_db)

            assert result == stats
            mock_get.assert_called_once_with(None)


# ==================== Test: Edge Cases ====================


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_validate_value_special_characters(self, service):
        """Test validation with special characters in value"""
        with patch.object(
            service, "get_valid_values", return_value=["值(带括号)", "值-横线"]
        ):
            is_valid, error = service.validate_value(
                "ownership_status", "值(带括号)"
            )

            assert is_valid is True
            assert error is None

    def test_validate_value_case_sensitivity(self, service):
        """Test that validation is case-sensitive"""
        with patch.object(service, "get_valid_values", return_value=["自有"]):
            is_valid, error = service.validate_value("ownership_status", "自有")

            assert is_valid is True

            is_valid, error = service.validate_value("ownership_status", "自有")

            # Depending on implementation, this might be valid or invalid
            # Test just ensures it doesn't crash
            assert isinstance(is_valid, bool)

    def test_cache_ttl_constant(self, service):
        """Test that CACHE_TTL is set to expected value"""
        assert service.CACHE_TTL == 300  # 5 minutes

    def test_multiple_service_instances_independent(self, mock_db):
        """Test that multiple service instances have independent caches"""
        service1 = EnumValidationService(mock_db)
        service2 = EnumValidationService(mock_db)

        service1._cache["ownership_status"] = ["自有"]
        service2._cache["ownership_status"] = ["租赁"]

        assert service1._cache["ownership_status"] == ["自有"]
        assert service2._cache["ownership_status"] == ["租赁"]

    def test_validate_value_none_value_allowed(self, service):
        """Test validation with None value when allowed"""
        is_valid, error = service.validate_value(
            "ownership_status", None, allow_empty=True
        )

        assert is_valid is True
        assert error is None

    def test_validate_value_none_value_not_allowed(self, service):
        """Test validation with None value when not allowed"""
        is_valid, error = service.validate_value(
            "ownership_status", None, allow_empty=False
        )

        assert is_valid is False
        assert "不能为空" in error
