"""分层约束测试：analytics 路由应走统一 ABAC 依赖。"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.api


def _read_module_source() -> str:
    from src.api.v1.analytics import analytics as module

    return Path(module.__file__).read_text(encoding="utf-8")


def test_analytics_module_should_import_authz_dependency() -> None:
    """analytics 路由应引入统一 ABAC 依赖。"""
    module_source = _read_module_source()
    assert "AuthzContext" in module_source
    assert "require_authz" in module_source


def test_analytics_business_endpoints_should_use_require_authz() -> None:
    """analytics 业务端点应接入统一 ABAC 依赖。"""
    module_source = _read_module_source()
    expected_patterns = [
        r"async def get_comprehensive_analytics[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"analytics\"",
        r"async def get_cache_stats[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"analytics\"",
        r"async def clear_cache[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_type=\"analytics\"[\s\S]*?resource_context=_ANALYTICS_UPDATE_RESOURCE_CONTEXT",
        r"async def get_trend_data[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"analytics\"",
        r"async def get_distribution_data[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"analytics\"",
        r"async def export_analytics[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"analytics\"",
    ]
    for pattern in expected_patterns:
        assert re.search(pattern, module_source), pattern


def test_analytics_unscoped_update_context_should_be_defined() -> None:
    from src.api.v1.analytics import analytics as module

    expected_sentinel = "__unscoped__:analytics:update"
    assert module._ANALYTICS_UPDATE_UNSCOPED_PARTY_ID == expected_sentinel
    assert module._ANALYTICS_UPDATE_RESOURCE_CONTEXT == {
        "party_id": expected_sentinel,
        "owner_party_id": expected_sentinel,
        "manager_party_id": expected_sentinel,
    }
