"""分层约束测试：distribution 路由应委托 DistributionService。"""

import inspect
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.schemas.statistics import ChartDataItem, DistributionResponse

pytestmark = pytest.mark.api


def test_distribution_api_module_should_not_use_crud_adapter_calls():
    """路由层不应直接调用 asset_crud。"""
    from src.api.v1.analytics.statistics_modules import distribution

    module_source = inspect.getsource(distribution)
    assert "asset_crud." not in module_source


@pytest.mark.asyncio
async def test_get_ownership_distribution_should_delegate_to_service(mock_db):
    """权属分布路由应委托给 service.get_ownership_distribution。"""
    from src.api.v1.analytics.statistics_modules.distribution import (
        get_ownership_distribution,
    )

    expected = DistributionResponse(
        total=3,
        categories=[
            ChartDataItem(name="已确权", value=1, percentage=33.33),
            ChartDataItem(name="未确权", value=1, percentage=33.33),
            ChartDataItem(name="部分确权", value=1, percentage=33.33),
        ],
    )
    mock_service = MagicMock()
    mock_service.get_ownership_distribution = AsyncMock(return_value=expected)

    result = await get_ownership_distribution(
        db=mock_db,
        current_user=MagicMock(id="user-1"),
        service=mock_service,
    )

    assert result == expected
    mock_service.get_ownership_distribution.assert_awaited_once_with(db=mock_db)


@pytest.mark.asyncio
async def test_get_asset_distribution_should_delegate_to_service(mock_db):
    """资产分布路由应委托给 service.get_asset_distribution。"""
    from src.api.v1.analytics.statistics_modules.distribution import (
        get_asset_distribution,
    )

    expected = {
        "success": True,
        "message": "资产分布统计数据获取成功",
        "data": {"total_assets": 0},
    }
    mock_service = MagicMock()
    mock_service.get_asset_distribution = AsyncMock(return_value=expected)

    result = await get_asset_distribution(
        group_by="ownership_status",
        should_include_deleted=False,
        db=mock_db,
        current_user=MagicMock(id="user-1"),
        service=mock_service,
    )

    assert result == expected
    mock_service.get_asset_distribution.assert_awaited_once_with(
        db=mock_db,
        group_by="ownership_status",
        should_include_deleted=False,
    )
