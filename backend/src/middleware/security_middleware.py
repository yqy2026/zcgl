"""
FastAPI安全中间件
提供请求验证、文件上传安全和速率限制功能
"""

import time
from typing import Callable
from fastapi import Request, Response, HTTPException, status, UploadFile
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
import logging
import asyncio
from collections import defaultdict

from ..core.security import RateLimiter, RequestSecurity
from ..core.logging_security import security_auditor
from ..core.exception_handler import ValidationException

logger = logging.getLogger(__name__)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """安全头部中间件"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """添加安全头部"""
        response = await call_next(request)

        # 安全头部
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'"

        return response

class RequestValidationMiddleware(BaseHTTPMiddleware):
    """请求验证中间件"""

    def __init__(self, app, rate_limit_config: dict = None):
        super().__init__(app)
        self.rate_limiter = RateLimiter()
        self.config = rate_limit_config or {}
        self.request_count = defaultdict(int)
        self.blocked_ips = {}
        self.suspicious_patterns = [
            r'<script', r'javascript:', r'vbscript:', r'onload=', r'onerror=',
            r'document\.cookie', r'eval\(', r'alert\(', r'window\.'
        ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """执行请求验证"""
        start_time = time.time()
        client_ip = self._get_client_ip(request)

        try:
            # 检查IP是否被封禁
            if self._is_ip_blocked(client_ip):
                await self._log_blocked_request(request, client_ip, "IP_BLOCKED")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="IP地址已被封禁"
                )

            # 请求频率限制
            if not self._check_rate_limit(client_ip, request):
                await self._log_blocked_request(request, client_ip, "RATE_LIMIT_EXCEEDED")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="请求过于频繁，请稍后重试"
                )

            # 请求内容验证
            await self._validate_request_content(request)

            # 处理请求
            response = await call_next(request)

            # 记录请求统计
            await self._log_request_stats(request, response, start_time, client_ip)

            return response

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Security middleware error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="请求处理失败"
            )

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端真实IP"""
        # 检查代理头部
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        return request.client.host

    def _is_ip_blocked(self, ip: str) -> bool:
        """检查IP是否被封禁"""
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
        # 不同请求类型的限制
        path = getattr(request.url, 'path', '')
        if path is None:
            path = ''

        if path.startswith('/api/v1/pdf_import'):
            # PDF导入限制：每分钟最多5次
            return self.rate_limiter.check_rate_limit(f"{ip}:pdf_import", 5, 60)
        elif path.startswith('/api/v1/excel'):
            # Excel操作限制：每分钟最多10次
            return self.rate_limiter.check_rate_limit(f"{ip}:excel", 10, 60)
        elif request.method == 'POST':
            # POST请求限制：每分钟最多30次
            return self.rate_limiter.check_rate_limit(f"{ip}:post", 30, 60)
        else:
            # 一般请求限制：每分钟最多100次
            return self.rate_limiter.check_rate_limit(ip, 100, 60)

    async def _validate_request_content(self, request: Request):
        """验证请求内容"""
        # 检查可疑的User-Agent
        user_agent = request.headers.get("User-Agent", "")
        if not user_agent or len(user_agent) < 10:
            await self._log_suspicious_request(request, "INVALID_USER_AGENT")

        # 检查请求路径中的可疑模式
        path = getattr(request.url, 'path', None)
        if path is None:
            path = ""
        else:
            path = path.lower()
        for pattern in self.suspicious_patterns:
            if pattern in path:
                await self._log_suspicious_request(request, "SUSPICIOUS_PATH")
                break

        # 检查查询参数
        query_params = dict(request.query_params)
        for key, value in query_params.items():
            if value is not None and isinstance(value, str) and any(pattern in value.lower() for pattern in self.suspicious_patterns):
                await self._log_suspicious_request(request, "SUSPICIOUS_QUERY_PARAM")
                break

    async def _log_blocked_request(self, request: Request, ip: str, reason: str):
        """记录被封禁的请求"""
        security_auditor.log_security_event(
            event_type="REQUEST_BLOCKED",
            details={
                "ip": ip,
                "reason": reason,
                "path": getattr(request.url, 'path', ''),
                "method": request.method,
                "user_agent": request.headers.get("User-Agent", ""),
                "timestamp": time.time()
            }
        )

        # 临时封禁IP
        if reason in ["RATE_LIMIT_EXCEEDED", "SUSPICIOUS_REQUEST"]:
            self.blocked_ips[ip] = time.time()

    async def _log_suspicious_request(self, request: Request, reason: str):
        """记录可疑请求"""
        client_ip = self._get_client_ip(request)

        security_auditor.log_security_event(
            event_type="SUSPICIOUS_REQUEST",
            details={
                "ip": client_ip,
                "reason": reason,
                "path": getattr(request.url, 'path', ''),
                "method": request.method,
                "user_agent": request.headers.get("User-Agent", ""),
                "query_params": dict(request.query_params),
                "timestamp": time.time()
            }
        )

    async def _log_request_stats(self, request: Request, response: Response,
                                start_time: float, ip: str):
        """记录请求统计信息"""
        processing_time = time.time() - start_time

        # 记录慢请求
        if processing_time > 5.0:  # 5秒以上为慢请求
            security_auditor.log_security_event(
                event_type="SLOW_REQUEST",
                details={
                    "ip": ip,
                    "path": getattr(request.url, 'path', ''),
                    "method": request.method,
                    "processing_time": processing_time,
                    "status_code": response.status_code
                }
            )

        # 更新请求计数
        self.request_count[ip] += 1

