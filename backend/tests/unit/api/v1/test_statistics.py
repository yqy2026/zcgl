from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.api.v1.analytics.statistics import router as statistics_router
from src.api.v1.analytics.statistics_modules.basic_stats import (
    clear_statistics_cache,
    get_basic_statistics,
    get_cache_info,
    get_comprehensive_statistics,
)
from src.middleware.auth import DataScopeContext

pytestmark = pytest.mark.api

EXPECTED_STATISTICS_PATHS = {
    "/basic",
    "/summary",
    "/dashboard",
    "/comprehensive",
    "/cache/clear",
    "/cache/info",
    "/ownership-distribution",
    "/property-nature-distribution",
    "/usage-status-distribution",
    "/asset-distribution",
    "/occupancy-rate/overall",
    "/occupancy-rate/by-category",
    "/occupancy-rate",
    "/area-summary",
    "/area-statistics",
    "/financial-summary",
    "/trend/{metric}",
}


def test_statistics_router_registers_expected_paths():
    route_paths = {route.path for route in statistics_router.routes}
    assert route_paths == EXPECTED_STATISTICS_PATHS


def test_statistics_router_registers_expected_methods():
    methods_by_path = {route.path: route.methods for route in statistics_router.routes}
    assert methods_by_path["/cache/clear"] == {"POST"}
    assert methods_by_path["/cache/info"] == {"GET"}
    assert methods_by_path["/trend/{metric}"] == {"GET"}


@pytest.mark.asyncio
async def test_clear_statistics_cache_returns_cleared_count():
    cache_manager = MagicMock()
    cache_manager.clear_pattern = AsyncMock(return_value=6)

    with patch(
        "src.api.v1.analytics.statistics_modules.basic_stats.get_cache_manager",
        new=AsyncMock(return_value=cache_manager),
    ):
        result = await clear_statistics_cache(current_user=MagicMock())

    assert result["success"] is True
    assert result["data"]["cleared_count"] == 6
    cache_manager.clear_pattern.assert_awaited_once_with("statistics:*")


@pytest.mark.asyncio
async def test_get_cache_info_returns_backend_type():
    class FakeBackend:
        pass

    cache_manager = MagicMock()
    cache_manager.backend = FakeBackend()

    with patch(
        "src.api.v1.analytics.statistics_modules.basic_stats.get_cache_manager",
        new=AsyncMock(return_value=cache_manager),
    ):
        result = await get_cache_info(current_user=MagicMock())

    assert result["success"] is True
    assert result["data"]["cache_backend"]["backend_type"] == "FakeBackend"
    assert result["data"]["cache_backend"]["namespace"] == "statistics"


@pytest.mark.asyncio
async def test_get_comprehensive_statistics_delegates_to_service(mock_db):
    expected = {"summary": "ok"}
    mock_service = MagicMock()
    mock_service.calculate_comprehensive_statistics = AsyncMock(return_value=expected)
    scope_ctx = DataScopeContext(
        scope_mode="manager",
        allowed_binding_types=["owner", "manager"],
        owner_party_ids=["owner-1"],
        manager_party_ids=["manager-1"],
        effective_party_ids=["manager-1"],
        source="query",
    )

    result = await get_comprehensive_statistics(
        should_include_deleted=True,
        db=mock_db,
        current_user=MagicMock(),
        service=mock_service,
        _scope_ctx=scope_ctx,
    )

    assert result == expected
    kwargs = mock_service.calculate_comprehensive_statistics.await_args.kwargs
    assert kwargs["db"] is mock_db
    assert kwargs["should_include_deleted"] is True
    assert kwargs["party_filter"].filter_mode == "manager"


@pytest.mark.asyncio
async def test_get_basic_statistics_delegates_scope_filter(mock_db):
    expected = MagicMock()
    mock_service = MagicMock()
    mock_service.calculate_basic_statistics = AsyncMock(return_value=expected)
    scope_ctx = DataScopeContext(
        scope_mode="owner",
        allowed_binding_types=["owner", "manager"],
        owner_party_ids=["owner-1"],
        manager_party_ids=["manager-1"],
        effective_party_ids=["owner-1"],
        source="query",
    )

    result = await get_basic_statistics(
        ownership_status=None,
        property_nature=None,
        usage_status=None,
        ownership_id=None,
        db=mock_db,
        current_user=MagicMock(),
        service=mock_service,
        _scope_ctx=scope_ctx,
    )

    assert result is expected
    kwargs = mock_service.calculate_basic_statistics.await_args.kwargs
    assert kwargs["party_filter"].filter_mode == "owner"
