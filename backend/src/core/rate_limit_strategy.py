from enum import Enum
from pydantic import BaseModel, Field
from src.core.environment import get_environment

class RateLimitStrategy(str, Enum):
    """Rate limit failure strategy"""
    STRICT = "strict"  # Block on error (fail-closed)
    PERMISSIVE = "permissive"  # Allow on error (fail-open)
    DEGRADED = "degraded"  # Fallback to simple IP limiting

class RateLimitConfig(BaseModel):
    """Rate limit configuration"""
    strategy: RateLimitStrategy = Field(
        default=RateLimitStrategy.STRICT,
        description="Strategy for rate limiter failures"
    )
    max_failures: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Max failures before entering degraded mode"
    )
    cooldown_seconds: int = Field(
        default=60,
        ge=10,
        le=600,
        description="Cooldown period in degraded mode"
    )

    def should_block_on_error(self) -> bool:
        """Determine if requests should be blocked on rate limiter error"""
        return self.strategy == RateLimitStrategy.STRICT

    @classmethod
    def from_env(cls) -> "RateLimitConfig":
        """Create config from environment variables"""
        env = get_environment()
        strategy_str = env.getenv("RATE_LIMIT_FAILURE_MODE", "strict")
        try:
            strategy = RateLimitStrategy(strategy_str)
        except ValueError:
            strategy = RateLimitStrategy.STRICT

        return cls(
            strategy=strategy,
            max_failures=int(env.getenv("RATE_LIMIT_MAX_FAILURES", "3")),
            cooldown_seconds=int(env.getenv("RATE_LIMIT_COOLDOWN_SECONDS", "60"))
        )
