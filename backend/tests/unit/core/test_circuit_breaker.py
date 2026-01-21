import time

from src.core.circuit_breaker import CircuitBreaker, CircuitState


def test_circuit_breaker_initially_closed():
    """Test that circuit breaker starts in closed state"""
    cb = CircuitBreaker(max_failures=3, cooldown=60)
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0


def test_circuit_breaker_opens_after_max_failures():
    """Test that circuit breaker opens after max failures"""
    cb = CircuitBreaker(max_failures=3, cooldown=60)
    for _ in range(3):
        cb.record_failure()
    assert cb.state == CircuitState.OPEN
    assert cb.is_open() is True


def test_circuit_breaker_blocks_when_open():
    """Test that requests are blocked when circuit is open"""
    cb = CircuitBreaker(max_failures=3, cooldown=1)
    for _ in range(3):
        cb.record_failure()
    assert cb.allow_request() is False


def test_circuit_breaker_resets_after_cooldown():
    """Test that circuit breaker resets after cooldown period"""
    cb = CircuitBreaker(max_failures=3, cooldown=1)
    for _ in range(3):
        cb.record_failure()
    assert cb.is_open() is True
    time.sleep(1.1)
    assert cb.allow_request() is True  # Should reset to half-open
    assert cb.state == CircuitState.HALF_OPEN


def test_circuit_breaker_closes_on_success():
    """Test that circuit breaker closes on successful request"""
    cb = CircuitBreaker(max_failures=3, cooldown=1)
    for _ in range(3):
        cb.record_failure()
    assert cb.state == CircuitState.OPEN
    time.sleep(1.1)  # Wait for cooldown to pass
    cb.allow_request()  # Transition to half-open
    cb.record_success()
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0
