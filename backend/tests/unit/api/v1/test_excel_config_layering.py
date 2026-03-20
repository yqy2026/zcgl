"""分层约束测试：excel config 路由应走统一 ABAC 依赖。"""

import ast
import inspect
import textwrap

import pytest

pytestmark = pytest.mark.api


def _read_module() -> object:
    from src.api.v1.documents.excel import config as module

    return module


def _read_function_source(function_name: str) -> str:
    module = _read_module()
    return inspect.getsource(getattr(module, function_name))


def _get_require_authz_keywords(function_name: str) -> dict[str, ast.expr]:
    function_source = textwrap.dedent(_read_function_source(function_name))
    parsed = ast.parse(function_source)
    for node in ast.walk(parsed):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "require_authz":
                return {
                    keyword.arg: keyword.value
                    for keyword in node.keywords
                    if keyword.arg is not None
                }
    raise AssertionError(f"{function_name} 未找到 require_authz 调用")


def _require_str_value(keyword_map: dict[str, ast.expr], key: str) -> str:
    value_node = keyword_map.get(key)
    assert isinstance(value_node, ast.Constant), f"{key} 应为字符串常量"
    assert isinstance(value_node.value, str), f"{key} 应为字符串常量"
    return value_node.value


def test_excel_config_key_endpoints_should_use_require_authz() -> None:
    """excel 配置关键端点应接入统一 ABAC 依赖。"""
    module_source = inspect.getsource(_read_module())
    assert "AuthzContext" in module_source
    assert "get_current_active_user" in module_source
    assert "require_permission(" not in module_source

    create_kwargs = _get_require_authz_keywords("create_excel_config")
    assert _require_str_value(create_kwargs, "action") == "create"
    assert _require_str_value(create_kwargs, "resource_type") == "excel_config"
    assert "resource_context" not in create_kwargs

    list_kwargs = _get_require_authz_keywords("get_excel_configs")
    assert _require_str_value(list_kwargs, "action") == "read"
    assert _require_str_value(list_kwargs, "resource_type") == "excel_config"
    assert "resource_id" not in list_kwargs

    default_kwargs = _get_require_authz_keywords("get_default_excel_config")
    assert _require_str_value(default_kwargs, "action") == "read"
    assert _require_str_value(default_kwargs, "resource_type") == "excel_config"
    assert "resource_id" not in default_kwargs

    detail_kwargs = _get_require_authz_keywords("get_excel_config")
    assert _require_str_value(detail_kwargs, "action") == "read"
    assert _require_str_value(detail_kwargs, "resource_type") == "excel_config"
    assert _require_str_value(detail_kwargs, "resource_id") == "{config_id}"

    update_kwargs = _get_require_authz_keywords("update_excel_config")
    assert _require_str_value(update_kwargs, "action") == "update"
    assert _require_str_value(update_kwargs, "resource_type") == "excel_config"
    assert _require_str_value(update_kwargs, "resource_id") == "{config_id}"

    delete_kwargs = _get_require_authz_keywords("delete_excel_config")
    assert _require_str_value(delete_kwargs, "action") == "delete"
    assert _require_str_value(delete_kwargs, "resource_type") == "excel_config"
    assert _require_str_value(delete_kwargs, "resource_id") == "{config_id}"


def test_excel_config_should_not_define_fake_unscoped_create_context() -> None:
    module = _read_module()
    assert not hasattr(module, "_EXCEL_CONFIG_CREATE_UNSCOPED_PARTY_ID")
    assert not hasattr(module, "_EXCEL_CONFIG_CREATE_RESOURCE_CONTEXT")
