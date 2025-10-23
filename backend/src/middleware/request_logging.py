"""
请求日志中间件
记录所有API请求的详细信息，用于安全和审计
"""

import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ..core.logging_security import log_request_info


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""

    def __init__(self, app):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 生成请求ID
        request_id = str(uuid.uuid4())

        # 记录请求开始时间
        start_time = time.time()

        # 获取客户端信息
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")

        # 执行请求
        response = await call_next(request)

        # 计算请求持续时间
        duration_ms = (time.time() - start_time) * 1000

        # 记录请求日志
        log_request_info(
            method=request.method,
            path=str(request.url.path),
            query_string=str(request.query_params) if request.query_params else None,
            status_code=response.status_code,
            duration_ms=duration_ms,
            request_id=request_id,
            client_ip=client_ip,
            user_agent=user_agent,
            # 尝试获取用户ID（如果有认证）
            user_id=getattr(request.state, 'user_id', None)
        )

        # 添加请求ID到响应头
        response.headers["X-Request-ID"] = request_id

        return response

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端IP地址"""
        # 检查代理头
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # 回退到客户端地址
        if request.client:
            return request.client.host

        return "unknown"


# 便捷函数创建中间件
def create_request_logging_middleware(app=None):
    """创建请求日志中间件"""
    if app is None:
        return RequestLoggingMiddleware
    return RequestLoggingMiddleware(app)