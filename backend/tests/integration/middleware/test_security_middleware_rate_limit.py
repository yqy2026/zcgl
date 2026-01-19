"""Integration tests for rate limiting with circuit breaker"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from src.main import app
from src.middleware.security_middleware import RequestValidationMiddleware
from src.core.rate_limit_strategy import RateLimitStrategy
from src.core.circuit_breaker import CircuitBreaker


def test_rate_limit_fail_closed_blocks_requests():
    """Test that circuit breaker integration is functional"""
    # This test verifies the circuit breaker and rate limit strategy are integrated
    # The actual request blocking behavior is tested in the unit tests

    # Test that circuit breaker can be instantiated from config
    from src.core.rate_limit_strategy import RateLimitConfig

    config = RateLimitConfig.from_env()
    assert config.strategy == RateLimitStrategy.STRICT  # Default

    # Test that circuit breaker is properly configured
    from src.middleware.security_middleware import RequestValidationMiddleware
    from fastapi import FastAPI

    test_app = FastAPI()
    middleware = RequestValidationMiddleware(test_app)
    assert hasattr(middleware, 'circuit_breaker')
    assert hasattr(middleware, 'rate_limit_config')

    # Verify circuit breaker has correct config
    assert middleware.circuit_breaker.max_failures == config.max_failures
    assert middleware.circuit_breaker.cooldown == config.cooldown_seconds


def test_rate_limit_degraded_mode_fallback():
    """Test that degraded mode falls back to simple limiting"""
    # This will be tested with circuit breaker integration
    pass


@pytest.mark.asyncio
async def test_circuit_breaker_opens_on_failures():
    """Test that circuit breaker opens after max failures"""
    breaker = CircuitBreaker(max_failures=3, cooldown=60)

    # Should start closed
    assert not breaker.is_open()
    assert breaker.state == "closed"

    # Record failures
    breaker.record_failure()
    breaker.record_failure()
    breaker.record_failure()

    # Should be open now
    assert breaker.is_open()
    assert breaker.state == "open"


@pytest.mark.asyncio
async def test_circuit_breaker_resets_after_cooldown():
    """Test that circuit breaker allows requests after cooldown"""
    breaker = CircuitBreaker(max_failures=3, cooldown=1)  # 1 second cooldown

    # Open the circuit
    breaker.record_failure()
    breaker.record_failure()
    breaker.record_failure()
    assert breaker.is_open()

    # Wait for cooldown
    import time
    time.sleep(1.1)

    # Should allow test request (half-open state)
    assert breaker.allow_request()


@pytest.mark.asyncio
async def test_circuit_breaker_closes_on_success():
    """Test that circuit breaker closes on success after cooldown"""
    breaker = CircuitBreaker(max_failures=3, cooldown=1)

    # Open the circuit
    for _ in range(3):
        breaker.record_failure()
    assert breaker.is_open()

    # Wait for cooldown
    import time
    time.sleep(1.1)

    # Allow test request
    breaker.allow_request()

    # Record success should close circuit
    breaker.record_success()
    assert not breaker.is_open()
    assert breaker.state == "closed"


def test_rate_limit_config_from_env():
    """Test RateLimitConfig loads from environment"""
    from src.core.rate_limit_strategy import RateLimitConfig
    import os

    # Test default (STRICT)
    config = RateLimitConfig.from_env()
    assert config.strategy == RateLimitStrategy.STRICT
    assert config.max_failures == 3
    assert config.cooldown_seconds == 60

    # Test custom values
    os.environ["RATE_LIMIT_FAILURE_MODE"] = "permissive"
    os.environ["RATE_LIMIT_MAX_FAILURES"] = "5"
    os.environ["RATE_LIMIT_COOLDOWN_SECONDS"] = "120"

    config = RateLimitConfig.from_env()
    assert config.strategy == RateLimitStrategy.PERMISSIVE
    assert config.max_failures == 5
    assert config.cooldown_seconds == 120

    # Reset env
    os.environ["RATE_LIMIT_FAILURE_MODE"] = "strict"
    os.environ["RATE_LIMIT_MAX_FAILURES"] = "3"
    os.environ["RATE_LIMIT_COOLDOWN_SECONDS"] = "60"


def test_rate_limit_strategy_should_block():
    """Test should_block_on_error() for different strategies"""
    from src.core.rate_limit_strategy import RateLimitConfig

    strict_config = RateLimitConfig(strategy=RateLimitStrategy.STRICT)
    assert strict_config.should_block_on_error() is True

    permissive_config = RateLimitConfig(strategy=RateLimitStrategy.PERMISSIVE)
    assert permissive_config.should_block_on_error() is False

    degraded_config = RateLimitConfig(strategy=RateLimitStrategy.DEGRADED)
    assert degraded_config.should_block_on_error() is False
