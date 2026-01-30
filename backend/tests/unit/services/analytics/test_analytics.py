"""
Comprehensive Unit Tests for Analytics Services

Tests for:
1. AnalyticsService - Comprehensive analytics and trend analysis
2. AreaService - Area calculations and aggregations

Coverage:
- Data aggregation logic
- Area calculations
- Statistical computations
- Report generation
- Data filtering and grouping
- Edge cases (empty data, null values)
- Performance with large datasets
"""

from unittest.mock import MagicMock, patch

import pytest

from src.services.analytics.analytics_service import AnalyticsService
from src.services.analytics.area_service import AreaCalculationError, AreaService

# =============================================================================
# Fixtures
# =============================================================================




@pytest.fixture
def analytics_service(mock_db):
    """Create AnalyticsService instance"""
    return AnalyticsService(mock_db)


@pytest.fixture
def area_service(mock_db):
    """Create AreaService instance"""
    return AreaService(mock_db)


@pytest.fixture
def sample_assets():
    """Create sample asset data for testing"""
    return [
        MagicMock(
            id=1,
            land_area=500.0,
            rentable_area=300.0,
            rented_area=240.0,
            unrented_area=60.0,
            non_commercial_area=50.0,
            property_nature="商业",
            business_category="零售",
            usage_status="已出租",
            data_status="正常",
        ),
        MagicMock(
            id=2,
            land_area=800.0,
            rentable_area=500.0,
            rented_area=400.0,
            unrented_area=100.0,
            non_commercial_area=80.0,
            property_nature="住宅",
            business_category="租赁",
            usage_status="已出租",
            data_status="正常",
        ),
        MagicMock(
            id=3,
            land_area=600.0,
            rentable_area=400.0,
            rented_area=0.0,
            unrented_area=400.0,
            non_commercial_area=60.0,
            property_nature="办公",
            business_category="写字楼",
            usage_status="空置",
            data_status="正常",
        ),
    ]


@pytest.fixture
def large_dataset_assets():
    """Create large dataset for performance testing"""
    assets = []
    for i in range(1000):
        assets.append(
            MagicMock(
                id=i,
                land_area=500.0 + i,
                rentable_area=300.0 + i,
                rented_area=200.0 + i,
                unrented_area=100.0,
                non_commercial_area=50.0,
                property_nature="商业" if i % 2 == 0 else "住宅",
                business_category="零售" if i % 3 == 0 else "租赁",
                usage_status="已出租" if i % 2 == 0 else "空置",
                data_status="正常",
            )
        )
    return assets


# =============================================================================
# AnalyticsService Tests
# =============================================================================


class TestAnalyticsServiceInitialization:
    """Tests for AnalyticsService initialization"""

    def test_init(self, mock_db):
        """Test service initialization"""
        service = AnalyticsService(mock_db)
        assert service.db == mock_db
        assert service.cache is not None
        assert service.response_handler is not None


class TestAnalyticsServiceFilterValidation:
    """Tests for filter validation"""

    def test_validate_filters_empty(self, analytics_service):
        """Test empty filter validation"""
        result = analytics_service._validate_filters({})
        assert result == {}

    def test_validate_filters_with_include_deleted(self, analytics_service):
        """Test filter with include_deleted"""
        result = analytics_service._validate_filters({"include_deleted": True})
        assert result["include_deleted"] is True

    def test_validate_filters_with_include_deleted_false(self, analytics_service):
        """Test filter with include_deleted=False"""
        result = analytics_service._validate_filters({"include_deleted": False})
        assert result["include_deleted"] is False

    def test_validate_filters_with_dates(self, analytics_service):
        """Test filter with date range"""
        filters = {
            "include_deleted": False,
            "date_from": "2024-01-01",
            "date_to": "2024-12-31",
        }
        result = analytics_service._validate_filters(filters)
        assert result["include_deleted"] is False
        assert result["date_from"] == "2024-01-01"
        assert result["date_to"] == "2024-12-31"

    def test_validate_filters_ignores_unknown_fields(self, analytics_service):
        """Test filter ignores unknown fields"""
        result = analytics_service._validate_filters({"unknown_field": "value"})
        assert result == {}


