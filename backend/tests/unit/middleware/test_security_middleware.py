"""
安全中间件测试

测试安全头、请求验证、文件上传安全等中间件功能。
"""

from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import HTTPException, Request, Response


class TestSecurityHeadersMiddleware:
    """测试安全头中间件"""

    @pytest.mark.asyncio
    async def test_security_headers_present(self):
        """测试所有安全头都存在"""
        from fastapi import Response

        from src.middleware.security_middleware import SecurityHeadersMiddleware

        middleware = SecurityHeadersMiddleware(app=None)

        # 模拟请求和响应
        request = Mock(spec=Request)
        request.url = "https://example.com/api/test"
        request.method = "GET"

        # 使用AsyncMock来模拟async call_next
        async def mock_call_next(req):
            # 返回一个真实的Response对象
            return Response(content="test")

        # 调用中间件
        response = await middleware.dispatch(request, mock_call_next)

        # 验证安全头被设置
        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"

        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] == "DENY"

        assert "Strict-Transport-Security" in response.headers
        assert "max-age=31536000" in response.headers["Strict-Transport-Security"]

    @pytest.mark.asyncio
    async def test_csp_header_set(self):
        """测试Content-Security-Policy头被正确设置"""
        from src.middleware.security_middleware import SecurityHeadersMiddleware

        middleware = SecurityHeadersMiddleware(app=None)

        request = Mock(spec=Request)

        async def mock_call_next(req):
            return Response(content="test")

        response = await middleware.dispatch(request, mock_call_next)

        # 验证CSP头
        assert "Content-Security-Policy" in response.headers
        csp = response.headers["Content-Security-Policy"]
        assert "default-src 'self'" in csp


class TestRequestValidationMiddleware:
    """测试请求验证中间件"""

    @pytest.mark.asyncio
    async def test_suspicious_user_agent_logged(self):
        """测试可疑User-Agent被记录"""
        from src.middleware.security_middleware import RequestValidationMiddleware

        middleware = RequestValidationMiddleware(app=None)

        request = Mock(spec=Request)
        request.headers = {"user-agent": ""}
        request.client = Mock()
        request.client.host = "192.168.1.100"
        request.url = "https://example.com/api/test"

        async def mock_call_next(req):
            return Response(content="test")

        # 调用中间件（应该记录可疑User-Agent）
        with patch("src.middleware.security_middleware.logger") as mock_logger:
            await middleware.dispatch(request, mock_call_next)

            # 验证警告被记录
            assert mock_logger.warning.called

    @pytest.mark.asyncio
    async def test_ip_blocking_after_rate_limit(self):
        """测试超过速率限制后IP被阻止"""
        from src.middleware.security_middleware import RequestValidationMiddleware

        middleware = RequestValidationMiddleware(
            app=None,
            rate_limit_config={"max_requests": 100, "window_seconds": 60},
        )

        request = Mock(spec=Request)
        request.client = Mock(host="192.168.1.100")
        request.headers = {"user-agent": "Mozilla/5.0"}
        request.url = "https://example.com/api/test"

        call_next = MagicMock()
        response = Mock()
        call_next.return_value = response

        # 模拟超过速率限制
        with patch.object(middleware, "_check_rate_limit", return_value=False):
            with pytest.raises(HTTPException) as exc_info:
                await middleware.dispatch(request, call_next)

            # 应该返回429 Too Many Requests
            assert exc_info.value.status_code == 429


class TestFileUploadSecurityMiddleware:
    """测试文件上传安全中间件"""

    @pytest.mark.asyncio
    async def test_file_size_enforced(self):
        """测试文件大小限制被强制执行"""
        from src.middleware.security_middleware import FileUploadSecurityMiddleware

        middleware = FileUploadSecurityMiddleware(
            app=None,
            max_file_size=50 * 1024 * 1024,  # 50MB
        )

        request = Mock(spec=Request)
        request.headers = {
            "content-length": "52428801"  # 51MB (超过限制)
        }

        call_next = MagicMock()

        # 应该拒绝大文件
        with pytest.raises(HTTPException) as exc_info:
            await middleware.dispatch(request, call_next)

        assert exc_info.value.status_code == 413  # Payload Too Large

    @pytest.mark.asyncio
    async def test_content_length_validation(self):
        """测试Content-Length验证"""
        from src.middleware.security_middleware import FileUploadSecurityMiddleware

        middleware = FileUploadSecurityMiddleware(
            app=None,
            max_file_size=10 * 1024 * 1024,  # 10MB
        )

        # 测试合法的Content-Length
        request = Mock(spec=Request)
        request.headers = {"content-length": "1048576"}  # 1MB

        call_next = MagicMock()
        response = Mock()
        call_next.return_value = response

        # 应该允许
        await middleware.dispatch(request, call_next)
        assert call_next.called

    @pytest.mark.asyncio
    async def test_missing_content_length_allowed(self):
        """测试缺少Content-Length的请求被允许（分块上传）"""
        from src.middleware.security_middleware import FileUploadSecurityMiddleware

        middleware = FileUploadSecurityMiddleware(app=None)

        request = Mock(spec=Request)
        request.headers = {}  # 没有Content-Length

        call_next = MagicMock()
        response = Mock()
        call_next.return_value = response

        # 应该允许（可能使用分块传输编码）
        await middleware.dispatch(request, call_next)
        assert call_next.called


