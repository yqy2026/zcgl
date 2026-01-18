#!/usr/bin/env python3
"""
测试数据库会话管理和事务失败场景
验证 PDFImportService 的数据库会话上下文管理器模式
"""

from unittest.mock import MagicMock, Mock, patch

import pytest
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError

from src.services.document.pdf_import_service import PDFImportService


class TestDatabaseSessionManagement:
    """测试数据库会话上下文管理器和事务失败"""

    @pytest.mark.asyncio
    async def test_persist_result_database_transaction_failure(self):
        """测试数据库事务在提交时失败的情况"""
        service = PDFImportService()
        session_id = "test-session-123"
        result = {"success": True, "extracted_fields": {"contract_number": "CT001"}}
        processing_time = 100.0

        # 模拟数据库管理器
        with patch("src.database._get_database_manager") as mock_db_manager:
            mock_session = Mock()
            mock_session.commit.side_effect = OperationalError(
                "Database locked", None, None
            )

            # 设置上下文管理器
            mock_context = MagicMock()
            mock_context.__enter__.return_value = mock_session
            mock_context.__exit__.return_value = False
            mock_db_manager.return_value.get_session.return_value = mock_context

            # 应该抛出异常
            with pytest.raises(OperationalError):
                await service._persist_processing_result(
                    session_id, result, processing_time
                )

            # 验证 rollback 被调用
            mock_session.rollback.assert_called_once()

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

        with patch("src.database._get_database_manager") as mock_db_manager:
            mock_session = Mock()
            # 第一次 query 成功返回 session 对象
            mock_pdf_session = Mock()
            mock_session.query.return_value.filter.return_value.first.return_value = (
                mock_pdf_session
            )
            # 提交时失败
            mock_session.commit.side_effect = SQLAlchemyError("Connection lost")

            mock_context = MagicMock()
            mock_context.__enter__.return_value = mock_session
            mock_context.__exit__.return_value = False
            mock_db_manager.return_value.get_session.return_value = mock_context

            # 应该抛出异常
            with pytest.raises(SQLAlchemyError):
                await service._persist_processing_error(session_id, error_result)

            # 验证错误被设置到 session 对象
            assert mock_pdf_session.error_message == "Extraction failed"
            assert mock_pdf_session.processing_result == error_result
            # 验证 rollback 被调用
            mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_persist_result_session_not_found(self):
        """测试会话不存在时的处理"""
        service = PDFImportService()
        session_id = "nonexistent-session"
        result = {"success": True}
        processing_time = 50.0

        with patch("src.database._get_database_manager") as mock_db_manager:
            mock_session = Mock()
            # query 返回 None（会话不存在）
            mock_session.query.return_value.filter.return_value.first.return_value = (
                None
            )

            mock_context = MagicMock()
            mock_context.__enter__.return_value = mock_session
            mock_context.__exit__.return_value = False
            mock_db_manager.return_value.get_session.return_value = mock_context

            # 不应该抛出异常，应该优雅处理
            await service._persist_processing_result(
                session_id, result, processing_time
            )

            # 验证没有调用 commit（因为没有数据要保存）
            mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_context_manager_ensures_cleanup_on_exception(self):
        """测试上下文管理器在异常时确保资源清理"""
        service = PDFImportService()
        session_id = "test-cleanup"
        result = {"success": True}
        processing_time = 75.0

        with patch("src.database._get_database_manager") as mock_db_manager:
            mock_session = Mock()
            mock_pdf_session = Mock()
            mock_session.query.return_value.filter.return_value.first.return_value = (
                mock_pdf_session
            )

            # 在设置属性后抛出异常
            def raise_on_commit():
                raise OperationalError("Deadlock detected", None, None)

            mock_session.commit.side_effect = raise_on_commit

            mock_context = MagicMock()
            mock_context.__enter__.return_value = mock_session
            mock_context.__exit__.return_value = False
            mock_db_manager.return_value.get_session.return_value = mock_context

            with pytest.raises(OperationalError):
                await service._persist_processing_result(
                    session_id, result, processing_time
                )

            # 验证上下文管理器的 __exit__ 被调用（资源清理）
            mock_context.__exit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_confirm_import_integrity_error_returns_user_error(self):
        """测试 confirm_import 在完整性约束冲突时返回用户错误"""
        service = PDFImportService()

        # 创建模拟的数据库会话
        mock_db = Mock()

        # 模拟会话存在
        mock_import_session = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_import_session
        )

        # 模拟添加合同时发生完整性错误（如合同号重复）
        mock_db.add.side_effect = IntegrityError(
            "Duplicate contract_number", None, None
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

        # 应该返回用户错误（不是系统错误）
        assert result["success"] is False
        assert result["error_category"] == "USER_ERROR"
        assert result["error_type"] == "INTEGRITY_ERROR"
        assert "suggested_action" in result
        # 验证回滚被调用
        mock_db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_confirm_import_operational_error_raises_exception(self):
        """测试 confirm_import 在数据库操作错误时抛出异常（系统错误）"""
        service = PDFImportService()

        mock_db = Mock()
        mock_import_session = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_import_session
        )

        # 模拟数据库操作错误
        mock_db.commit.side_effect = OperationalError("Connection timeout", None, None)

        session_id = "test-session"
        confirmed_data = {
            "contract_data": {
                "contract_number": "CT002",
                "tenant_name": "Test",
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
            }
        }

        # 系统错误应该抛出异常而不是返回错误字典
        with pytest.raises(RuntimeError) as exc_info:
            await service.confirm_import(mock_db, session_id, confirmed_data, user_id=1)

        assert "Database error creating contract" in str(exc_info.value)
