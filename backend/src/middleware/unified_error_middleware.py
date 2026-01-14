"""
统一错误处理中间件
集成FastAPI与统一错误处理系统
"""

import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from .unified_error_handler import ErrorCode, UnifiedError, UnifiedErrorHandler


class UnifiedErrorMiddleware(BaseHTTPMiddleware):
    """统一错误处理中间件"""

    def __init__(self, app: Any, error_handler: UnifiedErrorHandler | None = None) -> None:
        super().__init__(app)
        self.error_handler = error_handler or UnifiedErrorHandler()

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # 生成请求ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # 记录请求开始时间
        start_time = time.time()

        try:
            # 执行请求
            response = await call_next(request)

            # 计算处理时间
            process_time = time.time() - start_time

            # 添加响应头
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(process_time)

            return response

        except Exception as error:
            # 处理错误
            error_response = self.error_handler.handle_error(error, request)
            error_response.headers["X-Request-ID"] = request_id

            # 计算处理时间
            process_time = time.time() - start_time
            error_response.headers["X-Process-Time"] = str(process_time)

            return error_response  # type: ignore[no-any-return]


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""

    def __init__(self, app: Any, logger: Any | None = None) -> None:
        super().__init__(app)
        self.logger = logger or self._get_default_logger()

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # 记录请求开始
        start_time = time.time()
        request_id = getattr(request.state, "request_id", "unknown")

        # 记录请求信息
        self.logger.info(
            "Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "url": str(request.url),
                "client_ip": self._get_client_ip(request),
                "user_agent": request.headers.get("user-agent"),
                "content_type": request.headers.get("content-type"),
                "content_length": request.headers.get("content-length"),
            },
        )

        try:
            # 执行请求
            response = await call_next(request)

            # 计算处理时间
            process_time = time.time() - start_time

            # 记录响应信息
            self.logger.info(
                "Request completed",
                extra={
                    "request_id": request_id,
                    "status_code": response.status_code,
                    "process_time": process_time,
                    "response_size": response.headers.get("content-length"),
                },
            )

            return response

        except Exception as error:
            # 计算处理时间
            process_time = time.time() - start_time

            # 记录错误信息
            self.logger.error(
                "Request failed",
                extra={
                    "request_id": request_id,
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                    "process_time": process_time,
                },
            )

            # 重新抛出错误，让统一错误处理器处理
            raise

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端IP"""
        # 检查代理头
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # 返回直接连接的IP
        return request.client.host if request.client else "unknown"

    def _get_default_logger(self) -> Any:
        """获取默认日志器"""
        import logging

        return logging.getLogger("request_logger")


class SecurityMiddleware(BaseHTTPMiddleware):
    """安全头中间件"""

    def __init__(self, app: Any, enabled: bool = True) -> None:
        super().__init__(app)
        self.enabled = enabled

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)

        if not self.enabled:
            return response

        # 添加安全头
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )

        # HSTS (仅在HTTPS下)
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        # Content Security Policy
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self'"
        )
        response.headers["Content-Security-Policy"] = csp

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """简单速率限制中间件"""

    def __init__(
        self, app: Any, requests_per_minute: int = 60, enabled: bool = True
    ) -> None:
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.enabled = enabled
        self.requests: dict[str, list[tuple[float, int]]] = {}

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if not self.enabled:
            return await call_next(request)

        client_ip = self._get_client_ip(request)
        current_time = time.time()

        # 清理过期记录
        self._cleanup_expired_requests(current_time)

        # 检查速率限制
        if self._is_rate_limited(client_ip, current_time):
            raise UnifiedError(
                message="请求过于频繁，请稍后再试",
                code=ErrorCode.TOO_MANY_REQUESTS,
                status_code=429,
                severity="medium",
            )

        # 记录请求
        self._record_request(client_ip, current_time)

        return await call_next(request)

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端IP"""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        return request.client.host if request.client else "unknown"

    def _cleanup_expired_requests(self, current_time: float) -> None:
        """清理过期请求记录"""
        cutoff_time = current_time - 60  # 1分钟前

        for ip in list(self.requests.keys()):
            self.requests[ip] = [
                (timestamp, count)
                for timestamp, count in self.requests[ip]
                if timestamp > cutoff_time
            ]

            if not self.requests[ip]:
                del self.requests[ip]

    def _is_rate_limited(self, client_ip: str, current_time: float) -> bool:
        """检查是否超过速率限制"""
        if client_ip not in self.requests:
            return False

        # 计算最近1分钟的请求数
        cutoff_time = current_time - 60
        recent_requests = sum(
            count
            for timestamp, count in self.requests[client_ip]
            if timestamp > cutoff_time
        )

        return recent_requests >= self.requests_per_minute

    def _record_request(self, client_ip: str, current_time: float) -> None:
        """记录请求"""
        if client_ip not in self.requests:
            self.requests[client_ip] = []

        # 查找同一时间戳的记录
        for i, (timestamp, count) in enumerate(self.requests[client_ip]):
            if abs(timestamp - current_time) < 1:  # 1秒内视为同一时间
                self.requests[client_ip][i] = (timestamp, count + 1)
                break
        else:
            self.requests[client_ip].append((current_time, 1))


