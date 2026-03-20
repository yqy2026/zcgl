"""分层约束测试：collection 路由应委托 CollectionService。"""

import inspect
import json
import re
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.api


def test_collection_api_module_should_not_use_collection_crud_adapter_calls() -> None:
    """路由层不应直接调用 collection_crud。"""
    from src.api.v1.system import collection

    module_source = inspect.getsource(collection)
    assert "collection_crud." not in module_source


def test_collection_endpoints_should_use_require_authz() -> None:
    """collection 关键端点应接入 require_authz。"""
    from src.api.v1.system import collection

    module_source = inspect.getsource(collection)
    assert "AuthzContext" in module_source
    assert "require_authz" in module_source

    patterns = [
        r"async def get_collection_summary[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"collection\"",
        r"async def list_collection_records[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"collection\"",
        r"async def get_collection_record[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"collection\"[\s\S]*?resource_id=\"\{record_id\}\"[\s\S]*?deny_as_not_found=True",
        r"async def create_collection_record[\s\S]*?require_authz\([\s\S]*?action=\"create\"[\s\S]*?resource_type=\"collection\"[\s\S]*?resource_context=_COLLECTION_CREATE_RESOURCE_CONTEXT",
        r"async def update_collection_record[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_type=\"collection\"[\s\S]*?resource_id=\"\{record_id\}\"",
        r"async def delete_collection_record[\s\S]*?require_authz\([\s\S]*?action=\"delete\"[\s\S]*?resource_type=\"collection\"[\s\S]*?resource_id=\"\{record_id\}\"",
    ]
    for pattern in patterns:
        assert re.search(pattern, module_source), pattern


def test_collection_create_unscoped_context_should_be_defined() -> None:
    from src.api.v1.system import collection as module

    expected = "__unscoped__:collection:create"
    assert module._COLLECTION_CREATE_UNSCOPED_PARTY_ID == expected
    assert module._COLLECTION_CREATE_RESOURCE_CONTEXT == {
        "party_id": expected,
        "owner_party_id": expected,
        "manager_party_id": expected,
    }


@pytest.mark.asyncio
async def test_list_collection_records_should_delegate_to_service(mock_db) -> None:
    """列表路由应委托给 collection_service.list_records_async。"""
    from src.api.v1.system import collection as module
    from src.api.v1.system.collection import list_collection_records

    mock_service = MagicMock()
    mock_service.list_records_async = AsyncMock(
        return_value={
            "items": [],
            "page": 1,
            "page_size": 20,
            "total": 0,
        }
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "collection_service", mock_service)
        response = await list_collection_records(
            ledger_id=None,
            contract_id=None,
            collection_status=None,
            page=1,
            page_size=20,
            current_user=MagicMock(id="user-1"),
            db=mock_db,
        )

    payload = json.loads(response.body)
    assert payload["data"]["pagination"]["total"] == 0
    mock_service.list_records_async.assert_awaited_once_with(
        mock_db,
        ledger_id=None,
        contract_id=None,
        collection_status=None,
        page=1,
        page_size=20,
        current_user_id="user-1",
        party_filter=None,
    )


@pytest.mark.asyncio
async def test_get_collection_summary_should_delegate_current_user_id(mock_db) -> None:
    from src.api.v1.system import collection as module
    from src.api.v1.system.collection import get_collection_summary

    mock_service = MagicMock()
    mock_service.get_summary_async = AsyncMock(
        return_value={
            "total_overdue_count": 0,
            "total_overdue_amount": "0",
            "pending_collection_count": 0,
            "this_month_collection_count": 0,
            "collection_success_rate": None,
        }
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "collection_service", mock_service)
        await get_collection_summary(
            current_user=MagicMock(id="user-1"),
            db=mock_db,
        )

    mock_service.get_summary_async.assert_awaited_once_with(
        mock_db,
        current_user_id="user-1",
        party_filter=None,
    )
