"""分层约束测试：system_dictionaries 路由应委托 SystemDictionaryService。"""

import inspect
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.api


def test_system_dictionaries_api_module_should_not_use_crud_adapter_calls():
    """路由层不应直接调用 system_dictionary_crud。"""
    from src.api.v1.system import system_dictionaries

    module_source = inspect.getsource(system_dictionaries)
    assert "system_dictionary_crud." not in module_source


@pytest.mark.asyncio
async def test_get_system_dictionaries_should_delegate_to_service(mock_db):
    """列表路由应委托给 service.get_dictionaries_async。"""
    from src.api.v1.system.system_dictionaries import get_system_dictionaries

    mock_service = MagicMock()
    mock_service.get_dictionaries_async = AsyncMock(return_value=[])

    result = await get_system_dictionaries(
        dict_type="asset_type",
        is_active=True,
        db=mock_db,
        service=mock_service,
    )

    assert result == []
    mock_service.get_dictionaries_async.assert_awaited_once_with(
        db=mock_db,
        dict_type="asset_type",
        is_active=True,
    )


@pytest.mark.asyncio
async def test_get_dictionary_types_should_delegate_to_service(mock_db):
    """字典类型端点应委托给 service.get_types_async。"""
    from src.api.v1.system.system_dictionaries import get_dictionary_types

    mock_service = MagicMock()
    mock_service.get_types_async = AsyncMock(return_value=["asset_type", "region"])

    result = await get_dictionary_types(db=mock_db, service=mock_service)

    assert result == {"types": ["asset_type", "region"]}
    mock_service.get_types_async.assert_awaited_once_with(db=mock_db)
