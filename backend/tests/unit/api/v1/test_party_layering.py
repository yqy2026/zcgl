"""分层约束测试：party 路由应委托服务层。"""

import re
from unittest.mock import ANY, AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.api


def _read_module_source() -> str:
    from src.api.v1 import party as module

    with open(module.__file__, encoding="utf-8") as f:
        return f.read()


def test_party_module_should_not_import_party_crud_directly() -> None:
    """party 路由模块不应直接依赖 CRUD 层。"""
    module_source = _read_module_source()
    assert "from ...crud.party import" not in module_source
    assert "party_crud." not in module_source


def test_party_module_should_import_authz_dependency() -> None:
    """party 路由应引入统一 ABAC 依赖。"""
    module_source = _read_module_source()
    assert "AuthzContext" in module_source
    assert "require_authz" in module_source


def test_party_endpoints_should_use_require_authz() -> None:
    """party 关键端点应接入 require_authz。"""
    module_source = _read_module_source()
    expected_patterns = [
        r"async def list_parties[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"party\"",
        r"async def create_party[\s\S]*?require_authz\([\s\S]*?action=\"create\"[\s\S]*?resource_type=\"party\"[\s\S]*?resource_context=_PARTY_CREATE_RESOURCE_CONTEXT",
        r"async def get_party[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"party\"[\s\S]*?resource_id=\"\{party_id\}\"[\s\S]*?deny_as_not_found=True",
        r"async def update_party[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_type=\"party\"[\s\S]*?resource_id=\"\{party_id\}\"",
        r"async def delete_party[\s\S]*?require_authz\([\s\S]*?action=\"delete\"[\s\S]*?resource_type=\"party\"[\s\S]*?resource_id=\"\{party_id\}\"",
        r"async def get_party_hierarchy[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"party\"[\s\S]*?resource_id=\"\{party_id\}\"[\s\S]*?deny_as_not_found=True",
        r"async def add_party_hierarchy[\s\S]*?require_authz\([\s\S]*?action=\"create\"[\s\S]*?resource_type=\"party\"[\s\S]*?resource_id=\"\{party_id\}\"",
        r"async def delete_party_hierarchy[\s\S]*?require_authz\([\s\S]*?action=\"delete\"[\s\S]*?resource_type=\"party\"[\s\S]*?resource_id=\"\{party_id\}\"",
        r"async def get_party_contacts[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"party\"[\s\S]*?resource_id=\"\{party_id\}\"[\s\S]*?deny_as_not_found=True",
        r"async def create_party_contact[\s\S]*?require_authz\([\s\S]*?action=\"create\"[\s\S]*?resource_type=\"party\"[\s\S]*?resource_id=\"\{party_id\}\"",
    ]

    for pattern in expected_patterns:
        assert re.search(pattern, module_source), pattern


def test_party_unscoped_create_context_should_be_defined() -> None:
    from src.api.v1 import party

    expected = "__unscoped__:party:create"
    assert party._PARTY_CREATE_UNSCOPED_PARTY_ID == expected
    assert party._PARTY_CREATE_RESOURCE_CONTEXT == {
        "party_id": expected,
        "owner_party_id": expected,
        "manager_party_id": expected,
    }


@pytest.mark.asyncio
async def test_list_parties_should_delegate_to_service() -> None:
    """列表端点应委托 party_service.get_parties。"""
    from src.api.v1 import party as module
    from src.api.v1.party import list_parties

    mock_service = MagicMock()
    mock_service.get_parties = AsyncMock(return_value=[])

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "party_service", mock_service)
        result = await list_parties(
            skip=5,
            limit=10,
            party_type="owner",
            status="active",
            search=None,
            db=MagicMock(),
            current_user=MagicMock(),
        )

    assert result == []
    mock_service.get_parties.assert_awaited_once_with(
        ANY,
        skip=5,
        limit=10,
        party_type="owner",
        status="active",
        search=None,
    )


@pytest.mark.asyncio
async def test_list_parties_should_pass_search_keyword_to_service() -> None:
    """列表端点应将 search 参数透传给 party_service.get_parties。"""
    from src.api.v1 import party as module
    from src.api.v1.party import list_parties

    mock_service = MagicMock()
    mock_service.get_parties = AsyncMock(return_value=[])

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "party_service", mock_service)
        result = await list_parties(
            skip=0,
            limit=20,
            party_type=None,
            status=None,
            search="acme",
            db=MagicMock(),
            current_user=MagicMock(),
        )

    assert result == []
    mock_service.get_parties.assert_awaited_once_with(
        ANY,
        skip=0,
        limit=20,
        party_type=None,
        status=None,
        search="acme",
    )
