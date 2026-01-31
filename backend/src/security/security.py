"""
Security utilities facade.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import Depends, UploadFile
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .field_validation import FieldValidator, MODEL_REGISTRY
from .file_validation import FileValidationConfig, FileValidator, MAGIC_AVAILABLE, magic
from .ip_blacklist import IPBlacklistManager
from .rate_limiting import (
    AdaptiveRateLimiter,
    RateLimitConfig,
    RateLimiter,
    RequestLimiter,
    TokenBucketRateLimiter,
    adaptive_limiter,
    token_bucket_limiter,
)
from .request_security import RequestSecurity
from .security_analyzer import SecurityAnalyzer
from .security_middleware import SecurityMiddleware

__all__ = [
    "MAGIC_AVAILABLE",
    "magic",
    "FileValidationConfig",
    "FileValidator",
    "RateLimitConfig",
    "RateLimiter",
    "TokenBucketRateLimiter",
    "AdaptiveRateLimiter",
    "RequestLimiter",
    "IPBlacklistManager",
    "SecurityAnalyzer",
    "SecurityMiddleware",
    "RequestSecurity",
    "FieldValidator",
    "MODEL_REGISTRY",
    "token_bucket_limiter",
    "adaptive_limiter",
    "security_middleware",
    "request_security",
    "get_current_user",
    "validate_file_upload_dependency",
    "get_request_context",
]


security_middleware = SecurityMiddleware()
request_security = RequestSecurity()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
) -> None:
    """获取当前用户"""
    _ = credentials
    # 这里可以实现JWT验证或其他身份验证逻辑
    return None


async def validate_file_upload_dependency(
    file: UploadFile,
    allowed_types: list[str] | None = None,
    max_size: int | None = None,
) -> dict[str, Any]:
    """文件上传验证依赖"""
    return await security_middleware.validate_file_upload(file, allowed_types, max_size)


def get_request_context() -> dict[str, str]:
    """获取请求上下文"""
    return {"request_id": str(uuid.uuid4()), "timestamp": datetime.now(UTC).isoformat()}
