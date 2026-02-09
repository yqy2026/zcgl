"""
测试 OccupancyService（异步出租率计算服务）。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.analytics.occupancy_service import (
    OccupancyCalculationError,
    OccupancyService,
)

pytestmark = pytest.mark.asyncio


@pytest.fixture
def occupancy_service(mock_db):
    return OccupancyService(mock_db)


def _mock_execute_result(*, first=None, all_values=None):
    result = MagicMock()
    result.first.return_value = first
    result.all.return_value = [] if all_values is None else all_values
    return result


class TestOccupancyService:
    def test_init(self, mock_db):
        service = OccupancyService(mock_db)
        assert service.db == mock_db

    async def test_calculate_with_aggregation_no_filters(
        self, occupancy_service, mock_db
    ):
        mock_row = MagicMock(
            total_rentable_area=1000.0,
            total_rented_area=800.0,
            total_assets=10,
            rentable_assets_count=8,
        )
        mock_db.execute = AsyncMock(return_value=_mock_execute_result(first=mock_row))

        result = await occupancy_service.calculate_with_aggregation(filters=None)

        assert result["overall_rate"] == 80.0
        assert result["total_rentable_area"] == 1000.0
        assert result["total_rented_area"] == 800.0
        assert result["total_assets"] == 10
        assert result["rentable_assets_count"] == 8
        assert result["calculation_method"] == "aggregation"

    async def test_calculate_with_aggregation_with_filters(
        self, occupancy_service, mock_db
    ):
        mock_row = MagicMock(
            total_rentable_area=500.0,
            total_rented_area=400.0,
            total_assets=5,
            rentable_assets_count=4,
        )
        mock_db.execute = AsyncMock(return_value=_mock_execute_result(first=mock_row))

        result = await occupancy_service.calculate_with_aggregation(
            filters={"data_status": "正常"}
        )

        assert result["overall_rate"] == 80.0
        mock_db.execute.assert_awaited_once()

    async def test_calculate_with_aggregation_zero_rentable_area(
        self, occupancy_service, mock_db
    ):
        mock_row = MagicMock(
            total_rentable_area=0.0,
            total_rented_area=0.0,
            total_assets=0,
            rentable_assets_count=0,
        )
        mock_db.execute = AsyncMock(return_value=_mock_execute_result(first=mock_row))

        result = await occupancy_service.calculate_with_aggregation(filters=None)

        assert result["overall_rate"] == 0.0

    async def test_calculate_with_aggregation_fallback_to_memory(
        self, occupancy_service, mock_db
    ):
        mock_db.execute = AsyncMock(side_effect=Exception("Database error"))

        with patch.object(
            occupancy_service,
            "_calculate_in_memory",
            new=AsyncMock(return_value={"overall_rate": 75.0}),
        ) as mock_memory:
            result = await occupancy_service.calculate_with_aggregation(filters=None)

        mock_memory.assert_awaited_once_with(None)
        assert result["overall_rate"] == 75.0
        assert result["calculation_method"] == "memory_fallback"

    async def test_calculate_category_with_aggregation(self, occupancy_service, mock_db):
        mock_rows = [
            MagicMock(
                category="商业",
                total_rentable_area=1000.0,
                total_rented_area=800.0,
                total_assets=3,
                rentable_assets_count=3,
            ),
            MagicMock(
                category="住宅",
                total_rentable_area=500.0,
                total_rented_area=250.0,
                total_assets=2,
                rentable_assets_count=2,
            ),
        ]
        mock_db.execute = AsyncMock(return_value=_mock_execute_result(all_values=mock_rows))

        result = await occupancy_service.calculate_category_with_aggregation(
            category_field="property_nature",
            filters=None,
        )

        assert result["商业"]["overall_rate"] == 80.0
        assert result["住宅"]["overall_rate"] == 50.0

    @patch("src.services.analytics.occupancy_service.asset_crud")
    async def test_calculate_in_memory(self, mock_crud, occupancy_service):
        mock_assets = [
            MagicMock(rentable_area=100.0, rented_area=80.0),
            MagicMock(rentable_area=200.0, rented_area=150.0),
        ]
        mock_crud.get_multi_with_search_async = AsyncMock(
            side_effect=[
                (mock_assets, None),
                ([], None),
            ]
        )

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
            result = await occupancy_service._calculate_in_memory(filters=None)

        assert result["overall_rate"] == 76.67
        assert result["asset_count"] == 2

    @patch("src.services.analytics.occupancy_service.asset_crud")
    async def test_calculate_category_in_memory(self, mock_crud, occupancy_service):
        mock_assets = [
            MagicMock(property_nature="商业", rentable_area=100.0, rented_area=80.0),
            MagicMock(property_nature="住宅", rentable_area=200.0, rented_area=150.0),
        ]
        mock_crud.get_multi_with_search_async = AsyncMock(
            side_effect=[
                (mock_assets, None),
                ([], None),
            ]
        )

        mock_category_stats = {
            "商业": {"overall_rate": 80.0},
            "住宅": {"overall_rate": 75.0},
        }
        with patch(
            "src.services.analytics.occupancy_service.OccupancyRateCalculator.calculate_occupancy_by_category",
            return_value=mock_category_stats,
        ):
            result = await occupancy_service._calculate_category_in_memory(
                category_field="property_nature",
                filters=None,
            )

        assert "商业" in result
        assert "住宅" in result

    async def test_calculate_in_memory_error(self, occupancy_service):
        with patch(
            "src.services.analytics.occupancy_service.asset_crud.get_multi_with_search_async",
            new=AsyncMock(side_effect=Exception("CRUD error")),
        ):
            with pytest.raises(OccupancyCalculationError) as excinfo:
                await occupancy_service._calculate_in_memory(filters=None)

        assert "出租率计算失败" in str(excinfo.value)