class TestAnalyticsServiceCacheManagement:
    """Tests for cache management"""

    def test_generate_cache_key_consistency(self, analytics_service):
        """Test cache key generation is consistent"""
        filters1 = {"include_deleted": True}
        filters2 = {"include_deleted": True}

        key1 = analytics_service._generate_cache_key(filters1)
        key2 = analytics_service._generate_cache_key(filters2)

        assert key1 == key2

    def test_generate_cache_key_uniqueness(self, analytics_service):
        """Test cache key generation is unique for different filters"""
        filters1 = {"include_deleted": True}
        filters2 = {"include_deleted": False}

        key1 = analytics_service._generate_cache_key(filters1)
        key2 = analytics_service._generate_cache_key(filters2)

        assert key1 != key2

    def test_generate_cache_key_format(self, analytics_service):
        """Test cache key format"""
        filters = {"include_deleted": True}
        key = analytics_service._generate_cache_key(filters)

        assert key.startswith("analytics:")
        assert len(key.split(":")) == 2

    def test_clear_cache_success(self, analytics_service):
        """Test successful cache clearing"""
        analytics_service.cache.clear = MagicMock(return_value=True)

        result = analytics_service.clear_cache()

        assert result["status"] == "success"
        assert result["cleared_keys"] == 1
        assert "timestamp" in result

    def test_clear_cache_failure(self, analytics_service):
        """Test cache clearing with exception"""
        analytics_service.cache.clear = MagicMock(side_effect=Exception("Cache error"))

        result = analytics_service.clear_cache()

        assert result["status"] == "failed"
        assert result["cleared_keys"] == 0
        assert "error" in result
        assert "Cache error" in result["error"]
        assert "timestamp" in result

    def test_get_cache_stats(self, analytics_service):
        """Test getting cache statistics"""
        mock_stats = {"hits": 100, "misses": 10, "keys": 5}
        analytics_service.cache.get_stats = MagicMock(return_value=mock_stats)

        result = analytics_service.get_cache_stats()

        assert result["cache_type"] == "analytics_cache"
        assert result["stats"] == mock_stats
        assert "timestamp" in result

    def test_get_cache_stats_no_stats_method(self, analytics_service):
        """Test cache stats when get_stats method returns empty dict"""
        # Mock cache without get_stats returning data
        analytics_service.cache.get_stats = MagicMock(return_value={})

        result = analytics_service.get_cache_stats()

        assert result["cache_type"] == "analytics_cache"
        assert result["stats"] == {}


