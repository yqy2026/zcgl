"""分层约束测试：basic_stats 路由应委托 BasicStatsService。"""

import inspect
import re
from pathlib import Path
from unittest.mock import ANY, AsyncMock, MagicMock

import pytest

from src.schemas.statistics import BasicStatisticsResponse

pytestmark = pytest.mark.api


def test_basic_stats_api_module_should_not_use_crud_adapter_calls():
    """路由层不应直接调用 asset_crud。"""
    from src.api.v1.analytics.statistics_modules import basic_stats

    module_source = inspect.getsource(basic_stats)
    assert "asset_crud." not in module_source


def test_basic_stats_module_should_import_authz_dependency() -> None:
    """basic_stats 路由应引入统一 ABAC 依赖。"""
    from src.api.v1.analytics.statistics_modules import basic_stats as module

    module_source = Path(module.__file__).read_text(encoding="utf-8")
    assert "AuthzContext" in module_source
    assert "require_authz" in module_source


def test_basic_stats_key_endpoints_should_use_require_authz() -> None:
    """basic_stats 关键端点应接入 require_authz。"""
    from src.api.v1.analytics.statistics_modules import basic_stats as module

    module_source = Path(module.__file__).read_text(encoding="utf-8")
    expected_patterns = [
        r"async def get_basic_statistics[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"analytics\"",
        r"async def get_statistics_summary[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"analytics\"",
        r"async def get_dashboard_data[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"analytics\"",
        r"async def get_comprehensive_statistics[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"analytics\"",
        r"async def clear_statistics_cache[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_type=\"analytics\"[\s\S]*?resource_context=_ANALYTICS_UPDATE_RESOURCE_CONTEXT",
        r"async def get_cache_info[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"analytics\"",
    ]
    for pattern in expected_patterns:
        assert re.search(pattern, module_source), pattern


def test_basic_stats_unscoped_update_context_should_be_defined() -> None:
    from src.api.v1.analytics.statistics_modules import basic_stats as module

    expected_sentinel = "__unscoped__:analytics:update"
    assert module._ANALYTICS_UPDATE_UNSCOPED_PARTY_ID == expected_sentinel
    assert module._ANALYTICS_UPDATE_RESOURCE_CONTEXT == {
        "party_id": expected_sentinel,
        "owner_party_id": expected_sentinel,
        "manager_party_id": expected_sentinel,
    }


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
        _scope_ctx=MagicMock(
            scope_mode="owner",
            owner_party_ids=["owner-party-1"],
            manager_party_ids=[],
            effective_party_ids=["owner-party-1"],
        ),
        _authz_ctx=MagicMock(),
    )

    assert result == expected
    mock_service.calculate_basic_statistics.assert_awaited_once_with(
        db=mock_db,
        ownership_status=None,
        property_nature=None,
        usage_status=None,
        ownership_id=None,
        party_filter=ANY,
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
        _scope_ctx=MagicMock(
            scope_mode="owner",
            owner_party_ids=["owner-party-1"],
            manager_party_ids=[],
            effective_party_ids=["owner-party-1"],
        ),
        _authz_ctx=MagicMock(),
    )

    assert result == expected
    mock_service.calculate_comprehensive_statistics.assert_awaited_once_with(
        db=mock_db,
        should_include_deleted=False,
        party_filter=ANY,
    )
