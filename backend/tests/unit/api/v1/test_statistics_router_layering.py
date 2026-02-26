"""分层约束测试：statistics 聚合路由不应重复挂载 ABAC 依赖。"""

from pathlib import Path

import pytest

pytestmark = pytest.mark.api


def _read_module_source() -> str:
    from src.api.v1.analytics import statistics as module

    return Path(module.__file__).read_text(encoding="utf-8")


def test_statistics_router_module_should_not_import_authz_dependency() -> None:
    """统计聚合路由不应引入 require_authz（由子路由端点自行声明）。"""
    module_source = _read_module_source()
    assert "AuthzContext" not in module_source
    assert "require_authz" not in module_source


def test_statistics_router_include_routes_should_not_attach_extra_dependencies() -> None:
    """统计聚合路由 include_router 时不应叠加 mount-level dependencies。"""
    module_source = _read_module_source()
    expected_lines = [
        "router.include_router(basic_stats_router)",
        "router.include_router(distribution_router)",
        "router.include_router(occupancy_stats_router)",
        "router.include_router(area_stats_router)",
        "router.include_router(financial_stats_router)",
        "router.include_router(trend_stats_router)",
    ]
    for line in expected_lines:
        assert line in module_source, line
    assert "dependencies=[" not in module_source
