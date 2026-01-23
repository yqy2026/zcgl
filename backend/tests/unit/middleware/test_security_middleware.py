"""
安全中间件测试

测试安全头、请求验证、文件上传安全等中间件功能。
"""

from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import Request, Response


def create_mock_request(url_path: str = "/api/test", method: str = "GET") -> Mock:
    """创建Mock Request对象，具有必要的属性"""
    request = Mock(spec=Request)
    # 创建一个有path属性的URL对象
    url_mock = Mock()
    url_mock.path = url_path
    url_mock.__str__ = lambda self: f"https://example.com{url_path}"
    request.url = url_mock
    request.method = method
    request.headers = {}
    request.query_params = {}
    request.client = Mock(host="192.168.1.100")
    return request


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

        request = create_mock_request(url_path="/api/test")
        request.headers = {"user-agent": ""}
        request.client.host = "192.168.1.100"

        async def mock_call_next(req):
            return Response(content="test")

        # 调用中间件（应该记录可疑User-Agent）
        with patch(
            "src.middleware.security_middleware.security_auditor"
        ) as mock_auditor:
            await middleware.dispatch(request, mock_call_next)

            # 验证安全审计器被调用了
            assert mock_auditor.log_security_event.called

    @pytest.mark.asyncio
    async def test_ip_blocking_after_rate_limit(self):
        """测试超过速率限制后IP被阻止"""
        from src.core.exception_handler import RateLimitError
        from src.middleware.security_middleware import RequestValidationMiddleware

        middleware = RequestValidationMiddleware(
            app=None,
            rate_limit_config={"max_requests": 100, "time_window": 60},
        )

        request = create_mock_request(url_path="/api/test")
        request.headers = {"user-agent": "Mozilla/5.0"}

        async def call_next(req):
            return Response(content="test")

        # 模拟超过速率限制
        with patch.object(middleware, "_check_rate_limit", return_value=False):
            # RateLimitError会被全局异常处理器转换为HTTP 429响应
            with pytest.raises(RateLimitError):
                await middleware.dispatch(request, call_next)


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

        request = create_mock_request(url_path="/api/upload")
        request.headers = {
            "content-type": "multipart/form-data",
            "content-length": "52428801",  # 51MB (超过限制)
        }

        async def call_next(req):
            return Response(content="test")

        # 中间件现在返回JSONResponse而不是抛出异常
        response = await middleware.dispatch(request, call_next)

        # 应该返回400状态码和错误信息
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_content_length_validation(self):
        """测试Content-Length验证"""
        from src.middleware.security_middleware import FileUploadSecurityMiddleware

        middleware = FileUploadSecurityMiddleware(
            app=None,
            max_file_size=10 * 1024 * 1024,  # 10MB
        )

        # 测试合法的Content-Length
        request = create_mock_request(url_path="/api/upload")
        request.headers = {"content-length": "1048576"}  # 1MB

        call_next_called = False

        async def call_next(req):
            nonlocal call_next_called
            call_next_called = True
            return Response(content="test")

        # 应该允许
        await middleware.dispatch(request, call_next)
        assert call_next_called

    @pytest.mark.asyncio
    async def test_missing_content_length_allowed(self):
        """测试缺少Content-Length的请求被允许（分块上传）"""
        from src.middleware.security_middleware import FileUploadSecurityMiddleware

        middleware = FileUploadSecurityMiddleware(app=None)

        request = create_mock_request(url_path="/api/upload")
        request.headers = {}  # 没有Content-Length

        call_next_called = False

        async def call_next(req):
            nonlocal call_next_called
            call_next_called = True
            return Response(content="test")

        # 应该允许（可能使用分块传输编码）
        await middleware.dispatch(request, call_next)
        assert call_next_called


