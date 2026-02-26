"""分层约束测试：monitoring 路由应接入统一 ABAC 依赖。"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.api


def _read_module_source() -> str:
    from src.api.v1.system import monitoring as module

    return Path(module.__file__).read_text(encoding="utf-8")


def test_monitoring_module_should_import_authz_dependency() -> None:
    """monitoring 路由应引入统一 ABAC 依赖。"""
    module_source = _read_module_source()
    assert "AuthzContext" in module_source
    assert "require_authz" in module_source


def test_monitoring_endpoints_should_use_require_authz() -> None:
    """monitoring 关键端点应接入 require_authz。"""
    module_source = _read_module_source()
    expected_patterns = [
        r"async def report_route_performance[\s\S]*?require_authz\([\s\S]*?action=\"create\"[\s\S]*?resource_type=\"system_monitoring\"[\s\S]*?resource_context=_SYSTEM_MONITORING_CREATE_RESOURCE_CONTEXT",
        r"def get_system_health[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"system_monitoring\"",
        r"async def get_performance_dashboard[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"system_monitoring\"",
        r"async def get_system_metrics[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"system_monitoring\"",
        r"async def get_application_metrics[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"system_monitoring\"",
        r"async def get_system_monitoring_dashboard[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"system_monitoring\"",
        r"async def trigger_metrics_collection[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_type=\"system_monitoring\"[\s\S]*?resource_context=_SYSTEM_MONITORING_UPDATE_RESOURCE_CONTEXT",
    ]

    for pattern in expected_patterns:
        assert re.search(pattern, module_source), pattern


def test_monitoring_create_authz_context_should_use_unscoped_sentinel() -> None:
    from src.api.v1.system import monitoring as module

    expected_create_sentinel = "__unscoped__:system_monitoring:create"
    assert module._SYSTEM_MONITORING_CREATE_UNSCOPED_PARTY_ID == expected_create_sentinel
    assert module._SYSTEM_MONITORING_CREATE_RESOURCE_CONTEXT == {
        "party_id": expected_create_sentinel,
        "owner_party_id": expected_create_sentinel,
        "manager_party_id": expected_create_sentinel,
    }

    expected_update_sentinel = "__unscoped__:system_monitoring:update"
    assert module._SYSTEM_MONITORING_UPDATE_UNSCOPED_PARTY_ID == expected_update_sentinel
    assert module._SYSTEM_MONITORING_UPDATE_RESOURCE_CONTEXT == {
        "party_id": expected_update_sentinel,
        "owner_party_id": expected_update_sentinel,
        "manager_party_id": expected_update_sentinel,
    }
