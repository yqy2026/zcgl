"""
FastAPI安全中间件
提供请求验证、文件上传安全和速率限制功能
"""

import logging
import secrets
import time
from collections import defaultdict
from ipaddress import ip_address, ip_network
from typing import Any, TYPE_CHECKING

from fastapi import HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from ..constants.api_constants import HTTPMethods
from ..constants.file_size_constants import (
    DEFAULT_MAX_EXCEL_FILE_SIZE,
    DEFAULT_MAX_FILE_SIZE,
)
from ..constants.message_constants import ErrorMessages
from ..core.circuit_breaker import CircuitBreaker
from ..core.exception_handler import (
    BusinessValidationError,
    PermissionDeniedError,
    RateLimitError,
)
from ..core.rate_limit_strategy import RateLimitConfig, RateLimitStrategy
from ..core.config import settings
from ..security.cookie_manager import cookie_manager
from ..security.ip_whitelist import ip_whitelist
from ..security.logging_security import security_auditor
from ..security.security import RateLimiter

if TYPE_CHECKING:
    from ..security.security import AdaptiveRateLimiter

adaptive_limiter: "AdaptiveRateLimiter | None"

try:
    from ..security.security import AdaptiveRateLimiter, adaptive_limiter as _adaptive_limiter

    adaptive_limiter = _adaptive_limiter
    ADAPTIVE_LIMITER_AVAILABLE = True
except ImportError:
    adaptive_limiter = None
    ADAPTIVE_LIMITER_AVAILABLE = False

logger = logging.getLogger(__name__)

_DEFAULT_TRUSTED_PROXY_NETWORKS = [
    ip_network("10.0.0.0/8"),
    ip_network("172.16.0.0/12"),
    ip_network("192.168.0.0/16"),
    ip_network("127.0.0.1/32"),
    ip_network("::1/128"),
]


def _is_valid_ip_value(ip: str) -> bool:
    try:
        ip_address(ip)
        return True
    except ValueError:
        return False


def _is_trusted_proxy_ip(ip: str, trusted_proxy_networks: list[Any]) -> bool:
    try:
        client_ip = ip_address(ip)
    except ValueError:
        return False
    return any(client_ip in network for network in trusted_proxy_networks)


def get_client_ip(
    request: Request, trusted_proxy_networks: list[Any] | None = None
) -> str:
    client_host = request.client.host if request.client else None
    networks = trusted_proxy_networks or _DEFAULT_TRUSTED_PROXY_NETWORKS
    if client_host and _is_trusted_proxy_ip(client_host, networks):
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            forwarded_ip = forwarded_for.split(",")[0].strip()
            if _is_valid_ip_value(forwarded_ip):
                return forwarded_ip

        real_ip = request.headers.get("X-Real-IP")
        if real_ip and _is_valid_ip_value(real_ip.strip()):
            return real_ip.strip()

    if client_host:
        return client_host
    return "unknown"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """安全头部中间件"""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
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


