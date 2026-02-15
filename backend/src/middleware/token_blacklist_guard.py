"""Token blacklist guard utilities for auth middleware."""

from __future__ import annotations

import logging
from collections import deque
from collections.abc import Callable
from time import time

from ..constants.security_constants import (
    TOKEN_BLACKLIST_DEGRADE_THRESHOLD,
    TOKEN_BLACKLIST_DEGRADE_WINDOW_SECONDS,
    TOKEN_BLACKLIST_ERROR_THRESHOLD,
    TOKEN_BLACKLIST_ERROR_WINDOW_SECONDS,
)
from ..core.circuit_breaker import CircuitBreaker
from ..core.config import settings
from ..security.logging_security import security_monitor

logger = logging.getLogger(__name__)


class TokenBlacklistGuard:
    """Encapsulates blacklist degradation/error tracking with circuit protection."""

    def __init__(self, *, is_production: Callable[[], bool]) -> None:
        self._is_production = is_production
        self._degrade_events: deque[float] = deque(maxlen=100)
        self._error_events: deque[float] = deque(maxlen=100)
        self._last_degrade_alert_ts = 0.0
        self._last_error_alert_ts = 0.0
        self.circuit = CircuitBreaker(max_failures=5, cooldown=60)

    @staticmethod
    def _trim_recent_events(events: deque[float], window_seconds: int, now: float) -> int:
        while events and now - events[0] > window_seconds:
            events.popleft()
        return len(events)

    def _record_degraded(
        self, reason: str, jti: str | None, user_id: str | None
    ) -> None:
        now = time()
        self._degrade_events.append(now)
        recent = self._trim_recent_events(
            self._degrade_events,
            TOKEN_BLACKLIST_DEGRADE_WINDOW_SECONDS,
            now,
        )

        security_monitor.record_metric("token_blacklist.degraded", 1)
        security_monitor.record_event(
            "token_blacklist_degraded",
            reason=reason,
            jti=jti,
            user_id=user_id,
            recent_count=recent,
            window_seconds=TOKEN_BLACKLIST_DEGRADE_WINDOW_SECONDS,
        )
        if self._is_production():
            security_monitor.record_audit(
                "token_blacklist_degraded",
                reason=reason,
                jti=jti,
                user_id=user_id,
            )

        if (
            recent >= TOKEN_BLACKLIST_DEGRADE_THRESHOLD
            and now - self._last_degrade_alert_ts
            >= TOKEN_BLACKLIST_DEGRADE_WINDOW_SECONDS
        ):
            self._last_degrade_alert_ts = now
            logger.warning("Token blacklist degraded frequently in the last window.")
            security_monitor.record_event(
                "token_blacklist_degraded_frequent",
                count=recent,
                window_seconds=TOKEN_BLACKLIST_DEGRADE_WINDOW_SECONDS,
            )

    def _record_error(self, error: Exception, jti: str | None, user_id: str | None) -> None:
        now = time()
        self._error_events.append(now)
        recent = self._trim_recent_events(
            self._error_events,
            TOKEN_BLACKLIST_ERROR_WINDOW_SECONDS,
            now,
        )

        security_monitor.record_metric("token_blacklist.error", 1)
        security_monitor.record_event(
            "token_blacklist_error",
            error=str(error),
            jti=jti,
            user_id=user_id,
            recent_count=recent,
            window_seconds=TOKEN_BLACKLIST_ERROR_WINDOW_SECONDS,
        )

        if (
            recent >= TOKEN_BLACKLIST_ERROR_THRESHOLD
            and now - self._last_error_alert_ts >= TOKEN_BLACKLIST_ERROR_WINDOW_SECONDS
        ):
            self._last_error_alert_ts = now
            logger.warning("Token blacklist errors are frequent in the last window.")
            security_monitor.record_event(
                "token_blacklist_error_frequent",
                count=recent,
                window_seconds=TOKEN_BLACKLIST_ERROR_WINDOW_SECONDS,
            )

    def is_token_blacklisted(
        self, jti: str | None, user_id: str | None = None, session_id: str | None = None
    ) -> bool:
        """Check whether token is blacklisted (fail-closed on circuit/error)."""
        if not settings.TOKEN_BLACKLIST_ENABLED:
            return False

        if jti is None and user_id is None and session_id is None:
            return False

        if not self.circuit.allow_request():
            logger.error(
                "Token blacklist check degraded. Enforcing fail-closed in all environments."
            )
            self._record_degraded("circuit_open", jti, user_id)
            return True

        try:
            from ..security.token_blacklist import blacklist_manager

            result = blacklist_manager.is_blacklisted(jti=jti, user_id=user_id)
            self.circuit.record_success()
            return result
        except ImportError:
            logger.debug(f"Token blacklist not implemented, allowing token {jti}")
            self._record_degraded("not_implemented", jti, user_id)
            self.circuit.record_success()
            return False
        except Exception as error:
            self.circuit.record_failure()
            logger.warning(f"Error checking token blacklist: {error}")
            self._record_error(error, jti, user_id)
            return True
