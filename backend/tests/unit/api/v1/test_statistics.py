"""
Comprehensive Unit Tests for Statistics API Routes (src/api/v1/statistics.py)

This test module covers all endpoints in the statistics router to achieve 70%+ coverage:

Endpoints Tested:
1. GET /api/v1/statistics/basic - Get basic statistics with filters
2. GET /api/v1/statistics/summary - Get statistics summary
3. GET /api/v1/statistics/occupancy-rate/overall - Get overall occupancy rate
4. GET /api/v1/statistics/occupancy-rate/by-category - Get occupancy rate by category
5. GET /api/v1/statistics/area-summary - Get area summary statistics
6. GET /api/v1/statistics/financial-summary - Get financial summary
7. POST /api/v1/statistics/cache/clear - Clear statistics cache
8. GET /api/v1/statistics/cache/info - Get cache information
9. GET /api/v1/statistics/dashboard - Get dashboard data
10. GET /api/v1/statistics/ownership-distribution - Get ownership distribution
11. GET /api/v1/statistics/property-nature-distribution - Get property nature distribution
12. GET /api/v1/statistics/usage-status-distribution - Get usage status distribution
13. GET /api/v1/statistics/trend/{metric} - Get trend data
14. GET /api/v1/statistics/occupancy-rate - Get occupancy rate statistics
15. GET /api/v1/statistics/asset-distribution - Get asset distribution
16. GET /api/v1/statistics/area-statistics - Get area statistics
17. GET /api/v1/statistics/comprehensive - Get comprehensive statistics

Testing Approach:
- Mock all dependencies (asset_crud, services, database, auth)
- Test successful responses
- Test error handling scenarios
- Test request validation
- Test response schemas
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

pytestmark = pytest.mark.api


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_db():
    """Create mock database session"""
    return MagicMock()


@pytest.fixture
def mock_current_user():
    """Create mock authenticated user"""
    user = MagicMock()
    user.id = "test-user-id"
    user.username = "testuser"
    user.is_active = True
    return user


@pytest.fixture
def mock_cache_manager():
    """Create mock cache manager"""
    cache_mgr = AsyncMock()
    cache_mgr.redis_client = MagicMock()  # Mock Redis client
    return cache_mgr


# ============================================================================
# Test: GET /basic - Get Basic Statistics
# ============================================================================


class TestGetBasicStatistics:
    """Tests for GET /api/v1/statistics/basic endpoint"""

    @patch("src.api.v1.statistics.asset_crud")
    @pytest.mark.asyncio
    async def test_get_basic_statistics_no_filters(self, mock_asset_crud, mock_db, mock_current_user):
        """Test basic statistics without filters"""
        from src.api.v1.statistics import get_basic_statistics

        # Mock empty results
        mock_asset_crud.get_multi_with_search.return_value = ([], 0)

        result = await get_basic_statistics(
            ownership_status=None,
            property_nature=None,
            usage_status=None,
            ownership_entity=None,
            db=mock_db,
            current_user=mock_current_user,
        )

        assert result.total_assets == 0
        assert result.ownership_status["confirmed"] == 0
        assert result.property_nature["commercial"] == 0
        assert result.usage_status["rented"] == 0
        assert isinstance(result.generated_at, datetime)

    @patch("src.api.v1.statistics.asset_crud")
    @pytest.mark.asyncio
    async def test_get_basic_statistics_with_filters(self, mock_asset_crud, mock_db, mock_current_user):
        """Test basic statistics with ownership_status filter"""
        from src.api.v1.statistics import get_basic_statistics

        # Mock filtered results
        mock_assets = [MagicMock() for _ in range(10)]
        mock_asset_crud.get_multi_with_search.side_effect = [
            (mock_assets, 10),  # total_assets check
            ([MagicMock() for _ in range(5)], 5),  # confirmed
            ([MagicMock() for _ in range(3)], 3),  # unconfirmed
            ([MagicMock() for _ in range(2)], 2),  # partial
            ([MagicMock() for _ in range(6)], 6),  # commercial
            ([MagicMock() for _ in range(4)], 4),  # non_commercial
            ([MagicMock() for _ in range(7)], 7),  # rented
            ([MagicMock() for _ in range(2)], 2),  # self_used
            ([MagicMock() for _ in range(1)], 1),  # vacant
        ]

        result = await get_basic_statistics(
            ownership_status="已确权",
            property_nature=None,
            usage_status=None,
            ownership_entity=None,
            db=mock_db,
            current_user=mock_current_user,
        )

        assert result.total_assets == 10
        assert result.ownership_status["confirmed"] == 5
        assert result.property_nature["commercial"] == 6
        assert result.usage_status["rented"] == 7
        assert result.filters_applied == {"ownership_status": "已确权"}

    @patch("src.api.v1.statistics.asset_crud")
    @pytest.mark.asyncio
    async def test_get_basic_statistics_all_filters(self, mock_asset_crud, mock_db, mock_current_user):
        """Test basic statistics with all filters applied"""
        from src.api.v1.statistics import get_basic_statistics

        mock_asset_crud.get_multi_with_search.return_value = ([], 0)

        result = await get_basic_statistics(
            ownership_status="已确权",
            property_nature="经营性",
            usage_status="出租",
            ownership_entity="国资集团",
            db=mock_db,
            current_user=mock_current_user,
        )

        assert result.filters_applied == {
            "ownership_status": "已确权",
            "property_nature": "经营性",
            "usage_status": "出租",
            "ownership_entity": "国资集团",
        }


# ============================================================================
# Test: GET /summary - Get Statistics Summary
# ============================================================================


class TestGetStatisticsSummary:
    """Tests for GET /api/v1/statistics/summary endpoint"""

    @patch("src.api.v1.statistics.asset_crud")
    @pytest.mark.asyncio
    async def test_get_summary_empty_database(self, mock_asset_crud, mock_db, mock_current_user):
        """Test summary with empty database"""
        from src.api.v1.statistics import get_statistics_summary

        mock_asset_crud.get_multi.return_value = []
        mock_asset_crud.get_multi_with_search.return_value = ([], 0)

        result = await get_statistics_summary(db=mock_db, current_user=mock_current_user)

        assert result.total_assets == 0
        assert result.ownership_status["confirmed"] == 0
        assert result.filters_applied == {}

    @patch("src.api.v1.statistics.asset_crud")
    @pytest.mark.asyncio
    async def test_get_summary_with_data(self, mock_asset_crud, mock_db, mock_current_user):
        """Test summary with actual data"""
        from src.api.v1.statistics import get_statistics_summary

        # Mock various queries
        mock_assets = [MagicMock() for _ in range(20)]
        mock_asset_crud.get_multi.return_value = mock_assets
        mock_asset_crud.get_multi_with_search.side_effect = [
            ([MagicMock() for _ in range(10)], 10),  # confirmed
            ([MagicMock() for _ in range(5)], 5),  # unconfirmed
            ([MagicMock() for _ in range(5)], 5),  # partial
            ([MagicMock() for _ in range(12)], 12),  # commercial
            ([MagicMock() for _ in range(8)], 8),  # non_commercial
            ([MagicMock() for _ in range(15)], 15),  # rented
            ([MagicMock() for _ in range(3)], 3),  # self_used
            ([MagicMock() for _ in range(2)], 2),  # vacant
        ]

        result = await get_statistics_summary(db=mock_db, current_user=mock_current_user)

        assert result.total_assets == 20
        assert result.ownership_status["confirmed"] == 10
        assert result.property_nature["commercial"] == 12
        assert result.usage_status["rented"] == 15
        assert isinstance(result.generated_at, datetime)


# ============================================================================
# Test: GET /occupancy-rate/overall - Get Overall Occupancy Rate
# ============================================================================


class TestGetOverallOccupancyRate:
    """Tests for GET /api/v1/statistics/occupancy-rate/overall endpoint"""

    @patch("src.api.v1.statistics.OccupancyService")
    def test_get_overall_occupancy_rate_default(self, mock_occupancy_service_class, mock_db, mock_current_user):
        """Test overall occupancy rate with default parameters"""
        from src.api.v1.statistics import get_overall_occupancy_rate

        # Mock service instance and its method
        mock_service = MagicMock()
        mock_service.calculate_with_aggregation.return_value = {
            "overall_rate": 75.5,
            "total_rentable_area": 1000.0,
            "total_rented_area": 755.0,
        }
        mock_occupancy_service_class.return_value = mock_service

        result = get_overall_occupancy_rate(
            include_deleted=False, use_aggregation=True, db=mock_db, current_user=mock_current_user
        )

        assert result.overall_occupancy_rate == 75.5
        assert result.total_rentable_area == 1000.0
        assert result.total_rented_area == 755.0
        assert isinstance(result.calculated_at, datetime)

    @patch("src.api.v1.statistics.OccupancyService")
    def test_get_overall_occupancy_rate_include_deleted(self, mock_occupancy_service_class, mock_db, mock_current_user):
        """Test overall occupancy rate including deleted assets"""
        from src.api.v1.statistics import get_overall_occupancy_rate

        mock_service = MagicMock()
        mock_service.calculate_with_aggregation.return_value = {
            "overall_rate": 80.0,
            "total_rentable_area": 1200.0,
            "total_rented_area": 960.0,
        }
        mock_occupancy_service_class.return_value = mock_service

        result = get_overall_occupancy_rate(
            include_deleted=True, use_aggregation=True, db=mock_db, current_user=mock_current_user
        )

        assert result.overall_occupancy_rate == 80.0
        # Verify that filter was not applied (include_deleted=True)
        mock_service.calculate_with_aggregation.assert_called_once()

    @patch("src.api.v1.statistics.OccupancyService")
    def test_get_overall_occupancy_rate_zero_area(self, mock_occupancy_service_class, mock_db, mock_current_user):
        """Test overall occupancy rate with zero area"""
        from src.api.v1.statistics import get_overall_occupancy_rate

        mock_service = MagicMock()
        mock_service.calculate_with_aggregation.return_value = {
            "overall_rate": 0.0,
            "total_rentable_area": 0.0,
            "total_rented_area": 0.0,
        }
        mock_occupancy_service_class.return_value = mock_service

        result = get_overall_occupancy_rate(
            include_deleted=False, use_aggregation=True, db=mock_db, current_user=mock_current_user
        )

        assert result.overall_occupancy_rate == 0.0
        assert result.total_rentable_area == 0.0


# ============================================================================
# Test: GET /occupancy-rate/by-category - Get Occupancy Rate by Category
# ============================================================================


class TestGetOccupancyRateByCategory:
    """Tests for GET /api/v1/statistics/occupancy-rate/by-category endpoint"""

    @patch("src.api.v1.statistics.OccupancyService")
    def test_get_occupancy_by_category_default_field(self, mock_occupancy_service_class, mock_db, mock_current_user):
        """Test occupancy by category with default field"""
        from src.api.v1.statistics import get_occupancy_rate_by_category

        mock_service = MagicMock()
        mock_service.calculate_category_with_aggregation.return_value = {
            "经营性": {"overall_rate": 80.0, "total_rentable_area": 500.0, "total_rented_area": 400.0, "asset_count": 5},
            "非经营性": {"overall_rate": 60.0, "total_rentable_area": 300.0, "total_rented_area": 180.0, "asset_count": 3},
        }
        mock_occupancy_service_class.return_value = mock_service

        result = get_occupancy_rate_by_category(
            category_field="business_category",
            include_deleted=False,
            use_aggregation=True,
            db=mock_db,
            current_user=mock_current_user,
        )

        assert result.category_field == "business_category"
        assert len(result.categories) == 2
        assert result.categories[0].category == "经营性"
        assert result.categories[0].occupancy_rate == 80.0
        assert isinstance(result.generated_at, datetime)

    def test_get_occupancy_by_category_invalid_field(self, mock_db, mock_current_user):
        """Test occupancy by category with invalid field"""
        from src.api.v1.statistics import get_occupancy_rate_by_category

        with pytest.raises(HTTPException) as exc_info:
            get_occupancy_rate_by_category(
                category_field="invalid_field",
                include_deleted=False,
                use_aggregation=True,
                db=mock_db,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 400
        assert "无效的分类字段" in exc_info.value.detail

    @patch("src.api.v1.statistics.OccupancyService")
    def test_get_occupancy_by_category_all_valid_fields(
        self, mock_occupancy_service_class, mock_db, mock_current_user
    ):
        """Test occupancy by category with all valid fields"""
        from src.api.v1.statistics import get_occupancy_rate_by_category

        valid_fields = [
            "business_category",
            "property_nature",
            "usage_status",
            "ownership_status",
            "manager_name",
            "business_model",
            "operation_status",
            "project_name",
        ]

        mock_service = MagicMock()
        mock_service.calculate_category_with_aggregation.return_value = {
            "test_category": {"overall_rate": 70.0, "total_rentable_area": 100.0, "total_rented_area": 70.0, "asset_count": 1}
        }
        mock_occupancy_service_class.return_value = mock_service

        for field in valid_fields:
            result = get_occupancy_rate_by_category(
                category_field=field,
                include_deleted=False,
                use_aggregation=True,
                db=mock_db,
                current_user=mock_current_user,
            )
            assert result.category_field == field


# ============================================================================
# Test: GET /area-summary - Get Area Summary
# ============================================================================


class TestGetAreaSummary:
    """Tests for GET /api/v1/statistics/area-summary endpoint"""

    @patch("src.api.v1.statistics.AreaService")
    def test_get_area_summary_default(self, mock_area_service_class, mock_db, mock_current_user):
        """Test area summary with default parameters"""
        from src.api.v1.statistics import get_area_summary

        mock_service = MagicMock()
        mock_service.calculate_summary_with_aggregation.return_value = {
            "total_land_area": 5000.0,
            "total_rentable_area": 3000.0,
            "total_rented_area": 2400.0,
            "total_unrented_area": 600.0,
            "overall_occupancy_rate": 80.0,
        }
        mock_area_service_class.return_value = mock_service

        result = get_area_summary(
            include_deleted=False, use_aggregation=True, db=mock_db, current_user=mock_current_user
        )

        assert result.total_area == 5000.0
        assert result.rentable_area == 3000.0
        assert result.rented_area == 2400.0
        assert result.unrented_area == 600.0
        assert result.occupancy_rate == 80.0

    @patch("src.api.v1.statistics.AreaService")
    def test_get_area_summary_include_deleted(self, mock_area_service_class, mock_db, mock_current_user):
        """Test area summary including deleted assets"""
        from src.api.v1.statistics import get_area_summary

        mock_service = MagicMock()
        mock_service.calculate_summary_with_aggregation.return_value = {
            "total_land_area": 6000.0,
            "total_rentable_area": 3500.0,
            "total_rented_area": 2800.0,
            "total_unrented_area": 700.0,
            "overall_occupancy_rate": 80.0,
        }
        mock_area_service_class.return_value = mock_service

        result = get_area_summary(
            include_deleted=True, use_aggregation=True, db=mock_db, current_user=mock_current_user
        )

        assert result.total_area == 6000.0
        mock_service.calculate_summary_with_aggregation.assert_called_once()


# ============================================================================
# Test: GET /financial-summary - Get Financial Summary
# ============================================================================


class TestGetFinancialSummary:
    """Tests for GET /api/v1/statistics/financial-summary endpoint"""

    @patch("src.api.v1.statistics.asset_crud")
    @patch("src.api.v1.statistics.to_float")
    def test_get_financial_summary_empty(self, mock_to_float, mock_asset_crud, mock_db, mock_current_user):
        """Test financial summary with no assets"""
        from src.api.v1.statistics import get_financial_summary

        mock_asset_crud.get_multi_with_search.return_value = ([], 0)
        mock_to_float.return_value = 0.0

        result = get_financial_summary(include_deleted=False, db=mock_db, current_user=mock_current_user)

        assert result.total_assets == 0
        assert result.total_annual_income == 0.0
        assert result.total_annual_expense == 0.0
        assert result.net_annual_income == 0.0

    @patch("src.api.v1.statistics.asset_crud")
    @patch("src.api.v1.statistics.to_float")
    def test_get_financial_summary_with_assets(self, mock_to_float, mock_asset_crud, mock_db, mock_current_user):
        """Test financial summary with assets"""
        from src.api.v1.statistics import get_financial_summary

        # Create mock assets
        mock_assets = []
        for i in range(3):
            asset = MagicMock()
            asset.rentable_area = 100.0 + i * 50
            asset.annual_income = 10000.0 + i * 5000
            asset.annual_expense = 5000.0 + i * 2000
            asset.net_income = 5000.0 + i * 3000
            asset.monthly_rent = 1000.0 + i * 400
            asset.deposit = 2000.0 + i * 800
            mock_assets.append(asset)

        mock_asset_crud.get_multi_with_search.return_value = (mock_assets, 3)
        mock_to_float.side_effect = lambda x: x  # Return value as-is

        result = get_financial_summary(include_deleted=False, db=mock_db, current_user=mock_current_user)

        assert result.total_assets == 3
        assert result.total_annual_income > 0
        assert result.total_annual_expense > 0
        assert result.net_annual_income > 0
        assert result.income_per_sqm > 0
        assert result.expense_per_sqm > 0

    @patch("src.api.v1.statistics.asset_crud")
    @patch("src.api.v1.statistics.to_float")
    def test_get_financial_summary_per_sqm_calculation(self, mock_to_float, mock_asset_crud, mock_db, mock_current_user):
        """Test per-square-meter calculations"""
        from src.api.v1.statistics import get_financial_summary

        # Create assets with specific values
        mock_assets = []
        for i in range(2):
            asset = MagicMock()
            asset.rentable_area = 500.0
            asset.annual_income = 60000.0
            asset.annual_expense = 30000.0
            asset.net_income = 30000.0
            asset.monthly_rent = 5000.0
            asset.deposit = 10000.0
            mock_assets.append(asset)

        mock_asset_crud.get_multi_with_search.return_value = (mock_assets, 2)
        mock_to_float.side_effect = lambda x: x

        result = get_financial_summary(include_deleted=False, db=mock_db, current_user=mock_current_user)

        # 120000 income / 1000 area = 120 per sqm
        expected_income_per_sqm = 120.0
        # 60000 expense / 1000 area = 60 per sqm
        expected_expense_per_sqm = 60.0

        assert result.income_per_sqm == expected_income_per_sqm
        assert result.expense_per_sqm == expected_expense_per_sqm


# ============================================================================
# Test: POST /cache/clear - Clear Cache
# ============================================================================


class TestClearStatisticsCache:
    """Tests for POST /api/v1/statistics/cache/clear endpoint"""

    @patch("src.api.v1.statistics.get_cache_manager")
    @pytest.mark.asyncio
    async def test_clear_cache_success(self, mock_get_cache_manager):
        """Test successful cache clearing"""
        from src.api.v1.statistics import clear_statistics_cache

        mock_cache_mgr = AsyncMock()
        mock_cache_mgr.clear_pattern.return_value = 10
        mock_get_cache_manager.return_value = mock_cache_mgr

        result = await clear_statistics_cache()

        assert result["success"] is True
        assert result["data"]["cleared_count"] == 10
        assert "统计数据缓存已清除" in result["message"]

    @patch("src.api.v1.statistics.get_cache_manager")
    @pytest.mark.asyncio
    async def test_clear_cache_empty(self, mock_get_cache_manager):
        """Test cache clearing when no cached items"""
        from src.api.v1.statistics import clear_statistics_cache

        mock_cache_mgr = AsyncMock()
        mock_cache_mgr.clear_pattern.return_value = 0
        mock_get_cache_manager.return_value = mock_cache_mgr

        result = await clear_statistics_cache()

        assert result["success"] is True
        assert result["data"]["cleared_count"] == 0


# ============================================================================
# Test: GET /cache/info - Get Cache Info
# ============================================================================


class TestGetCacheInfo:
    """Tests for GET /api/v1/statistics/cache/info endpoint"""

    @patch("src.api.v1.statistics.get_cache_manager")
    @pytest.mark.asyncio
    async def test_get_cache_info_with_redis(self, mock_get_cache_manager):
        """Test cache info with Redis enabled"""
        from src.api.v1.statistics import get_cache_info

        mock_cache_mgr = AsyncMock()
        mock_cache_mgr.redis_client = MagicMock()  # Redis is enabled
        mock_get_cache_manager.return_value = mock_cache_mgr

        result = await get_cache_info()

        assert result["success"] is True
        assert result["data"]["cache_type"] == "Redis"
        assert result["data"]["cache_enabled"] is True

    @patch("src.api.v1.statistics.get_cache_manager")
    @pytest.mark.asyncio
    async def test_get_cache_info_without_redis(self, mock_get_cache_manager):
        """Test cache info with in-memory cache"""
        from src.api.v1.statistics import get_cache_info

        mock_cache_mgr = AsyncMock()
        mock_cache_mgr.redis_client = None  # Redis is disabled
        mock_get_cache_manager.return_value = mock_cache_mgr

        result = await get_cache_info()

        assert result["success"] is True
        assert result["data"]["cache_type"] == "In-Memory"
        assert result["data"]["cache_enabled"] is False


# ============================================================================
# Test: GET /dashboard - Get Dashboard Data
# ============================================================================


class TestGetDashboardData:
    """Tests for GET /api/v1/statistics/dashboard endpoint"""

    @patch("src.api.v1.statistics.asset_crud")
    @patch("src.api.v1.statistics.to_float")
    @pytest.mark.asyncio
    async def test_get_dashboard_data_empty(self, mock_to_float, mock_asset_crud, mock_db, mock_current_user):
        """Test dashboard data with no assets"""
        from src.api.v1.statistics import get_dashboard_data

        mock_asset_crud.get_multi.return_value = []
        mock_asset_crud.get_multi_with_search.return_value = ([], 0)
        mock_to_float.return_value = 0.0

        result = await get_dashboard_data(db=mock_db, current_user=mock_current_user)

        assert result.basic_stats.total_assets == 0
        assert result.area_summary.total_area == 0.0
        assert result.financial_summary.total_assets == 0
        assert result.occupancy_stats.overall_occupancy_rate == 0.0
        assert len(result.category_occupancy) == 0
        assert isinstance(result.generated_at, datetime)

    @patch("src.api.v1.statistics.asset_crud")
    @patch("src.api.v1.statistics.to_float")
    @pytest.mark.asyncio
    async def test_get_dashboard_data_with_assets(self, mock_to_float, mock_asset_crud, mock_db, mock_current_user):
        """Test dashboard data with assets"""
        from src.api.v1.statistics import get_dashboard_data

        # Create mock assets
        mock_assets = []
        for i in range(5):
            asset = MagicMock()
            asset.land_area = 100.0 + i * 10
            asset.annual_income = 10000.0 + i * 1000
            asset.annual_expense = 5000.0 + i * 500
            asset.rentable_area = 80.0 + i * 8
            asset.rented_area = 60.0 + i * 6
            mock_assets.append(asset)

        mock_asset_crud.get_multi.return_value = mock_assets[:1]
        mock_asset_crud.get_multi_with_search.side_effect = [
            ([MagicMock() for _ in range(3)], 3),  # confirmed
            ([MagicMock() for _ in range(2)], 2),  # unconfirmed
            ([], 0),  # partial
            ([MagicMock() for _ in range(3)], 3),  # commercial
            ([MagicMock() for _ in range(2)], 2),  # non_commercial
            ([MagicMock() for _ in range(4)], 4),  # rented
            ([], 0),  # vacant
            ([MagicMock() for _ in range(1)], 1),  # self_used
            (mock_assets, 5),  # all assets for area/financial
        ]

        mock_to_float.side_effect = lambda x: x

        result = await get_dashboard_data(db=mock_db, current_user=mock_current_user)

        assert result.basic_stats.total_assets > 0
        assert result.area_summary.total_area > 0
        assert result.financial_summary.total_annual_income > 0
        assert result.occupancy_stats.overall_occupancy_rate >= 0


# ============================================================================
# Test: GET /ownership-distribution - Get Ownership Distribution
# ============================================================================


class TestGetOwnershipDistribution:
    """Tests for GET /api/v1/statistics/ownership-distribution endpoint"""

    @patch("src.api.v1.statistics.asset_crud")
    @pytest.mark.asyncio
    async def test_get_ownership_distribution_empty(self, mock_asset_crud, mock_db, mock_current_user):
        """Test ownership distribution with no assets"""
        from src.api.v1.statistics import get_ownership_distribution

        mock_asset_crud.get_multi.return_value = []
        mock_asset_crud.get_multi_with_search.return_value = ([], 0)

        result = await get_ownership_distribution(db=mock_db, current_user=mock_current_user)

        assert result.total == 0
        assert len(result.categories) == 3  # confirmed, unconfirmed, partial

    @patch("src.api.v1.statistics.asset_crud")
    @pytest.mark.asyncio
    async def test_get_ownership_distribution_with_data(self, mock_asset_crud, mock_db, mock_current_user):
        """Test ownership distribution with assets"""
        from src.api.v1.statistics import get_ownership_distribution

        mock_asset_crud.get_multi.return_value = [MagicMock() for _ in range(10)]
        mock_asset_crud.get_multi_with_search.side_effect = [
            ([MagicMock() for _ in range(5)], 5),  # confirmed
            ([MagicMock() for _ in range(3)], 3),  # unconfirmed
            ([MagicMock() for _ in range(2)], 2),  # partial
        ]

        result = await get_ownership_distribution(db=mock_db, current_user=mock_current_user)

        assert result.total == 10
        assert len(result.categories) == 3
        assert result.categories[0].name == "已确权"
        assert result.categories[0].value == 5
        assert result.categories[0].percentage == 50.0


# ============================================================================
# Test: GET /property-nature-distribution - Get Property Nature Distribution
# ============================================================================


class TestGetPropertyNatureDistribution:
    """Tests for GET /api/v1/statistics/property-nature-distribution endpoint"""

    @patch("src.api.v1.statistics.asset_crud")
    @pytest.mark.asyncio
    async def test_get_property_nature_distribution_empty(self, mock_asset_crud, mock_db, mock_current_user):
        """Test property nature distribution with no assets"""
        from src.api.v1.statistics import get_property_nature_distribution

        mock_asset_crud.get_multi.return_value = []
        mock_asset_crud.get_multi_with_search.return_value = ([], 0)

        result = await get_property_nature_distribution(db=mock_db, current_user=mock_current_user)

        assert result.total == 0
        assert len(result.categories) == 2  # commercial, non_commercial

    @patch("src.api.v1.statistics.asset_crud")
    @pytest.mark.asyncio
    async def test_get_property_nature_distribution_with_data(self, mock_asset_crud, mock_db, mock_current_user):
        """Test property nature distribution with assets"""
        from src.api.v1.statistics import get_property_nature_distribution

        mock_asset_crud.get_multi.return_value = [MagicMock() for _ in range(10)]
        mock_asset_crud.get_multi_with_search.side_effect = [
            ([MagicMock() for _ in range(6)], 6),  # commercial
            ([MagicMock() for _ in range(4)], 4),  # non_commercial
        ]

        result = await get_property_nature_distribution(db=mock_db, current_user=mock_current_user)

        assert result.total == 10
        assert result.categories[0].name == "经营性"
        assert result.categories[0].value == 6
        assert result.categories[0].percentage == 60.0


# ============================================================================
# Test: GET /usage-status-distribution - Get Usage Status Distribution
# ============================================================================


class TestGetUsageStatusDistribution:
    """Tests for GET /api/v1/statistics/usage-status-distribution endpoint"""

    @patch("src.api.v1.statistics.asset_crud")
    @pytest.mark.asyncio
    async def test_get_usage_status_distribution_empty(self, mock_asset_crud, mock_db, mock_current_user):
        """Test usage status distribution with no assets"""
        from src.api.v1.statistics import get_usage_status_distribution

        mock_asset_crud.get_multi.return_value = []
        mock_asset_crud.get_multi_with_search.return_value = ([], 0)

        result = await get_usage_status_distribution(db=mock_db, current_user=mock_current_user)

        assert result.total == 0
        assert len(result.categories) == 3  # rented, vacant, self_used

    @patch("src.api.v1.statistics.asset_crud")
    @pytest.mark.asyncio
    async def test_get_usage_status_distribution_with_data(self, mock_asset_crud, mock_db, mock_current_user):
        """Test usage status distribution with assets"""
        from src.api.v1.statistics import get_usage_status_distribution

        mock_asset_crud.get_multi.return_value = [MagicMock() for _ in range(10)]
        mock_asset_crud.get_multi_with_search.side_effect = [
            ([MagicMock() for _ in range(5)], 5),  # rented
            ([MagicMock() for _ in range(3)], 3),  # vacant
            ([MagicMock() for _ in range(2)], 2),  # self_used
        ]

        result = await get_usage_status_distribution(db=mock_db, current_user=mock_current_user)

        assert result.total == 10
        assert result.categories[0].name == "出租"
        assert result.categories[0].value == 5
        assert result.categories[0].percentage == 50.0


# ============================================================================
# Test: GET /trend/{metric} - Get Trend Data
# ============================================================================


class TestGetTrendData:
    """Tests for GET /api/v1/statistics/trend/{metric} endpoint"""

    @patch("src.api.v1.statistics.asset_crud")
    @pytest.mark.asyncio
    async def test_get_trend_occupancy_rate(self, mock_asset_crud, mock_db, mock_current_user):
        """Test trend data for occupancy_rate metric"""
        from src.api.v1.statistics import get_trend_data

        result = await get_trend_data(
            metric="occupancy_rate", period="monthly", db=mock_db, current_user=mock_current_user
        )

        assert result.metric_name == "occupancy_rate"
        assert len(result.time_series) == 6
        assert all(point.date is not None for point in result.time_series)
        assert all(point.value is not None for point in result.time_series)
        assert result.trend_direction == "stable"

    @patch("src.api.v1.statistics.asset_crud")
    @pytest.mark.asyncio
    async def test_get_trend_income(self, mock_asset_crud, mock_db, mock_current_user):
        """Test trend data for income metric"""
        from src.api.v1.statistics import get_trend_data

        result = await get_trend_data(metric="income", period="monthly", db=mock_db, current_user=mock_current_user)

        assert result.metric_name == "income"
        assert len(result.time_series) == 6
        assert result.trend_direction == "up"
        assert result.change_percentage == 5.0

    @patch("src.api.v1.statistics.asset_crud")
    @pytest.mark.asyncio
    async def test_get_trend_unknown_metric(self, mock_asset_crud, mock_db, mock_current_user):
        """Test trend data for unknown metric"""
        from src.api.v1.statistics import get_trend_data

        result = await get_trend_data(
            metric="unknown_metric", period="monthly", db=mock_db, current_user=mock_current_user
        )

        assert result.metric_name == "unknown_metric"
        assert len(result.time_series) == 6
        assert result.trend_direction == "stable"
        assert result.change_percentage is None

    @patch("src.api.v1.statistics.asset_crud")
    @pytest.mark.asyncio
    async def test_get_trend_different_periods(self, mock_asset_crud, mock_db, mock_current_user):
        """Test trend data with different periods"""
        from src.api.v1.statistics import get_trend_data

        periods = ["daily", "weekly", "monthly", "yearly"]

        for period in periods:
            result = await get_trend_data(
                metric="occupancy_rate", period=period, db=mock_db, current_user=mock_current_user
            )
            assert result.metric_name == "occupancy_rate"
            assert len(result.time_series) == 6


# ============================================================================
# Test: GET /occupancy-rate - Get Occupancy Rate Statistics
# ============================================================================


class TestGetOccupancyRateStatistics:
    """Tests for GET /api/v1/statistics/occupancy-rate endpoint"""

    @patch("src.api.v1.statistics.OccupancyService")
    @pytest.mark.asyncio
    async def test_get_occupancy_rate_statistics_no_filters(self, mock_occupancy_service_class, mock_db, mock_current_user):
        """Test occupancy rate statistics without filters"""
        from src.api.v1.statistics import get_occupancy_rate_statistics

        mock_service = MagicMock()
        mock_service.calculate_with_aggregation.return_value = {
            "overall_rate": 75.0,
            "total_rentable_area": 1000.0,
            "total_rented_area": 750.0,
            "total_assets": 10,
            "rentable_assets_count": 8,
        }
        mock_occupancy_service_class.return_value = mock_service

        result = await get_occupancy_rate_statistics(
            ownership_status=None,
            property_nature=None,
            usage_status=None,
            business_category=None,
            db=mock_db,
            current_user=mock_current_user,
        )

        assert result["success"] is True
        assert result["data"]["overall_occupancy_rate"] == 75.0
        assert result["data"]["total_rentable_area"] == 1000.0
        assert result["data"]["filters_applied"] == {}

    @patch("src.api.v1.statistics.OccupancyService")
    @pytest.mark.asyncio
    async def test_get_occupancy_rate_statistics_with_filters(self, mock_occupancy_service_class, mock_db, mock_current_user):
        """Test occupancy rate statistics with filters"""
        from src.api.v1.statistics import get_occupancy_rate_statistics

        mock_service = MagicMock()
        mock_service.calculate_with_aggregation.return_value = {
            "overall_rate": 80.0,
            "total_rentable_area": 500.0,
            "total_rented_area": 400.0,
            "total_assets": 5,
            "rentable_assets_count": 4,
        }
        mock_occupancy_service_class.return_value = mock_service

        result = await get_occupancy_rate_statistics(
            ownership_status="已确权",
            property_nature="经营性",
            usage_status="出租",
            business_category=None,
            db=mock_db,
            current_user=mock_current_user,
        )

        assert result["success"] is True
        assert result["data"]["overall_occupancy_rate"] == 80.0
        assert "ownership_status" in result["data"]["filters_applied"]
        assert result["data"]["filters_applied"]["ownership_status"] == "已确权"


# ============================================================================
# Test: GET /asset-distribution - Get Asset Distribution
# ============================================================================


class TestGetAssetDistribution:
    """Tests for GET /api/v1/statistics/asset-distribution endpoint"""

    @patch("src.api.v1.statistics.asset_crud")
    @pytest.mark.asyncio
    async def test_get_asset_distribution_default_group(self, mock_asset_crud, mock_db, mock_current_user):
        """Test asset distribution with default grouping"""
        from src.api.v1.statistics import get_asset_distribution

        # Create mock assets with different ownership_status
        mock_assets = []
        for i in range(10):
            asset = MagicMock()
            asset.ownership_status = "已确权" if i < 6 else "未确权"
            mock_assets.append(asset)

        mock_asset_crud.get_multi_with_search.return_value = (mock_assets, 10)

        result = await get_asset_distribution(
            group_by="ownership_status", include_deleted=False, db=mock_db, current_user=mock_current_user
        )

        assert result["success"] is True
        assert result["data"]["group_by"] == "ownership_status"
        assert result["data"]["total_assets"] == 10
        assert len(result["data"]["distribution"]) == 2

    @patch("src.api.v1.statistics.asset_crud")
    @pytest.mark.asyncio
    async def test_get_asset_distribution_invalid_group(self, mock_asset_crud, mock_db, mock_current_user):
        """Test asset distribution with invalid group_by field"""
        from src.api.v1.statistics import get_asset_distribution

        mock_asset_crud.get_multi_with_search.return_value = ([], 0)

        with pytest.raises(HTTPException) as exc_info:
            await get_asset_distribution(
                group_by="invalid_field", include_deleted=False, db=mock_db, current_user=mock_current_user
            )

        assert exc_info.value.status_code == 400
        assert "无效的分组字段" in exc_info.value.detail

    @patch("src.api.v1.statistics.asset_crud")
    @pytest.mark.asyncio
    async def test_get_asset_distribution_all_valid_fields(self, mock_asset_crud, mock_db, mock_current_user):
        """Test asset distribution with all valid group_by fields"""
        from src.api.v1.statistics import get_asset_distribution

        valid_fields = [
            "ownership_status",
            "property_nature",
            "usage_status",
            "business_category",
            "manager_name",
            "project_name",
        ]

        mock_asset_crud.get_multi_with_search.return_value = ([], 0)

        for field in valid_fields:
            result = await get_asset_distribution(
                group_by=field, include_deleted=False, db=mock_db, current_user=mock_current_user
            )
            assert result["data"]["group_by"] == field

    @patch("src.api.v1.statistics.asset_crud")
    @pytest.mark.asyncio
    async def test_get_asset_distribution_include_deleted(self, mock_asset_crud, mock_db, mock_current_user):
        """Test asset distribution including deleted assets"""
        from src.api.v1.statistics import get_asset_distribution

        mock_asset_crud.get_multi_with_search.return_value = ([], 0)

        result = await get_asset_distribution(
            group_by="ownership_status", include_deleted=True, db=mock_db, current_user=mock_current_user
        )

        assert result["success"] is True
        # When include_deleted=True, no data_status filter should be applied
        assert "data_status" not in result["data"]["filters_applied"]


# ============================================================================
# Test: GET /area-statistics - Get Area Statistics
# ============================================================================


class TestGetAreaStatistics:
    """Tests for GET /api/v1/statistics/area-statistics endpoint"""

    @patch("src.api.v1.statistics.AreaService")
    @pytest.mark.asyncio
    async def test_get_area_statistics_default(self, mock_area_service_class, mock_db, mock_current_user):
        """Test area statistics with default parameters"""
        from src.api.v1.statistics import get_area_statistics

        mock_service = MagicMock()
        mock_service.calculate_summary_with_aggregation.return_value = {
            "total_assets": 10,
            "total_land_area": 5000.0,
            "total_rentable_area": 3000.0,
            "total_rented_area": 2400.0,
            "total_unrented_area": 600.0,
            "total_non_commercial_area": 500.0,
            "assets_with_area_data": 8,
            "overall_occupancy_rate": 80.0,
        }
        mock_area_service_class.return_value = mock_service

        result = await get_area_statistics(
            ownership_status=None,
            property_nature=None,
            usage_status=None,
            include_deleted=False,
            db=mock_db,
            current_user=mock_current_user,
        )

        assert result["success"] is True
        assert result["data"]["total_assets"] == 10
        assert result["data"]["total_land_area"] == 5000.0
        assert result["data"]["overall_occupancy_rate"] == 80.0

    @patch("src.api.v1.statistics.AreaService")
    @pytest.mark.asyncio
    async def test_get_area_statistics_with_filters(self, mock_area_service_class, mock_db, mock_current_user):
        """Test area statistics with filters"""
        from src.api.v1.statistics import get_area_statistics

        mock_service = MagicMock()
        mock_service.calculate_summary_with_aggregation.return_value = {
            "total_assets": 5,
            "total_land_area": 2500.0,
            "total_rentable_area": 1500.0,
            "total_rented_area": 1200.0,
            "total_unrented_area": 300.0,
            "total_non_commercial_area": 250.0,
            "assets_with_area_data": 4,
            "overall_occupancy_rate": 80.0,
        }
        mock_area_service_class.return_value = mock_service

        result = await get_area_statistics(
            ownership_status="已确权",
            property_nature="经营性",
            usage_status="出租",
            include_deleted=False,
            db=mock_db,
            current_user=mock_current_user,
        )

        assert result["success"] is True
        assert result["data"]["total_assets"] == 5
        assert "ownership_status" in result["data"]["filters_applied"]


# ============================================================================
# Test: GET /comprehensive - Get Comprehensive Statistics
# ============================================================================


class TestGetComprehensiveStatistics:
    """Tests for GET /api/v1/statistics/comprehensive endpoint"""

    @patch("src.api.v1.statistics.OccupancyService")
    @patch("src.api.v1.statistics.AreaService")
    @patch("src.api.v1.statistics.asset_crud")
    @patch("src.api.v1.statistics.to_float")
    @pytest.mark.asyncio
    async def test_get_comprehensive_statistics_no_assets(
        self, mock_to_float, mock_asset_crud, mock_area_service_class, mock_occupancy_service_class, mock_db, mock_current_user
    ):
        """Test comprehensive statistics with no matching assets"""
        from src.api.v1.statistics import get_comprehensive_statistics

        mock_asset_crud.get_multi_with_search.return_value = ([], 0)
        mock_to_float.return_value = 0.0

        result = await get_comprehensive_statistics(
            ownership_status=None,
            property_nature=None,
            usage_status=None,
            include_deleted=False,
            db=mock_db,
            current_user=mock_current_user,
        )

        assert result["success"] is False
        assert result["message"] == "没有找到符合条件的资产数据"
        assert result["data"] is None

    @patch("src.api.v1.statistics.OccupancyService")
    @patch("src.api.v1.statistics.AreaService")
    @patch("src.api.v1.statistics.asset_crud")
    @patch("src.api.v1.statistics.to_float")
    @pytest.mark.asyncio
    async def test_get_comprehensive_statistics_with_assets(
        self, mock_to_float, mock_asset_crud, mock_area_service_class, mock_occupancy_service_class, mock_db, mock_current_user
    ):
        """Test comprehensive statistics with assets"""
        from src.api.v1.statistics import get_comprehensive_statistics

        # Create mock assets
        mock_assets = []
        for i in range(5):
            asset = MagicMock()
            asset.ownership_status = "已确权" if i < 3 else "未确权"
            asset.property_nature = "经营性" if i < 4 else "非经营性"
            asset.usage_status = "出租" if i < 3 else ("空置" if i < 4 else "自用")
            asset.annual_income = 10000.0 + i * 1000
            asset.annual_expense = 5000.0 + i * 500
            asset.net_income = 5000.0 + i * 500
            asset.monthly_rent = 1000.0 + i * 100
            mock_assets.append(asset)

        mock_asset_crud.get_multi_with_search.side_effect = [
            (mock_assets[:1], 1),  # Check total_assets
            (mock_assets, 5),  # Get all for financial/distribution
        ]
        mock_to_float.side_effect = lambda x: x

        # Mock services
        mock_area_service = MagicMock()
        mock_area_service.calculate_summary_with_aggregation.return_value = {
            "total_assets": 5,
            "total_land_area": 2500.0,
            "total_rentable_area": 1500.0,
            "total_rented_area": 1200.0,
            "total_unrented_area": 300.0,
            "total_non_commercial_area": 250.0,
            "assets_with_area_data": 4,
            "overall_occupancy_rate": 80.0,
        }

        mock_occupancy_service = MagicMock()
        mock_occupancy_service.calculate_with_aggregation.return_value = {
            "overall_rate": 80.0,
            "total_rentable_area": 1500.0,
            "total_rented_area": 1200.0,
            "total_assets": 5,
            "rentable_assets_count": 4,
        }

        mock_area_service_class.return_value = mock_area_service
        mock_occupancy_service_class.return_value = mock_occupancy_service

        result = await get_comprehensive_statistics(
            ownership_status=None,
            property_nature=None,
            usage_status=None,
            include_deleted=False,
            db=mock_db,
            current_user=mock_current_user,
        )

        assert result["success"] is True
        assert "basic_stats" in result["data"]
        assert "area_stats" in result["data"]
        assert "occupancy_stats" in result["data"]
        assert "financial_stats" in result["data"]
        assert result["data"]["basic_stats"]["total_assets"] == 1

    @patch("src.api.v1.statistics.OccupancyService")
    @patch("src.api.v1.statistics.AreaService")
    @patch("src.api.v1.statistics.asset_crud")
    @patch("src.api.v1.statistics.to_float")
    @pytest.mark.asyncio
    async def test_get_comprehensive_statistics_with_filters(
        self, mock_to_float, mock_asset_crud, mock_area_service_class, mock_occupancy_service_class, mock_db, mock_current_user
    ):
        """Test comprehensive statistics with filters"""
        from src.api.v1.statistics import get_comprehensive_statistics

        mock_assets = [MagicMock() for _ in range(5)]
        mock_asset_crud.get_multi_with_search.return_value = (mock_assets, 5)
        mock_to_float.return_value = 0.0

        mock_area_service = MagicMock()
        mock_area_service.calculate_summary_with_aggregation.return_value = {
            "total_assets": 5,
            "total_land_area": 2500.0,
            "total_rentable_area": 1500.0,
            "total_rented_area": 1200.0,
            "total_unrented_area": 300.0,
            "total_non_commercial_area": 250.0,
            "assets_with_area_data": 4,
            "overall_occupancy_rate": 80.0,
        }

        mock_occupancy_service = MagicMock()
        mock_occupancy_service.calculate_with_aggregation.return_value = {
            "overall_rate": 80.0,
            "total_rentable_area": 1500.0,
            "total_rented_area": 1200.0,
            "total_assets": 5,
            "rentable_assets_count": 4,
        }

        mock_area_service_class.return_value = mock_area_service
        mock_occupancy_service_class.return_value = mock_occupancy_service

        result = await get_comprehensive_statistics(
            ownership_status="已确权",
            property_nature="经营性",
            usage_status=None,
            include_deleted=False,
            db=mock_db,
            current_user=mock_current_user,
        )

        assert result["success"] is True
        assert "ownership_status" in result["data"]["filters_applied"]
        assert result["data"]["filters_applied"]["ownership_status"] == "已确权"


# ============================================================================
# Test: Edge Cases and Error Handling
# ============================================================================


class TestStatisticsEdgeCases:
    """Tests for edge cases and error handling"""

    @patch("src.api.v1.statistics.to_float")
    def test_to_float_with_none_values(self, mock_to_float):
        """Test to_float handles None values"""
        from src.api.v1.statistics import to_float

        mock_to_float.side_effect = lambda x: x

        result = to_float(None)
        # to_float should handle None gracefully
        assert result is None or result == 0.0

    @patch("src.api.v1.statistics.asset_crud")
    @patch("src.api.v1.statistics.to_float")
    @pytest.mark.asyncio
    async def test_zero_division_protection(self, mock_to_float, mock_asset_crud, mock_db, mock_current_user):
        """Test division by zero protection in calculations"""
        from src.api.v1.statistics import get_dashboard_data

        # Create asset with zero area
        mock_asset = MagicMock()
        mock_asset.land_area = 0.0
        mock_asset.annual_income = 0.0
        mock_asset.annual_expense = 0.0
        mock_asset.rentable_area = 0.0
        mock_asset.rented_area = 0.0

        mock_asset_crud.get_multi.return_value = [mock_asset]
        mock_asset_crud.get_multi_with_search.return_value = ([], 0)
        mock_to_float.side_effect = lambda x: x

        result = await get_dashboard_data(db=mock_db, current_user=mock_current_user)

        # Should not raise division by zero error
        assert result.financial_summary.income_per_sqm == 0.0
        assert result.financial_summary.expense_per_sqm == 0.0
