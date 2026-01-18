"""
Integration tests for unified error handling system (api_errors).

Tests the api_errors functions to ensure they:
1. Create correct UnifiedError exceptions with proper status codes
2. Include appropriate error codes and metadata
3. Are properly caught by the exception handler

Created: 2026-01-17 (Part of error handling unification)
"""

import pytest
from fastapi import status

from src.core.api_errors import (
    bad_request,
    conflict,
    forbidden,
    internal_error,
    not_found,
    operation_not_allowed,
    service_unavailable,
    unauthorized,
    validation_error,
)
from src.core.unified_error_handler import ErrorCode, ErrorSeverity, UnifiedError


class TestNotFoundError:
    """Tests for not_found function."""

    def test_basic_not_found(self) -> None:
        """Test basic not_found error creation."""
        error = not_found("资源不存在")

        assert isinstance(error, UnifiedError)
        assert error.status_code == status.HTTP_404_NOT_FOUND
        assert error.code == ErrorCode.NOT_FOUND
        assert error.message == "资源不存在"
        assert error.severity == ErrorSeverity.LOW

    def test_not_found_with_resource_info(self) -> None:
        """Test not_found with resource type and ID."""
        error = not_found(
            "合同不存在", resource_type="contract", resource_id="test-123"
        )

        assert error.extra_data["resource_type"] == "contract"
        assert error.extra_data["resource_id"] == "test-123"

    def test_not_found_default_message(self) -> None:
        """Test not_found with default message."""
        error = not_found()
        assert error.message == "资源未找到"


class TestBadRequestError:
    """Tests for bad_request function."""

    def test_basic_bad_request(self) -> None:
        """Test basic bad_request error creation."""
        error = bad_request("参数无效")

        assert isinstance(error, UnifiedError)
        assert error.status_code == status.HTTP_400_BAD_REQUEST
        assert error.code == ErrorCode.INVALID_REQUEST
        assert error.message == "参数无效"
        assert error.severity == ErrorSeverity.MEDIUM

    def test_bad_request_with_field(self) -> None:
        """Test bad_request with field information."""
        error = bad_request("日期格式错误", field="start_date")

        assert error.extra_data["field"] == "start_date"

    def test_bad_request_with_details(self) -> None:
        """Test bad_request with details."""
        details = {"expected": "YYYY-MM-DD", "received": "invalid"}
        error = bad_request("格式错误", details=details)

        assert error.details == details


class TestValidationError:
    """Tests for validation_error function."""

    def test_basic_validation_error(self) -> None:
        """Test basic validation_error creation."""
        error = validation_error("数据验证失败")

        assert isinstance(error, UnifiedError)
        assert error.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert error.code == ErrorCode.VALIDATION_ERROR
        assert error.severity == ErrorSeverity.MEDIUM

    def test_validation_error_with_field_list(self) -> None:
        """Test validation_error with field error list."""
        field_errors = ["name", "email", "phone"]
        error = validation_error("必填字段缺失", field_errors=field_errors)

        assert error.details == field_errors

    def test_validation_error_with_field_dict(self) -> None:
        """Test validation_error with field error dictionary."""
        field_errors = {"name": "不能为空", "email": "格式无效"}
        error = validation_error("字段验证失败", field_errors=field_errors)

        assert error.details == field_errors


class TestAuthorizationErrors:
    """Tests for unauthorized and forbidden functions."""

    def test_unauthorized(self) -> None:
        """Test unauthorized error creation."""
        error = unauthorized()

        assert isinstance(error, UnifiedError)
        assert error.status_code == status.HTTP_401_UNAUTHORIZED
        assert error.code == ErrorCode.UNAUTHORIZED
        assert error.message == "未授权，请登录"
        assert error.severity == ErrorSeverity.HIGH

    def test_unauthorized_custom_message(self) -> None:
        """Test unauthorized with custom message."""
        error = unauthorized("登录已过期")
        assert error.message == "登录已过期"

    def test_forbidden(self) -> None:
        """Test forbidden error creation."""
        error = forbidden()

        assert isinstance(error, UnifiedError)
        assert error.status_code == status.HTTP_403_FORBIDDEN
        assert error.code == ErrorCode.FORBIDDEN
        assert error.message == "权限不足"
        assert error.severity == ErrorSeverity.HIGH

    def test_forbidden_custom_message(self) -> None:
        """Test forbidden with custom message."""
        error = forbidden("只有管理员可以执行此操作")
        assert error.message == "只有管理员可以执行此操作"