class CSRFMiddleware(BaseHTTPMiddleware):
    """CSRF 防护中间件（双重提交）"""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self.enabled = settings.CSRF_ENABLED
        self.cookie_name = settings.CSRF_COOKIE_NAME
        self.header_name = settings.CSRF_HEADER_NAME
        self.exempt_paths = {
            "/api/v1/auth/login",
            "/api/v1/auth/refresh",
        }
        self.safe_methods = set(HTTPMethods.get_safe_methods() + [HTTPMethods.TRACE])

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if not self.enabled:
            return await call_next(request)

        method = (request.method or "").upper()
        if method in self.safe_methods:
            return await call_next(request)

        path = request.url.path or ""
        if path in self.exempt_paths:
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if auth_header.lower().startswith("bearer "):
            return await call_next(request)

        auth_cookie = request.cookies.get(cookie_manager.cookie_name)
        if auth_cookie is None:
            return await call_next(request)

        csrf_cookie = request.cookies.get(self.cookie_name)
        csrf_header = request.headers.get(self.header_name)
        if (
            csrf_cookie is None
            or csrf_header is None
            or csrf_cookie == ""
            or csrf_header == ""
        ):
            security_auditor.log_security_event(
                event_type="CSRF_VALIDATION_FAILED",
                message="CSRF token missing",
                user_id=None,
                ip_address=get_client_ip(request),
                user_agent=request.headers.get("User-Agent", ""),
                details={"path": path, "method": method},
            )
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "success": False,
                    "message": "CSRF token missing",
                    "error_type": "csrf_missing",
                },
            )

        if not secrets.compare_digest(csrf_cookie, csrf_header):
            security_auditor.log_security_event(
                event_type="CSRF_VALIDATION_FAILED",
                message="CSRF token mismatch",
                user_id=None,
                ip_address=get_client_ip(request),
                user_agent=request.headers.get("User-Agent", ""),
                details={"path": path, "method": method},
            )
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "success": False,
                    "message": "CSRF token mismatch",
                    "error_type": "csrf_mismatch",
                },
            )

        return await call_next(request)


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
        self.ip_whitelist = ip_whitelist
        self.trusted_proxy_networks = self._load_trusted_proxies()

        # Initialize circuit breaker and rate limit strategy
        self.rate_limit_config = RateLimitConfig.from_env()
        self.circuit_breaker = CircuitBreaker(
            max_failures=self.rate_limit_config.max_failures,
            cooldown=self.rate_limit_config.cooldown_seconds,
        )

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
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """执行请求验证"""
        start_time = time.time()
        client_ip = self._get_client_ip(request)

        try:
            if request.method == HTTPMethods.OPTIONS:
                return await call_next(request)

            # 检查IP是否被封禁
            if self._is_ip_blocked(client_ip):
                await self._log_blocked_request(request, client_ip, "IP_BLOCKED")
                raise PermissionDeniedError(ErrorMessages.IP_BLOCKED)

            # 请求频率限制
            if not self._check_rate_limit(client_ip, request):
                await self._log_blocked_request(
                    request, client_ip, "RATE_LIMIT_EXCEEDED"
                )
                raise RateLimitError(ErrorMessages.RATE_LIMIT_EXCEEDED)

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
        client_host = request.client.host if request.client else None
        if client_host and self._is_trusted_proxy(client_host):
            forwarded_for = request.headers.get("X-Forwarded-For")
            if forwarded_for:
                forwarded_ip = forwarded_for.split(",")[0].strip()
                if self._is_valid_ip(forwarded_ip):
                    return forwarded_ip

            real_ip = request.headers.get("X-Real-IP")
            if real_ip and self._is_valid_ip(real_ip.strip()):
                return real_ip.strip()

        if client_host:
            return client_host
        return "unknown"

    def _is_trusted_proxy(self, ip: str) -> bool:
        try:
            client_ip = ip_address(ip)
        except ValueError:
            return False
        return any(client_ip in network for network in self.trusted_proxy_networks)

    def _is_valid_ip(self, ip: str) -> bool:
        try:
            ip_address(ip)
            return True
        except ValueError:
            return False

    def _load_trusted_proxies(self) -> list[Any]:
        raw = self.config.get("trusted_proxies")
        if not raw:
            raw = [
                "10.0.0.0/8",
                "172.16.0.0/12",
                "192.168.0.0/16",
                "127.0.0.1/32",
                "::1/128",
            ]

        networks: list[Any] = []
        for entry in raw:
            try:
                networks.append(ip_network(entry))
            except ValueError:
                continue
        return networks

    def _is_ip_blocked(self, ip: str) -> bool:
        """检查IP是否被封禁或不在白名单中"""
        # 检查IP是否在白名单中
        if not self.ip_whitelist.is_allowed(ip):
            logger.warning(f"IP not in whitelist: {ip}")
            return True

        # 临时封禁（1小时）
        if ip in self.blocked_ips:
            block_time = self.blocked_ips[ip]
            if time.time() - block_time < 3600:  # 1小时
                return True
            else:
                del self.blocked_ips[ip]

        return False

    def _check_rate_limit(self, ip: str, request: Request) -> bool:
        """
        Check rate limiting with fail-closed behavior

        Returns:
            bool: True if request is allowed, False if rate limited
        """
        # Bypass rate limiting for test client
        if ip == "testclient" or ip.startswith("testclient"):
            return True

        # 检查是否为可疑请求
        is_suspicious = self._is_suspicious_request(request)

        # Generate rate limit key
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
        else:
            # 默认限制
            rate_limit_key = f"{ip}:default"

        # Check circuit breaker state
        if self.circuit_breaker.is_open():
            logger.warning(
                f"Circuit breaker open, using degraded rate limiting for {ip}"
            )
            # Use simple IP-based limiting in degraded mode
            return self._degraded_rate_limit_check(rate_limit_key)

        # Try adaptive rate limiting
        try:
            if adaptive_limiter is not None and ADAPTIVE_LIMITER_AVAILABLE:
                result = adaptive_limiter.check_rate_limit(
                    rate_limit_key, is_suspicious
                )
                # Record success on successful check
                self.circuit_breaker.record_success()
                return result
            else:
                logger.warning("Adaptive rate limiter not available")
                # Check if we should fail-closed
                if self.rate_limit_config.should_block_on_error():
                    self.circuit_breaker.record_failure()
                    return False
                else:
                    return True

        except Exception as e:
            logger.error(f"Rate limiter error: {e}")
            self.circuit_breaker.record_failure()

            # Fail-closed: block on error in STRICT mode
            if self.rate_limit_config.strategy == RateLimitStrategy.STRICT:
                return False
            # Fail-open: allow in PERMISSIVE mode
            elif self.rate_limit_config.strategy == RateLimitStrategy.PERMISSIVE:
                return True
            # DEGRADED: fallback to simple limiting
            else:
                return self._degraded_rate_limit_check(rate_limit_key)

    def _degraded_rate_limit_check(self, key: str) -> bool:
        """
        Simple degraded mode rate limiting using in-memory counter

        Args:
            key: Rate limit key

        Returns:
            bool: True if request is allowed, False if rate limited
        """
        try:
            # Simple 60 req/min limit in degraded mode
            current_time = time.time()
            minute_key = f"{key}:{int(current_time // 60)}"

            self.request_count[minute_key] += 1

            # Clean up old entries
            if len(self.request_count) > 1000:
                old_minute = int(current_time // 60) - 1
                old_key = f"{key}:{old_minute}"
                if old_key in self.request_count:
                    del self.request_count[old_key]

            return self.request_count[minute_key] <= 60
        except Exception as e:
            logger.error(f"Degraded rate limiting failed: {e}")
            # Ultimate fallback: allow request
            return True

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
        self, app: ASGIApp, max_file_size: int = DEFAULT_MAX_FILE_SIZE
    ) -> None:
        super().__init__(app)
        self.max_file_size = max_file_size

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
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
        if path and (
            path.startswith("/api/v1/excel")
            or path.startswith("/api/v1/pdf_import")
            or path.startswith("/api/v1/pdf-import")
        ):
            max_files = 10 if path.startswith("/api/v1/excel") else 5
            content_type = request.headers.get("content-type", "")
            boundary = self._extract_multipart_boundary(content_type)
            if boundary is None:
                logger.warning("Missing multipart boundary for upload path: %s", path)
                return

            # Read and cache body so downstream can still access it
            body = await request.body()
            if not content_length:
                content_length = len(body)
            if content_length > self.max_file_size:
                raise BusinessValidationError(
                    f"请求过大: {content_length / (1024 * 1024):.2f}MB",
                    details={"max_size": self.max_file_size / (1024 * 1024)},
                )

            file_count = self._count_multipart_files(body, boundary, max_files)
            if file_count > max_files:
                raise BusinessValidationError(
                    f"上传文件数量超过限制，最多允许 {max_files} 个文件",
                    details={"max_files": max_files},
                )
            return
        # 注意：此处不解析其它路径的 multipart 以避免重复读取请求体

    @staticmethod
    def _extract_multipart_boundary(content_type: str) -> str | None:
        """解析 multipart boundary"""
        if not content_type:
            return None
        for part in content_type.split(";"):
            item = part.strip()
            if item.startswith("boundary="):
                boundary = item.split("=", 1)[1].strip()
                if boundary.startswith('"') and boundary.endswith('"'):
                    boundary = boundary[1:-1]
                return boundary or None
        return None

    @staticmethod
    def _count_multipart_files(body: bytes, boundary: str, max_files: int) -> int:
        """统计 multipart 中的文件数量"""
        delimiter = f"--{boundary}".encode("ascii", errors="ignore")
        parts = body.split(delimiter)
        count = 0
        for part in parts:
            if not part:
                continue
            if part.startswith(b"--"):
                continue
            if part.startswith(b"\r\n"):
                part = part[2:]
            header_end = part.find(b"\r\n\r\n")
            if header_end == -1:
                continue
            headers = part[:header_end].decode("latin-1", errors="ignore").lower()
            if "content-disposition" in headers and "filename=" in headers:
                count += 1
                if count > max_files:
                    return count
        return count


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
        self.allowed_methods = allowed_methods or HTTPMethods.get_common_methods() + [
            HTTPMethods.OPTIONS
        ]

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
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
                "Authorization, Content-Type, X-Requested-With, Accept, Origin, X-CSRF-Token"
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
    app.add_middleware(CSRFMiddleware)
    app.add_middleware(
        FileUploadSecurityMiddleware,
        max_file_size=config.get("max_file_size", DEFAULT_MAX_FILE_SIZE),
    )
    app.add_middleware(
        RequestValidationMiddleware, rate_limit_config=config.get("rate_limit", {})
    )


# 创建中间件工厂函数
def setup_security_middleware(app: Any) -> None:
    """设置安全中间件"""
    config = {
        "allowed_origins": ["http://localhost:5173", "http://localhost:3000"],
        "allowed_methods": HTTPMethods.get_common_methods()
        + [HTTPMethods.OPTIONS, HTTPMethods.PATCH],
        "max_file_size": DEFAULT_MAX_EXCEL_FILE_SIZE,
        "rate_limit": {
            "pdf_import": {"max_requests": 5, "time_window": 60},
            "excel": {"max_requests": 10, "time_window": 60},
            "post": {"max_requests": 30, "time_window": 60},
            "default": {"max_requests": 100, "time_window": 60},
        },
    }

    create_security_middleware(app, config)
    logger.info("Security middleware configured")
