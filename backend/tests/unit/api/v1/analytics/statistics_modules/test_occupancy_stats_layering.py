"""分层约束测试：occupancy_stats 路由应走统一 ABAC 依赖。"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.api


def _read_module_source() -> str:
    from src.api.v1.analytics.statistics_modules import occupancy_stats as module

    return Path(module.__file__).read_text(encoding="utf-8")


def test_occupancy_stats_module_should_import_authz_dependency() -> None:
    """occupancy_stats 路由应引入统一 ABAC 依赖。"""
    module_source = _read_module_source()
    assert "AuthzContext" in module_source
    assert "require_authz" in module_source


def test_occupancy_stats_endpoints_should_use_require_authz() -> None:
    """occupancy_stats 关键端点应接入 require_authz。"""
    module_source = _read_module_source()
    expected_patterns = [
        r"async def get_overall_occupancy_rate[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"analytics\"",
        r"async def get_occupancy_rate_by_category[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"analytics\"",
        r"async def get_occupancy_rate_statistics[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"analytics\"",
    ]
    for pattern in expected_patterns:
        assert re.search(pattern, module_source), pattern
