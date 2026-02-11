"""分层约束测试：pdf_batch_routes 路由应委托服务层。"""

import json
from pathlib import Path
from unittest.mock import ANY, AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.api


def test_pdf_batch_routes_module_should_not_import_session_crud_directly() -> None:
    """pdf_batch_routes 路由模块不应直接导入 PDFImportSessionCRUD。"""
    from src.api.v1.documents import pdf_batch_routes as module

    module_source = Path(module.__file__).read_text(encoding="utf-8")
    assert "from ....crud.pdf_import_session import PDFImportSessionCRUD" not in module_source
    assert "PDFImportSessionCRUD(" not in module_source


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
