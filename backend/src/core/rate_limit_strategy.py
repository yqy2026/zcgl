import os
from enum import Enum

from pydantic import BaseModel, Field


class RateLimitStrategy(str, Enum):
    """Rate limit failure strategy"""

    STRICT = "strict"  # Block on error (fail-closed)
    PERMISSIVE = "permissive"  # Allow on error (fail-open)
    DEGRADED = "degraded"  # Fallback to simple IP limiting


class RateLimitConfig(BaseModel):
    """Rate limit configuration"""

    strategy: RateLimitStrategy = Field(
        default=RateLimitStrategy.STRICT,
        description="Strategy for rate limiter failures",
    )
    max_failures: int = Field(
        default=3, ge=1, le=10, description="Max failures before entering degraded mode"
    )
    cooldown_seconds: int = Field(
        default=60, ge=10, le=600, description="Cooldown period in degraded mode"
    )

    def should_block_on_error(self) -> bool:
        """Determine if requests should be blocked on rate limiter error"""
        return self.strategy == RateLimitStrategy.STRICT

    @classmethod
    def from_env(cls) -> "RateLimitConfig":
        """Create config from environment variables"""
        strategy_str = os.getenv("RATE_LIMIT_FAILURE_MODE", "strict")
        try:
            strategy = RateLimitStrategy(strategy_str)
        except ValueError:
            strategy = RateLimitStrategy.STRICT

        try:
            max_failures = int(os.getenv("RATE_LIMIT_MAX_FAILURES", "3"))
        except (ValueError, TypeError):
            max_failures = 3

        try:
            cooldown_seconds = int(os.getenv("RATE_LIMIT_COOLDOWN_SECONDS", "60"))
        except (ValueError, TypeError):
            cooldown_seconds = 60

        return cls(
            strategy=strategy,
            max_failures=max_failures,
            cooldown_seconds=cooldown_seconds,
        )
