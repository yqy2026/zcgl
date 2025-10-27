"""
API安全中间件
"""

import asyncio
import hashlib
import hmac
import time
from collections import defaultdict
from datetime import datetime

from fastapi import Request, status
from fastapi.responses import JSONResponse


# 速率限制存储（内存版本，生产环境建议使用Redis）
class RateLimiter:
    """速率限制器"""

    def __init__(self):
        self.requests = defaultdict(list)  # 存储每个IP的请求时间戳
        self.lock = asyncio.Lock()

    async def is_allowed(
        self, client_ip: str, max_requests: int = 100, window_seconds: int = 3600
    ) -> bool:
        """检查是否允许请求（基于IP的速率限制）"""
        async with self.lock:
            now = time.time()
            # 清理过期的请求记录
            self.requests[client_ip] = [
                timestamp
                for timestamp in self.requests[client_ip]
                if now - timestamp < window_seconds
            ]

            # 检查是否超过限制
            if len(self.requests[client_ip]) >= max_requests:
                return False

            # 记录当前请求
            self.requests[client_ip].append(now)
            return True

    async def is_allowed_by_user(
        self, user_id: str, max_requests: int = 1000, window_seconds: int = 3600
    ) -> bool:
        """检查是否允许请求（基于用户的速率限制）"""
        async with self.lock:
            now = time.time()
            # 清理过期的请求记录
            self.requests[user_id] = [
                timestamp
                for timestamp in self.requests[user_id]
                if now - timestamp < window_seconds
            ]

            # 检查是否超过限制
            if len(self.requests[user_id]) >= max_requests:
                return False

            # 记录当前请求
            self.requests[user_id].append(now)
            return True


# 创建全局速率限制器实例
rate_limiter = RateLimiter()


class APISecurityMiddleware:
    """API安全中间件"""

    def __init__(self):
        self.api_keys = {}  # 存储API密钥（生产环境应从安全存储读取）

    async def verify_request_signature(self, request: Request) -> bool:
        """验证请求签名"""
        # 获取签名头
        signature = request.headers.get("X-Signature")
        timestamp = request.headers.get("X-Timestamp")
        api_key = request.headers.get("X-API-Key")

        # 如果没有签名要求，直接通过
        if not signature and not timestamp and not api_key:
            return True

        # 检查必需的头
        if not all([signature, timestamp, api_key]):
            return False

        # 验证时间戳（防止重放攻击）
        try:
            request_time = int(timestamp)
            current_time = int(time.time())
            if abs(current_time - request_time) > 300:  # 5分钟时间窗口
                return False
        except ValueError:
            return False

        # 获取API密钥
        secret_key = self.api_keys.get(api_key)
        if not secret_key:
            return False

        # 重新计算签名
        try:
            # 获取请求体
            body = await request.body()
            body_str = body.decode("utf-8") if body else ""

            # 构造签名字符串
            sign_string = (
                f"{request.method}\n{str(request.url.path)}\n{timestamp}\n{body_str}"
            )

            # 计算HMAC签名
            expected_signature = hmac.new(
                secret_key.encode("utf-8"), sign_string.encode("utf-8"), hashlib.sha256
            ).hexdigest()

            # 比较签名
            return hmac.compare_digest(signature, expected_signature)
        except Exception:
            return False

    async def check_rate_limit(
        self, request: Request, user_id: str | None = None
    ) -> bool:
        """检查速率限制"""
        client_ip = self.get_client_ip(request)

        # 全局限制（每小时1000次）
        if not await rate_limiter.is_allowed(client_ip, 1000, 3600):
            return False

        # 用户级别限制（如果已认证）
        if user_id:
            if not await rate_limiter.is_allowed_by_user(user_id, 10000, 3600):
                return False

        # 特定端点限制
        endpoint = str(request.url.path)
        if endpoint in ["/api/v1/auth/login", "/api/v1/auth/refresh"]:
            # 认证端点更严格的限制（每小时100次）
            if not await rate_limiter.is_allowed(client_ip, 100, 3600):
                return False
        elif endpoint.startswith("/api/v1/users"):
            # 用户管理端点限制（每小时500次）
            if not await rate_limiter.is_allowed(client_ip, 500, 3600):
                return False

        return True

    def get_client_ip(self, request: Request) -> str:
        """获取客户端IP地址"""
        # 检查X-Forwarded-For头（如果有反向代理）
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        # 检查X-Real-IP头
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # 使用客户端IP
        return request.client.host if request.client else "unknown"

    async def log_request(self, request: Request, user_id: str | None = None):
        """记录请求日志"""
        # 这里可以集成到审计日志系统
        print(
            f"API请求: {request.method} {str(request.url.path)} from {self.get_client_ip(request)} user: {user_id}"
        )


# 创建全局API安全中间件实例
api_security = APISecurityMiddleware()


async def api_security_middleware(request: Request, call_next):
    """API安全中间件函数"""
    try:
        # 获取用户ID（如果已认证）
        user_id = None
        # 这里需要从请求中提取用户信息，简化处理
        # 实际实现中需要从JWT令牌中提取用户ID

        # 检查速率限制
        if not await api_security.check_rate_limit(request, user_id):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Too Many Requests",
                    "message": "请求过于频繁，请稍后再试",
                    "timestamp": datetime.now().isoformat(),
                },
            )

        # 验证请求签名（如果提供了签名信息）
        if request.headers.get("X-Signature"):
            if not await api_security.verify_request_signature(request):
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "error": "Invalid Signature",
                        "message": "请求签名无效",
                        "timestamp": datetime.now().isoformat(),
                    },
                )

        # 记录请求
        await api_security.log_request(request, user_id)

        # 继续处理请求
        response = await call_next(request)
        return response

    except Exception as e:
        # 记录安全错误
        print(f"API安全中间件错误: {e}")
        # 继续处理请求（不要因为安全中间件错误阻止正常请求）
        response = await call_next(request)
        return response