class TestAnalyticsServiceComprehensiveAnalytics:
    """Tests for comprehensive analytics calculation"""

    def test_get_comprehensive_analytics_cache_hit(self, analytics_service):
        """Test analytics retrieval from cache"""
        mock_cache_data = {
            "total_assets": 100,
            "timestamp": "2024-01-01T00:00:00",
        }
        analytics_service.cache.get = MagicMock(return_value=mock_cache_data)

        result = analytics_service.get_comprehensive_analytics(
            filters={}, should_use_cache=True
        )

        assert result == mock_cache_data

    @patch("src.services.analytics.area_service.AreaService")
    @patch("src.services.analytics.occupancy_service.OccupancyService")
    def test_get_comprehensive_analytics_cache_miss(
        self, mock_occupancy_cls, mock_area_cls, analytics_service
    ):
        """Test analytics calculation when cache miss"""
        analytics_service.cache.get = MagicMock(return_value=None)

        # Mock AreaService
        mock_area_service = MagicMock()
        mock_area_service.calculate_summary_with_aggregation.return_value = {
            "total_assets": 10,
            "total_land_area": 5000.0,
        }
        mock_area_cls.return_value = mock_area_service

        # Mock OccupancyService
        mock_occupancy_service = MagicMock()
        mock_occupancy_service.calculate_with_aggregation.return_value = {
            "overall_rate": 80.0,
        }
        mock_occupancy_cls.return_value = mock_occupancy_service

        # Mock database query
        mock_assets = [MagicMock(data_status="正常")]
        analytics_service.db.query.return_value.filter.return_value.all.return_value = (
            mock_assets
        )

        result = analytics_service.get_comprehensive_analytics(
            filters={}, should_use_cache=True
        )

        assert "total_assets" in result
        assert "timestamp" in result
        assert "area_summary" in result
        assert "occupancy_rate" in result

    @patch("src.services.analytics.area_service.AreaService")
    @patch("src.services.analytics.occupancy_service.OccupancyService")
    def test_get_comprehensive_analytics_with_filters(
        self, mock_occupancy_cls, mock_area_cls, analytics_service
    ):
        """Test analytics with filters"""
        analytics_service.cache.get = MagicMock(return_value=None)

        mock_area_service = MagicMock()
        mock_area_service.calculate_summary_with_aggregation.return_value = {
            "total_assets": 5,
        }
        mock_area_cls.return_value = mock_area_service

        mock_occupancy_service = MagicMock()
        mock_occupancy_service.calculate_with_aggregation.return_value = {
            "overall_rate": 75.0,
        }
        mock_occupancy_cls.return_value = mock_occupancy_service

        mock_assets = [MagicMock(data_status="正常")]
        analytics_service.db.query.return_value.filter.return_value.all.return_value = (
            mock_assets
        )

        filters = {"include_deleted": False, "date_from": "2024-01-01"}
        result = analytics_service.get_comprehensive_analytics(
            filters=filters, should_use_cache=False
        )

        assert "total_assets" in result

    def test_get_comprehensive_analytics_with_deleted_assets(self, analytics_service):
        """Test analytics including deleted assets"""
        analytics_service.cache.get = MagicMock(return_value=None)

        with patch("src.services.analytics.area_service.AreaService") as mock_area_cls:
            mock_area_service = MagicMock()
            mock_area_service.calculate_summary_with_aggregation.return_value = {
                "total_assets": 15,
            }
            mock_area_cls.return_value = mock_area_service

            with patch(
                "src.services.analytics.occupancy_service.OccupancyService"
            ) as mock_occupancy_cls:
                mock_occupancy_service = MagicMock()
                mock_occupancy_service.calculate_with_aggregation.return_value = {
                    "overall_rate": 70.0,
                }
                mock_occupancy_cls.return_value = mock_occupancy_service

                # Mock query to return all assets (no filtering)
                mock_assets = [
                    MagicMock(data_status="正常"),
                    MagicMock(data_status="已删除"),
                ]
                analytics_service.db.query.return_value.all.return_value = mock_assets

                filters = {"include_deleted": True}
                result = analytics_service.get_comprehensive_analytics(
                    filters=filters, should_use_cache=False
                )

                assert result["total_assets"] == 2


class TestAnalyticsServiceTrendCalculation:
    """Tests for trend calculation"""

    def test_calculate_occupancy_trend_monthly(self, analytics_service):
        """Test monthly occupancy trend calculation"""
        mock_assets = [MagicMock(data_status="正常")]
        analytics_service.db.query.return_value.filter.return_value.all.return_value = (
            mock_assets
        )

        result = analytics_service.calculate_trend(
            trend_type="occupancy", time_dimension="monthly", filters={}
        )

        assert isinstance(result, list)
        assert len(result) > 0
        assert "period" in result[0]
        assert "occupancy_rate" in result[0]
        assert "rented_area" in result[0]

    def test_calculate_area_trend_monthly(self, analytics_service):
        """Test monthly area trend calculation"""
        mock_assets = [MagicMock(data_status="正常")]
        analytics_service.db.query.return_value.filter.return_value.all.return_value = (
            mock_assets
        )

        result = analytics_service.calculate_trend(
            trend_type="area", time_dimension="monthly", filters={}
        )

        assert isinstance(result, list)
        assert len(result) > 0
        assert "period" in result[0]
        assert "total_land_area" in result[0]
        assert "total_rentable_area" in result[0]

    def test_calculate_trend_unknown_type(self, analytics_service):
        """Test trend calculation with unknown type"""
        mock_assets = [MagicMock(data_status="正常")]
        analytics_service.db.query.return_value.filter.return_value.all.return_value = (
            mock_assets
        )

        result = analytics_service.calculate_trend(
            trend_type="unknown_type", time_dimension="monthly", filters={}
        )

        assert result == []

    def test_calculate_trend_with_filters(self, analytics_service):
        """Test trend calculation with filters"""
        mock_assets = [MagicMock(data_status="正常")]
        analytics_service.db.query.return_value.filter.return_value.all.return_value = (
            mock_assets
        )

        filters = {"date_from": "2024-01-01"}
        result = analytics_service.calculate_trend(
            trend_type="occupancy", time_dimension="monthly", filters=filters
        )

        assert isinstance(result, list)


