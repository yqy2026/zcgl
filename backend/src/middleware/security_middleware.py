from collections.abc import Callable
from typing import Any

"""
FastAPI安全中间件
提供请求验证、文件上传安全和速率限制功能
"""

import logging
import time
from collections import defaultdict

from fastapi import HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ..constants.errors.messages import ErrorMessages
from ..constants.http.methods import HTTPMethods
from ..core.exception_handler import BusinessValidationError
from ..core.logging_security import security_auditor
from ..core.security import RateLimiter

try:
    from ..core.security.ratelimit import AdaptiveRateLimiter, adaptive_limiter

    ADAPTIVE_LIMITER_AVAILABLE = True
except ImportError:
    # Use string annotation to avoid NameError when AdaptiveRateLimiter is not defined
    adaptive_limiter_var: "AdaptiveRateLimiter | None" = None
    ADAPTIVE_LIMITER_AVAILABLE = False
    # Create a compatible wrapper for type checking
    adaptive_limiter = adaptive_limiter_var  # type: ignore[assignment]

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """安全头部中间件"""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Any]
    ) -> Response:
        """添加安全头部"""
        response: Response = await call_next(request)

        # 安全头部
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'"

        return response


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """请求验证中间件"""

    def __init__(
        self, app: ASGIApp, rate_limit_config: dict[str, Any] | None = None
    ) -> None:
        super().__init__(app)
        self.rate_limiter = RateLimiter()
        self.config = rate_limit_config or {}
        self.request_count: dict[str, int] = defaultdict(int)
        self.blocked_ips: dict[str, float] = {}
        self.suspicious_patterns = [
            r"<script",
            r"javascript:",
            r"vbscript:",
            r"onload=",
            r"onerror=",
            r"document\.cookie",
            r"eval\(",
            r"alert\(",
            r"window\.",
        ]

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Any]
    ) -> Response:
        """执行请求验证"""
        start_time = time.time()
        client_ip = self._get_client_ip(request)

        try:
            # 检查IP是否被封禁
            if self._is_ip_blocked(client_ip):
                await self._log_blocked_request(request, client_ip, "IP_BLOCKED")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=ErrorMessages.IP_BLOCKED,
                )

            # 请求频率限制
            if not self._check_rate_limit(client_ip, request):
                await self._log_blocked_request(
                    request, client_ip, "RATE_LIMIT_EXCEEDED"
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=ErrorMessages.RATE_LIMIT_EXCEEDED,
                )

            # 请求内容验证
            await self._validate_request_content(request)

            # 处理请求
            response: Response = await call_next(request)

            # 记录请求统计
            await self._log_request_stats(request, response, start_time, client_ip)

            return response

        except HTTPException:
            # HTTPException 应该正常传播，不应该被重新抛出为 500
            raise
        except Exception as e:
            # 对于非 HTTPException 的异常，记录详细日志后重新抛出
            # 不要掩盖原始错误信息
            logger.exception(
                f"Security middleware caught unexpected exception: {type(e).__name__}: {str(e)}"
            )
            # 重新抛出原始异常，让上层处理器处理
            raise

    def _sanitize_exception_message(self, message: str) -> str:
        """清理异常消息中的不可序列化内容"""
        if not isinstance(message, str):
            try:
                message = str(message)
            except Exception:
                message = "<无法序列化的异常信息>"

        # 限制消息长度
        if len(message) > 500:
            message = message[:500] + "...(截断)"

        # 移除可能包含对象引用的模式
        import re

        # 移除类似 "<class 'src.models.rent_contract.RentLedger'>" 的内容
        message = re.sub(r"<class '[^']*'>", "<模型对象>", message)
        # 移除可能的对象ID引用
        message = re.sub(r"object at 0x[0-9a-fA-F]+>", "<对象实例>", message)
        # 移除更多的对象引用模式
        message = re.sub(r"<[^>]*object[^>]*>", "<对象实例>", message)
        # 移除可能的内存地址引用
        message = re.sub(r"0x[0-9a-fA-F]{8,}", "<内存地址>", message)
        # 移除可能的模块路径引用
        message = re.sub(
            r"[a-zA-Z_][a-zA-Z0-9_.]*\.[a-zA-Z_][a-zA-Z0-9_.]*", "<模块引用>", message
        )
        # 移除可能的尖括号包围的内容（除了我们替换的占位符）
        message = re.sub(
            r"<(?!模型对象|对象实例|内存地址|模块引用|无法序列化的异常信息)[^>]*>",
            "<未知对象>",
            message,
        )

        return message

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端真实IP"""
        # 检查代理头部
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        # 确保返回默认IP而不是None
        if request.client:
            return request.client.host
        return "unknown"

    def _is_ip_blocked(self, ip: str) -> bool:
        """检查IP是否被封禁"""
        # 本地开发环境IP白名单
        local_whitelist = [
            "127.0.0.1",
            "localhost",
            "::1",
            "0.0.0.0",  # nosec - B104: Docker/容器环境, not binding
            "192.168.1.90",  # 当前本地网络IP
        ]

        # 如果是本地IP，直接允许
        if (
            ip in local_whitelist
            or ip.startswith("192.168.")
            or ip.startswith("10.")
            or ip.startswith("172.")
        ):
            # 如果本地IP被封禁，清除封禁记录
            if ip in self.blocked_ips:
                del self.blocked_ips[ip]
                logger.info(f" cleared block for local IP: {ip}")
            return False

        # 临时封禁（1小时）
        if ip in self.blocked_ips:
            block_time = self.blocked_ips[ip]
            if time.time() - block_time < 3600:  # 1小时
                return True
            else:
                del self.blocked_ips[ip]

        return False

    def _check_rate_limit(self, ip: str, request: Request) -> bool:
        """检查请求频率限制"""
        # 本地开发环境更宽松的限制
        (
            ip in ["127.0.0.1", "localhost", "::1", "0.0.0.0"]  # nosec - B104: Local IP check, not binding
            or ip.startswith("192.168.")
            or ip.startswith("10.")
            or ip.startswith("172.")
        )

        # 检查是否为可疑请求
        is_suspicious = self._is_suspicious_request(request)

        # 使用自适应速率限制器
        rate_limit_key = ip
        path = request.url.path or ""

        if path.startswith("/api/v1/pdf_import"):
            # PDF导入限制
            rate_limit_key = f"{ip}:pdf_import"
        elif path.startswith("/api/v1/excel"):
            # Excel操作限制
            rate_limit_key = f"{ip}:excel"
        elif request.method == HTTPMethods.POST:
            # POST请求限制
            rate_limit_key = f"{ip}:post"

        # 检查速率限制
        if adaptive_limiter is not None and ADAPTIVE_LIMITER_AVAILABLE:
            return adaptive_limiter.check_rate_limit(rate_limit_key, is_suspicious)
        else:
            # 如果自适应限流器不可用，使用简单的默认限流器
            logger.warning(
                "Adaptive rate limiter not available, using default rate limiting"
            )
            return True  # 默认允许通过，在生产环境中应该实现更严格的限流

    def _is_suspicious_request(self, request: Request) -> bool:
        """检查是否为可疑请求"""
        # 检查User-Agent
        user_agent = request.headers.get("User-Agent", "")
        if not user_agent or len(user_agent) < 10:
            return True

        # 检查路径中的可疑模式
        path = request.url.path or ""
        for pattern in self.suspicious_patterns:
            if pattern in path.lower():
                return True

        # 检查查询参数中的可疑模式
        query_params = dict(request.query_params)
        for _key, value in query_params.items():
            if (
                value is not None
                and isinstance(value, str)
                and any(
                    pattern in value.lower() for pattern in self.suspicious_patterns
                )
            ):
                return True

        return False

    async def _validate_request_content(self, request: Request) -> None:
        """验证请求内容"""
        # 检查可疑的User-Agent
        user_agent = request.headers.get("User-Agent", "")
        if not user_agent or len(user_agent) < 10:
            await self._log_suspicious_request(request, "INVALID_USER_AGENT")

        # 检查请求路径中的可疑模式
        path = request.url.path
        path = "" if path is None else path.lower()
        for pattern in self.suspicious_patterns:
            if pattern in path:
                await self._log_suspicious_request(request, "SUSPICIOUS_PATH")
                break

        # 检查查询参数
        query_params = dict(request.query_params)
        for _key, value in query_params.items():
            if (
                value is not None
                and isinstance(value, str)
                and any(
                    pattern in value.lower() for pattern in self.suspicious_patterns
                )
            ):
                await self._log_suspicious_request(request, "SUSPICIOUS_QUERY_PARAM")
                break

    async def _log_blocked_request(
        self, request: Request, ip: str, reason: str
    ) -> None:
        """记录被封禁的请求"""
        security_auditor.log_security_event(
            event_type="REQUEST_BLOCKED",
            message=f"Request blocked from {ip}: {reason}",
            user_id=None,
            ip_address=ip,
            user_agent=request.headers.get("User-Agent", ""),
            details={
                "reason": reason,
                "path": request.url.path,
                "method": request.method,
                "timestamp": time.time(),
            },
        )

        # 临时封禁IP
        if reason in ["RATE_LIMIT_EXCEEDED", "SUSPICIOUS_REQUEST"]:
            self.blocked_ips[ip] = time.time()

    async def _log_suspicious_request(self, request: Request, reason: str) -> None:
        """记录可疑请求"""
        client_ip = self._get_client_ip(request)

        security_auditor.log_security_event(
            event_type="SUSPICIOUS_REQUEST",
            message=f"Suspicious request from {client_ip}: {reason}",
            user_id=None,
            ip_address=client_ip,
            user_agent=request.headers.get("User-Agent", ""),
            details={
                "reason": reason,
                "path": request.url.path,
                "method": request.method,
                "query_params": dict(request.query_params),
                "timestamp": time.time(),
            },
        )

    async def _log_request_stats(
        self, request: Request, response: Response, start_time: float, ip: str
    ) -> None:
        """记录请求统计信息"""
        try:
            processing_time = time.time() - start_time

            # 记录慢请求
            if processing_time > 5.0:  # 5秒以上为慢请求
                security_auditor.log_security_event(
                    event_type="SLOW_REQUEST",
                    message=f"Slow request from {ip}: {processing_time:.2f}s",
                    user_id=None,
                    ip_address=ip,
                    details={
                        "path": request.url.path,
                        "method": request.method,
                        "processing_time": processing_time,
                        "status_code": response.status_code,
                    },
                )

            # 更新请求计数
            self.request_count[ip] += 1
        except Exception as e:
            # Don't re-raise, just log the error
            logger.error(f"Error logging request stats: {e}")


class FileUploadSecurityMiddleware(BaseHTTPMiddleware):
    """文件上传安全中间件"""

    def __init__(
        self, app: ASGIApp, max_file_size: int = 50 * 1024 * 1024
    ) -> None:  # 50MB
        super().__init__(app)
        self.max_file_size = max_file_size

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Any]
    ) -> Response:
        """处理文件上传安全检查"""

        # 检查是否为文件上传请求
        if request.headers.get("content-type", "").startswith("multipart/form-data"):
            try:
                await self._validate_file_upload(request)
            except BusinessValidationError as e:
                logger.error(f"File upload validation failed: {str(e)}")
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "success": False,
                        "message": str(e),
                        "error_type": "validation_error",
                    },
                )
            except Exception as e:
                logger.error(f"File upload security check failed: {str(e)}")
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={
                        "success": False,
                        "message": ErrorMessages.FILE_UPLOAD_VALIDATION_FAILED,
                        "error_type": "security_error",
                    },
                )

        result: Response = await call_next(request)
        return result

    async def _validate_file_upload(self, request: Request) -> None:
        """验证文件上传"""
        content_length = int(request.headers.get("content-length", 0))

        # 检查请求大小
        if content_length > self.max_file_size:
            raise BusinessValidationError(
                f"请求过大: {content_length / (1024 * 1024):.2f}MB",
                details={"max_size": self.max_file_size / (1024 * 1024)},
            )

        # 检查文件数量限制
        path = request.url.path
        if path and path.startswith("/api/v1/excel"):
            # Excel导入限制：单次最多上传10个文件
            pass
        elif path and path.startswith("/api/v1/pdf_import"):
            # PDF导入限制：单次最多上传5个文件
            pass
            # 注意：这里不能直接读取request.body，因为流已经被消耗
            # 实际的文件验证需要在具体的API端点中进行


class CORSExtendedMiddleware(BaseHTTPMiddleware):
    """扩展的CORS中间件"""

    def __init__(
        self,
        app: ASGIApp,
        allowed_origins: list[str] | None = None,
        allowed_methods: list[str] | None = None,
    ) -> None:
        super().__init__(app)
        self.allowed_origins = allowed_origins or [
            "http://localhost:5173",
            "http://localhost:3000",
        ]
        self.allowed_methods = allowed_methods or HTTPMethods.get_common_methods() + [HTTPMethods.OPTIONS]

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Any]
    ) -> Response:
        """处理CORS和安全头部"""

        # 预检请求处理
        if request.method == HTTPMethods.OPTIONS:
            return Response()

        response: Response = await call_next(request)

        # 设置CORS头部
        origin = request.headers.get("origin")
        if origin and (origin in self.allowed_origins or "localhost" in origin):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = ", ".join(
                self.allowed_methods
            )
            response.headers["Access-Control-Allow-Headers"] = (
                "Authorization, Content-Type, X-Requested-With, Accept, Origin"
            )
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Max-Age"] = "86400"

        # 安全头部
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"

        return response


def create_security_middleware(app: Any, config: dict[str, Any] | None = None) -> None:
    """
    创建安全中间件链

    Args:
        app: FastAPI应用
        config: 安全配置
    """
    config = config or {}

    # 按顺序添加中间件
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        FileUploadSecurityMiddleware,
        max_file_size=config.get("max_file_size", 50 * 1024 * 1024),
    )
    app.add_middleware(
        RequestValidationMiddleware, rate_limit_config=config.get("rate_limit", {})
    )


# 创建中间件工厂函数
def setup_security_middleware(app: Any) -> None:
    """设置安全中间件"""
    config = {
        "allowed_origins": ["http://localhost:5173", "http://localhost:3000"],
        "allowed_methods": HTTPMethods.get_common_methods() + [HTTPMethods.OPTIONS, HTTPMethods.PATCH],
        "max_file_size": 100 * 1024 * 1024,  # 100MB
        "rate_limit": {
            "pdf_import": {"max_requests": 5, "time_window": 60},
            "excel": {"max_requests": 10, "time_window": 60},
            "post": {"max_requests": 30, "time_window": 60},
            "default": {"max_requests": 100, "time_window": 60},
        },
    }

    create_security_middleware(app, config)
    logger.info("Security middleware configured")
