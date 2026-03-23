"""分层约束测试：pdf_batch_routes 路由应委托服务层。"""

import json
import re
from pathlib import Path
from unittest.mock import ANY, AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.api


def _read_module_source() -> str:
    from src.api.v1.documents import pdf_batch_routes as module

    return Path(module.__file__).read_text(encoding="utf-8")


def test_pdf_batch_routes_module_should_not_import_session_crud_directly() -> None:
    """pdf_batch_routes 路由模块不应直接导入 PDFImportSessionCRUD。"""
    module_source = _read_module_source()
    assert "from ....crud.pdf_import_session import PDFImportSessionCRUD" not in module_source
    assert "PDFImportSessionCRUD(" not in module_source


def test_pdf_batch_routes_key_endpoints_should_use_require_authz() -> None:
    """pdf 批处理关键端点应接入统一 ABAC 依赖。"""
    module_source = _read_module_source()
    expected_patterns = [
        r"async def batch_upload_pdfs[\s\S]*?require_authz\([\s\S]*?action=\"create\"[\s\S]*?resource_type=\"contract\"[\s\S]*?resource_context=_CONTRACT_CREATE_RESOURCE_CONTEXT",
        r"async def get_batch_status[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"contract\"",
        r"async def list_batches[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"contract\"",
        r"async def cancel_batch[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_type=\"contract\"[\s\S]*?resource_context=_CONTRACT_UPDATE_RESOURCE_CONTEXT",
        r"def cleanup_completed_batches[\s\S]*?require_authz\([\s\S]*?action=\"delete\"[\s\S]*?resource_type=\"contract\"[\s\S]*?resource_context=_CONTRACT_DELETE_RESOURCE_CONTEXT",
        r"def batch_health_check[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"contract\"",
    ]
    for pattern in expected_patterns:
        assert re.search(pattern, module_source), pattern


def test_pdf_batch_routes_unscoped_write_context_should_be_defined() -> None:
    from src.api.v1.documents import pdf_batch_routes as module

    expected_create = "__unscoped__:contract:create"
    assert module._CONTRACT_CREATE_UNSCOPED_PARTY_ID == expected_create
    assert module._CONTRACT_CREATE_RESOURCE_CONTEXT == {
        "party_id": expected_create,
        "owner_party_id": expected_create,
        "manager_party_id": expected_create,
    }

    expected_update = "__unscoped__:contract:update"
    assert module._CONTRACT_UPDATE_UNSCOPED_PARTY_ID == expected_update
    assert module._CONTRACT_UPDATE_RESOURCE_CONTEXT == {
        "party_id": expected_update,
        "owner_party_id": expected_update,
        "manager_party_id": expected_update,
    }

    expected_delete = "__unscoped__:contract:delete"
    assert module._CONTRACT_DELETE_UNSCOPED_PARTY_ID == expected_delete
    assert module._CONTRACT_DELETE_RESOURCE_CONTEXT == {
        "party_id": expected_delete,
        "owner_party_id": expected_delete,
        "manager_party_id": expected_delete,
    }


@pytest.mark.asyncio
async def test_get_batch_status_should_delegate_session_lookup_to_service() -> None:
    """批处理状态接口应委托 PDFImportService 获取会话映射。"""
    from src.api.v1.documents import pdf_batch_routes as module
    from src.api.v1.documents.pdf_batch_routes import get_batch_status

    mock_service = MagicMock()
    mock_service.get_session_map_async = AsyncMock(
        return_value={
            "session-1": MagicMock(
                original_filename="demo.pdf",
                status=MagicMock(value="processing"),
                progress_percentage=50.0,
                error_message=None,
            )
        }
    )
    mock_service_cls = MagicMock(return_value=mock_service)
    mock_user = MagicMock()
    mock_user.id = "user-1"

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "PDFImportService", mock_service_cls)
        monkeypatch.setattr(
            module,
            "_resolve_accessible_organization_ids",
            AsyncMock(return_value=[]),
        )
        monkeypatch.setattr(
            module,
            "_get_batch_status",
            lambda _batch_id, **_kwargs: {
                "batch_id": "batch-1",
                "status": "processing",
                "session_ids": ["session-1"],
                "created_at": "2026-02-08T00:00:00",
                "updated_at": "2026-02-08T00:00:00",
            },
        )
        monkeypatch.setattr(
            module,
            "_calculate_batch_progress",
            lambda _batch_id: {"total": 1, "completed": 0, "failed": 0, "processing": 1, "pending": 0},
        )

        result = await get_batch_status(
            batch_id="batch-1",
            db=MagicMock(),
            current_user=mock_user,
        )

    body = json.loads(result.body.decode())
    assert body["data"]["batch_status"]["batch_id"] == "batch-1"
    mock_service.get_session_map_async.assert_awaited_once_with(
        db=ANY,
        session_ids=["session-1"],
        current_user_id="user-1",
    )


@pytest.mark.asyncio
async def test_cancel_batch_should_delegate_session_lookup_to_service() -> None:
    """取消批处理接口应委托 PDFImportService 获取会话映射。"""
    from src.api.v1.documents import pdf_batch_routes as module
    from src.api.v1.documents.pdf_batch_routes import cancel_batch

    mock_service = MagicMock()
    mock_service.get_session_map_async = AsyncMock(
        return_value={
            "session-1": MagicMock(is_processing=True),
        }
    )
    mock_service.cancel_processing = AsyncMock(return_value=None)
    mock_service_cls = MagicMock(return_value=mock_service)
    mock_user = MagicMock()
    mock_user.id = "user-1"

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "PDFImportService", mock_service_cls)
        monkeypatch.setattr(
            module,
            "_resolve_accessible_organization_ids",
            AsyncMock(return_value=[]),
        )
        monkeypatch.setattr(
            module,
            "_get_batch_status",
            lambda _batch_id, **_kwargs: {
                "batch_id": "batch-1",
                "status": module.BatchStatus.PROCESSING,
                "session_ids": ["session-1"],
            },
        )
        monkeypatch.setattr(module, "_update_batch_status", lambda *_args, **_kwargs: None)

        result = await cancel_batch(
            batch_id="batch-1",
            db=MagicMock(),
            current_user=mock_user,
        )

    body = json.loads(result.body.decode())
    assert body["data"]["cancelled_count"] == 1
    mock_service.get_session_map_async.assert_awaited_once_with(
        db=ANY,
        session_ids=["session-1"],
        current_user_id="user-1",
    )
    mock_service.cancel_processing.assert_awaited_once_with(
        db=ANY,
        session_id="session-1",
        reason="Batch batch-1 cancelled by user",
        current_user_id="user-1",
    )
