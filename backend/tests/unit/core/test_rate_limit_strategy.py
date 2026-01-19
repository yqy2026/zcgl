import pytest
from src.core.rate_limit_strategy import RateLimitStrategy, RateLimitConfig

def test_rate_limit_strategy_enum():
    """Test that rate limit strategy enum has correct values"""
    assert RateLimitStrategy.STRICT.value == "strict"
    assert RateLimitStrategy.PERMISSIVE.value == "permissive"
    assert RateLimitStrategy.DEGRADED.value == "degraded"

def test_rate_limit_config_defaults():
    """Test rate limit config has secure defaults"""
    config = RateLimitConfig()
    assert config.strategy == RateLimitStrategy.STRICT
    assert config.max_failures == 3
    assert config.cooldown_seconds == 60

def test_strict_mode_blocks_on_error():
    """Test that strict mode blocks requests when rate limiter fails"""
    config = RateLimitConfig(strategy=RateLimitStrategy.STRICT)
    # Simulate rate limiter error
    assert config.should_block_on_error() is True

def test_permissive_mode_allows_on_error():
    """Test that permissive mode allows requests when rate limiter fails"""
    config = RateLimitConfig(strategy=RateLimitStrategy.PERMISSIVE)
    assert config.should_block_on_error() is False
