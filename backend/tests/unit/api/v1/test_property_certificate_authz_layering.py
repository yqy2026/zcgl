"""Layering constraints for property_certificate authz wiring."""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.api


def _read_module_source() -> str:
    from src.api.v1.assets import property_certificate as module

    return Path(module.__file__).read_text(encoding="utf-8")


def test_property_certificate_module_should_import_authz_dependency() -> None:
    """产权证路由应引入统一 ABAC 依赖。"""
    module_source = _read_module_source()
    assert "AuthzContext" in module_source
    assert "get_current_active_user" in module_source
    assert "require_authz" in module_source
    assert "require_permission(" not in module_source


def test_property_certificate_endpoints_should_use_require_authz() -> None:
    """关键 create/read/update/delete 端点应接入统一 ABAC 依赖。"""
    module_source = _read_module_source()

    expected_patterns = [
        # upload/confirm_import/create 使用专用 create helper，统一注入组织/主体上下文
        r"async def upload_certificate[\s\S]*?_authz_ctx:\s*AuthzContext\s*=\s*Depends\(_require_property_certificate_create_authz\)",
        r"async def confirm_import[\s\S]*?_authz_ctx:\s*AuthzContext\s*=\s*Depends\(_require_property_certificate_create_authz\)",
        r"async def create_certificate[\s\S]*?_authz_ctx:\s*AuthzContext\s*=\s*Depends\(_require_property_certificate_create_authz\)",
        r"async def list_certificates[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"property_certificate\"",
        # get / update / delete with resource id
        r"async def get_certificate[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"property_certificate\"[\s\S]*?resource_id=\"\{certificate_id\}\"[\s\S]*?deny_as_not_found=True",
        r"async def update_certificate[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_type=\"property_certificate\"[\s\S]*?resource_id=\"\{certificate_id\}\"",
        r"async def delete_certificate[\s\S]*?require_authz\([\s\S]*?action=\"delete\"[\s\S]*?resource_type=\"property_certificate\"[\s\S]*?resource_id=\"\{certificate_id\}\"",
    ]
    for pattern in expected_patterns:
        assert re.search(pattern, module_source), pattern


@pytest.mark.asyncio
async def test_property_certificate_create_authz_should_include_organization_scope_context() -> None:
    """产权证 create 鉴权应注入组织/主体上下文，避免空资源上下文放行。"""
    from src.api.v1.assets import property_certificate as module

    mock_authz_service = MagicMock()
    mock_authz_service.check_access = AsyncMock(
        return_value=MagicMock(allowed=True, reason_code="allow")
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "authz_service", mock_authz_service, raising=False)
        monkeypatch.setattr(
            module,
            "_resolve_organization_party_id",
            AsyncMock(return_value="party-org-1"),
        )
        result = await module._require_property_certificate_create_authz(  # type: ignore[attr-defined]
            current_user=MagicMock(id="user-1", default_organization_id="org-1"),
            db=MagicMock(),
        )

    assert result.allowed is True
    assert result.resource_context["organization_id"] == "org-1"
    assert result.resource_context["party_id"] == "party-org-1"
    assert result.resource_context["owner_party_id"] == "party-org-1"
    assert result.resource_context["manager_party_id"] == "party-org-1"
    _args, kwargs = mock_authz_service.check_access.await_args
    assert kwargs["resource_type"] == "property_certificate"
    assert kwargs["action"] == "create"
    assert kwargs["resource_id"] is None
    assert kwargs["resource"]["organization_id"] == "org-1"
    assert kwargs["resource"]["party_id"] == "party-org-1"


@pytest.mark.asyncio
async def test_property_certificate_create_authz_should_fallback_to_unscoped_sentinel() -> None:
    """产权证 create 缺少组织上下文时应写入 unscoped 哨兵。"""
    from src.api.v1.assets import property_certificate as module

    mock_authz_service = MagicMock()
    mock_authz_service.check_access = AsyncMock(
        return_value=MagicMock(allowed=True, reason_code="allow")
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "authz_service", mock_authz_service, raising=False)
        result = await module._require_property_certificate_create_authz(  # type: ignore[attr-defined]
            current_user=MagicMock(id="user-1", default_organization_id=None),
            db=MagicMock(),
        )

    assert result.allowed is True
    assert result.resource_context == {
        "party_id": module._PROPERTY_CERTIFICATE_CREATE_UNSCOPED_PARTY_ID,  # type: ignore[attr-defined]
        "owner_party_id": module._PROPERTY_CERTIFICATE_CREATE_UNSCOPED_PARTY_ID,  # type: ignore[attr-defined]
        "manager_party_id": module._PROPERTY_CERTIFICATE_CREATE_UNSCOPED_PARTY_ID,  # type: ignore[attr-defined]
    }