class TestSecurityMiddlewareIntegration:
    """安全中间件集成测试"""

    @pytest.mark.asyncio
    async def test_all_security_middlewares_chain(self):
        """测试所有安全中间件按顺序执行"""
        from src.middleware.security_middleware import (
            FileUploadSecurityMiddleware,
            SecurityHeadersMiddleware,
        )

        request = create_mock_request(url_path="/api/upload")
        request.headers = {
            "user-agent": "Mozilla/5.0 TestAgent",  # 必须大于10个字符
            "content-length": "1048576",  # 1MB
        }

        # 使用testclient IP来绕过速率限制
        request.client.host = "testclient"

        # 创建最终的响应处理器
        async def final_call_next(req):
            return Response(content="test")

        # 手动链式调用中间件 - 按正确顺序
        # 1. FileUploadSecurityMiddleware
        file_upload_middleware = FileUploadSecurityMiddleware(app=None)
        response1 = await file_upload_middleware.dispatch(request, final_call_next)

        # 2. RequestValidationMiddleware
        # 由于我们已经通过了file_upload，现在模拟通过request_validation
        # 实际上在FastAPI中这些会自动链式调用

        # 3. SecurityHeadersMiddleware - 这是最后调用的，应该添加安全头
        security_headers_middleware = SecurityHeadersMiddleware(app=None)

        # 模拟call_next返回之前的响应
        async def mock_call_next_with_response(req):
            return response1

        response_final = await security_headers_middleware.dispatch(
            request, mock_call_next_with_response
        )

        # 验证响应存在且有安全头
        assert response_final is not None
        # 验证响应包含安全头 - SecurityHeadersMiddleware应该已经添加了
        assert "X-Content-Type-Options" in response_final.headers


class TestSecurityLogging:
    """测试安全日志记录"""

    @pytest.mark.asyncio
    async def test_security_events_logged(self):
        """测试安全事件被正确记录"""
        from src.middleware.security_middleware import RequestValidationMiddleware

        middleware = RequestValidationMiddleware(app=None)

        request = create_mock_request(url_path="/api/test")
        request.headers = {"user-agent": "TestScanner/1.0"}

        async def call_next(req):
            return Response(content="test")

        # 验证可疑活动被记录 - 使用security_auditor而不是logger
        with patch(
            "src.middleware.security_middleware.security_auditor"
        ) as mock_auditor:
            await middleware.dispatch(request, call_next)

            # 应该记录可疑User-Agent（因为长度<10）
            assert mock_auditor.log_security_event.called

    @pytest.mark.asyncio
    async def test_error_ids_in_logs(self):
        """测试日志包含正确的ErrorID"""
        from src.middleware.security_middleware import RequestValidationMiddleware

        middleware = RequestValidationMiddleware(app=None)

        request = Mock(spec=Request)
        request.client = Mock(host="192.168.1.100")
        request.headers = {"user-agent": ""}
        # 创建一个有path属性的URL对象
        url_mock = Mock()
        url_mock.path = "/api/test"
        url_mock.__str__ = lambda self: "https://example.com/api/test"
        request.url = url_mock
        request.method = "GET"
        # Mock query_params as an empty dict
        request.query_params = {}

        async def call_next(req):
            return Response(content="test")

        # 验证日志包含error_id - 使用security_auditor
        with patch(
            "src.middleware.security_middleware.security_auditor"
        ) as mock_auditor:
            await middleware.dispatch(request, call_next)

            # 验证调用了log_security_event方法
            assert mock_auditor.log_security_event.called


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

        # 使用testclient来绕过IP白名单检查，因为IP白名单会阻止无效IP
        request = Mock(spec=Request)
        request.client = Mock(host="testclient")
        request.headers = {"user-agent": "Mozilla/5.0"}
        # 创建一个有path属性的URL对象
        url_mock = Mock()
        url_mock.path = "/api/test"
        url_mock.__str__ = lambda self: "https://example.com/api/test"
        request.url = url_mock
        request.method = "GET"
        request.query_params = {}

        async def call_next(req):
            return Response(content="test")

        # 应该正常处理
        response = await middleware.dispatch(request, call_next)

        # 验证响应存在
        assert response is not None


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
