"""分层约束测试：dictionaries 路由应委托 service 层。"""

import inspect
import re

import pytest

pytestmark = pytest.mark.api


def test_dictionaries_api_module_should_not_use_crud_adapter_calls() -> None:
    """路由层不应直接调用 system_dictionary_crud / enum_field_crud。"""
    from src.api.v1.system import dictionaries

    module_source = inspect.getsource(dictionaries)
    assert "system_dictionary_crud." not in module_source
    assert "enum_field_crud." not in module_source


def test_dictionaries_endpoints_should_use_require_authz() -> None:
    """dictionaries 关键端点应接入 require_authz。"""
    from src.api.v1.system import dictionaries

    module_source = inspect.getsource(dictionaries)
    assert "AuthzContext" in module_source
    assert "require_authz" in module_source

    patterns = [
        r"async def get_dictionary_options[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"dictionary\"[\s\S]*?resource_id=\"\{dict_type\}\"[\s\S]*?deny_as_not_found=True",
        r"async def quick_create_dictionary[\s\S]*?require_authz\([\s\S]*?action=\"create\"[\s\S]*?resource_type=\"dictionary\"[\s\S]*?resource_id=\"\{dict_type\}\"",
        r"async def get_dictionary_types[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"dictionary\"",
        r"async def get_validation_statistics[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"dictionary\"",
        r"async def add_dictionary_value[\s\S]*?require_authz\([\s\S]*?action=\"create\"[\s\S]*?resource_type=\"dictionary\"[\s\S]*?resource_id=\"\{dict_type\}\"",
        r"async def delete_dictionary_type[\s\S]*?require_authz\([\s\S]*?action=\"delete\"[\s\S]*?resource_type=\"dictionary\"[\s\S]*?resource_id=\"\{dict_type\}\"",
    ]

    for pattern in patterns:
        assert re.search(pattern, module_source), pattern
