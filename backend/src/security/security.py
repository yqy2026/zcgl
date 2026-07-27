"""Security utilities facade."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from src.crud.field_whitelist import get_whitelist_for_model

from ..middleware.auth import get_current_user as get_current_user
from .field_validation import MODEL_REGISTRY, FieldValidator
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
    "get_request_context",
    "get_whitelist_for_model",
]

security_middleware = SecurityMiddleware()
request_security = RequestSecurity()


def get_request_context() -> dict[str, str]:
    """Return a minimal request correlation context."""
    return {"request_id": str(uuid.uuid4()), "timestamp": datetime.now(UTC).isoformat()}
