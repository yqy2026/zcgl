"""分层约束测试：custom_fields 路由应委托服务层。"""

import re
from pathlib import Path
from unittest.mock import ANY, AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.api


def _read_module_source() -> str:
    from src.api.v1.assets import custom_fields as module

    return Path(module.__file__).read_text(encoding="utf-8")


def test_custom_fields_module_should_not_use_crud_adapter_calls() -> None:
    """路由模块不应直接调用 custom_field_crud。"""
    module_source = _read_module_source()
    assert "from ....crud.custom_field import custom_field_crud" not in module_source
    assert "custom_field_crud." not in module_source


def test_custom_fields_module_should_import_authz_dependency() -> None:
    """custom_fields 路由应引入统一 ABAC 依赖。"""
    module_source = _read_module_source()
    assert "AuthzContext" in module_source
    assert "require_authz" in module_source


def test_custom_fields_endpoints_should_use_require_authz() -> None:
    """custom_fields 关键端点应接入 require_authz。"""
    module_source = _read_module_source()
    expected_patterns = [
        r"async def get_custom_fields[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"custom_field\"",
        r"async def get_custom_field[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"custom_field\"[\s\S]*?resource_id=\"\{field_id\}\"",
        r"async def create_custom_field[\s\S]*?require_authz\([\s\S]*?action=\"create\"[\s\S]*?resource_type=\"custom_field\"",
        r"async def update_custom_field[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_type=\"custom_field\"[\s\S]*?resource_id=\"\{field_id\}\"",
        r"async def delete_custom_field[\s\S]*?require_authz\([\s\S]*?action=\"delete\"[\s\S]*?resource_type=\"custom_field\"[\s\S]*?resource_id=\"\{field_id\}\"",
        r"async def validate_custom_field_value[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"custom_field\"",
        r"async def get_asset_custom_field_values[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"asset\"[\s\S]*?resource_id=\"\{asset_id\}\"[\s\S]*?deny_as_not_found=True",
        r"async def update_asset_custom_field_values[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_type=\"asset\"[\s\S]*?resource_id=\"\{asset_id\}\"",
        r"async def batch_set_custom_field_values[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_type=\"custom_field\"",
    ]
    for pattern in expected_patterns:
        assert re.search(pattern, module_source), pattern


def test_custom_field_should_not_define_fake_unscoped_write_context() -> None:
    from src.api.v1.assets import custom_fields

    assert not hasattr(custom_fields, "_ASSET_CUSTOM_FIELD_CREATE_UNSCOPED_PARTY_ID")
    assert not hasattr(custom_fields, "_ASSET_CUSTOM_FIELD_CREATE_RESOURCE_CONTEXT")
    assert not hasattr(
        custom_fields,
        "_ASSET_CUSTOM_FIELD_BATCH_UPDATE_UNSCOPED_PARTY_ID",
    )
    assert not hasattr(
        custom_fields,
        "_ASSET_CUSTOM_FIELD_BATCH_UPDATE_RESOURCE_CONTEXT",
    )


@pytest.mark.asyncio
async def test_get_custom_fields_should_delegate_custom_field_service() -> None:
    """字段列表接口应委托 custom_field_service.get_custom_fields_async。"""
    from src.api.v1.assets import custom_fields as module
    from src.api.v1.assets.custom_fields import get_custom_fields

    mock_service = MagicMock()
    mock_service.get_custom_fields_async = AsyncMock(return_value=[MagicMock()])
    mock_user = MagicMock()
    mock_user.id = "user-1"

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "custom_field_service", mock_service)
        monkeypatch.setattr(
            module.AssetCustomFieldResponse,
            "model_validate",
            staticmethod(lambda _: {"id": "field-1"}),
        )
        result = await get_custom_fields(
            asset_id="asset-1",
            field_type="text",
            is_required=True,
            is_active=True,
            db=MagicMock(),
            current_user=mock_user,
        )

    assert len(result) == 1
    mock_service.get_custom_fields_async.assert_awaited_once_with(
        db=ANY,
        filters={
            "asset_id": "asset-1",
            "field_type": "text",
            "is_required": True,
            "is_active": True,
        },
    )


@pytest.mark.asyncio
async def test_get_custom_field_should_delegate_custom_field_service() -> None:
    """字段详情接口应委托 custom_field_service.get_custom_field_async。"""
    from src.api.v1.assets import custom_fields as module
    from src.api.v1.assets.custom_fields import get_custom_field

    mock_service = MagicMock()
    mock_service.get_custom_field_async = AsyncMock(return_value=MagicMock())
    mock_user = MagicMock()
    mock_user.id = "user-1"

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "custom_field_service", mock_service)
        monkeypatch.setattr(
            module.AssetCustomFieldResponse,
            "model_validate",
            staticmethod(lambda _: {"id": "field-1"}),
        )
        result = await get_custom_field(
            field_id="field-1",
            db=MagicMock(),
            current_user=mock_user,
        )

    assert result["id"] == "field-1"
    mock_service.get_custom_field_async.assert_awaited_once_with(
        db=ANY,
        field_id="field-1",
    )


@pytest.mark.asyncio
async def test_validate_custom_field_value_should_delegate_service_validation() -> None:
    """字段值校验接口应委托 custom_field_service.validate_custom_field_value_async。"""
    from src.api.v1.assets import custom_fields as module
    from src.api.v1.assets.custom_fields import validate_custom_field_value

    mock_service = MagicMock()
    mock_service.validate_custom_field_value_async = AsyncMock(return_value=(True, None))

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "custom_field_service", mock_service)
        result = await validate_custom_field_value(
            field_id="field-1",
            value="ok",
            db=MagicMock(),
            current_user=MagicMock(),
        )

    assert result["valid"] is True
    mock_service.validate_custom_field_value_async.assert_awaited_once_with(
        db=ANY,
        field_id="field-1",
        value="ok",
    )


@pytest.mark.asyncio
async def test_get_asset_custom_field_values_should_delegate_service_query() -> None:
    """资产字段值接口应委托 custom_field_service.get_asset_field_values_async。"""
    from src.api.v1.assets import custom_fields as module
    from src.api.v1.assets.custom_fields import get_asset_custom_field_values

    values = [{"field_name": "field_1", "value": "value_1"}]
    mock_service = MagicMock()
    mock_service.get_asset_field_values_async = AsyncMock(return_value=values)

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "custom_field_service", mock_service)
        result = await get_asset_custom_field_values(
            asset_id="asset-1",
            db=MagicMock(),
            current_user=MagicMock(),
        )

    assert result == {"asset_id": "asset-1", "values": values}
    mock_service.get_asset_field_values_async.assert_awaited_once_with(
        db=ANY,
        asset_id="asset-1",
    )
