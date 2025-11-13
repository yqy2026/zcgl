"""
增强安全中间件
提供请求验证、SQL注入防护、XSS防护等安全功能
"""

import re
import time
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint
import logging

logger = logging.getLogger(__name__)

# SQL注入检测模式
SQL_INJECTION_PATTERNS = [
    r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
    r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
    r"(\b(OR|AND)\s+\'\w+\'\s*=\s*\'\w+')",
    r"(--|#|/\*|\*/)",
    r"(\b(SLEEP|BENCHMARK|LOAD_FILE|OUTFILE)\b)",
    r"(\b(INFORMATION_SCHEMA|SYS|MASTER|MSDB)\b)",
    r"(=\s*\'.*?\'\s*OR\s*\'\w+\'\s*=\s*\')",
]

# XSS检测模式
XSS_PATTERNS = [
    r"(<script[^>]*>.*?</script>)",
    r"(javascript\s*:)",
    r"(on\w+\s*=)",
    r"(<iframe[^>]*>)",
    r"(<object[^>]*>)",
    r"(<embed[^>]*>)",
    r"(<link[^>]*>)",
    r"(<meta[^>]*>)",
]

# 路径遍历检测模式
PATH_TRAVERSAL_PATTERNS = [
    r"(\.\./)",
    r"(\.\.\\)",
    r"(%2e%2e%2f)",
    r"(%2e%2e\\)",
    r"(\.\.%2f)",
    r"(\.\.\\)",
]