class TestAnalyticsServiceDistributionCalculation:
    """Tests for distribution calculation"""

    def test_calculate_distribution_by_property_nature(self, analytics_service):
        """Test distribution by property nature"""
        mock_assets = [
            MagicMock(property_nature="商业", rentable_area=1000, data_status="正常"),
            MagicMock(property_nature="住宅", rentable_area=500, data_status="正常"),
            MagicMock(property_nature="商业", rentable_area=800, data_status="正常"),
        ]
        analytics_service.db.query.return_value.filter.return_value.all.return_value = (
            mock_assets
        )

        result = analytics_service.calculate_distribution(
            distribution_type="property_nature", filters={}
        )

        assert result["distribution_type"] == "property_nature"
        assert "data" in result
        assert result["total"] == 2
        assert result["data"]["商业"]["count"] == 2
        assert result["data"]["商业"]["area"] == 1800
        assert result["data"]["住宅"]["count"] == 1

    def test_calculate_distribution_by_business_category(self, analytics_service):
        """Test distribution by business category"""
        mock_assets = [
            MagicMock(business_category="零售", rentable_area=1000, data_status="正常"),
            MagicMock(business_category="办公", rentable_area=500, data_status="正常"),
            MagicMock(business_category="零售", rentable_area=800, data_status="正常"),
        ]
        analytics_service.db.query.return_value.filter.return_value.all.return_value = (
            mock_assets
        )

        result = analytics_service.calculate_distribution(
            distribution_type="business_category", filters={}
        )

        assert result["distribution_type"] == "business_category"
        assert result["data"]["零售"]["count"] == 2
        assert result["data"]["零售"]["area"] == 1800

    def test_calculate_distribution_with_null_values(self, analytics_service):
        """Test distribution with null values"""
        mock_assets = [
            MagicMock(property_nature="商业", rentable_area=1000, data_status="正常"),
            MagicMock(property_nature=None, rentable_area=500, data_status="正常"),
        ]
        analytics_service.db.query.return_value.filter.return_value.all.return_value = (
            mock_assets
        )

        result = analytics_service.calculate_distribution(
            distribution_type="property_nature", filters={}
        )

        # Should handle null values by converting to string "None"
        assert "data" in result


# =============================================================================
# AreaService Tests
# =============================================================================


class TestAreaServiceInitialization:
    """Tests for AreaService initialization"""

    def test_init(self, mock_db):
        """Test service initialization"""
        service = AreaService(mock_db)
        assert service.db == mock_db


