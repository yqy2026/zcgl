"""分层约束测试：organization 路由应接入统一 ABAC 依赖。"""

import inspect
import re
from unittest.mock import ANY, AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.api


def _read_module_source() -> str:
    from src.api.v1.auth import organization as module

    return inspect.getsource(module)


def test_organization_module_should_import_authz_dependency() -> None:
    """organization 路由应引入统一 ABAC 依赖。"""
    module_source = _read_module_source()
    assert "AuthzContext" in module_source
    assert "require_authz" in module_source


def test_organization_endpoints_should_use_require_authz() -> None:
    """organization 关键端点应接入 require_authz。"""
    module_source = _read_module_source()
    expected_patterns = [
        r"async def get_organizations[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"organization\"",
        r"async def get_organization_tree[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"organization\"",
        r"async def search_organizations[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"organization\"",
        r"async def get_organization_statistics[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"organization\"",
        r"async def get_organization[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_id=\"\{org_id\}\"[\s\S]*?deny_as_not_found=True",
        r"async def get_organization_children[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_id=\"\{org_id\}\"[\s\S]*?deny_as_not_found=True",
        r"async def get_organization_path[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_id=\"\{org_id\}\"[\s\S]*?deny_as_not_found=True",
        r"async def get_organization_history[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_id=\"\{org_id\}\"[\s\S]*?deny_as_not_found=True",
        r"async def create_organization[\s\S]*?_authz_ctx:\s*AuthzContext\s*=\s*Depends\(_require_organization_create_authz\)",
        r"async def update_organization[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_id=\"\{org_id\}\"",
        r"async def delete_organization[\s\S]*?require_authz\([\s\S]*?action=\"delete\"[\s\S]*?resource_id=\"\{org_id\}\"",
        r"async def move_organization[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_id=\"\{org_id\}\"",
        r"async def batch_organization_operation[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_type=\"organization\"",
        r"async def advanced_search_organizations[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"organization\"",
    ]

    for pattern in expected_patterns:
        assert re.search(pattern, module_source), pattern


@pytest.mark.asyncio
async def test_organization_create_authz_should_include_parent_scope_context() -> None:
    from src.api.v1.auth import organization as module

    org_create = MagicMock(parent_id="org-parent-1")
    mock_authz_service = MagicMock()
    mock_authz_service.check_access = AsyncMock(
        return_value=MagicMock(allowed=True, reason_code="allow")
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "authz_service", mock_authz_service, raising=False)
        monkeypatch.setattr(
            module,
            "_resolve_organization_party_id",
            AsyncMock(return_value="party-parent-1"),
        )
        result = await module._require_organization_create_authz(  # type: ignore[attr-defined]
            organization=org_create,
            current_user=MagicMock(id="user-1", default_organization_id="org-self-1"),
            db=MagicMock(),
        )

    assert result.allowed is True
    assert result.resource_context["organization_id"] == "org-parent-1"
    assert result.resource_context["party_id"] == "party-parent-1"
    assert result.resource_context["owner_party_id"] == "party-parent-1"
    assert result.resource_context["manager_party_id"] == "party-parent-1"


@pytest.mark.asyncio
async def test_organization_create_authz_should_fallback_to_unscoped_sentinel() -> None:
    from src.api.v1.auth import organization as module

    org_create = MagicMock(parent_id=None)
    mock_authz_service = MagicMock()
    mock_authz_service.check_access = AsyncMock(
        return_value=MagicMock(allowed=True, reason_code="allow")
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "authz_service", mock_authz_service, raising=False)
        result = await module._require_organization_create_authz(  # type: ignore[attr-defined]
            organization=org_create,
            current_user=MagicMock(id="user-1", default_organization_id=None),
            db=MagicMock(),
        )

    assert result.allowed is True
    assert result.resource_context == {
        "party_id": module._ORGANIZATION_CREATE_UNSCOPED_PARTY_ID,  # type: ignore[attr-defined]
        "owner_party_id": module._ORGANIZATION_CREATE_UNSCOPED_PARTY_ID,  # type: ignore[attr-defined]
        "manager_party_id": module._ORGANIZATION_CREATE_UNSCOPED_PARTY_ID,  # type: ignore[attr-defined]
    }


def test_organization_batch_update_should_not_define_fake_unscoped_context() -> None:
    from src.api.v1.auth import organization as module

    assert not hasattr(module, "_ORGANIZATION_BATCH_UPDATE_UNSCOPED_PARTY_ID")
    assert not hasattr(module, "_ORGANIZATION_BATCH_UPDATE_RESOURCE_CONTEXT")


@pytest.mark.asyncio
async def test_batch_organization_operation_should_check_manage_permission() -> None:
    from src.api.v1.auth import organization as module
    from src.api.v1.auth.organization import batch_organization_operation
    from src.schemas.organization import OrganizationBatchRequest

    batch_request = OrganizationBatchRequest(
        organization_ids=["org-1", "org-2"],
        action="delete",
        updated_by="admin",
    )
    mock_permission_service = MagicMock()
    mock_permission_service.can_manage_organization = AsyncMock(
        side_effect=[True, False]
    )
    mock_org_service = MagicMock()
    mock_org_service.delete_organization = AsyncMock(return_value=True)

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            module,
            "OrganizationPermissionService",
            MagicMock(return_value=mock_permission_service),
        )
        monkeypatch.setattr(module, "organization_service", mock_org_service)
        result = await batch_organization_operation(
            batch_request=batch_request,
            db=MagicMock(),
            current_user=MagicMock(id="user-1"),
        )

    assert len(result["results"]) == 1
    assert len(result["errors"]) == 1
    assert result["errors"][0]["id"] == "org-2"
    assert result["errors"][0]["error"] == "无权管理该组织"
    mock_org_service.delete_organization.assert_awaited_once_with(
        ANY,
        org_id="org-1",
        deleted_by="admin",
    )