class FileUploadSecurityMiddleware(BaseHTTPMiddleware):
    """文件上传安全中间件"""

    def __init__(self, app, max_file_size: int = 50 * 1024 * 1024):  # 50MB
        super().__init__(app)
        self.max_file_size = max_file_size

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理文件上传安全检查"""

        # 检查是否为文件上传请求
        if request.headers.get("content-type", "").startswith("multipart/form-data"):
            try:
                await self._validate_file_upload(request)
            except ValidationException as e:
                logger.error(f"File upload validation failed: {str(e)}")
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "success": False,
                        "message": str(e),
                        "error_type": "validation_error"
                    }
                )
            except Exception as e:
                logger.error(f"File upload security check failed: {str(e)}")
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={
                        "success": False,
                        "message": "文件上传验证失败",
                        "error_type": "security_error"
                    }
                )

        return await call_next(request)

    async def _validate_file_upload(self, request: Request):
        """验证文件上传"""
        content_length = int(request.headers.get("content-length", 0))

        # 检查请求大小
        if content_length > self.max_file_size:
            raise ValidationException(
                f"请求过大: {content_length / (1024 * 1024):.2f}MB",
                details={"max_size": self.max_file_size / (1024 * 1024)}
            )

        # 检查文件数量限制
        path = getattr(request.url, 'path', '')
        if path and path.startswith('/api/v1/excel'):
            # Excel导入限制：单次最多上传10个文件
            max_files = 10
        elif path and path.startswith('/api/v1/pdf_import'):
            # PDF导入限制：单次最多上传5个文件
            max_files = 5
        else:
            max_files = 1

        # 注意：这里不能直接读取request.body，因为流已经被消耗
        # 实际的文件验证需要在具体的API端点中进行

class CORSExtendedMiddleware(BaseHTTPMiddleware):
    """扩展的CORS中间件"""

    def __init__(self, app, allowed_origins: list = None, allowed_methods: list = None):
        super().__init__(app)
        self.allowed_origins = allowed_origins or ["http://localhost:5173", "http://localhost:3000"]
        self.allowed_methods = allowed_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理CORS和安全头部"""

        # 预检请求处理
        if request.method == "OPTIONS":
            response = Response()
        else:
            response = await call_next(request)

        # 设置CORS头部
        origin = request.headers.get("origin")
        if origin and (origin in self.allowed_origins or "localhost" in origin):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allowed_methods)
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

def create_security_middleware(app, config: dict = None):
    """
    创建安全中间件链

    Args:
        app: FastAPI应用
        config: 安全配置
    """
    config = config or {}

    # 按顺序添加中间件
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(CORSExtendedMiddleware,
                      allowed_origins=config.get("allowed_origins"),
                      allowed_methods=config.get("allowed_methods"))
    app.add_middleware(FileUploadSecurityMiddleware,
                      max_file_size=config.get("max_file_size", 50 * 1024 * 1024))
    app.add_middleware(RequestValidationMiddleware,
                      rate_limit_config=config.get("rate_limit", {}))

# 创建中间件工厂函数
def setup_security_middleware(app):
    """设置安全中间件"""
    config = {
        "allowed_origins": ["http://localhost:5173", "http://localhost:3000"],
        "allowed_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        "max_file_size": 100 * 1024 * 1024,  # 100MB
        "rate_limit": {
            "pdf_import": {"max_requests": 5, "time_window": 60},
            "excel": {"max_requests": 10, "time_window": 60},
            "post": {"max_requests": 30, "time_window": 60},
            "default": {"max_requests": 100, "time_window": 60}
        }
    }

    create_security_middleware(app, config)
    logger.info("Security middleware configured")