class TestAreaServiceAggregationCalculation:
    """Tests for area aggregation calculation"""

    def test_calculate_summary_with_aggregation_basic(self, area_service, mock_db):
        """Test basic area aggregation"""
        mock_result = MagicMock()
        mock_result.total_assets = 10
        mock_result.total_land_area = 5000.0
        mock_result.total_rentable_area = 3000.0
        mock_result.total_rented_area = 2400.0
        mock_result.total_non_commercial_area = 500.0
        mock_result.assets_with_area_data = 8

        mock_query = MagicMock()
        mock_query.with_entities.return_value.first.return_value = mock_result
        mock_db.query.return_value = mock_query

        result = area_service.calculate_summary_with_aggregation(filters=None)

        assert result["total_assets"] == 10
        assert result["total_land_area"] == 5000.0
        assert result["total_rentable_area"] == 3000.0
        assert result["total_rented_area"] == 2400.0
        assert result["total_unrented_area"] == 600.0
        assert result["total_non_commercial_area"] == 500.0
        assert result["assets_with_area_data"] == 8
        assert result["overall_occupancy_rate"] == 80.0
        assert result["calculation_method"] == "aggregation"

    def test_calculate_summary_with_aggregation_with_filters(
        self, area_service, mock_db
    ):
        """Test aggregation with filters"""
        mock_result = MagicMock()
        mock_result.total_assets = 5
        mock_result.total_land_area = 2500.0
        mock_result.total_rentable_area = 1500.0
        mock_result.total_rented_area = 1200.0
        mock_result.total_non_commercial_area = 250.0
        mock_result.assets_with_area_data = 4

        mock_query = MagicMock()
        mock_filtered = MagicMock()
        mock_query.filter.return_value = mock_filtered
        mock_filtered.with_entities.return_value.first.return_value = mock_result
        mock_db.query.return_value = mock_query

        filters = {"data_status": "正常"}
        result = area_service.calculate_summary_with_aggregation(filters=filters)

        assert result["total_assets"] == 5
        mock_query.filter.assert_called_once()

    def test_calculate_summary_with_aggregation_zero_values(
        self, area_service, mock_db
    ):
        """Test aggregation with all zero values"""
        mock_result = MagicMock()
        mock_result.total_assets = 0
        mock_result.total_land_area = 0.0
        mock_result.total_rentable_area = 0.0
        mock_result.total_rented_area = 0.0
        mock_result.total_non_commercial_area = 0.0
        mock_result.assets_with_area_data = 0

        mock_query = MagicMock()
        mock_query.with_entities.return_value.first.return_value = mock_result
        mock_db.query.return_value = mock_query

        result = area_service.calculate_summary_with_aggregation(filters=None)

        assert result["total_assets"] == 0
        assert result["overall_occupancy_rate"] == 0.0
        assert result["total_unrented_area"] == 0.0

    def test_calculate_summary_with_aggregation_null_result(
        self, area_service, mock_db
    ):
        """Test aggregation when result is None"""
        mock_query = MagicMock()
        mock_query.with_entities.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        result = area_service.calculate_summary_with_aggregation(filters=None)

        assert result["total_assets"] == 0
        assert result["overall_occupancy_rate"] == 0.0
        assert result["calculation_method"] == "aggregation"

    def test_calculate_summary_with_aggregation_occupancy_rate_division_by_zero(
        self, area_service, mock_db
    ):
        """Test occupancy rate calculation handles division by zero"""
        mock_result = MagicMock()
        mock_result.total_assets = 10
        mock_result.total_land_area = 5000.0
        mock_result.total_rentable_area = 0.0  # Zero rentable area
        mock_result.total_rented_area = 0.0
        mock_result.total_non_commercial_area = 500.0
        mock_result.assets_with_area_data = 8

        mock_query = MagicMock()
        mock_query.with_entities.return_value.first.return_value = mock_result
        mock_db.query.return_value = mock_query

        result = area_service.calculate_summary_with_aggregation(filters=None)

        assert result["overall_occupancy_rate"] == 0.0

    def test_calculate_summary_with_aggregation_unrented_area_calculation(
        self, area_service, mock_db
    ):
        """Test unrented area is calculated correctly"""
        mock_result = MagicMock()
        mock_result.total_assets = 10
        mock_result.total_land_area = 5000.0
        mock_result.total_rentable_area = 3000.0
        mock_result.total_rented_area = 3500.0  # More than rentable (edge case)
        mock_result.total_non_commercial_area = 500.0
        mock_result.assets_with_area_area = 8

        mock_query = MagicMock()
        mock_query.with_entities.return_value.first.return_value = mock_result
        mock_db.query.return_value = mock_query

        result = area_service.calculate_summary_with_aggregation(filters=None)

        # Unrented should be max(0, rentable - rented) = max(0, 3000 - 3500) = 0
        assert result["total_unrented_area"] == 0.0

    def test_calculate_summary_with_aggregation_fallback_to_memory(
        self, area_service, mock_db
    ):
        """Test fallback to memory calculation on exception"""
        mock_query = MagicMock()
        mock_query.with_entities.side_effect = Exception("Database error")
        mock_db.query.return_value = mock_query

        with patch.object(
            area_service,
            "_calculate_summary_in_memory",
            return_value={
                "total_assets": 10,
                "overall_occupancy_rate": 75.0,
                "calculation_method": "memory",
            },
        ) as mock_memory:
            result = area_service.calculate_summary_with_aggregation(filters=None)

            mock_memory.assert_called_once_with(None)
            assert result["overall_occupancy_rate"] == 75.0
            assert result["calculation_method"] == "memory_fallback"


