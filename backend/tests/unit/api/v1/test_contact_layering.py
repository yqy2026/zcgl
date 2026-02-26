"""分层约束测试：contact 路由应委托 ContactService。"""

import inspect
import json
import re
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.schemas.contact import ContactCreate

pytestmark = pytest.mark.api


def test_contact_api_module_should_not_use_crud_adapter_calls():
    """路由层不应直接调用 contact_crud。"""
    from src.api.v1.system import contact

    module_source = inspect.getsource(contact)
    assert "contact_crud." not in module_source


def test_contact_endpoints_should_use_require_authz() -> None:
    """contact 关键端点应接入 require_authz。"""
    from src.api.v1.system import contact

    module_source = inspect.getsource(contact)
    assert "AuthzContext" in module_source
    assert "require_authz" in module_source

    patterns = [
        r"async def create_contact[\s\S]*?require_authz\([\s\S]*?action=\"create\"[\s\S]*?resource_type=\"contact\"[\s\S]*?resource_context=_CONTACT_CREATE_RESOURCE_CONTEXT",
        r"async def get_contact[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"contact\"[\s\S]*?resource_id=\"\{contact_id\}\"[\s\S]*?deny_as_not_found=True",
        r"async def get_entity_contacts[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"contact\"[\s\S]*?resource_id=\"\{entity_id\}\"[\s\S]*?deny_as_not_found=True",
        r"async def get_primary_contact[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"contact\"[\s\S]*?resource_id=\"\{entity_id\}\"[\s\S]*?deny_as_not_found=True",
        r"async def update_contact[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_type=\"contact\"[\s\S]*?resource_id=\"\{contact_id\}\"",
        r"async def delete_contact[\s\S]*?require_authz\([\s\S]*?action=\"delete\"[\s\S]*?resource_type=\"contact\"[\s\S]*?resource_id=\"\{contact_id\}\"",
        r"async def create_contacts_batch[\s\S]*?require_authz\([\s\S]*?action=\"create\"[\s\S]*?resource_type=\"contact\"[\s\S]*?resource_id=\"\{entity_id\}\"",
    ]
    for pattern in patterns:
        assert re.search(pattern, module_source), pattern


def test_contact_create_unscoped_context_should_be_defined() -> None:
    from src.api.v1.system import contact as module

    expected = "__unscoped__:contact:create"
    assert module._CONTACT_CREATE_UNSCOPED_PARTY_ID == expected
    assert module._CONTACT_CREATE_RESOURCE_CONTEXT == {
        "party_id": expected,
        "owner_party_id": expected,
        "manager_party_id": expected,
    }


@pytest.mark.asyncio
async def test_get_entity_contacts_should_delegate_to_service(mock_db):
    """实体联系人列表路由应委托 service.get_entity_contacts。"""
    from src.api.v1.system.contact import get_entity_contacts

    mock_service = MagicMock()
    mock_service.get_entity_contacts = AsyncMock(return_value=([], 0))

    response = await get_entity_contacts(
        entity_type="ownership",
        entity_id="entity-1",
        db=mock_db,
        current_user=MagicMock(id="user-1"),
        page=2,
        page_size=10,
        service=mock_service,
    )

    payload = json.loads(response.body)
    assert payload["data"]["pagination"]["total"] == 0
    mock_service.get_entity_contacts.assert_awaited_once_with(
        db=mock_db,
        entity_type="ownership",
        entity_id="entity-1",
        skip=10,
        limit=10,
    )


@pytest.mark.asyncio
async def test_create_contacts_batch_should_delegate_to_service(mock_db):
    """批量创建路由应委托 service.create_contacts_batch。"""
    from src.api.v1.system.contact import create_contacts_batch

    mock_service = MagicMock()
    mock_service.create_contacts_batch = AsyncMock(return_value=[])
    current_user = MagicMock(username="tester")

    contacts_in = [
        ContactCreate(
            name="Alice",
            entity_type="ownership",
            entity_id="entity-1",
        )
    ]

    result = await create_contacts_batch(
        entity_type="ownership",
        entity_id="entity-1",
        db=mock_db,
        contacts_in=contacts_in,
        current_user=current_user,
        service=mock_service,
    )

    assert result == []
    mock_service.create_contacts_batch.assert_awaited_once()
    call_kwargs = mock_service.create_contacts_batch.await_args.kwargs
    assert call_kwargs["db"] is mock_db
    assert len(call_kwargs["contacts_data"]) == 1
    assert call_kwargs["contacts_data"][0]["entity_type"] == "ownership"
    assert call_kwargs["contacts_data"][0]["entity_id"] == "entity-1"
    assert call_kwargs["contacts_data"][0]["created_by"] == "tester"
