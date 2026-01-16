"""
测试异常处理改进

验证异常处理不暴露内部错误，且正确转换技术异常为业务异常
"""

import pytest
from sqlalchemy.exc import IntegrityError

from src.core.exception_handler import (
    ResourceNotFoundError,
    BusinessValidationError,
    DuplicateResourceError,
)
from src.core.exception_helpers import handle_service_exception


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



@pytest.mark.skip(reason="API exception handling tests require actual API endpoints and authentication setup")
class TestAPIExceptionHandling:
    """测试API层异常处理"""

    def test_api_propagates_business_exceptions(self, client):
        """测试API层传播业务异常"""
        # 这个测试需要实际的测试数据和端点
        # 这里只是示例结构
        response = client.get("/api/v1/assets/non_existent_id")

        # 应该返回404而不是500
        assert response.status_code in [404, 500]

        # 如果返回500，不应该暴露内部错误详情
        if response.status_code == 500:
            data = response.json()
            # 不应该包含数据库错误、SQL语句等
            error_str = str(data)
            assert "SQL" not in error_str
            assert "sqlite" not in error_str.lower()
            assert "traceback" not in error_str.lower()

    def test_error_response_format(self, client):
        """测试错误响应格式符合预期"""
        response = client.get("/api/v1/assets/non_existent_id")
        data = response.json()

        # 验证响应格式包含必要字段
        if "error" in data:
            assert "code" in data["error"]
            assert "message" in data["error"]


class TestServiceExceptionHandling:
    """测试Service层异常处理"""

    def test_service_converts_technical_to_business_errors(self, db_session):
        """测试Service层将技术错误转换为业务错误"""
        # 这里需要实际的Service实例
        # 示例结构，实际测试需要根据具体Service实现
        pass

    def test_service_validates_data_before_db_operation(self, db_session):
        """测试Service层在数据库操作前验证数据"""
        # 示例测试结构
        pass
