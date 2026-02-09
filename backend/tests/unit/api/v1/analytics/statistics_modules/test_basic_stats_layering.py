"""分层约束测试：basic_stats 路由应委托 BasicStatsService。"""

import inspect
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.schemas.statistics import BasicStatisticsResponse

pytestmark = pytest.mark.api


def test_basic_stats_api_module_should_not_use_crud_adapter_calls():
    """路由层不应直接调用 asset_crud。"""
    from src.api.v1.analytics.statistics_modules import basic_stats

    module_source = inspect.getsource(basic_stats)
    assert "asset_crud." not in module_source


@pytest.mark.asyncio
async def test_get_basic_statistics_should_delegate_to_service(mock_db):
    """基础统计路由应委托给 service.calculate_basic_statistics。"""
    from src.api.v1.analytics.statistics_modules.basic_stats import get_basic_statistics

    expected = BasicStatisticsResponse(
        total_assets=0,
        ownership_status={"confirmed": 0, "unconfirmed": 0, "partial": 0},
        property_nature={"commercial": 0, "non_commercial": 0},
        usage_status={"rented": 0, "self_used": 0, "vacant": 0},
        generated_at="2026-02-08T00:00:00",
        filters_applied={},
    )
    mock_service = MagicMock()
    mock_service.calculate_basic_statistics = AsyncMock(return_value=expected)

    result = await get_basic_statistics(
        ownership_status=None,
        property_nature=None,
        usage_status=None,
        ownership_id=None,
        db=mock_db,
        current_user=MagicMock(id="user-1"),
        service=mock_service,
    )

    assert result == expected
    mock_service.calculate_basic_statistics.assert_awaited_once_with(
        db=mock_db,
        ownership_status=None,
        property_nature=None,
        usage_status=None,
        ownership_id=None,
    )


@pytest.mark.asyncio
async def test_get_comprehensive_statistics_should_delegate_to_service(mock_db):
    """综合统计路由应委托给 service.calculate_comprehensive_statistics。"""
    from src.api.v1.analytics.statistics_modules.basic_stats import (
        get_comprehensive_statistics,
    )

    expected = {
        "success": True,
        "message": "综合统计数据获取成功",
        "data": {"total_assets": 0},
    }
    mock_service = MagicMock()
    mock_service.calculate_comprehensive_statistics = AsyncMock(return_value=expected)

    result = await get_comprehensive_statistics(
        should_include_deleted=False,
        db=mock_db,
        current_user=MagicMock(id="user-1"),
        service=mock_service,
    )

    assert result == expected
    mock_service.calculate_comprehensive_statistics.assert_awaited_once_with(
        db=mock_db,
        should_include_deleted=False,
    )