class TestAreaServiceMemoryCalculation:
    """Tests for memory-based calculation"""

    @patch("src.services.analytics.area_service.asset_crud")
    def test_calculate_summary_in_memory_basic(self, mock_crud, area_service):
        """Test basic memory calculation"""
        mock_assets = [
            MagicMock(
                land_area=500.0,
                rentable_area=300.0,
                rented_area=240.0,
                unrented_area=60.0,
                non_commercial_area=50.0,
            ),
            MagicMock(
                land_area=500.0,
                rentable_area=200.0,
                rented_area=160.0,
                unrented_area=40.0,
                non_commercial_area=30.0,
            ),
        ]
        mock_crud.get_multi_with_search.side_effect = [
            (mock_assets, None),
            ([], None),
        ]

        result = area_service._calculate_summary_in_memory(filters=None)

        assert result["total_assets"] == 2
        assert result["total_land_area"] == 1000.0
        assert result["total_rentable_area"] == 500.0
        assert result["total_rented_area"] == 400.0
        assert result["total_unrented_area"] == 100.0
        assert result["total_non_commercial_area"] == 80.0
        assert result["assets_with_area_data"] == 2
        assert result["overall_occupancy_rate"] == 80.0

    @patch("src.services.analytics.area_service.asset_crud")
    def test_calculate_summary_in_memory_partial_data(self, mock_crud, area_service):
        """Test memory calculation with partial missing data"""
        mock_assets = [
            MagicMock(
                land_area=500.0,
                rentable_area=300.0,
                rented_area=240.0,
                unrented_area=None,
                non_commercial_area=None,
            ),
            MagicMock(
                land_area=None,
                rentable_area=200.0,
                rented_area=160.0,
                unrented_area=40.0,
                non_commercial_area=30.0,
            ),
        ]
        mock_crud.get_multi_with_search.side_effect = [
            (mock_assets, None),
            ([], None),
        ]

        result = area_service._calculate_summary_in_memory(filters=None)

        assert result["total_assets"] == 2
        assert result["total_land_area"] == 500.0
        assert result["assets_with_area_data"] == 1
        assert result["total_unrented_area"] == 40.0
        assert result["total_non_commercial_area"] == 30.0

    @patch("src.services.analytics.area_service.asset_crud")
    def test_calculate_summary_in_memory_all_null_values(self, mock_crud, area_service):
        """Test memory calculation with all null values"""
        mock_assets = [
            MagicMock(
                land_area=None,
                rentable_area=None,
                rented_area=None,
                unrented_area=None,
                non_commercial_area=None,
            )
        ]
        mock_crud.get_multi_with_search.side_effect = [
            (mock_assets, None),
            ([], None),
        ]

        result = area_service._calculate_summary_in_memory(filters=None)

        assert result["total_assets"] == 1
        assert result["total_land_area"] == 0.0
        assert result["assets_with_area_data"] == 0
        assert result["overall_occupancy_rate"] == 0.0

    @patch("src.services.analytics.area_service.asset_crud")
    def test_calculate_summary_in_memory_zero_rentable_area(
        self, mock_crud, area_service
    ):
        """Test memory calculation with zero rentable area"""
        mock_assets = [
            MagicMock(
                land_area=500.0,
                rentable_area=0.0,
                rented_area=0.0,
                unrented_area=0.0,
                non_commercial_area=50.0,
            )
        ]
        mock_crud.get_multi_with_search.side_effect = [
            (mock_assets, None),
            ([], None),
        ]

        result = area_service._calculate_summary_in_memory(filters=None)

        assert result["overall_occupancy_rate"] == 0.0

    @patch("src.services.analytics.area_service.asset_crud")
    def test_calculate_summary_in_memory_rounding(self, mock_crud, area_service):
        """Test memory calculation rounds to 2 decimal places"""
        mock_assets = [
            MagicMock(
                land_area=500.123,
                rentable_area=300.456,
                rented_area=240.789,
                unrented_area=60.0,
                non_commercial_area=50.999,
            )
        ]
        mock_crud.get_multi_with_search.side_effect = [
            (mock_assets, None),
            ([], None),
        ]

        result = area_service._calculate_summary_in_memory(filters=None)

        assert result["total_land_area"] == 500.12
        assert result["total_rentable_area"] == 300.46
        assert result["total_rented_area"] == 240.79
        assert result["total_non_commercial_area"] == 51.0

    @patch("src.services.analytics.area_service.asset_crud")
    def test_calculate_summary_in_memory_pagination(self, mock_crud, area_service):
        """Test memory calculation handles pagination correctly"""
        # Create 1500 assets to test pagination (batch_size=1000)
        mock_assets_batch1 = [MagicMock(land_area=100.0, rentable_area=50.0)] * 1000
        mock_assets_batch2 = [MagicMock(land_area=100.0, rentable_area=50.0)] * 500

        mock_crud.get_multi_with_search.side_effect = [
            (mock_assets_batch1, None),
            (mock_assets_batch2, None),
            ([], None),
        ]

        result = area_service._calculate_summary_in_memory(filters=None)

        assert result["total_assets"] == 1500
        assert result["total_land_area"] == 150000.0
        assert result["total_rentable_area"] == 75000.0

    @patch("src.services.analytics.area_service.asset_crud")
    def test_calculate_summary_in_memory_with_filters(self, mock_crud, area_service):
        """Test memory calculation with filters"""
        mock_assets = [
            MagicMock(
                land_area=500.0,
                rentable_area=300.0,
                rented_area=240.0,
                unrented_area=60.0,
                non_commercial_area=50.0,
            )
        ]
        mock_crud.get_multi_with_search.side_effect = [
            (mock_assets, None),
            ([], None),
        ]

        filters = {"data_status": "正常"}
        result = area_service._calculate_summary_in_memory(filters=filters)

        mock_crud.get_multi_with_search.assert_called_with(
            db=area_service.db, skip=0, limit=1000, filters=filters
        )
        assert result["total_assets"] == 1

    def test_calculate_summary_in_memory_error(self, area_service):
        """Test memory calculation raises error on exception"""
        with patch(
            "src.services.analytics.area_service.asset_crud.get_multi_with_search",
            side_effect=Exception("CRUD error"),
        ):
            with pytest.raises(AreaCalculationError) as excinfo:
                area_service._calculate_summary_in_memory(filters=None)

            assert "面积汇总计算失败" in str(excinfo.value)