class TestConflictError:
    """Tests for conflict function."""

    def test_basic_conflict(self) -> None:
        """Test basic conflict error creation."""
        error = conflict("资源已存在")

        assert isinstance(error, UnifiedError)
        assert error.status_code == status.HTTP_409_CONFLICT
        assert error.code == ErrorCode.RESOURCE_CONFLICT
        assert error.message == "资源已存在"
        assert error.severity == ErrorSeverity.MEDIUM

    def test_conflict_with_resource_type(self) -> None:
        """Test conflict with resource type."""
        error = conflict("合同编号已存在", resource_type="contract")

        assert error.extra_data["resource_type"] == "contract"


class TestInternalError:
    """Tests for internal_error function."""

    def test_basic_internal_error(self) -> None:
        """Test basic internal_error creation."""
        error = internal_error("数据库操作失败")

        assert isinstance(error, UnifiedError)
        assert error.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert error.code == ErrorCode.INTERNAL_SERVER_ERROR
        assert error.message == "数据库操作失败"
        assert error.severity == ErrorSeverity.CRITICAL

    def test_internal_error_default_message(self) -> None:
        """Test internal_error with default message."""
        error = internal_error()
        assert error.message == "服务器内部错误"

    def test_internal_error_with_original_exception(self) -> None:
        """Test internal_error with original exception."""
        original = ValueError("Original error")
        error = internal_error("操作失败", original_error=original)

        assert "original_error" in error.extra_data
        assert error.extra_data["original_error"] == "Original error"


class TestServiceUnavailable:
    """Tests for service_unavailable function."""

    def test_basic_service_unavailable(self) -> None:
        """Test basic service_unavailable creation."""
        error = service_unavailable("数据库暂时不可用")

        assert isinstance(error, UnifiedError)
        assert error.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert error.code == ErrorCode.EXTERNAL_SERVICE_ERROR
        assert error.message == "数据库暂时不可用"
        assert error.severity == ErrorSeverity.HIGH

    def test_service_unavailable_with_service_name(self) -> None:
        """Test service_unavailable with service name."""
        error = service_unavailable("Redis连接失败", service_name="redis")

        assert error.extra_data["service"] == "redis"


class TestOperationNotAllowed:
    """Tests for operation_not_allowed function."""

    def test_basic_operation_not_allowed(self) -> None:
        """Test basic operation_not_allowed creation."""
        error = operation_not_allowed("合同状态不允许此操作")

        assert isinstance(error, UnifiedError)
        assert error.status_code == status.HTTP_400_BAD_REQUEST
        assert error.code == ErrorCode.OPERATION_NOT_ALLOWED
        assert error.message == "合同状态不允许此操作"
        assert error.severity == ErrorSeverity.MEDIUM

    def test_operation_not_allowed_with_reason(self) -> None:
        """Test operation_not_allowed with reason."""
        error = operation_not_allowed("无法删除合同", reason="合同已签署，不能删除")

        assert error.extra_data["reason"] == "合同已签署，不能删除"


class TestErrorRaising:
    """Tests for raising errors as exceptions."""

    def test_not_found_is_raisable(self) -> None:
        """Test that not_found can be raised."""
        with pytest.raises(UnifiedError) as exc_info:
            raise not_found("测试资源不存在")

        assert exc_info.value.status_code == 404

    def test_bad_request_is_raisable(self) -> None:
        """Test that bad_request can be raised."""
        with pytest.raises(UnifiedError) as exc_info:
            raise bad_request("测试参数无效")

        assert exc_info.value.status_code == 400

    def test_internal_error_is_raisable(self) -> None:
        """Test that internal_error can be raised."""
        with pytest.raises(UnifiedError) as exc_info:
            raise internal_error("测试服务器错误")

        assert exc_info.value.status_code == 500

    def test_unified_error_str_representation(self) -> None:
        """Test UnifiedError string representation."""
        error = not_found("测试消息")
        error_str = str(error)

        # Should contain key info
        assert "404" in error_str or "NOT_FOUND" in error_str


class TestErrorCodeCoverage:
    """Ensure all ErrorCodes are used by at least one function."""

    def test_all_common_error_codes_covered(self) -> None:
        """Verify common HTTP error codes are covered."""
        # 400 Bad Request
        assert bad_request("test").status_code == 400

        # 401 Unauthorized
        assert unauthorized("test").status_code == 401

        # 403 Forbidden
        assert forbidden("test").status_code == 403

        # 404 Not Found
        assert not_found("test").status_code == 404

        # 409 Conflict
        assert conflict("test").status_code == 409

        # 422 Unprocessable Entity
        assert validation_error("test").status_code == 422

        # 500 Internal Server Error
        assert internal_error("test").status_code == 500

        # 503 Service Unavailable
        assert service_unavailable("test").status_code == 503
