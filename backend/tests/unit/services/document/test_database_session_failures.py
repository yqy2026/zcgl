#!/usr/bin/env python3
"""
测试数据库会话管理和事务失败场景
验证 PDFImportService 的异步数据库会话管理模式
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from src.services.document.pdf_import_service import PDFImportService


def _mock_execute_scalars_first(item):
    result = MagicMock()
    scalars = MagicMock()
    scalars.first.return_value = item
    result.scalars.return_value = scalars
    return result


def _mock_async_session_context(db):
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=db)
    context.__aexit__ = AsyncMock(return_value=False)
    return context


class TestDatabaseSessionManagement:
    """测试数据库会话上下文管理器和事务失败"""

    @pytest.mark.asyncio
    async def test_persist_result_database_transaction_failure(self):
        """测试数据库事务在提交时失败的情况"""
        service = PDFImportService()
        session_id = "test-session-123"
        result = {"success": True, "extracted_fields": {"contract_number": "CT001"}}
        processing_time = 100.0

        mock_pdf_session = MagicMock()
        mock_db = MagicMock()
        mock_db.execute = AsyncMock(
            return_value=_mock_execute_scalars_first(mock_pdf_session)
        )
        mock_db.commit = AsyncMock(
            side_effect=OperationalError("Database locked", None, None)
        )
        mock_db.rollback = AsyncMock()

        mock_context = _mock_async_session_context(mock_db)
        with patch("src.database.async_session_scope", return_value=mock_context):
            with pytest.raises(OperationalError):
                await service._persist_processing_result(
                    session_id, result, processing_time
                )

        mock_db.rollback.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_persist_error_database_commit_failure(self):
        """测试错误持久化时数据库提交失败"""
        service = PDFImportService()
        session_id = "test-session-456"
        error_result = {
            "success": False,
            "error": "Extraction failed",
            "error_type": "ExtractionError",
        }

        mock_pdf_session = MagicMock()
        mock_db = MagicMock()
        mock_db.execute = AsyncMock(
            return_value=_mock_execute_scalars_first(mock_pdf_session)
        )
        mock_db.commit = AsyncMock(side_effect=SQLAlchemyError("Connection lost"))
        mock_db.rollback = AsyncMock()

        mock_context = _mock_async_session_context(mock_db)
        with patch("src.database.async_session_scope", return_value=mock_context):
            with pytest.raises(SQLAlchemyError):
                await service._persist_processing_error(session_id, error_result)

        assert mock_pdf_session.error_message == "Extraction failed"
        assert mock_pdf_session.processing_result == error_result
        mock_db.rollback.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_persist_result_session_not_found(self):
        """测试会话不存在时的处理"""
        service = PDFImportService()
        session_id = "nonexistent-session"
        result = {"success": True}
        processing_time = 50.0

        mock_db = MagicMock()
        mock_db.execute = AsyncMock(return_value=_mock_execute_scalars_first(None))
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()

        mock_context = _mock_async_session_context(mock_db)
        with patch("src.database.async_session_scope", return_value=mock_context):
            await service._persist_processing_result(session_id, result, processing_time)

        mock_db.commit.assert_not_awaited()
        mock_db.rollback.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_context_manager_ensures_cleanup_on_exception(self):
        """测试上下文管理器在异常时确保资源清理"""
        service = PDFImportService()
        session_id = "test-cleanup"
        result = {"success": True}
        processing_time = 75.0

        mock_pdf_session = MagicMock()
        mock_db = MagicMock()
        mock_db.execute = AsyncMock(
            return_value=_mock_execute_scalars_first(mock_pdf_session)
        )
        mock_db.commit = AsyncMock(
            side_effect=OperationalError("Deadlock detected", None, None)
        )
        mock_db.rollback = AsyncMock()

        mock_context = _mock_async_session_context(mock_db)
        with patch("src.database.async_session_scope", return_value=mock_context):
            with pytest.raises(OperationalError):
                await service._persist_processing_result(
                    session_id, result, processing_time
                )

        mock_context.__aexit__.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_confirm_import_missing_required_context_does_not_commit(self):
        """缺少新体系必填上下文时，confirm_import 不应提交任何事务。"""
        service = PDFImportService()

        mock_import_session = MagicMock()
        mock_import_session.status = "ready_for_review"
        mock_db = MagicMock()
        mock_db.flush = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_db.rollback = AsyncMock()
        mock_db.add = MagicMock()

        session_id = "test-session"
        confirmed_data = {
            "owner_party_id": "party-owner",
            "contract_data": {
                "contract_number": "CT001",
                "tenant_name": "Test Tenant",
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
            }
        }

        with patch(
            "src.services.document.pdf_import_service.pdf_import_session_crud.get_by_session_id_async",
            new=AsyncMock(return_value=mock_import_session),
        ):
            result = await service.confirm_import(
                mock_db, session_id, confirmed_data, user_id=1
            )

        assert result["success"] is False
        assert "Missing required fields" in result["error"]
        mock_db.add.assert_not_called()
        mock_db.flush.assert_not_awaited()
        mock_db.commit.assert_not_awaited()
        mock_db.refresh.assert_not_awaited()
        mock_db.rollback.assert_not_awaited()
