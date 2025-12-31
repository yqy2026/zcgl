"""
请求日志中间件
记录所有API请求的详细信息，用于安全和审计
"""

import time
import uuid
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ..core.logging_security import SensitiveDataFilter, log_request_info


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""

    def __init__(self, app):
        super().__init__(app)
        self.sensitive_filter = SensitiveDataFilter()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 生成请求ID
        request_id = str(uuid.uuid4())

        # 记录请求开始时间
        start_time = time.time()

        # 获取客户端信息
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")

        # 对用户代理进行脱敏处理
        user_agent = self.sensitive_filter._filter_sensitive_data(user_agent)

        # 执行请求
        response = await call_next(request)

        # 计算请求持续时间
        duration_ms = (time.time() - start_time) * 1000

        # 获取用户ID（如果有认证）
        user_id = getattr(request.state, "user_id", None)

        # 对查询参数进行脱敏处理
        query_params = dict(request.query_params)
        filtered_query_params = {}
        for key, value in query_params.items():
            # 检查键是否敏感
            if self.sensitive_filter._is_sensitive_key(key):
                filtered_query_params[key] = "***"
            else:
                # 对值进行脱敏处理
                filtered_query_params[key] = (
                    self.sensitive_filter._filter_sensitive_data(str(value))
                )

        # 记录请求日志
        log_request_info(
            method=request.method,
            path=str(request.url.path),
            query_string=str(filtered_query_params) if filtered_query_params else None,
            status_code=response.status_code,
            duration_ms=duration_ms,
            request_id=request_id,
            client_ip=client_ip,
            user_agent=user_agent,
            user_id=user_id,
        )

        # 添加请求ID到响应头
        response.headers["X-Request-ID"] = request_id

        return response

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端IP地址"""
        # 检查代理头
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:  # pragma: no cover
            return forwarded_for.split(",")[0].strip()  # pragma: no cover

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:  # pragma: no cover
            return real_ip  # pragma: no cover

        # 回退到客户端地址
        if request.client:  # pragma: no cover
            return request.client.host  # pragma: no cover

        return "unknown"  # pragma: no cover


# 便捷函数创建中间件
def create_request_logging_middleware(app=None):
    """创建请求日志中间件"""
    if app is None:  # pragma: no cover
        return RequestLoggingMiddleware  # pragma: no cover
    return RequestLoggingMiddleware(app)  # pragma: no cover
