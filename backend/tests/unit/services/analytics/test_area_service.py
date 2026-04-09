"""
测试 AreaService (面积汇总计算服务)
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.analytics.area_service import AreaCalculationError, AreaService


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.execute = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.delete = MagicMock()
    db.flush = AsyncMock()
    return db


@pytest.fixture
def area_service(mock_db):
    """创建 AreaService 实例"""
    return AreaService(mock_db)


class TestAreaService:
    """测试 AreaService 类"""

    def test_init(self, mock_db):
        """测试服务初始化"""
        service = AreaService(mock_db)
        assert service.db == mock_db

    @pytest.mark.asyncio
    async def test_calculate_summary_with_aggregation(self, area_service, mock_db):
        """测试面积汇总聚合计算"""
        # Mock 查询结果
        mock_result = MagicMock()
        mock_result.total_assets = 10
        mock_result.total_land_area = 5000.0
        mock_result.total_rentable_area = 3000.0
        mock_result.total_rented_area = 2400.0
        mock_result.total_non_commercial_area = 500.0
        mock_result.assets_with_area_data = 8

        mock_exec_result = MagicMock()
        mock_exec_result.first.return_value = mock_result
        mock_db.execute.return_value = mock_exec_result

        # 执行计算
        result = await area_service.calculate_summary_with_aggregation(filters=None)

        # 验证结果
        assert result["total_assets"] == 10
        assert result["total_land_area"] == 5000.0
        assert result["total_rentable_area"] == 3000.0
        assert result["total_rented_area"] == 2400.0
        assert result["total_unrented_area"] == 600.0  # 3000-2400
        assert result["total_non_commercial_area"] == 500.0
        assert result["assets_with_area_data"] == 8
        assert result["overall_occupancy_rate"] == 80.0  # 2400/3000*100

    @pytest.mark.asyncio
    async def test_calculate_summary_with_aggregation_with_filters(
        self, area_service, mock_db
    ):
        """测试带筛选条件的面积汇总计算"""
        mock_result = MagicMock()
        mock_result.total_assets = 5
        mock_result.total_land_area = 2500.0
        mock_result.total_rentable_area = 1500.0
        mock_result.total_rented_area = 1200.0
        mock_result.total_non_commercial_area = 250.0
        mock_result.assets_with_area_data = 4

        mock_exec_result = MagicMock()
        mock_exec_result.first.return_value = mock_result
        mock_db.execute.return_value = mock_exec_result

        # 执行计算
        filters = {"data_status": "正常"}
        result = await area_service.calculate_summary_with_aggregation(filters=filters)

        # 验证结果和filter调用
        assert result["total_assets"] == 5

    @pytest.mark.asyncio
    async def test_calculate_summary_with_aggregation_zero_rentable_area(
        self, area_service, mock_db
    ):
        """测试可出租面积为0的情况"""
        mock_result = MagicMock()
        mock_result.total_assets = 0
        mock_result.total_land_area = 0.0
        mock_result.total_rentable_area = 0.0
        mock_result.total_rented_area = 0.0
        mock_result.total_non_commercial_area = 0.0
        mock_result.assets_with_area_data = 0

        mock_exec_result = MagicMock()
        mock_exec_result.first.return_value = mock_result
        mock_db.execute.return_value = mock_exec_result

        result = await area_service.calculate_summary_with_aggregation(filters=None)

        # 验证出租率为0
        assert result["overall_occupancy_rate"] == 0.0
        assert result["total_unrented_area"] == 0.0

    @pytest.mark.asyncio
    async def test_calculate_summary_with_aggregation_fallback_to_memory(
        self, area_service, mock_db
    ):
        """测试聚合查询失败时降级到内存计算"""
        # Mock 聚合查询抛出异常
        mock_db.execute.side_effect = Exception("Database error")

        # Mock 内存计算
        with patch.object(
            area_service,
            "_calculate_summary_in_memory",
            new_callable=AsyncMock,
            return_value={"total_assets": 10, "overall_occupancy_rate": 75.0},
        ) as mock_memory:
            result = await area_service.calculate_summary_with_aggregation(filters=None)

            # 验证降级到内存计算
            mock_memory.assert_called_once_with(None, party_filter=None)
            assert result["overall_occupancy_rate"] == 75.0

    @patch("src.services.analytics.area_service.asset_crud")
    @pytest.mark.asyncio
    async def test_calculate_summary_in_memory(self, mock_crud, area_service, mock_db):
        """测试内存计算模式"""
        # Mock 资产数据
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
        mock_crud.get_multi_with_search_async = AsyncMock(
            side_effect=[
            (mock_assets, None),
            ([], None),
            ]
        )

        result = await area_service._calculate_summary_in_memory(filters=None)

        # 验证结果
        assert result["total_assets"] == 2
        assert result["total_land_area"] == 1000.0
        assert result["total_rentable_area"] == 500.0
        assert result["total_rented_area"] == 400.0
        assert result["total_unrented_area"] == 100.0
        assert result["total_non_commercial_area"] == 80.0
        assert result["assets_with_area_data"] == 2
        assert result["overall_occupancy_rate"] == 80.0

    @patch("src.services.analytics.area_service.asset_crud")
    @pytest.mark.asyncio
    async def test_calculate_summary_in_memory_partial_data(self, mock_crud, area_service):
        """测试内存计算处理部分数据缺失的情况"""
        # Mock 部分字段缺失的资产数据
        mock_assets = [
            MagicMock(
                land_area=500.0,
                rentable_area=300.0,
                rented_area=240.0,
                unrented_area=None,  # 缺失
                non_commercial_area=None,  # 缺失
            ),
            MagicMock(
                land_area=None,  # 缺失
                rentable_area=200.0,
                rented_area=160.0,
                unrented_area=40.0,
                non_commercial_area=30.0,
            ),
        ]
        mock_crud.get_multi_with_search_async = AsyncMock(
            side_effect=[
            (mock_assets, None),
            ([], None),
            ]
        )

        result = await area_service._calculate_summary_in_memory(filters=None)

        # 验证结果 - 只统计有数据的字段
        assert result["total_assets"] == 2
        assert result["total_land_area"] == 500.0  # 只有第一个资产有数据
        assert result["assets_with_area_data"] == 1  # 只有第一个资产有土地面积
        assert result["overall_occupancy_rate"] == 80.0

    @patch("src.services.analytics.area_service.asset_crud")
    @pytest.mark.asyncio
    async def test_calculate_summary_in_memory_zero_rentable_area(
        self, mock_crud, area_service
    ):
        """测试内存计算可出租面积为0的情况"""
        mock_assets = [
            MagicMock(
                land_area=500.0,
                rentable_area=0.0,
                rented_area=0.0,
                unrented_area=0.0,
                non_commercial_area=50.0,
            )
        ]
        mock_crud.get_multi_with_search_async = AsyncMock(
            side_effect=[
            (mock_assets, None),
            ([], None),
            ]
        )

        result = await area_service._calculate_summary_in_memory(filters=None)

        # 验证出租率为0
        assert result["overall_occupancy_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_calculate_summary_in_memory_error(self, area_service):
        """测试内存计算失败时抛出异常"""
        with patch(
            "src.services.analytics.area_service.asset_crud.get_multi_with_search_async",
            side_effect=Exception("CRUD error"),
        ):
            with pytest.raises(AreaCalculationError) as excinfo:
                await area_service._calculate_summary_in_memory(filters=None)

            assert "面积汇总计算失败" in str(excinfo.value)

    @patch("src.services.analytics.area_service.asset_crud")
    @pytest.mark.asyncio
    async def test_calculate_summary_in_memory_rounding(self, mock_crud, area_service):
        """测试内存计算结果四舍五入"""
        mock_assets = [
            MagicMock(
                land_area=500.123,
                rentable_area=300.456,
                rented_area=240.789,
                unrented_area=60.0,
                non_commercial_area=50.999,
            )
        ]
        mock_crud.get_multi_with_search_async = AsyncMock(
            side_effect=[
            (mock_assets, None),
            ([], None),
            ]
        )

        result = await area_service._calculate_summary_in_memory(filters=None)

        # 验证四舍五入到2位小数
        assert result["total_land_area"] == 500.12
        assert result["total_rentable_area"] == 300.46
        assert result["total_rented_area"] == 240.79
        assert result["total_non_commercial_area"] == 51.0