class TestAreaServiceEdgeCases:
    """Tests for edge cases and error handling"""

    def test_aggregation_with_negative_values(self, area_service, mock_db):
        """Test aggregation handles negative values (edge case)"""
        mock_result = MagicMock()
        mock_result.total_assets = 5
        mock_result.total_land_area = 5000.0
        mock_result.total_rentable_area = 3000.0
        mock_result.total_rented_area = -100.0  # Negative (edge case)
        mock_result.total_non_commercial_area = 500.0
        mock_result.assets_with_area_data = 4

        mock_query = MagicMock()
        mock_query.with_entities.return_value.first.return_value = mock_result
        mock_db.query.return_value = mock_query

        result = area_service.calculate_summary_with_aggregation(filters=None)

        # Unrented = max(0, 3000 - (-100)) = max(0, 3100) = 3100
        assert result["total_unrented_area"] == 3100.0

    @patch("src.services.analytics.area_service.asset_crud")
    def test_memory_calculation_with_negative_values(self, mock_crud, area_service):
        """Test memory calculation handles negative values"""
        mock_assets = [
            MagicMock(
                land_area=500.0,
                rentable_area=300.0,
                rented_area=-100.0,  # Negative (edge case)
                unrented_area=60.0,
                non_commercial_area=50.0,
            )
        ]
        mock_crud.get_multi_with_search.side_effect = [
            (mock_assets, None),
            ([], None),
        ]

        result = area_service._calculate_summary_in_memory(filters=None)

        # Should still calculate, though values may be unusual
        assert "total_rented_area" in result


# =============================================================================
# Integration Tests (Service Interactions)
# =============================================================================


