"""分层约束测试：auth security 路由应接入统一 ABAC 依赖。"""

import inspect
import re
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.api


def _read_module_source() -> str:
    from src.api.v1.auth.auth_modules import security as module

    return inspect.getsource(module)


def test_auth_security_module_should_import_authz_dependency() -> None:
    """security 路由应引入统一 ABAC 依赖。"""
    module_source = _read_module_source()
    assert "AuthzContext" in module_source
    assert "require_authz" in module_source


def test_auth_security_endpoint_should_use_require_authz() -> None:
    """安全配置端点应接入 require_authz。"""
    module_source = _read_module_source()
    pattern = (
        r"def get_security_config[\s\S]*?require_authz\("
        r"[\s\S]*?action=\"read\"[\s\S]*?resource_type=\"system_settings\""
    )
    assert re.search(pattern, module_source), pattern


def test_get_security_config_should_return_policy_payload() -> None:
    """安全配置端点应返回策略与配置字段。"""
    from src.api.v1.auth.auth_modules.security import get_security_config

    result = get_security_config(current_user=MagicMock(id="admin-id"))

    assert "password_policy" in result
    assert "token_config" in result
    assert "session_config" in result
    assert "audit_config" in result