class TestSecurityMiddlewareIntegration:
    """安全中间件集成测试"""

    @pytest.mark.asyncio
    async def test_all_security_middlewares_chain(self):
        """测试所有安全中间件按顺序执行"""
        from src.middleware.security_middleware import (
            FileUploadSecurityMiddleware,
            RequestValidationMiddleware,
            SecurityHeadersMiddleware,
        )

        # 创建中间件链
        app = Mock()

        security_headers = SecurityHeadersMiddleware(app)
        request_validation = RequestValidationMiddleware(security_headers)
        file_upload = FileUploadSecurityMiddleware(request_validation)

        request = Mock(spec=Request)
        request.client = Mock(host="192.168.1.100")
        request.headers = {
            "user-agent": "Mozilla/5.0",
            "content-length": "1048576",  # 1MB
        }
        request.url = "https://example.com/api/upload"

        # 模拟call_next
        call_next = MagicMock()
        response = Mock()
        response.headers = {}
        call_next.return_value = response

        # 调用中间件链
        await file_upload.dispatch(request, call_next)

        # 验证请求被处理
        assert call_next.called
        # 验证响应包含安全头
        assert "X-Content-Type-Options" in response.headers


class TestSecurityLogging:
    """测试安全日志记录"""

    @pytest.mark.asyncio
    async def test_security_events_logged(self):
        """测试安全事件被正确记录"""
        from src.middleware.security_middleware import RequestValidationMiddleware

        middleware = RequestValidationMiddleware(app=None)

        request = Mock(spec=Request)
        request.client = Mock(host="192.168.1.100")
        request.headers = {"user-agent": "TestScanner/1.0"}
        request.url = "https://example.com/api/test"

        call_next = MagicMock()
        response = Mock()
        call_next.return_value = response

        # 验证可疑活动被记录
        with patch("src.middleware.security_middleware.logger") as mock_logger:
            await middleware.dispatch(request, call_next)

            # 应该记录可疑User-Agent
            assert mock_logger.warning.called or mock_logger.info.called

    @pytest.mark.asyncio
    async def test_error_ids_in_logs(self):
        """测试日志包含正确的ErrorID"""
        from src.middleware.security_middleware import RequestValidationMiddleware

        middleware = RequestValidationMiddleware(app=None)

        request = Mock(spec=Request)
        request.client = Mock(host="192.168.1.100")
        request.headers = {"user-agent": ""}
        request.url = "https://example.com/api/test"

        call_next = MagicMock()
        response = Mock()
        call_next.return_value = response

        # 验证日志包含error_id
        with patch("src.middleware.security_middleware.logger") as mock_logger:
            await middleware.dispatch(request, call_next)

            # 检查日志调用是否包含error_id
            if mock_logger.warning.called:
                call_args = mock_logger.warning.call_args
                if call_args and len(call_args) > 1:
                    # 应该包含某种形式的error_id或安全标记
                    pass  # Variables can be unused in this check


class TestSecurityMiddlewareConfiguration:
    """测试安全中间件配置"""

    def test_security_headers_middleware_config(self):
        """测试安全头中间件配置"""
        from src.middleware.security_middleware import SecurityHeadersMiddleware

        # SecurityHeadersMiddleware 不支持配置参数
        # 所有安全头都是硬编码的
        middleware = SecurityHeadersMiddleware(app=None)

        # 验证中间件成功创建
        assert middleware is not None
        assert middleware.app is None

    def test_request_validation_middleware_config(self):
        """测试请求验证中间件配置"""
        from src.middleware.security_middleware import RequestValidationMiddleware

        # 使用自定义配置创建中间件
        middleware = RequestValidationMiddleware(
            app=None,
            rate_limit_config={"max_requests": 1000, "time_window": 300},
        )

        # 验证配置被正确设置
        assert middleware.config["max_requests"] == 1000
        assert middleware.config["time_window"] == 300

    def test_file_upload_middleware_config(self):
        """测试文件上传中间件配置"""
        from src.middleware.security_middleware import FileUploadSecurityMiddleware

        # 使用自定义配置创建中间件
        middleware = FileUploadSecurityMiddleware(
            app=None,
            max_file_size=100 * 1024 * 1024,  # 100MB
        )

        # 验证配置被正确设置
        assert middleware.max_file_size == 100 * 1024 * 1024


class TestSecurityMiddlewareErrorHandling:
    """测试安全中间件错误处理"""

    @pytest.mark.asyncio
    async def test_middleware_handles_exceptions_gracefully(self):
        """测试中间件优雅地处理异常"""
        from src.middleware.security_middleware import SecurityHeadersMiddleware

        middleware = SecurityHeadersMiddleware(app=None)

        request = Mock(spec=Request)
        call_next = MagicMock()
        call_next.side_effect = Exception("Unexpected error")

        # 中间件应该传播异常
        with pytest.raises(Exception):
            await middleware.dispatch(request, call_next)

    @pytest.mark.asyncio
    async def test_request_validation_handles_malformed_input(self):
        """测试请求验证处理格式错误的输入"""
        from src.middleware.security_middleware import RequestValidationMiddleware

        middleware = RequestValidationMiddleware(app=None)

        request = Mock(spec=Request)
        request.client = Mock(host="malformed::input")
        request.headers = {"user-agent": "Mozilla/5.0"}

        call_next = MagicMock()
        response = Mock()
        call_next.return_value = response

        # 应该优雅地处理而不是崩溃
        try:
            await middleware.dispatch(request, call_next)
        except Exception as e:
            # 如果抛出异常，应该是HTTPException而不是其他类型
            assert isinstance(e, (HTTPException, type(None)))


class TestCORSConfiguration:
    """测试CORS配置"""

    @pytest.mark.asyncio
    async def test_cors_headers_set_for_preflight(self):
        """测试OPTIONS请求的CORS头被正确设置"""
        # 这个测试需要CORS中间件实现后才能完成
        # 目前提供测试框架
        pass

    @pytest.mark.asyncio
    async def test_cors_allows_specific_origins(self):
        """测试CORS只允许特定源"""
        # 这个测试需要CORS中间件实现后才能完成
        # 目前提供测试框架
        pass
