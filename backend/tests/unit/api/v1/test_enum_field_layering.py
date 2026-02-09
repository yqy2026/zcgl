"""分层约束测试：enum_field 路由必须通过 Service 协调。"""

import ast
import inspect
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

