"""分层约束测试：error_recovery 路由应接入统一 ABAC 依赖。"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.api


def _read_module_source() -> str:
    from src.api.v1.system import error_recovery as module

    return Path(module.__file__).read_text(encoding="utf-8")


def test_error_recovery_module_should_import_authz_dependency() -> None:
    """error_recovery 路由应引入统一 ABAC 依赖。"""
    module_source = _read_module_source()
    assert "AuthzContext" in module_source
    assert "get_current_active_user" in module_source
    assert "require_authz" in module_source
    assert "require_permission(" not in module_source


def test_error_recovery_endpoints_should_use_require_authz() -> None:
    """error_recovery 关键端点应接入 require_authz。"""
    module_source = _read_module_source()
    expected_patterns = [
        r"async def get_recovery_statistics[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"error_recovery\"",
        r"async def get_recovery_strategies[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"error_recovery\"",
        r"async def update_recovery_strategy[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_type=\"error_recovery\"[\s\S]*?resource_id=\"\{category\}\"",
        r"async def get_circuit_breaker_status[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"error_recovery\"",
        r"async def reset_circuit_breaker[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_type=\"error_recovery\"[\s\S]*?resource_id=\"\{category\}\"",
        r"async def get_recovery_history[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"error_recovery\"",
        r"async def test_error_recovery[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_type=\"error_recovery\"[\s\S]*?resource_id=_resolve_test_recovery_category_resource_id",
        r"async def clear_recovery_history[\s\S]*?require_authz\([\s\S]*?action=\"delete\"[\s\S]*?resource_type=\"error_recovery\"[\s\S]*?resource_context=_ERROR_RECOVERY_DELETE_RESOURCE_CONTEXT",
    ]

    for pattern in expected_patterns:
        assert re.search(pattern, module_source), pattern


def test_error_recovery_test_endpoint_should_not_use_path_template_for_body_category() -> None:
    """/test 端点的 category 来自 body，不应继续使用 path template。"""
    module_source = _read_module_source()
    assert 'async def _resolve_test_recovery_category_resource_id(' in module_source
    assert 'resource_id="{category}"' not in re.search(
        r"async def test_error_recovery[\s\S]*?\)\s*->\s*dict\[str,\s*Any\]:",
        module_source,
    ).group(0)


def test_error_recovery_unscoped_delete_context_should_be_defined() -> None:
    from src.api.v1.system import error_recovery as module

    expected_sentinel = "__unscoped__:error_recovery:delete"
    assert module._ERROR_RECOVERY_DELETE_UNSCOPED_PARTY_ID == expected_sentinel
    assert module._ERROR_RECOVERY_DELETE_RESOURCE_CONTEXT == {
        "party_id": expected_sentinel,
        "owner_party_id": expected_sentinel,
        "manager_party_id": expected_sentinel,
    }
