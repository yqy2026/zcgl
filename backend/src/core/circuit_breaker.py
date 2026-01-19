import time
from dataclasses import dataclass
from enum import Enum


class CircuitState(str, Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, block requests
    HALF_OPEN = "half_open"  # Testing if system recovered

@dataclass
class CircuitBreaker:
    """Circuit breaker for fail-closed rate limiting"""
    max_failures: int = 3
    cooldown: int = 60  # seconds
    _state: CircuitState = CircuitState.CLOSED
    _failure_count: int = 0
    _last_failure_time: float = 0.0

    @property
    def state(self) -> CircuitState:
        """Get current circuit state"""
        return self._state

    @property
    def failure_count(self) -> int:
        """Get current failure count"""
        return self._failure_count

    def record_failure(self) -> None:
        """Record a failure and potentially open circuit"""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._failure_count >= self.max_failures:
            self._state = CircuitState.OPEN

    def record_success(self) -> None:
        """Record a success and close circuit if half-open"""
        self._failure_count = 0
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.CLOSED

    def is_open(self) -> bool:
        """Check if circuit is currently open"""
        return self._state == CircuitState.OPEN

    def allow_request(self) -> bool:
        """Check if request should be allowed"""
        if self._state == CircuitState.CLOSED:
            return True

        if self._state == CircuitState.OPEN:
            # Check if cooldown period has passed
            if time.time() - self._last_failure_time > self.cooldown:
                self._state = CircuitState.HALF_OPEN
                return True
            return False

        # HALF_OPEN state - allow test request
        return True