class MetricsMiddleware(BaseHTTPMiddleware):
    """指标收集中间件"""

    def __init__(self, app: Any, enabled: bool = True) -> None:
        super().__init__(app)
        self.enabled = enabled
        self.metrics: dict[str, Any] = {
            "total_requests": 0,
            "total_errors": 0,
            "request_duration": [],
            "status_codes": {},
        }

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if not self.enabled:
            return await call_next(request)

        start_time = time.time()

        try:
            response = await call_next(request)

            # 记录指标
            self._record_metrics(request, response, start_time, False)

            return response

        except Exception:
            # 记录错误指标
            self._record_metrics(request, None, start_time, True)

            # 重新抛出错误
            raise

    def _record_metrics(
        self,
        request: Request,
        response: Response | None,
        start_time: float,
        is_error: bool,
    ) -> None:
        """记录指标"""
        process_time = time.time() - start_time

        # 总请求数
        total_requests = self.metrics["total_requests"]
        assert isinstance(total_requests, int)
        self.metrics["total_requests"] = total_requests + 1

        # 错误数
        if is_error:
            total_errors = self.metrics["total_errors"]
            assert isinstance(total_errors, int)
            self.metrics["total_errors"] = total_errors + 1

        # 请求持续时间
        request_duration = self.metrics["request_duration"]
        assert isinstance(request_duration, list)
        request_duration.append(process_time)

        # 状态码统计
        if response:
            status_code = response.status_code
            status_codes = self.metrics["status_codes"]
            assert isinstance(status_codes, dict)
            status_codes[status_code] = status_codes.get(status_code, 0) + 1

        # 保持最近1000个请求的持续时间
        if len(request_duration) > 1000:
            self.metrics["request_duration"] = request_duration[-1000:]

    def get_metrics(self) -> dict[str, Any]:
        """获取指标"""
        durations = self.metrics["request_duration"]
        assert isinstance(durations, list)

        total_requests = self.metrics["total_requests"]
        assert isinstance(total_requests, int)
        total_errors = self.metrics["total_errors"]
        assert isinstance(total_errors, int)
        status_codes = self.metrics["status_codes"]
        assert isinstance(status_codes, dict)

        return {
            "total_requests": total_requests,
            "total_errors": total_errors,
            "error_rate": total_errors / max(total_requests, 1),
            "avg_request_duration": sum(durations) / len(durations) if durations else 0,
            "max_request_duration": max(durations) if durations else 0,
            "min_request_duration": min(durations) if durations else 0,
            "status_codes": status_codes.copy(),
        }

    def reset_metrics(self) -> None:
        """重置指标"""
        self.metrics = {
            "total_requests": 0,
            "total_errors": 0,
            "request_duration": [],
            "status_codes": {},
        }
