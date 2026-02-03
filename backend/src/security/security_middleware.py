"""
Security request validation helpers.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import Request, UploadFile

from ..core.config import settings
from ..core.exception_handler import PermissionDeniedError, RateLimitError
from .file_validation import FileValidator
from .logging_security import security_auditor
from .rate_limiting import RateLimiter


class SecurityMiddleware:
    """安全中间件"""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        base_config: dict[str, Any] = {
            "enabled": settings.SECURITY_MIDDLEWARE_ENABLED,
            "ip_blacklist_enabled": settings.SECURITY_MIDDLEWARE_IP_BLACKLIST_ENABLED,
            "ip_blacklist": list(settings.IP_BLACKLIST),
            "rate_limit_enabled": settings.SECURITY_MIDDLEWARE_RATE_LIMIT_ENABLED,
            "rate_limits": settings.SECURITY_MIDDLEWARE_RATE_LIMITS,
            "user_agent_check_enabled": settings.SECURITY_MIDDLEWARE_USER_AGENT_CHECK_ENABLED,
            "user_agent_min_length": settings.SECURITY_MIDDLEWARE_USER_AGENT_MIN_LENGTH,
        }
        if config:
            base_config.update(config)

        self.config = base_config
        self.enabled = bool(self.config.get("enabled", True))
        self.ip_blacklist_enabled = bool(self.config.get("ip_blacklist_enabled", True))
        self.rate_limit_enabled = bool(self.config.get("rate_limit_enabled", True))
        self.user_agent_check_enabled = bool(
            self.config.get("user_agent_check_enabled", True)
        )
        self.user_agent_min_length = int(self.config.get("user_agent_min_length", 10))
        self.ip_blacklist = self._normalize_ip_blacklist(
            self.config.get("ip_blacklist", [])
        )

        rate_limits = self.config.get("rate_limits")
        self.rate_limiter = (
            RateLimiter(rate_limits) if isinstance(rate_limits, dict) else RateLimiter()
        )
        self.file_validator = FileValidator()
        self.logger = logging.getLogger(__name__)

    async def validate_request(self, request: Request) -> bool:
        """
        验证请求安全性

        Args:
            request: FastAPI请求对象

        Returns:
            bool: 验证是否通过
        """
        if not self.enabled:
            return True

        # 获取客户端IP
        client_ip = request.client.host if request.client else "unknown"

        # 检查IP黑名单
        if self.ip_blacklist_enabled and self._is_ip_blacklisted(client_ip):
            raise PermissionDeniedError("IP地址已被封禁")

        # 检查请求频率限制
        if self.rate_limit_enabled and not self.rate_limiter.check_rate_limit(
            client_ip
        ):
            raise RateLimitError("请求过于频繁，请稍后重试")

        # 检查User-Agent
        if self.user_agent_check_enabled:
            user_agent = request.headers.get("User-Agent", "")
            if not user_agent or len(user_agent) < self.user_agent_min_length:
                security_auditor.log_security_event(
                    event_type="SUSPICIOUS_USER_AGENT",
                    message=f"Suspicious User-Agent from {client_ip}: '{user_agent}'",
                    ip_address=client_ip,
                    details={"user_agent": user_agent},
                )

        return True

    def _is_ip_blacklisted(self, ip: str) -> bool:
        """检查IP是否在黑名单中"""
        return ip in self.ip_blacklist

    @staticmethod
    def _normalize_ip_blacklist(value: object) -> set[str]:
        if value is None:
            return set()
        if isinstance(value, str):
            return {item.strip() for item in value.split(",") if item.strip()}
        if isinstance(value, (list, set, tuple)):
            return {str(item).strip() for item in value if str(item).strip()}
        return set()

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
