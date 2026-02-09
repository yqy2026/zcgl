#!/usr/bin/env python3
"""
测试数据库会话管理和事务失败场景
验证 PDFImportService 的异步数据库会话管理模式
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError

from src.core.exception_handler import InternalServerError
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
    async def test_confirm_import_integrity_error_returns_user_error(self):
        """测试 confirm_import 在完整性约束冲突时返回用户错误"""
        service = PDFImportService()

        mock_import_session = MagicMock()
        mock_db = MagicMock()
        mock_db.execute = AsyncMock(
            return_value=_mock_execute_scalars_first(mock_import_session)
        )
        mock_db.flush = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_db.rollback = AsyncMock()
        mock_db.add = MagicMock(
            side_effect=IntegrityError("Duplicate contract_number", None, None)
        )

        session_id = "test-session"
        confirmed_data = {
            "contract_data": {
                "contract_number": "CT001",
                "tenant_name": "Test Tenant",
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
            }
        }

        result = await service.confirm_import(
            mock_db, session_id, confirmed_data, user_id=1
        )

        assert result["success"] is False
        assert result["error_category"] == "USER_ERROR"
        assert result["error_type"] == "INTEGRITY_ERROR"
        assert "suggested_action" in result
        mock_db.rollback.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_confirm_import_operational_error_raises_exception(self):
        """测试 confirm_import 在数据库操作错误时抛出异常（系统错误）"""
        service = PDFImportService()

        mock_import_session = MagicMock()
        mock_db = MagicMock()
        mock_db.execute = AsyncMock(
            return_value=_mock_execute_scalars_first(mock_import_session)
        )
        mock_db.flush = AsyncMock()
        mock_db.commit = AsyncMock(
            side_effect=OperationalError("Connection timeout", None, None)
        )
        mock_db.refresh = AsyncMock()
        mock_db.rollback = AsyncMock()
        mock_db.add = MagicMock()

        session_id = "test-session"
        confirmed_data = {
            "contract_data": {
                "contract_number": "CT002",
                "tenant_name": "Test",
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
            }
        }

        with pytest.raises(InternalServerError) as exc_info:
            await service.confirm_import(mock_db, session_id, confirmed_data, user_id=1)

        assert "Database error creating contract" in str(exc_info.value)
