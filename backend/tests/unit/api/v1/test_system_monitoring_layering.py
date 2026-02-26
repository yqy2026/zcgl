"""分层约束测试：system_monitoring 子模块应接入统一 ABAC 依赖。"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.api


def _read_endpoints_source() -> str:
    from src.api.v1.system.system_monitoring import endpoints as module

    return Path(module.__file__).read_text(encoding="utf-8")


def _read_database_endpoints_source() -> str:
    from src.api.v1.system.system_monitoring import database_endpoints as module

    return Path(module.__file__).read_text(encoding="utf-8")


def test_system_monitoring_endpoints_module_should_import_authz_dependency() -> None:
    """system_monitoring/endpoints.py 应引入统一 ABAC 依赖。"""
    module_source = _read_endpoints_source()
    assert "AuthzContext" in module_source
    assert "require_authz" in module_source


def test_system_monitoring_endpoints_should_use_require_authz() -> None:
    """system_monitoring/endpoints.py 关键端点应接入 require_authz。"""
    module_source = _read_endpoints_source()
    expected_patterns = [
        r"def get_system_metrics[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"system_monitoring\"",
        r"def get_application_metrics[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"system_monitoring\"",
        r"async def get_health_status[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"system_monitoring\"",
        r"def get_history[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"system_monitoring\"",
        r"def get_performance_alerts[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"system_monitoring\"",
        r"def resolve_alert[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_type=\"system_monitoring\"",
        r"async def get_monitoring_dashboard[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"system_monitoring\"",
        r"def trigger_metrics_collection[\s\S]*?require_authz\([\s\S]*?action=\"create\"[\s\S]*?resource_type=\"system_monitoring\"[\s\S]*?resource_context=_SYSTEM_MONITORING_CREATE_RESOURCE_CONTEXT",
        r"def get_encryption_status[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"system_monitoring\"",
    ]
    for pattern in expected_patterns:
        assert re.search(pattern, module_source), pattern


def test_system_monitoring_create_authz_context_should_use_unscoped_sentinel() -> None:
    from src.api.v1.system.system_monitoring import endpoints as module

    expected_sentinel = "__unscoped__:system_monitoring:create"
    assert module._SYSTEM_MONITORING_CREATE_UNSCOPED_PARTY_ID == expected_sentinel
    assert module._SYSTEM_MONITORING_CREATE_RESOURCE_CONTEXT == {
        "party_id": expected_sentinel,
        "owner_party_id": expected_sentinel,
        "manager_party_id": expected_sentinel,
    }


def test_system_monitoring_database_endpoints_module_should_import_authz_dependency() -> None:
    """system_monitoring/database_endpoints.py 应引入统一 ABAC 依赖。"""
    module_source = _read_database_endpoints_source()
    assert "AuthzContext" in module_source
    assert "require_authz" in module_source


def test_system_monitoring_database_endpoints_should_use_require_authz() -> None:
    """system_monitoring/database_endpoints.py 关键端点应接入 require_authz。"""
    module_source = _read_database_endpoints_source()
    expected_patterns = [
        r"async def get_database_health_metrics[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"system_monitoring\"",
        r"def get_slow_queries[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"system_monitoring\"",
        r"def optimize_database[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_type=\"system_monitoring\"[\s\S]*?resource_context=_SYSTEM_MONITORING_UPDATE_RESOURCE_CONTEXT",
        r"def cleanup_database[\s\S]*?require_authz\([\s\S]*?action=\"delete\"[\s\S]*?resource_type=\"system_monitoring\"[\s\S]*?resource_context=_SYSTEM_MONITORING_DELETE_RESOURCE_CONTEXT",
        r"def get_connection_pool_status[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"system_monitoring\"",
    ]
    for pattern in expected_patterns:
        assert re.search(pattern, module_source), pattern


def test_system_monitoring_database_write_authz_context_should_use_unscoped_sentinel() -> None:
    from src.api.v1.system.system_monitoring import database_endpoints as module

    expected_update_sentinel = "__unscoped__:system_monitoring:update"
    assert (
        module._SYSTEM_MONITORING_UPDATE_UNSCOPED_PARTY_ID
        == expected_update_sentinel
    )
    assert module._SYSTEM_MONITORING_UPDATE_RESOURCE_CONTEXT == {
        "party_id": expected_update_sentinel,
        "owner_party_id": expected_update_sentinel,
        "manager_party_id": expected_update_sentinel,
    }

    expected_delete_sentinel = "__unscoped__:system_monitoring:delete"
    assert (
        module._SYSTEM_MONITORING_DELETE_UNSCOPED_PARTY_ID
        == expected_delete_sentinel
    )
    assert module._SYSTEM_MONITORING_DELETE_RESOURCE_CONTEXT == {
        "party_id": expected_delete_sentinel,
        "owner_party_id": expected_delete_sentinel,
        "manager_party_id": expected_delete_sentinel,
    }
