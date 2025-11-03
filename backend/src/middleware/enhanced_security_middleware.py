from typing import Any

"""
增强安全中间件
集成密码策略、JWT管理、账户安全等功能
"""

import time

from fastapi import HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware

from ..core.config import settings
from ..services.security_service import SecurityService


class EnhancedSecurityMiddleware(BaseHTTPMiddleware):
    """增强安全中间件"""

    def __init__(self, app):
        super().__init__(app)
        self.security_service = None  # 延迟初始化
        self.failed_attempts: dict[str, list] = {}  # IP失败尝试记录
        self.rate_limits: dict[str, dict] = {}  # 速率限制记录

    async def dispatch(self, request: Request, call_next):
        """处理请求"""
        # 延迟初始化安全服务
        if not self.security_service:
            from ..database import SessionLocal

            db = SessionLocal()
            self.security_service = SecurityService(db)

        # 获取客户端信息
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")

        # 速率限制检查
        if not await self._check_rate_limit(client_ip):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="请求过于频繁，请稍后再试",
            )

        # 可疑活动检测
        await self._detect_suspicious_activity(request, client_ip, user_agent)

        # 安全头设置
        response = await call_next(request)
        await self._add_security_headers(response)

        return response

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端IP"""
        # 检查代理头
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        return request.client.host

    async def _check_rate_limit(self, client_ip: str) -> bool:
        """检查速率限制"""
        now = time.time()

        # 清理过期记录
        self._cleanup_expired_rate_limits(now)

        # 获取或创建速率限制记录
        if client_ip not in self.rate_limits:
            self.rate_limits[client_ip] = {"requests": [], "failed_logins": []}

        # 检查通用请求限制
        recent_requests = [
            req_time
            for req_time in self.rate_limits[client_ip]["requests"]
            if now - req_time < 60  # 1分钟内
        ]

        if len(recent_requests) > 100:  # 每分钟最多100个请求
            return False

        # 记录当前请求
        self.rate_limits[client_ip]["requests"].append(now)
        return True

    def _cleanup_expired_rate_limits(self, now: float):
        """清理过期的速率限制记录"""
        cutoff_time = now - 300  # 5分钟前

        expired_ips = []
        for ip, limits in self.rate_limits.items():
            # 清理过期的请求记录
            limits["requests"] = [
                req_time for req_time in limits["requests"] if req_time > cutoff_time
            ]
            limits["failed_logins"] = [
                fail_time
                for fail_time in limits["failed_logins"]
                if fail_time > cutoff_time
            ]

            # 如果没有最近的记录，标记为过期
            if not limits["requests"] and not limits["failed_logins"]:
                expired_ips.append(ip)

        # 删除过期记录
        for ip in expired_ips:
            del self.rate_limits[ip]

    async def _detect_suspicious_activity(
        self, request: Request, client_ip: str, user_agent: str
    ):
        """检测可疑活动"""
        path = request.url.path

        # 只对认证相关路径进行检测
        if not (path.startswith("/api/v1/auth/") or path.startswith("/login")):
            return

        # 检查失败登录尝试
        if path.endswith("/login") and request.method == "POST":
            await self._track_login_attempt(request, client_ip, user_agent)

        # 检查暴力破解模式
        await self._check_brute_force_pattern(client_ip)

        # 检查异常用户代理
        await self._check_suspicious_user_agent(user_agent, client_ip)

    async def _track_login_attempt(
        self, request: Request, client_ip: str, user_agent: str
    ):
        """跟踪登录尝试"""
        # 这里需要在请求处理完成后检查结果
        # 暂时记录IP，实际的失败检测在认证处理器中进行
        pass

    async def _check_brute_force_pattern(self, client_ip: str):
        """检查暴力破解模式"""
        now = time.time()

        if client_ip not in self.rate_limits:
            return

        # 检查短时间内的多次失败尝试
        recent_failures = [
            fail_time
            for fail_time in self.rate_limits[client_ip].get("failed_logins", [])
            if now - fail_time < 300  # 5分钟内
        ]

        if len(recent_failures) > 10:  # 5分钟内超过10次失败
            # 记录可疑活动
            if self.security_service:
                await self._log_suspicious_activity(
                    client_ip,
                    "brute_force_detected",
                    {"failed_attempts": len(recent_failures)},
                )

    async def _check_suspicious_user_agent(self, user_agent: str, client_ip: str):
        """检查可疑用户代理"""
        suspicious_patterns = [
            "sqlmap",
            "nikto",
            "nmap",
            "masscan",
            "zap",
            "burp",
            "python-requests",
            "curl",
            "wget",
            "scanner",
        ]

        user_agent_lower = user_agent.lower()
        for pattern in suspicious_patterns:
            if pattern in user_agent_lower:
                await self._log_suspicious_activity(
                    client_ip,
                    "suspicious_user_agent",
                    {"user_agent": user_agent, "pattern": pattern},
                )
                break

    async def _log_suspicious_activity(
        self, client_ip: str, activity_type: str, details: dict
    ):
        """记录可疑活动"""
        if self.security_service:
            try:
                # 这里可以根据需要实现更复杂的日志记录
                print(
                    f"[SECURITY] 可疑活动检测: {activity_type}, IP: {client_ip}, 详情: {details}"
                )
            except Exception as e:
                print(f"[SECURITY] 记录可疑活动失败: {e}")

    async def _add_security_headers(self, response: Response):
        """添加安全头"""
        # 防止点击劫持
        response.headers["X-Frame-Options"] = "DENY"

        # 防止MIME类型嗅探
        response.headers["X-Content-Type-Options"] = "nosniff"

        # XSS保护
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # 强制HTTPS（生产环境）
        if not settings.DEBUG:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        # 内容安全策略
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        response.headers["Content-Security-Policy"] = csp

        # 引用策略
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # 权限策略
        permissions_policy = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "accelerometer=()"
        )
        response.headers["Permissions-Policy"] = permissions_policy


class EnhancedTokenValidator:
    """增强令牌验证器"""

    def __init__(self):
        self.security_service = None

    async def validate_token(self) -> dict[str, Any]:
        """验证令牌"""
        if not self.security_service:
            from ..database import SessionLocal

            db = SessionLocal()
            self.security_service = SecurityService(db)

        # 获取设备信息
        device_info = {
            "ip_address": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent", ""),
            "device_id": request.headers.get("X-Device-ID"),
            "platform": request.headers.get("X-Platform"),
        }

        # 使用增强验证
        result = self.security_service.validate_token_enhanced(
            credentials.credentials, "access"
        )

        if not result["valid"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=result.get("error", "令牌无效"),
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 检查设备指纹（如果存在）
        payload = result["payload"]
        expected_fingerprint = payload.get("device_fingerprint")
        if expected_fingerprint:
            current_fingerprint = self.security_service._generate_device_fingerprint(
                device_info
            )
            if expected_fingerprint != current_fingerprint:
                # 设备不匹配，可能的安全风险
                await self._handle_device_mismatch(result["user_id"], device_info)

        return result

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端IP"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        return request.client.host

    async def _handle_device_mismatch(self, user_id: str, device_info: dict):
        """处理设备不匹配"""
        if self.security_service:
            try:
                # 记录可疑活动
                await self.security_service._log_security_event(
                    user_id, "device_mismatch", device_info
                )
            except Exception as e:
                print(f"[SECURITY] 处理设备不匹配失败: {e}")


# 全局实例
enhanced_token_validator = EnhancedTokenValidator()


async def get_current_user_enhanced(self) -> dict[str, Any]:
    """获取当前用户（增强版）"""
    return await enhanced_token_validator.validate_token(credentials, request)
