"""分层约束测试：area_stats 路由应委托 AreaStatsService。"""

import inspect
import re
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.schemas.statistics import AreaSummaryResponse

pytestmark = pytest.mark.api


def test_area_stats_api_module_should_not_use_crud_adapter_calls():
    """路由层不应直接调用 asset_crud。"""
    from src.api.v1.analytics.statistics_modules import area_stats

    module_source = inspect.getsource(area_stats)
    assert "asset_crud." not in module_source


def test_area_stats_module_should_import_authz_dependency() -> None:
    """area_stats 路由应引入统一 ABAC 依赖。"""
    from src.api.v1.analytics.statistics_modules import area_stats as module

    module_source = Path(module.__file__).read_text(encoding="utf-8")
    assert "AuthzContext" in module_source
    assert "require_authz" in module_source


def test_area_stats_endpoints_should_use_require_authz() -> None:
    """area_stats 关键端点应接入 require_authz。"""
    from src.api.v1.analytics.statistics_modules import area_stats as module

    module_source = Path(module.__file__).read_text(encoding="utf-8")
    expected_patterns = [
        r"async def get_area_summary[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"analytics\"",
        r"async def get_area_statistics[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"analytics\"",
    ]
    for pattern in expected_patterns:
        assert re.search(pattern, module_source), pattern


@pytest.mark.asyncio
async def test_get_area_summary_should_delegate_to_service(mock_db):
    """面积汇总路由应委托给 service.calculate_area_summary。"""
    from src.api.v1.analytics.statistics_modules.area_stats import get_area_summary

    expected = AreaSummaryResponse(
        total_area=0.0,
        rentable_area=0.0,
        rented_area=0.0,
        unrented_area=0.0,
        occupancy_rate=0.0,
    )
    mock_service = MagicMock()
    mock_service.calculate_area_summary = AsyncMock(return_value=expected)

    result = await get_area_summary(
        should_include_deleted=False,
        should_use_aggregation=True,
        db=mock_db,
        current_user=MagicMock(id="user-1"),
        service=mock_service,
    )

    assert result == expected
    mock_service.calculate_area_summary.assert_awaited_once_with(
        db=mock_db,
        should_include_deleted=False,
        should_use_aggregation=True,
    )


@pytest.mark.asyncio
async def test_get_area_statistics_should_delegate_to_service(mock_db):
    """面积统计路由应委托给 service.calculate_area_statistics。"""
    from src.api.v1.analytics.statistics_modules.area_stats import get_area_statistics

    expected = {
        "success": True,
        "message": "面积统计数据获取成功",
        "data": {"total_assets": 0},
    }
    mock_service = MagicMock()
    mock_service.calculate_area_statistics = AsyncMock(return_value=expected)

    result = await get_area_statistics(
        ownership_status=None,
        property_nature=None,
        usage_status=None,
        should_include_deleted=False,
        db=mock_db,
        current_user=MagicMock(id="user-1"),
        service=mock_service,
    )

    assert result == expected
    mock_service.calculate_area_statistics.assert_awaited_once_with(
        db=mock_db,
        ownership_status=None,
        property_nature=None,
        usage_status=None,
        should_include_deleted=False,
    )