class EnhancedSecurityMiddleware(BaseHTTPMiddleware):
    """增强安全中间件"""

    def __init__(
        self,
        app,
        max_request_size: int = 10 * 1024 * 1024,  # 10MB
        blocked_ips: List[str] = None,
        allowed_origins: List[str] = None
    ):
        super().__init__(app)
        self.max_request_size = max_request_size
        self.blocked_ips = blocked_ips or []
        self.allowed_origins = allowed_origins or []

        # 请求频率限制
        self.request_counts: Dict[str, List[datetime]] = {}
        self.suspicious_requests: Dict[str, int] = {}

        # 安全事件记录
        self.security_events: List[Dict[str, Any]] = []

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
    ) -> Response:
        """处理请求并执行安全检查"""

        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "")

        # IP黑名单检查
        if client_ip in self.blocked_ips:
            await self._log_security_event("BLOCKED_IP", client_ip, {
                "user_agent": user_agent,
                "path": request.url.path
            })
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="访问被拒绝"
            )

        # 请求频率检查
        if not await self._check_request_frequency(client_ip):
            await self._log_security_event("RATE_LIMIT", client_ip, {
                "path": request.url.path,
                "user_agent": user_agent
            })
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="请求过于频繁"
            )

        # 可疑请求检查
        if await self._is_suspicious_request(client_ip):
            await self._log_security_event("SUSPICIOUS_REQUEST", client_ip, {
                "path": request.url.path,
                "user_agent": user_agent
            })
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="请求被标记为可疑"
            )

        # 请求大小检查
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_request_size:
            await self._log_security_event("LARGE_REQUEST", client_ip, {
                "content_length": content_length,
                "path": request.url.path
            })
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="请求体过大"
            )

        # 检查请求方法和路径
        await self._validate_request_method_and_path(request, client_ip)

        # 检查请求头
        await self._validate_headers(request, client_ip)

        # 检查查询参数
        await self._validate_query_params(request, client_ip)

        # 对于POST/PUT请求，检查请求体
        if request.method in ["POST", "PUT", "PATCH"]:
            await self._validate_request_body(request, client_ip)

        try:
            response = await call_next(request)

            # 添加安全头
            await self._add_security_headers(response)

            return response

        except HTTPException:
            raise
        except Exception as e:
            # 记录异常安全事件
            await self._log_security_event("UNHANDLED_EXCEPTION", client_ip, {
                "error": str(e),
                "path": request.url.path
            })
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="服务器内部错误"
            )

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端真实IP"""
        # 检查代理头
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        return request.client.host if request.client else "unknown"

    async def _check_request_frequency(self, client_ip: str) -> bool:
        """检查请求频率"""
        now = datetime.now()

        # 清理过期的请求记录（超过1分钟的）
        if client_ip in self.request_counts:
            self.request_counts[client_ip] = [
                req_time for req_time in self.request_counts[client_ip]
                if now - req_time < timedelta(minutes=1)
            ]
        else:
            self.request_counts[client_ip] = []

        # 检查最近1分钟的请求数量
        recent_requests = len(self.request_counts[client_ip])
        if recent_requests > 100:  # 每分钟最多100次请求
            return False

        # 记录当前请求
        self.request_counts[client_ip].append(now)
        return True

    async def _is_suspicious_request(self, client_ip: str) -> bool:
        """检查是否为可疑请求"""
        # 基于IP的可疑请求计数
        suspicious_count = self.suspicious_requests.get(client_ip, 0)

        # 如果可疑请求次数过多，则拒绝
        if suspicious_count > 10:
            return False  # 已经记录为可疑，不再重复检查

        return False

    async def _validate_request_method_and_path(self, request: Request, client_ip: str) -> None:
        """验证请求方法和路径"""
        # 检查HTTP方法
        allowed_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
        if request.method not in allowed_methods:
            await self._log_security_event("INVALID_METHOD", client_ip, {
                "method": request.method,
                "path": request.url.path
            })
            raise HTTPException(
                status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                detail="不允许的HTTP方法"
            )

        # 检查路径遍历攻击
        for pattern in PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, request.url.path, re.IGNORECASE):
                await self._log_security_event("PATH_TRAVERSAL", client_ip, {
                    "path": request.url.path,
                    "pattern": pattern
                })
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="路径格式无效"
                )

    async def _validate_headers(self, request: Request, client_ip: str) -> None:
        """验证请求头"""
        # 检查Host头
        host = request.headers.get("Host", "")
        if not host or len(host) > 253:  # RFC规范
            await self._log_security_event("INVALID_HOST", client_ip, {
                "host": host
            })
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的Host头"
            )

        # 检查User-Agent
        user_agent = request.headers.get("User-Agent", "")
        if not user_agent or len(user_agent) > 500:
            await self._log_security_event("SUSPICIOUS_USER_AGENT", client_ip, {
                "user_agent": user_agent[:100] + "..." if len(user_agent) > 100 else user_agent
            })
            # 不直接拒绝，但记录可疑行为

        # 检查Referer（如果需要）
        referer = request.headers.get("Referer", "")
        if referer and self.allowed_origins:
            if not any(origin in referer for origin in self.allowed_origins):
                await self._log_security_event("INVALID_REFERER", client_ip, {
                    "referer": referer
                })

    async def _validate_query_params(self, request: Request, client_ip: str) -> None:
        """验证查询参数"""
        for key, value in request.query_params.items():
            # SQL注入检查
            if await self._check_sql_injection(value):
                await self._log_security_event("SQL_INJECTION_QUERY", client_ip, {
                    "param": key,
                    "value": value[:100]
                })
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="查询参数包含非法字符"
                )

            # XSS检查
            if await self._check_xss(value):
                await self._log_security_event("XSS_QUERY", client_ip, {
                    "param": key,
                    "value": value[:100]
                })
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="查询参数包含非法字符"
                )

    async def _validate_request_body(self, request: Request, client_ip: str) -> None:
        """验证请求体"""
        try:
            # 获取请求体
            body = await request.body()

            if not body:
                return

            # 解码为字符串进行检查
            try:
                body_str = body.decode('utf-8')
            except UnicodeDecodeError:
                # 如果不是UTF-8编码，尝试其他编码
                try:
                    body_str = body.decode('gbk')
                except UnicodeDecodeError:
                    # 无法解码，记录为可疑
                    await self._log_security_event("INVALID_ENCODING", client_ip, {
                        "content_type": request.headers.get("Content-Type", "")
                    })
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="请求体编码无效"
                    )

            # SQL注入检查
            if await self._check_sql_injection(body_str):
                await self._log_security_event("SQL_INJECTION_BODY", client_ip, {
                    "body_preview": body_str[:200]
                })
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="请求体包含非法字符"
                )

            # XSS检查
            if await self._check_xss(body_str):
                await self._log_security_event("XSS_BODY", client_ip, {
                    "body_preview": body_str[:200]
                })
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="请求体包含非法字符"
                )

        except Exception as e:
            if isinstance(e, HTTPException):
                raise
            # 其他异常记录但不阻止请求
            await self._log_security_event("BODY_VALIDATION_ERROR", client_ip, {
                "error": str(e)
            })

    async def _check_sql_injection(self, text: str) -> bool:
        """检查SQL注入"""
        for pattern in SQL_INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL):
                return True
        return False

    async def _check_xss(self, text: str) -> bool:
        """检查XSS攻击"""
        for pattern in XSS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL):
                return True
        return False

    async def _add_security_headers(self, response: Response) -> None:
        """添加安全响应头"""
        # 防止点击劫持
        response.headers["X-Frame-Options"] = "DENY"

        # 防止MIME类型嗅探
        response.headers["X-Content-Type-Options"] = "nosniff"

        # XSS保护
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # 强制HTTPS（生产环境）
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # 内容安全策略
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self'"
        )

        # 引用策略
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # 权限策略
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), "
            "payment=(), usb=(), magnetometer=(), gyroscope=()"
        )

    async def _log_security_event(self, event_type: str, client_ip: str, details: Dict[str, Any]) -> None:
        """记录安全事件"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "client_ip": client_ip,
            "details": details
        }

        self.security_events.append(event)

        # 保留最近1000个事件
        if len(self.security_events) > 1000:
            self.security_events = self.security_events[-1000:]

        # 记录日志
        logger.warning(f"Security Event: {event_type} from {client_ip} - {details}")

        # 更新可疑请求计数
        if event_type in ["SQL_INJECTION_BODY", "XSS_BODY", "PATH_TRAVERSAL"]:
            self.suspicious_requests[client_ip] = self.suspicious_requests.get(client_ip, 0) + 1

    def get_security_stats(self) -> Dict[str, Any]:
        """获取安全统计信息"""
        now = datetime.now()
        last_hour = now - timedelta(hours=1)
        last_day = now - timedelta(days=1)

        # 过滤事件
        recent_events = [e for e in self.security_events if datetime.fromisoformat(e["timestamp"]) > last_hour]
        daily_events = [e for e in self.security_events if datetime.fromisoformat(e["timestamp"]) > last_day]

        # 统计事件类型
        event_types = {}
        for event in recent_events:
            event_type = event["event_type"]
            event_types[event_type] = event_types.get(event_type, 0) + 1

        # 统计可疑IP
        suspicious_ips = [
            ip for ip, count in self.suspicious_requests.items()
            if count > 0
        ]

        return {
            "total_security_events": len(self.security_events),
            "last_hour_events": len(recent_events),
            "last_day_events": len(daily_events),
            "event_types": event_types,
            "suspicious_ips": suspicious_ips,
            "blocked_ips_count": len(self.blocked_ips),
            "active_request_ips": len(self.request_counts)
        }

    def get_recent_security_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取最近的安全事件"""
        return sorted(
            self.security_events,
            key=lambda x: x["timestamp"],
            reverse=True
        )[:limit]