"""
Security request validation helpers.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import Request, UploadFile

from ..core.exception_handler import PermissionDeniedError, RateLimitError
from .file_validation import FileValidator
from .logging_security import security_auditor
from .rate_limiting import RateLimiter

class SecurityMiddleware:
    """安全中间件"""

    def __init__(self) -> None:
        self.rate_limiter = RateLimiter()
        self.file_validator = FileValidator()
        self.config: dict[str, Any] = {}  # TODO: 未来可添加安全中间件配置
        self.logger = logging.getLogger(__name__)

    async def validate_request(self, request: Request) -> bool:
        """
        验证请求安全性

        Args:
            request: FastAPI请求对象

        Returns:
            bool: 验证是否通过
        """
        # 获取客户端IP
        client_ip = request.client.host if request.client else "unknown"

        # 检查IP黑名单
        if self._is_ip_blacklisted(client_ip):
            raise PermissionDeniedError("IP地址已被封禁")

        # 检查请求频率限制
        if not self.rate_limiter.check_rate_limit(client_ip):
            raise RateLimitError("请求过于频繁，请稍后重试")

        # 检查User-Agent
        user_agent = request.headers.get("User-Agent", "")
        if not user_agent or len(user_agent) < 10:
            security_auditor.log_security_event(
                event_type="SUSPICIOUS_USER_AGENT",
                message=f"Suspicious User-Agent from {client_ip}: '{user_agent}'",
                ip_address=client_ip,
                details={"user_agent": user_agent},
            )

        return True

    def _is_ip_blacklisted(self, ip: str) -> bool:
        """检查IP是否在黑名单中"""
        blacklist = self.config.get("ip_blacklist", [])
        return ip in blacklist

    async def validate_file_upload(
        self,
        file: UploadFile,
        allowed_types: list[str] | None = None,
        max_size: int | None = None,
    ) -> dict[str, Any]:
        """
        验证文件上传

        Args:
            file: 上传的文件
            allowed_types: 允许的文件类型
            max_size: 最大文件大小

        Returns:
            Dict: 验证结果
        """
        # 确保参数有默认值
        if allowed_types is None:
            allowed_types = []
        if max_size is None:
            max_size = 0

        return self.file_validator.validate_upload(file, allowed_types, max_size)
