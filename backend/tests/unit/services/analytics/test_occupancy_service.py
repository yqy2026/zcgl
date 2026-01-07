"""
测试 OccupancyService (出租率计算服务)
"""

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from src.services.analytics.occupancy_service import (
    OccupancyCalculationError,
    OccupancyService,
)


@pytest.fixture
def mock_db():
    """创建模拟数据库会话"""
    return MagicMock(spec=Session)


@pytest.fixture
def occupancy_service(mock_db):
    """创建 OccupancyService 实例"""
    return OccupancyService(mock_db)


class TestOccupancyService:
    """测试 OccupancyService 类"""

    def test_init(self, mock_db):
        """测试服务初始化"""
        service = OccupancyService(mock_db)
        assert service.db == mock_db

    def test_calculate_with_aggregation_no_filters(self, occupancy_service, mock_db):
        """测试无筛选条件的聚合计算"""
        # Mock 查询结果
        mock_result = MagicMock()
        mock_result.total_rentable_area = 1000.0
        mock_result.total_rented_area = 800.0
        mock_result.total_assets = 10
        mock_result.rentable_assets_count = 8

        mock_query = MagicMock()
        mock_query.with_entities.return_value.first.return_value = mock_result
        mock_db.query.return_value = mock_query

        # 执行计算
        result = occupancy_service.calculate_with_aggregation(filters=None)

        # 验证结果
        assert result["overall_rate"] == 80.0  # 800/1000*100
        assert result["total_rentable_area"] == 1000.0
        assert result["total_rented_area"] == 800.0
        assert result["total_assets"] == 10
        assert result["rentable_assets_count"] == 8

    def test_calculate_with_aggregation_with_filters(self, occupancy_service, mock_db):
        """测试带筛选条件的聚合计算"""
        # Mock 查询链
        mock_result = MagicMock()
        mock_result.total_rentable_area = 500.0
        mock_result.total_rented_area = 400.0
        mock_result.total_assets = 5
        mock_result.rentable_assets_count = 4

        mock_query = MagicMock()
        mock_filtered = MagicMock()
        mock_query.filter.return_value = mock_filtered
        mock_filtered.with_entities.return_value.first.return_value = mock_result
        mock_db.query.return_value = mock_query

        # 执行计算
        filters = {"data_status": "正常"}
        result = occupancy_service.calculate_with_aggregation(filters=filters)

        # 验证结果和filter调用
        assert result["overall_rate"] == 80.0
        mock_query.filter.assert_called_once()

    def test_calculate_with_aggregation_zero_rentable_area(
        self, occupancy_service, mock_db
    ):
        """测试可出租面积为0的情况"""
        mock_result = MagicMock()
        mock_result.total_rentable_area = 0.0
        mock_result.total_rented_area = 0.0
        mock_result.total_assets = 0
        mock_result.rentable_assets_count = 0

        mock_query = MagicMock()
        mock_query.with_entities.return_value.first.return_value = mock_result
        mock_db.query.return_value = mock_query

        result = occupancy_service.calculate_with_aggregation(filters=None)

        # 验证出租率为0
        assert result["overall_rate"] == 0.0

    def test_calculate_with_aggregation_fallback_to_memory(
        self, occupancy_service, mock_db
    ):
        """测试聚合查询失败时降级到内存计算"""
        # Mock 聚合查询抛出异常
        mock_query = MagicMock()
        mock_query.with_entities.side_effect = Exception("Database error")
        mock_db.query.return_value = mock_query

        # Mock 内存计算
        with patch.object(
            occupancy_service,
            "_calculate_in_memory",
            return_value={"overall_rate": 75.0},
        ) as mock_memory:
            result = occupancy_service.calculate_with_aggregation(filters=None)

            # 验证降级到内存计算
            mock_memory.assert_called_once_with(None)
            assert result["overall_rate"] == 75.0

    @pytest.mark.skip(reason="需要集成测试环境，单元测试mock链式调用复杂")
    def test_calculate_category_with_aggregation(self, occupancy_service, mock_db):
        """测试分类聚合计算"""
        # 这个测试需要集成测试环境，单元测试中SQLAlchemy链式调用mock过于复杂
        pass

    @pytest.mark.skip(reason="需要集成测试环境，单元测试mock链式调用复杂")
    def test_calculate_category_with_aggregation_unknown_category(
        self, occupancy_service, mock_db
    ):
        """测试未知分类的处理"""
        # 这个测试需要集成测试环境，单元测试中SQLAlchemy链式调用mock过于复杂
        pass

    @patch("src.services.analytics.occupancy_service.asset_crud")
    def test_calculate_in_memory(self, mock_crud, occupancy_service, mock_db):
        """测试内存计算模式"""
        # Mock 资产数据
        mock_assets = [
            MagicMock(rentable_area=100.0, rented_area=80.0),
            MagicMock(rentable_area=200.0, rented_area=150.0),
        ]
        mock_crud.get_multi_with_search.side_effect = [
            (mock_assets, None),  # 第一次调用返回数据
            ([], None),  # 第二次调用返回空，结束循环
        ]

        # Mock OccupancyRateCalculator
        mock_stats = {
            "overall_rate": 76.67,
            "total_rentable_area": 300.0,
            "total_rented_area": 230.0,
            "total_unrented_area": 70.0,
            "asset_count": 2,
            "rentable_asset_count": 2,
        }
        with patch(
            "src.services.analytics.occupancy_service.OccupancyRateCalculator.calculate_overall_occupancy_rate",
            return_value=mock_stats,
        ):
            result = occupancy_service._calculate_in_memory(filters=None)

            # 验证结果
            assert result["overall_rate"] == 76.67
            assert result["asset_count"] == 2

    @patch("src.services.analytics.occupancy_service.asset_crud")
    def test_calculate_category_in_memory(self, mock_crud, occupancy_service):
        """测试分类内存计算"""
        # Mock 资产数据
        mock_assets = [
            MagicMock(property_nature="商业", rentable_area=100.0, rented_area=80.0),
            MagicMock(property_nature="住宅", rentable_area=200.0, rented_area=150.0),
        ]
        mock_crud.get_multi_with_search.side_effect = [
            (mock_assets, None),
            ([], None),
        ]

        # Mock OccupancyRateCalculator
        mock_category_stats = {
            "商业": {"overall_rate": 80.0},
            "住宅": {"overall_rate": 75.0},
        }
        with patch(
            "src.services.analytics.occupancy_service.OccupancyRateCalculator.calculate_occupancy_by_category",
            return_value=mock_category_stats,
        ):
            result = occupancy_service._calculate_category_in_memory(
                category_field="property_nature", filters=None
            )

            # 验证结果
            assert "商业" in result
            assert "住宅" in result

    def test_calculate_in_memory_error(self, occupancy_service):
        """测试内存计算失败时抛出异常"""
        with patch(
            "src.services.analytics.occupancy_service.asset_crud.get_multi_with_search",
            side_effect=Exception("CRUD error"),
        ):
            with pytest.raises(OccupancyCalculationError) as excinfo:
                occupancy_service._calculate_in_memory(filters=None)

            assert "出租率计算失败" in str(excinfo.value)
