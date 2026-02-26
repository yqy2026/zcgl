"""分层约束测试：system 路由关键端点鉴权依赖。"""

import inspect
import re

import pytest

pytestmark = pytest.mark.api


def test_system_api_module_should_not_import_crud() -> None:
    """路由层不应直接引入 CRUD 层。"""
    from src.api.v1.system import system

    module_source = inspect.getsource(system)
    assert "crud" not in module_source


def test_system_endpoints_should_use_require_authz() -> None:
    """system 核心端点应接入 require_authz。"""
    from src.api.v1.system import system

    module_source = inspect.getsource(system)
    assert "AuthzContext" in module_source
    assert "require_authz" in module_source

    patterns = [
        r"async def health_check[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"system_monitoring\"",
        r"def app_info[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"system_settings\"",
        r"def api_root[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"system_settings\"",
    ]
    for pattern in patterns:
        assert re.search(pattern, module_source), pattern
