"""
测试异常处理改进

验证异常处理不暴露内部错误，且正确转换技术异常为业务异常
"""

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.exc import IntegrityError

from src.core.exception_handler import (
    BusinessValidationError,
    DuplicateResourceError,
    handle_service_exception,
)


class TestExceptionHelpers:
    """测试异常处理辅助函数"""

    def test_handle_integrity_error_unique_constraint(self):
        """测试数据库唯一约束冲突转换为 DuplicateResourceError"""
        error = IntegrityError("unique constraint failed", None, None)

        with pytest.raises(DuplicateResourceError):
            handle_service_exception(error, "TestService", "create")

    def test_handle_integrity_error_other(self):
        """测试其他数据库完整性错误转换为 BusinessValidationError"""
        error = IntegrityError("foreign key constraint failed", None, None)

        with pytest.raises(BusinessValidationError, match="数据完整性错误"):
            handle_service_exception(error, "TestService", "delete")

    def test_handle_value_error(self):
        """测试 ValueError 转换为 BusinessValidationError"""
        error = ValueError("Invalid value")

        with pytest.raises(BusinessValidationError, match="数据验证失败"):
            handle_service_exception(error, "TestService", "validate")

    def test_handle_type_error(self):
        """测试 TypeError 转换为 BusinessValidationError"""
        error = TypeError("Invalid type")

        with pytest.raises(BusinessValidationError, match="数据验证失败"):
            handle_service_exception(error, "TestService", "process")

    def test_handle_unknown_exception_reraises(self):
        """测试未知异常重新抛出"""
        error = RuntimeError("Unexpected error")

        # 应该重新抛出原始异常
        with pytest.raises(RuntimeError, match="Unexpected error"):
            handle_service_exception(error, "TestService", "execute")

    def test_logs_error(self, caplog):
        """测试错误被正确记录"""
        error = ValueError("Test error")

        with pytest.raises(BusinessValidationError):
            with caplog.at_level("ERROR"):
                handle_service_exception(error, "TestService", "test_operation")

        # 验证日志记录
        assert "TestService - test_operation failed" in caplog.text


class TestAPIExceptionHandling:
    """测试API层异常处理"""

    @patch("src.api.v1.assets.assets.AsyncAssetService.get_asset", new_callable=AsyncMock)
    def test_api_propagates_business_exceptions(self, mock_get_asset, client):
        """测试API层业务异常保持契约语义"""
        mock_get_asset.side_effect = BusinessValidationError(
            "资产ID格式不正确",
            field_errors={"asset_id": ["invalid"]},
        )

        response = client.get("/api/v1/assets/non_existent_id")

        assert response.status_code == 422
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert data["error"]["message"] == "资产ID格式不正确"

    @patch("src.api.v1.assets.assets.AsyncAssetService.get_asset", new_callable=AsyncMock)
    def test_api_general_exception_masked_as_internal_error(
        self, mock_get_asset, client
    ):
        """测试API层通用异常会走错误恢复中间件契约"""
        mock_get_asset.side_effect = RuntimeError("database unavailable")

        response = client.get("/api/v1/assets/non_existent_id")

        assert response.status_code == 503
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "DATABASE_ERROR"
        assert data["error"]["message"] == "database unavailable"
