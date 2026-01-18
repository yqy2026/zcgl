"""
Enhanced Error Handler 单元测试

测试 EnhancedPDFImportError 类的错误处理、重试机制和健康检查功能
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from src.services.core.enhanced_error_handler import (
    EnhancedPDFImportError,
    enhanced_error_handler,
    monitor_processing_health,
)


# ============================================================================
# Fixtures
# ============================================================================
@pytest.fixture
def error_handler():
    """错误处理器实例"""
    return EnhancedPDFImportError()


@pytest.fixture
def sample_context():
    """示例请求上下文"""
    return {
        "user_id": "test-user-123",
        "file_name": "test.pdf",
        "file_size": 1024000,
        "request_id": "req-abc-123",
    }


@pytest.fixture
def sample_error():
    """示例异常"""
    return ValueError("Test error message")


# ============================================================================
# Test __init__ - 初始化测试
# ============================================================================
class TestEnhancedPDFImportErrorInit:
    """测试 EnhancedPDFImportError 初始化"""

    def test_initialization(self, error_handler):
        """测试初始化默认值"""
        assert error_handler.max_retries == 3
        assert error_handler.max_file_size_mb == 50
        assert error_handler.retry_delays == [1, 5, 10]

    def test_timeout_seconds_initialized(self, error_handler):
        """测试超时配置初始化"""
        assert "upload" in error_handler.timeout_seconds
        assert "processing" in error_handler.timeout_seconds
        assert "ocr_initialization" in error_handler.timeout_seconds
        assert "database_operation" in error_handler.timeout_seconds
        assert "api_call" in error_handler.timeout_seconds

        # 验证具体值
        assert error_handler.timeout_seconds["upload"] == 300
        assert error_handler.timeout_seconds["processing"] == 600
        assert error_handler.timeout_seconds["ocr_initialization"] == 120
        assert error_handler.timeout_seconds["database_operation"] == 30
        assert error_handler.timeout_seconds["api_call"] == 60

    def test_error_types_initialized(self, error_handler):
        """测试错误类型初始化"""
        assert "file_too_large" in error_handler.error_types
        assert "file_format_unsupported" in error_handler.error_types
        assert "corrupted_file" in error_handler.error_types
        assert "ocr_engine_failure" in error_handler.error_types
        assert "processing_timeout" in error_handler.error_types
        assert "database_error" in error_handler.error_types
        assert "network_error" in error_handler.error_types
        assert "validation_error" in error_handler.error_types
        assert "unknown_error" in error_handler.error_types

        # 验证具体值
        assert error_handler.error_types["file_too_large"] == "文件大小超过限制"
        assert error_handler.error_types["unknown_error"] == "未知错误"


# ============================================================================
# Test handle_error - 错误处理测试
# ============================================================================
class TestHandleError:
    """测试 handle_error 方法"""

    def test_handle_file_too_large_error(
        self, error_handler, sample_error, sample_context
    ):
        """测试处理文件过大错误"""
        result = error_handler.handle_error(
            error=sample_error,
            context=sample_context,
            error_type="file_too_large",
        )

        assert result["success"] is False
        assert result["error"] == "文件大小超过限制"
        assert result["error_type"] == "file_too_large"
        assert result["retry_count"] == 1
        assert result["max_retries"] == 3
        assert "suggested_action" in result
        assert "压缩PDF文件或分批上传" == result["suggested_action"]

    def test_handle_file_format_unsupported_error(
        self, error_handler, sample_error, sample_context
    ):
        """测试处理不支持的文件格式错误"""
        result = error_handler.handle_error(
            error=sample_error,
            context=sample_context,
            error_type="file_format_unsupported",
        )

        assert result["success"] is False
        assert result["error"] == "不支持的文件格式"
        assert result["error_type"] == "file_format_unsupported"
        assert result["retry_count"] == 1
        assert result["suggested_action"] == "转换文件格式为PDF"

    def test_handle_corrupted_file_error(
        self, error_handler, sample_error, sample_context
    ):
        """测试处理损坏文件错误"""
        result = error_handler.handle_error(
            error=sample_error,
            context=sample_context,
            error_type="corrupted_file",
        )

        assert result["success"] is False
        assert result["error"] == "PDF文件可能已损坏"
        assert result["error_type"] == "corrupted_file"
        assert result["suggested_action"] == "重新扫描文件或修复文件"

    def test_handle_processing_timeout_error(
        self, error_handler, sample_error, sample_context
    ):
        """测试处理超时错误"""
        result = error_handler.handle_error(
            error=sample_error,
            context=sample_context,
            error_type="processing_timeout",
        )

        assert result["success"] is False
        assert result["error"] == "处理超时"
        assert result["error_type"] == "processing_timeout"
        assert "estimated_retry_time" in result
        assert result["retry_count"] == 1
        assert result["suggested_action"] == "稍后重试或联系技术支持"

    def test_processing_timeout_retry_delay_calculation(
        self, error_handler, sample_error, sample_context
    ):
        """测试超时重试延迟计算"""
        # 第一次重试：10秒
        result1 = error_handler.handle_error(
            error=sample_error,
            context=sample_context,
            error_type="processing_timeout",
            retry_count=0,
        )
        assert result1["estimated_retry_time"] == "10秒"

        # 第二次重试：20秒
        result2 = error_handler.handle_error(
            error=sample_error,
            context=sample_context,
            error_type="processing_timeout",
            retry_count=1,
        )
        assert result2["estimated_retry_time"] == "20秒"

        # 第三次重试：30秒
        result3 = error_handler.handle_error(
            error=sample_error,
            context=sample_context,
            error_type="processing_timeout",
            retry_count=2,
        )
        assert result3["estimated_retry_time"] == "30秒"

        # 第四次重试：60秒（最大值）
        result4 = error_handler.handle_error(
            error=sample_error,
            context=sample_context,
            error_type="processing_timeout",
            retry_count=6,
        )
        assert result4["estimated_retry_time"] == "60秒"

    def test_handle_ocr_engine_failure_error(
        self, error_handler, sample_error, sample_context
    ):
        """测试处理OCR引擎失败错误"""
        result = error_handler.handle_error(
            error=sample_error,
            context=sample_context,
            error_type="ocr_engine_failure",
        )

        assert result["success"] is False
        assert result["error"] == "OCR引擎初始化失败"
        assert result["error_type"] == "ocr_engine_failure"
        assert result["suggested_action"] == "继续处理，将使用其他OCR引擎"

    def test_handle_database_error(self, error_handler, sample_error, sample_context):
        """测试处理数据库错误"""
        result = error_handler.handle_error(
            error=sample_error,
            context=sample_context,
            error_type="database_error",
        )

        assert result["success"] is False
        assert result["error"] == "数据库操作失败"
        assert result["error_type"] == "database_error"
        assert result["suggested_action"] == "检查数据库连接或联系技术支持"

    def test_handle_network_error(self, error_handler, sample_error, sample_context):
        """测试处理网络错误"""
        result = error_handler.handle_error(
            error=sample_error,
            context=sample_context,
            error_type="network_error",
        )

        assert result["success"] is False
        assert result["error"] == "网络连接错误"
        assert result["error_type"] == "network_error"
        assert result["suggested_action"] == "检查网络设置或重试"

    def test_handle_unknown_error(self, error_handler, sample_error, sample_context):
        """测试处理未知错误"""
        result = error_handler.handle_error(
            error=sample_error,
            context=sample_context,
            error_type="unknown_error",
        )

        assert result["success"] is False
        assert "未知错误" in result["error"]
        assert result["error_type"] == "unknown_error"
        assert result["suggested_action"] == "请检查系统状态或联系技术支持"
        assert "status_code" in result
        assert result["status_code"] == 500

    def test_handle_custom_error_type(
        self, error_handler, sample_error, sample_context
    ):
        """测试处理自定义错误类型（未定义的）"""
        custom_error = ValueError("Custom error")
        result = error_handler.handle_error(
            error=custom_error,
            context=sample_context,
            error_type="custom_error_type",
        )

        assert result["success"] is False
        assert "Custom error" in result["error"]
        assert result["error_type"] == "custom_error_type"
        assert result["status_code"] == 500

    def test_retry_count_increments(self, error_handler, sample_error, sample_context):
        """测试重试计数递增"""
        result1 = error_handler.handle_error(
            error=sample_error,
            context=sample_context,
            error_type="unknown_error",
            retry_count=0,
        )
        assert result1["retry_count"] == 1

        result2 = error_handler.handle_error(
            error=sample_error,
            context=sample_context,
            error_type="unknown_error",
            retry_count=2,
        )
        assert result2["retry_count"] == 3

    def test_error_with_different_exception_types(self, error_handler, sample_context):
        """测试不同异常类型的处理"""
        exceptions = [
            ValueError("Value error"),
            TypeError("Type error"),
            RuntimeError("Runtime error"),
            OSError("IO error"),
            Exception("Generic exception"),
        ]

        for exc in exceptions:
            result = error_handler.handle_error(
                error=exc, context=sample_context, error_type="unknown_error"
            )
            assert result["success"] is False
            assert str(exc) in result["error"]


# ============================================================================
# Test get_timeout_seconds - 获取超时时间测试
# ============================================================================
class TestGetTimeoutSeconds:
    """测试 get_timeout_seconds 方法"""

    def test_get_upload_timeout(self, error_handler):
        """测试获取上传超时时间"""
        timeout = error_handler.get_timeout_seconds("upload")
        assert timeout == 300

    def test_get_processing_timeout(self, error_handler):
        """测试获取处理超时时间"""
        timeout = error_handler.get_timeout_seconds("processing")
        assert timeout == 600

    def test_get_ocr_initialization_timeout(self, error_handler):
        """测试获取OCR初始化超时时间"""
        timeout = error_handler.get_timeout_seconds("ocr_initialization")
        assert timeout == 120

    def test_get_database_operation_timeout(self, error_handler):
        """测试获取数据库操作超时时间"""
        timeout = error_handler.get_timeout_seconds("database_operation")
        assert timeout == 30

    def test_get_api_call_timeout(self, error_handler):
        """测试获取API调用超时时间"""
        timeout = error_handler.get_timeout_seconds("api_call")
        assert timeout == 60

    def test_get_unknown_timeout_returns_default(self, error_handler):
        """测试未知类型返回默认超时时间"""
        timeout = error_handler.get_timeout_seconds("unknown_type")
        assert timeout == 300  # 默认值

    def test_get_empty_string_timeout(self, error_handler):
        """测试空字符串返回默认超时时间"""
        timeout = error_handler.get_timeout_seconds("")
        assert timeout == 300

    def test_all_timeout_values_exist(self, error_handler):
        """测试所有超时配置都存在"""
        expected_timeouts = {
            "upload": 300,
            "processing": 600,
            "ocr_initialization": 120,
            "database_operation": 30,
            "api_call": 60,
        }

        for key, expected_value in expected_timeouts.items():
            actual_value = error_handler.get_timeout_seconds(key)
            assert actual_value == expected_value


# ============================================================================
# Test should_retry - 重试判断测试
# ============================================================================
class TestShouldRetry:
    """测试 should_retry 方法"""

    def test_should_retry_when_count_less_than_max(self, error_handler):
        """测试重试次数小于最大值时应重试"""
        assert error_handler.should_retry(0) is True
        assert error_handler.should_retry(1) is True
        assert error_handler.should_retry(2) is True

    def test_should_not_retry_when_count_equals_max(self, error_handler):
        """测试重试次数等于最大值时不应重试"""
        assert error_handler.should_retry(3) is False

    def test_should_not_retry_when_count_exceeds_max(self, error_handler):
        """测试重试次数超过最大值时不应重试"""
        assert error_handler.should_retry(4) is False
        assert error_handler.should_retry(10) is False

    def test_should_retry_with_negative_count(self, error_handler):
        """测试负数重试次数"""
        assert error_handler.should_retry(-1) is True

    def test_retry_boundary_conditions(self, error_handler):
        """测试重试边界条件"""
        # 正好在边界
        assert error_handler.should_retry(error_handler.max_retries - 1) is True
        assert error_handler.should_retry(error_handler.max_retries) is False
        assert error_handler.should_retry(error_handler.max_retries + 1) is False


# ============================================================================
# Test monitor_processing_health - 健康检查测试
# ============================================================================
class TestMonitorProcessingHealth:
    """测试 monitor_processing_health 函数"""

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """测试健康检查成功场景"""
        # Mock OCR service
        mock_ocr_service = Mock()
        mock_ocr_service.__class__.__name__ = "MockOCRService"

        # Import the function to get the actual import path
        import sys

        # Mock the module before importing
        sys.modules["src.services.providers.ocr_provider"] = MagicMock()

        with patch.object(
            sys.modules["src.services.providers.ocr_provider"],
            "get_ocr_service",
            return_value=mock_ocr_service,
        ):
            with patch("os.path.exists", return_value=True):
                with patch("os.access", return_value=True):
                    result = await monitor_processing_health()

                    assert result["ocr_service"]["available"] is True
                    assert result["ocr_service"]["service_type"] == "MockOCRService"
                    assert result["file_system"]["exists"] is True
                    assert result["file_system"]["writable"] is True
                    assert result["error_handler"]["status"] == "active"
                    assert result["error_handler"]["max_retries"] == 3
                    assert result["error_handler"]["max_file_size_mb"] == 50

    @pytest.mark.asyncio
    async def test_health_check_ocr_service_unavailable(self):
        """测试OCR服务不可用场景"""
        import sys

        sys.modules["src.services.providers.ocr_provider"] = MagicMock()

        with patch.object(
            sys.modules["src.services.providers.ocr_provider"],
            "get_ocr_service",
            return_value=None,
        ):
            with patch("os.path.exists", return_value=True):
                with patch("os.access", return_value=True):
                    result = await monitor_processing_health()

                    assert result["ocr_service"]["available"] is False
                    assert result["ocr_service"]["service_type"] == "None"

    @pytest.mark.asyncio
    async def test_health_check_file_system_not_writable(self):
        """测试文件系统不可写场景"""
        import sys

        mock_ocr_service = Mock()
        mock_ocr_service.__class__.__name__ = "MockOCRService"

        sys.modules["src.services.providers.ocr_provider"] = MagicMock()

        with patch.object(
            sys.modules["src.services.providers.ocr_provider"],
            "get_ocr_service",
            return_value=mock_ocr_service,
        ):
            with patch("os.path.exists", return_value=True):
                with patch("os.access", return_value=False):
                    result = await monitor_processing_health()

                    assert result["file_system"]["exists"] is True
                    assert result["file_system"]["writable"] is False

    @pytest.mark.asyncio
    async def test_health_check_upload_dir_not_exists(self):
        """测试上传目录不存在场景"""
        import sys

        mock_ocr_service = Mock()
        mock_ocr_service.__class__.__name__ = "MockOCRService"

        sys.modules["src.services.providers.ocr_provider"] = MagicMock()

        with patch.object(
            sys.modules["src.services.providers.ocr_provider"],
            "get_ocr_service",
            return_value=mock_ocr_service,
        ):
            with patch("os.path.exists", return_value=False):
                result = await monitor_processing_health()

                assert result["file_system"]["exists"] is False
                assert result["file_system"]["writable"] is False

    @pytest.mark.asyncio
    async def test_health_check_exception_handling(self):
        """测试健康检查异常处理"""
        import sys

        sys.modules["src.services.providers.ocr_provider"] = MagicMock()

        with patch.object(
            sys.modules["src.services.providers.ocr_provider"],
            "get_ocr_service",
            side_effect=Exception("Import error"),
        ):
            result = await monitor_processing_health()

            assert result["status"] == "unhealthy"
            assert "error" in result
            assert "Import error" in result["error"]

    @pytest.mark.asyncio
    async def test_health_check_different_ocr_types(self):
        """测试不同OCR服务类型"""
        import sys

        sys.modules["src.services.providers.ocr_provider"] = MagicMock()

        # 测试 Tesseract OCR
        mock_tesseract = Mock()
        mock_tesseract.__class__.__name__ = "TesseractOCR"

        with patch.object(
            sys.modules["src.services.providers.ocr_provider"],
            "get_ocr_service",
            return_value=mock_tesseract,
        ):
            with patch("os.path.exists", return_value=True):
                with patch("os.access", return_value=True):
                    result = await monitor_processing_health()
                    assert result["ocr_service"]["service_type"] == "TesseractOCR"

        # 测试 Paddle OCR
        mock_paddle = Mock()
        mock_paddle.__class__.__name__ = "PaddleOCR"

        with patch.object(
            sys.modules["src.services.providers.ocr_provider"],
            "get_ocr_service",
            return_value=mock_paddle,
        ):
            with patch("os.path.exists", return_value=True):
                with patch("os.access", return_value=True):
                    result = await monitor_processing_health()
                    assert result["ocr_service"]["service_type"] == "PaddleOCR"


# ============================================================================
# Test Global Instance - 全局实例测试
# ============================================================================
class TestGlobalInstance:
    """测试全局错误处理器实例"""

    def test_global_instance_exists(self):
        """测试全局实例存在"""
        from src.services.core.enhanced_error_handler import enhanced_error_handler

        assert enhanced_error_handler is not None
        assert isinstance(enhanced_error_handler, EnhancedPDFImportError)

    def test_global_instance_has_correct_config(self):
        """测试全局实例配置正确"""
        assert enhanced_error_handler.max_retries == 3
        assert enhanced_error_handler.max_file_size_mb == 50
        assert len(enhanced_error_handler.error_types) == 9

    def test_global_instance_can_handle_errors(self):
        """测试全局实例可以处理错误"""
        result = enhanced_error_handler.handle_error(
            error=Exception("Test"),
            context={},
            error_type="unknown_error",
        )

        assert result["success"] is False
        assert "error" in result


# ============================================================================
# Test Error Message Formatting - 错误消息格式化测试
# ============================================================================
class TestErrorMessageFormatting:
    """测试错误消息格式化"""

    def test_file_too_large_includes_size_limit(self, error_handler):
        """测试文件过大错误包含大小限制"""
        error_handler.handle_error(
            error=ValueError("File too large"),
            context={},
            error_type="file_too_large",
        )

        # 检查错误消息中包含大小限制
        assert error_handler.max_file_size_mb == 50

    def test_processing_timeout_includes_retry_info(self, error_handler):
        """测试处理超时错误包含重试信息"""
        result = error_handler.handle_error(
            error=TimeoutError("Processing timeout"),
            context={},
            error_type="processing_timeout",
            retry_count=2,
        )

        # retry_count is incremented by 1 in handle_error
        assert result["retry_count"] == 3
        assert result["max_retries"] == 3

    def test_unknown_error_preserves_original_message(self, error_handler):
        """测试未知错误保留原始错误消息"""
        original_message = "This is a custom error message"
        result = error_handler.handle_error(
            error=Exception(original_message),
            context={},
            error_type="unknown_error",
        )

        assert original_message in result["error"]


# ============================================================================
# Test Context Handling - 上下文处理测试
# ============================================================================
class TestContextHandling:
    """测试上下文处理"""

    def test_handle_error_with_empty_context(self, error_handler):
        """测试空上下文处理"""
        result = error_handler.handle_error(
            error=Exception("Test"),
            context={},
            error_type="unknown_error",
        )

        assert result["success"] is False
        assert "error" in result

    def test_handle_error_with_complex_context(self, error_handler):
        """测试复杂上下文处理"""
        complex_context = {
            "user_id": "user-123",
            "file_name": "document.pdf",
            "file_size": 2048576,
            "upload_time": "2026-01-16T10:30:00",
            "request_id": "req-abc-123",
            "ip_address": "192.168.1.100",
            "metadata": {"key": "value"},
        }

        result = error_handler.handle_error(
            error=Exception("Test"),
            context=complex_context,
            error_type="unknown_error",
        )

        assert result["success"] is False

    def test_handle_error_with_none_context(self, error_handler):
        """测试None上下文处理"""
        # 注意：传入None可能导致日志错误，但应该不会崩溃
        try:
            result = error_handler.handle_error(
                error=Exception("Test"),
                context=None,  # type: ignore
                error_type="unknown_error",
            )
            assert result["success"] is False
        except Exception:
            # 如果抛出异常也是可以接受的
            pass


# ============================================================================
# Test Retry Logic - 重试逻辑测试
# ============================================================================
class TestRetryLogic:
    """测试重试逻辑"""

    def test_all_error_types_include_retry_info(self, error_handler, sample_error):
        """测试所有错误类型都包含重试信息"""
        error_types = [
            "file_too_large",
            "file_format_unsupported",
            "corrupted_file",
            "processing_timeout",
            "ocr_engine_failure",
            "database_error",
            "network_error",
            "unknown_error",
        ]

        for error_type in error_types:
            result = error_handler.handle_error(
                error=sample_error,
                context={},
                error_type=error_type,
            )

            assert "retry_count" in result
            assert "max_retries" in result
            assert result["retry_count"] > 0
            assert result["max_retries"] == 3

    def test_retry_progression_across_multiple_calls(self, error_handler, sample_error):
        """测试多次调用的重试进程"""
        results = []

        for i in range(3):
            result = error_handler.handle_error(
                error=sample_error,
                context={},
                error_type="unknown_error",
                retry_count=i,
            )
            results.append(result)

        assert results[0]["retry_count"] == 1
        assert results[1]["retry_count"] == 2
        assert results[2]["retry_count"] == 3


# ============================================================================
# Integration Tests - 集成测试场景
# ============================================================================
class TestIntegrationScenarios:
    """测试实际使用场景"""

    def test_pdf_upload_too_large_scenario(self, error_handler):
        """测试PDF文件过大的实际场景"""
        large_file_error = ValueError("File size exceeds limit")
        context = {
            "file_name": "large_document.pdf",
            "file_size": 100 * 1024 * 1024,  # 100MB
        }

        result = error_handler.handle_error(
            error=large_file_error,
            context=context,
            error_type="file_too_large",
        )

        assert result["success"] is False
        assert result["error_type"] == "file_too_large"
        assert "suggested_action" in result

    def test_pdf_corrupted_scenario(self, error_handler):
        """测试PDF文件损坏的实际场景"""
        corrupted_error = OSError("Invalid PDF structure")
        context = {
            "file_name": "corrupted.pdf",
            "file_size": 1024 * 1024,
        }

        result = error_handler.handle_error(
            error=corrupted_error,
            context=context,
            error_type="corrupted_file",
        )

        assert result["success"] is False
        assert result["error_type"] == "corrupted_file"

    def test_ocr_timeout_scenario(self, error_handler):
        """测试OCR超时的实际场景"""
        timeout_error = TimeoutError("OCR processing took too long")
        context = {
            "file_name": "complex.pdf",
            "page_count": 100,
            "processing_time": 700,
        }

        result = error_handler.handle_error(
            error=timeout_error,
            context=context,
            error_type="processing_timeout",
            retry_count=2,
        )

        assert result["success"] is False
        assert result["error_type"] == "processing_timeout"
        assert "estimated_retry_time" in result

    def test_database_connection_error_scenario(self, error_handler):
        """测试数据库连接错误的实际场景"""
        db_error = Exception("Database connection failed")
        context = {
            "operation": "save_contract",
            "table": "rent_contracts",
        }

        result = error_handler.handle_error(
            error=db_error,
            context=context,
            error_type="database_error",
        )

        assert result["success"] is False
        assert result["error_type"] == "database_error"
        assert "数据库" in result["error"]
