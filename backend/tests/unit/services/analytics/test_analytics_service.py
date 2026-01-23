"""
测试 AnalyticsService (综合分析服务)
"""

from unittest.mock import MagicMock, patch

import pytest

from src.services.analytics.analytics_service import AnalyticsService


@pytest.fixture
def mock_db():
    """创建模拟数据库会话"""
    return MagicMock()


@pytest.fixture
def analytics_service(mock_db):
    """创建 AnalyticsService 实例"""
    return AnalyticsService(mock_db)


class TestAnalyticsService:
    """测试 AnalyticsService 类"""

    def test_init(self, mock_db):
        """测试服务初始化"""
        service = AnalyticsService(mock_db)
        assert service.db == mock_db
        assert service.cache is not None
        assert service.response_handler is not None

    def test_validate_filters_empty(self, analytics_service):
        """测试空筛选条件验证"""
        result = analytics_service._validate_filters({})
        assert result == {}

    def test_validate_filters_with_include_deleted(self, analytics_service):
        """测试包含 include_deleted 的筛选条件"""
        result = analytics_service._validate_filters({"include_deleted": True})
        assert result["include_deleted"] is True

    def test_validate_filters_with_dates(self, analytics_service):
        """测试包含日期的筛选条件"""
        filters = {
            "include_deleted": False,
            "date_from": "2024-01-01",
            "date_to": "2024-12-31",
        }
        result = analytics_service._validate_filters(filters)
        assert result["include_deleted"] is False
        assert result["date_from"] == "2024-01-01"
        assert result["date_to"] == "2024-12-31"

    def test_generate_cache_key(self, analytics_service):
        """测试缓存键生成"""
        filters1 = {"include_deleted": True}
        filters2 = {"include_deleted": True}

        key1 = analytics_service._generate_cache_key(filters1)
        key2 = analytics_service._generate_cache_key(filters2)

        # 相同的筛选条件应该生成相同的键
        assert key1 == key2

        # 不同的筛选条件应该生成不同的键
        filters3 = {"include_deleted": False}
        key3 = analytics_service._generate_cache_key(filters3)
        assert key1 != key3

    @patch(
        "src.services.analytics.analytics_service.AnalyticsService._calculate_analytics"
    )
    @patch(
        "src.services.analytics.analytics_service.AnalyticsService._generate_cache_key"
    )
    def test_get_comprehensive_analytics_with_cache(
        self, mock_generate_key, mock_calculate, analytics_service
    ):
        """测试使用缓存的综合分析"""
        # Mock缓存命中
        mock_cache_data = {"total": 100, "timestamp": "2024-01-01"}
        analytics_service.cache.get = MagicMock(return_value=mock_cache_data)
        mock_generate_key.return_value = "test_key"

        result = analytics_service.get_comprehensive_analytics(
            filters={}, should_use_cache=True
        )

        # 应该返回缓存数据
        assert result == mock_cache_data
        # 不应该调用计算方法
        mock_calculate.assert_not_called()

    @patch(
        "src.services.analytics.analytics_service.AnalyticsService._generate_cache_key"
    )
    def test_get_comprehensive_analytics_without_cache(
        self, mock_generate_key, analytics_service
    ):
        """测试不使用缓存的综合分析"""
        # Mock缓存未命中
        analytics_service.cache.get = MagicMock(return_value=None)
        mock_generate_key.return_value = "test_key"

        # Mock AreaService 和 OccupancyService - 修复导入路径
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
                mock_occupancy_service.calculate_overall_rate.return_value = {
                    "rate": 0.85
                }
                mock_occupancy_cls.return_value = mock_occupancy_service

                # Mock数据库查询 - 使用 data_status
                mock_assets = [MagicMock(data_status="正常")]
                analytics_service.db.query.return_value.filter.return_value.all.return_value = mock_assets

                result = analytics_service.get_comprehensive_analytics(
                    filters={}, should_use_cache=False
                )

                # 验证结果结构
                assert "total_assets" in result
                assert "timestamp" in result
                assert "area_summary" in result
                assert "occupancy_rate" in result

    def test_clear_cache(self, analytics_service):
        """测试清除缓存"""
        analytics_service.cache.clear = MagicMock(return_value=True)

        result = analytics_service.clear_cache()

        assert result["status"] == "success"
        assert "timestamp" in result

    def test_get_cache_stats(self, analytics_service):
        """测试获取缓存统计"""
        mock_stats = {"hits": 100, "misses": 10}
        analytics_service.cache.get_stats = MagicMock(return_value=mock_stats)

        result = analytics_service.get_cache_stats()

        assert result["cache_type"] == "analytics_cache"
        assert result["stats"] == mock_stats

    @patch(
        "src.services.analytics.analytics_service.AnalyticsService._generate_occupancy_trend"
    )
    def test_calculate_trend_occupancy(self, mock_trend, analytics_service):
        """测试计算出租率趋势"""
        mock_trend_data = [
            {"period": "2024-01", "occupancy_rate": 0.85},
            {"period": "2024-02", "occupancy_rate": 0.87},
        ]
        mock_trend.return_value = mock_trend_data

        # Mock数据库查询 - 使用 data_status 而不是 is_deleted
        mock_assets = [MagicMock(data_status="正常")]
        analytics_service.db.query.return_value.filter.return_value.all.return_value = (
            mock_assets
        )

        result = analytics_service.calculate_trend(
            trend_type="occupancy", time_dimension="monthly", filters={}
        )

        assert result == mock_trend_data

    @patch(
        "src.services.analytics.analytics_service.AnalyticsService._generate_area_trend"
    )
    def test_calculate_trend_area(self, mock_trend, analytics_service):
        """测试计算面积趋势"""
        mock_trend_data = [
            {"period": "2024-01", "total_area": 5000},
            {"period": "2024-02", "total_area": 5100},
        ]
        mock_trend.return_value = mock_trend_data

        # Mock数据库查询 - 使用 data_status
        mock_assets = [MagicMock(data_status="正常")]
        analytics_service.db.query.return_value.filter.return_value.all.return_value = (
            mock_assets
        )

        result = analytics_service.calculate_trend(
            trend_type="area", time_dimension="monthly", filters={}
        )

        assert result == mock_trend_data

    def test_calculate_distribution(self, analytics_service):
        """测试计算分布数据"""
        # Mock资产数据
        mock_assets = [
            MagicMock(
                property_nature="Commercial",
                rentable_area=1000,
                data_status="正常",
            ),
            MagicMock(
                property_nature="Residential",
                rentable_area=500,
                data_status="正常",
            ),
            MagicMock(
                property_nature="Commercial",
                rentable_area=800,
                data_status="正常",
            ),
        ]
        analytics_service.db.query.return_value.filter.return_value.all.return_value = (
            mock_assets
        )

        result = analytics_service.calculate_distribution(
            distribution_type="property_nature", filters={}
        )

        assert result["distribution_type"] == "property_nature"
        assert "data" in result
        assert result["total"] == 2  # Commercial 和 Residential 两种
        assert result["data"]["Commercial"]["count"] == 2
        assert result["data"]["Commercial"]["area"] == 1800
        assert result["data"]["Residential"]["count"] == 1

    @patch(
        "src.services.analytics.analytics_service.AnalyticsService._calculate_analytics"
    )
    @patch(
        "src.services.analytics.analytics_service.AnalyticsService._generate_cache_key"
    )
    def test_cache_is_set_after_calculation(
        self, mock_generate_key, mock_calculate, analytics_service
    ):
        """测试缓存设置逻辑（覆盖第71行）"""
        # Mock缓存未命中，需要计算并设置缓存
        analytics_service.cache.get = MagicMock(return_value=None)
        analytics_service.cache.set = MagicMock()
        mock_generate_key.return_value = "test_key"
        mock_calculate.return_value = {"total": 100}

        # 调用时使用缓存
        result = analytics_service.get_comprehensive_analytics(
            filters={}, should_use_cache=True
        )

        # 验证缓存被设置
        analytics_service.cache.set.assert_called_once_with(
            "test_key", {"total": 100}, ttl=3600
        )
        assert result == {"total": 100}

    def test_calculate_trend_unknown_type(self, analytics_service):
        """测试未知趋势类型返回空列表（覆盖第213行）"""
        # Mock数据库查询
        mock_assets = [MagicMock(data_status="正常")]
        analytics_service.db.query.return_value.filter.return_value.all.return_value = (
            mock_assets
        )

        result = analytics_service.calculate_trend(
            trend_type="unknown_type", time_dimension="monthly", filters={}
        )

        assert result == []

    @patch("src.services.analytics.area_service.AreaService")
    @patch("src.services.analytics.occupancy_service.OccupancyService")
    def test_clear_cache_exception_handling(
        self, mock_occupancy_cls, mock_area_cls, analytics_service
    ):
        """测试清除缓存时的异常处理（覆盖第157-158行）"""
        # Mock缓存清除时抛出异常
        analytics_service.cache.clear = MagicMock(side_effect=Exception("Cache error"))

        result = analytics_service.clear_cache()

        # 异常时应返回 status='failed' 和 error 信息
        assert result["status"] == "failed"
        assert result["cleared_keys"] == 0
        assert "error" in result
        assert "Cache error" in result["error"]
        assert "timestamp" in result

    def test_generate_occupancy_trend_directly(self, analytics_service):
        """测试直接调用出租率趋势生成（覆盖第221行）"""
        mock_assets = [MagicMock(data_status="正常")]
        result = analytics_service._generate_occupancy_trend(mock_assets, "monthly")

        assert isinstance(result, list)
        assert len(result) > 0
        assert result[0]["period"] == "2024-01"
        assert "occupancy_rate" in result[0]

    def test_generate_area_trend_directly(self, analytics_service):
        """测试直接调用面积趋势生成（覆盖第241行）"""
        mock_assets = [MagicMock(data_status="正常")]
        result = analytics_service._generate_area_trend(mock_assets, "monthly")

        assert isinstance(result, list)
        assert len(result) > 0
        assert result[0]["period"] == "2024-01"
        assert "total_rentable_area" in result[0]