class TestServiceIntegration:
    """Tests for service interactions and complex scenarios"""

    @patch("src.services.analytics.area_service.AreaService")
    @patch("src.services.analytics.occupancy_service.OccupancyService")
    def test_analytics_service_integration_with_area_and_occupancy(
        self, mock_occupancy_cls, mock_area_cls, analytics_service
    ):
        """Test AnalyticsService integrates correctly with Area and Occupancy services"""
        analytics_service.cache.get = MagicMock(return_value=None)

        # Mock AreaService
        mock_area_service = MagicMock()
        mock_area_service.calculate_summary_with_aggregation.return_value = {
            "total_assets": 100,
            "total_land_area": 50000.0,
            "total_rentable_area": 30000.0,
            "total_rented_area": 24000.0,
            "overall_occupancy_rate": 80.0,
        }
        mock_area_cls.return_value = mock_area_service

        # Mock OccupancyService
        mock_occupancy_service = MagicMock()
        mock_occupancy_service.calculate_with_aggregation.return_value = {
            "overall_rate": 80.0,
            "total_rentable_area": 30000.0,
            "total_rented_area": 24000.0,
        }
        mock_occupancy_cls.return_value = mock_occupancy_service

        # Mock database query
        mock_assets = [MagicMock(data_status="正常")]
        analytics_service.db.query.return_value.filter.return_value.all.return_value = (
            mock_assets
        )

        result = analytics_service.get_comprehensive_analytics(
            filters={}, should_use_cache=True
        )

        # Verify integration
        mock_area_service.calculate_summary_with_aggregation.assert_called_once()
        mock_occupancy_service.calculate_with_aggregation.assert_called_once()
        assert result["area_summary"]["overall_occupancy_rate"] == 80.0
        assert result["occupancy_rate"]["overall_rate"] == 80.0

    def test_cache_set_after_calculation(self, analytics_service):
        """Test cache is set after calculation"""
        analytics_service.cache.get = MagicMock(return_value=None)
        analytics_service.cache.set = MagicMock()

        with patch("src.services.analytics.area_service.AreaService") as mock_area_cls:
            mock_area_service = MagicMock()
            mock_area_service.calculate_summary_with_aggregation.return_value = {
                "total_assets": 10
            }
            mock_area_cls.return_value = mock_area_service

            with patch(
                "src.services.analytics.occupancy_service.OccupancyService"
            ) as mock_occupancy_cls:
                mock_occupancy_service = MagicMock()
                mock_occupancy_service.calculate_with_aggregation.return_value = {
                    "overall_rate": 80.0
                }
                mock_occupancy_cls.return_value = mock_occupancy_service

                mock_assets = [MagicMock(data_status="正常")]
                analytics_service.db.query.return_value.filter.return_value.all.return_value = mock_assets

                result = analytics_service.get_comprehensive_analytics(
                    filters={}, should_use_cache=True
                )

                # Verify cache.set was called
                assert analytics_service.cache.set.called
                call_args = analytics_service.cache.set.call_args
                assert call_args[0][1] == result  # Second arg is the result
                assert call_args[1]["ttl"] == 3600  # TTL is 1 hour


# =============================================================================
# Performance Tests
# =============================================================================


class TestPerformance:
    """Tests for performance with large datasets"""

    @patch("src.services.analytics.area_service.asset_crud")
    def test_area_service_large_dataset_memory_calculation(
        self, mock_crud, area_service
    ):
        """Test area service handles large dataset efficiently"""
        # Create large dataset
        large_batch = [
            MagicMock(
                land_area=500.0,
                rentable_area=300.0,
                rented_area=240.0,
                unrented_area=60.0,
                non_commercial_area=50.0,
            )
            for _ in range(1000)
        ]

        mock_crud.get_multi_with_search.side_effect = [
            (large_batch, None),
            ([], None),
        ]

        import time

        start_time = time.time()
        result = area_service._calculate_summary_in_memory(filters=None)
        end_time = time.time()

        assert result["total_assets"] == 1000
        assert result["total_land_area"] == 500000.0
        # Should complete in reasonable time (< 1 second for 1000 records)
        assert end_time - start_time < 1.0

    def test_analytics_service_large_dataset_distribution(self, analytics_service):
        """Test analytics service distribution with large dataset"""
        # Create large dataset
        large_dataset = []
        for i in range(1000):
            large_dataset.append(
                MagicMock(
                    property_nature="商业" if i % 2 == 0 else "住宅",
                    rentable_area=100.0 + i,
                    data_status="正常",
                )
            )

        analytics_service.db.query.return_value.filter.return_value.all.return_value = (
            large_dataset
        )

        import time

        start_time = time.time()
        result = analytics_service.calculate_distribution(
            distribution_type="property_nature", filters={}
        )
        end_time = time.time()

        assert result["total"] == 2
        assert result["data"]["商业"]["count"] == 500
        assert result["data"]["住宅"]["count"] == 500
        # Should complete in reasonable time
        assert end_time - start_time < 1.0


# =============================================================================
# Test Count Summary
# =============================================================================

"""
Total Test Count: 40

AnalyticsService Tests: 17
- Initialization: 1
- Filter Validation: 5
- Cache Management: 5
- Comprehensive Analytics: 3
- Trend Calculation: 4
- Distribution Calculation: 3

AreaService Tests: 18
- Initialization: 1
- Aggregation Calculation: 7
- Memory Calculation: 8
- Edge Cases: 2

Integration Tests: 2

Performance Tests: 2

Test Categories:
- Unit tests: 36
- Integration tests: 2
- Performance tests: 2
- Edge case tests: 8
- Null/empty data tests: 6
"""
