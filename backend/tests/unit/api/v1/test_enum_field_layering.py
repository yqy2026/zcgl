"""分层约束测试：enum_field 路由必须通过 Service 协调。"""

import ast
import inspect
import re
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.schemas.enum_field import EnumFieldTypeCreate

pytestmark = pytest.mark.api


def _get_crud_imports(module_source: str) -> list[str]:
    tree = ast.parse(module_source)
    crud_imports: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module_name = node.module or ""
            if "crud" in module_name.split("."):
                crud_imports.append(module_name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imported_name = alias.name
                if "crud" in imported_name.split("."):
                    crud_imports.append(imported_name)

    return crud_imports


def test_enum_field_api_module_should_not_import_crud():
    """API 层不应直接依赖 CRUD 模块。"""
    from src.api.v1.system import enum_field

    module_source = inspect.getsource(enum_field)
    crud_imports = _get_crud_imports(module_source)

    assert crud_imports == []


def test_enum_field_endpoints_should_use_require_authz() -> None:
    """enum_field 关键业务端点应接入 require_authz（debug 端点除外）。"""
    from src.api.v1.system import enum_field

    module_source = inspect.getsource(enum_field)
    assert "AuthzContext" in module_source
    assert "require_authz" in module_source

    patterns = [
        r"async def get_enum_field_types[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"enum_field\"",
        r"async def get_enum_field_statistics[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"enum_field\"",
        r"async def get_enum_field_type[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"enum_field\"[\s\S]*?resource_id=\"\{type_id\}\"[\s\S]*?deny_as_not_found=True",
        r"async def create_enum_field_type[\s\S]*?require_authz\([\s\S]*?action=\"create\"[\s\S]*?resource_type=\"enum_field\"[\s\S]*?resource_context=_ENUM_FIELD_TYPE_CREATE_RESOURCE_CONTEXT",
        r"async def update_enum_field_type[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_type=\"enum_field\"[\s\S]*?resource_id=\"\{type_id\}\"",
        r"async def delete_enum_field_type[\s\S]*?require_authz\([\s\S]*?action=\"delete\"[\s\S]*?resource_type=\"enum_field\"[\s\S]*?resource_id=\"\{type_id\}\"",
        r"async def get_enum_field_categories[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"enum_field\"",
        r"async def get_enum_field_values[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"enum_field\"[\s\S]*?resource_id=\"\{type_id\}\"[\s\S]*?deny_as_not_found=True",
        r"async def get_enum_field_values_tree[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"enum_field\"[\s\S]*?resource_id=\"\{type_id\}\"[\s\S]*?deny_as_not_found=True",
        r"async def get_enum_field_value[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"enum_field\"[\s\S]*?resource_id=\"\{value_id\}\"[\s\S]*?deny_as_not_found=True",
        r"async def create_enum_field_value[\s\S]*?require_authz\([\s\S]*?action=\"create\"[\s\S]*?resource_type=\"enum_field\"[\s\S]*?resource_id=\"\{type_id\}\"",
        r"async def update_enum_field_value[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_type=\"enum_field\"[\s\S]*?resource_id=\"\{value_id\}\"",
        r"async def delete_enum_field_value[\s\S]*?require_authz\([\s\S]*?action=\"delete\"[\s\S]*?resource_type=\"enum_field\"[\s\S]*?resource_id=\"\{value_id\}\"",
        r"async def batch_create_enum_field_values[\s\S]*?require_authz\([\s\S]*?action=\"create\"[\s\S]*?resource_type=\"enum_field\"[\s\S]*?resource_id=\"\{type_id\}\"",
        r"async def get_enum_field_usage[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"enum_field\"",
        r"async def create_enum_field_usage[\s\S]*?require_authz\([\s\S]*?action=\"create\"[\s\S]*?resource_type=\"enum_field\"[\s\S]*?resource_context=_ENUM_FIELD_USAGE_CREATE_RESOURCE_CONTEXT",
        r"async def update_enum_field_usage[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_type=\"enum_field\"[\s\S]*?resource_id=\"\{usage_id\}\"",
        r"async def delete_enum_field_usage[\s\S]*?require_authz\([\s\S]*?action=\"delete\"[\s\S]*?resource_type=\"enum_field\"[\s\S]*?resource_id=\"\{usage_id\}\"",
        r"async def get_enum_field_type_history[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"enum_field\"[\s\S]*?resource_id=\"\{type_id\}\"[\s\S]*?deny_as_not_found=True",
        r"async def get_enum_field_value_history[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"enum_field\"[\s\S]*?resource_id=\"\{value_id\}\"[\s\S]*?deny_as_not_found=True",
    ]

    for pattern in patterns:
        assert re.search(pattern, module_source), pattern


def test_enum_field_create_unscoped_context_should_be_defined() -> None:
    from src.api.v1.system import enum_field as module

    expected_type_create = "__unscoped__:enum_field_type:create"
    assert module._ENUM_FIELD_TYPE_CREATE_UNSCOPED_PARTY_ID == expected_type_create
    assert module._ENUM_FIELD_TYPE_CREATE_RESOURCE_CONTEXT == {
        "party_id": expected_type_create,
        "owner_party_id": expected_type_create,
        "manager_party_id": expected_type_create,
    }

    expected_usage_create = "__unscoped__:enum_field_usage:create"
    assert module._ENUM_FIELD_USAGE_CREATE_UNSCOPED_PARTY_ID == expected_usage_create
    assert module._ENUM_FIELD_USAGE_CREATE_RESOURCE_CONTEXT == {
        "party_id": expected_usage_create,
        "owner_party_id": expected_usage_create,
        "manager_party_id": expected_usage_create,
    }


@pytest.mark.asyncio
async def test_get_enum_field_types_should_delegate_to_service(mock_db):
    """类型列表路由应委托给 service。"""
    from src.api.v1.system.enum_field import get_enum_field_types

    expected = [MagicMock(id="type-1")]
    mock_service = MagicMock()
    mock_service.get_enum_field_types = AsyncMock(return_value=expected)

    result = await get_enum_field_types(
        page=1,
        page_size=20,
        category=None,
        status=None,
        is_system=None,
        keyword=None,
        db=mock_db,
        service=mock_service,
    )

    assert result == expected
    mock_service.get_enum_field_types.assert_awaited_once_with(
        db=mock_db,
        page=1,
        page_size=20,
        category=None,
        status=None,
        is_system=None,
        keyword=None,
    )


@pytest.mark.asyncio
async def test_create_enum_field_type_should_delegate_to_service(mock_db):
    """创建类型路由应委托给 service。"""
    from src.api.v1.system.enum_field import create_enum_field_type

    payload = EnumFieldTypeCreate(
        name="测试类型",
        code="test_type",
        category="asset",
        description="desc",
        created_by="tester",
    )

    expected = MagicMock(id="new-type-id")
    mock_service = MagicMock()
    mock_service.create_enum_field_type = AsyncMock(return_value=expected)

    result = await create_enum_field_type(payload, db=mock_db, service=mock_service)

    assert result == expected
    mock_service.create_enum_field_type.assert_awaited_once_with(
        db=mock_db,
        enum_type=payload,
    )
