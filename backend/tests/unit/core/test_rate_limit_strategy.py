import os

from src.core.rate_limit_strategy import RateLimitConfig, RateLimitStrategy


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


def test_from_env_defaults():
    """Test from_env() uses correct defaults when env vars not set"""
    # Clear env vars to test defaults
    os.environ.pop("RATE_LIMIT_FAILURE_MODE", None)
    os.environ.pop("RATE_LIMIT_MAX_FAILURES", None)
    os.environ.pop("RATE_LIMIT_COOLDOWN_SECONDS", None)

    config = RateLimitConfig.from_env()

    assert config.strategy == RateLimitStrategy.STRICT
    assert config.max_failures == 3
    assert config.cooldown_seconds == 60


def test_from_env_custom_values():
    """Test from_env() loads custom values from environment"""
    os.environ["RATE_LIMIT_FAILURE_MODE"] = "permissive"
    os.environ["RATE_LIMIT_MAX_FAILURES"] = "5"
    os.environ["RATE_LIMIT_COOLDOWN_SECONDS"] = "120"

    config = RateLimitConfig.from_env()

    assert config.strategy == RateLimitStrategy.PERMISSIVE
    assert config.max_failures == 5
    assert config.cooldown_seconds == 120

    # Clean up
    os.environ.pop("RATE_LIMIT_FAILURE_MODE", None)
    os.environ.pop("RATE_LIMIT_MAX_FAILURES", None)
    os.environ.pop("RATE_LIMIT_COOLDOWN_SECONDS", None)


def test_from_env_invalid_strategy():
    """Test from_env() falls back to STRICT for invalid strategy"""
    os.environ["RATE_LIMIT_FAILURE_MODE"] = "invalid_strategy"

    config = RateLimitConfig.from_env()

    assert config.strategy == RateLimitStrategy.STRICT

    # Clean up
    os.environ.pop("RATE_LIMIT_FAILURE_MODE", None)


def test_from_env_invalid_max_failures():
    """Test from_env() falls back to default for invalid max_failures"""
    os.environ["RATE_LIMIT_MAX_FAILURES"] = "not_a_number"

    config = RateLimitConfig.from_env()

    assert config.max_failures == 3

    # Clean up
    os.environ.pop("RATE_LIMIT_MAX_FAILURES", None)


def test_from_env_invalid_cooldown():
    """Test from_env() falls back to default for invalid cooldown"""
    os.environ["RATE_LIMIT_COOLDOWN_SECONDS"] = "invalid"

    config = RateLimitConfig.from_env()

    assert config.cooldown_seconds == 60

    # Clean up
    os.environ.pop("RATE_LIMIT_COOLDOWN_SECONDS", None)


def test_from_env_degraded_mode():
    """Test from_env() loads degraded mode from environment"""
    os.environ["RATE_LIMIT_FAILURE_MODE"] = "degraded"

    config = RateLimitConfig.from_env()

    assert config.strategy == RateLimitStrategy.DEGRADED

    # Clean up
    os.environ.pop("RATE_LIMIT_FAILURE_MODE", None)
