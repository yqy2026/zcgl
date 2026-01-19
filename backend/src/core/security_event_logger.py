"""
Security Event Logger

Centralized logging system for security-related events including
authentication failures, permission denials, rate limiting, and more.

Uses Redis for fast threshold checking and database for long-term storage.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from src.models.security_event import (
    SecurityEvent,
    SecurityEventType,
    SecuritySeverity,
)
from src.utils.cache_manager import cache_manager

logger = logging.getLogger(__name__)


class SecurityEventLogger:
    """
    Centralized security event logging system.

    Tracks security events in both Redis (for fast threshold checking)
    and database (for long-term storage and auditing).
    """

    # Default configuration
    DEFAULT_ALERT_THRESHOLD = 5  # events per window
    DEFAULT_ALERT_WINDOW_MINUTES = 10  # minutes

    # Severity mapping for event types
    EVENT_SEVERITY_MAP = {
        SecurityEventType.AUTH_FAILURE: SecuritySeverity.MEDIUM,
        SecurityEventType.AUTH_SUCCESS: SecuritySeverity.LOW,
        SecurityEventType.PERMISSION_DENIED: SecuritySeverity.MEDIUM,
        SecurityEventType.RATE_LIMIT_EXCEEDED: SecuritySeverity.HIGH,
        SecurityEventType.SUSPICIOUS_ACTIVITY: SecuritySeverity.HIGH,
        SecurityEventType.ACCOUNT_LOCKED: SecuritySeverity.CRITICAL,
    }

    def __init__(
        self,
        db: Optional[Session] = None,
        alert_threshold: int = DEFAULT_ALERT_THRESHOLD,
        alert_window_minutes: int = DEFAULT_ALERT_WINDOW_MINUTES,
    ):
        """
        Initialize the security event logger.

        Args:
            db: Optional database session. If None, creates new session per operation.
            alert_threshold: Number of events before triggering alert
            alert_window_minutes: Time window in minutes for threshold checking
        """
        self.db = db
        self.alert_threshold = alert_threshold
        self.alert_window_minutes = alert_window_minutes

    def _get_redis_key(self, event_type: str, ip: str) -> str:
        """
        Generate Redis key for event tracking.

        Args:
            event_type: Type of security event
            ip: IP address

        Returns:
            Redis key string
        """
        return f"security_events:{event_type}:{ip}"

    def _get_event_severity(self, event_type: SecurityEventType) -> SecuritySeverity:
        """
        Get severity level for an event type.

        Args:
            event_type: Type of security event

        Returns:
            Severity level
        """
        return self.EVENT_SEVERITY_MAP.get(
            event_type, SecuritySeverity.MEDIUM
        )

    def _log_to_redis(
        self,
        event_type: SecurityEventType,
        ip: str,
        metadata: dict[str, Any],
    ) -> bool:
        """
        Log event to Redis for fast threshold checking.

        Args:
            event_type: Type of security event
            ip: IP address
            metadata: Event metadata

        Returns:
            True if successful, False otherwise
        """
        try:
            key = self._get_redis_key(event_type.value, ip)

            # Get current count - use synchronous approach
            try:
                # Try to get existing data
                current_data = cache_manager.get("security_events", key)
                if asyncio.iscoroutine(current_data):
                    # It's a coroutine, skip for now (can't await in sync context)
                    return False
            except TypeError:
                # cache_manager.get might be async, skip Redis update
                return False

            if current_data is None:
                current_data = {"count": 0, "events": []}

            # Increment count and add event
            current_data["count"] += 1
            current_data["events"].append({
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata,
            })

            # Keep only recent events (within window)
            expire_seconds = self.alert_window_minutes * 60

            try:
                result = cache_manager.set(
                    "security_events",
                    key,
                    current_data,
                    expire=expire_seconds
                )
                if asyncio.iscoroutine(result):
                    # It's a coroutine, skip
                    return False
                return True
            except TypeError:
                return False

        except Exception as e:
            logger.error(f"Failed to log security event to Redis: {e}")
            return False

    def _log_to_database(
        self,
        event_type: SecurityEventType,
        severity: SecuritySeverity,
        user_id: Optional[str],
        ip: Optional[str],
        metadata: dict[str, Any],
    ) -> Optional[SecurityEvent]:
        """
        Log event to database for long-term storage.

        Args:
            event_type: Type of security event
            severity: Severity level
            user_id: User ID if applicable
            ip: IP address
            metadata: Event metadata

        Returns:
            Created SecurityEvent object or None if failed
        """
        try:
            from src.database import SessionLocal

            # Use provided session or create new one
            if self.db is not None:
                db = self.db
                should_close = False
            else:
                db: Session = SessionLocal()
                should_close = True

            try:
                event = SecurityEvent(
                    event_type=event_type.value,
                    severity=severity.value,
                    user_id=user_id,
                    ip_address=ip,
                    event_metadata=metadata,
                    created_at=datetime.now(),
                )

                db.add(event)
                db.commit()
                db.refresh(event)

                return event

            except Exception as e:
                db.rollback()
                logger.error(f"Failed to commit security event to database: {e}")
                return None

            finally:
                if should_close:
                    db.close()

        except Exception as e:
            logger.error(f"Failed to create database session for security event: {e}")
            return None

    def log_auth_failure(
        self,
        ip: str,
        username: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> Optional[SecurityEvent]:
        """
        Log authentication failure event.

        Args:
            ip: IP address of the request
            username: Username if provided
            reason: Reason for failure

        Returns:
            Created SecurityEvent object
        """
        event_type = SecurityEventType.AUTH_FAILURE
        severity = self._get_event_severity(event_type)

        metadata = {
            "username": username,
            "reason": reason,
        }

        # Log to Redis for fast threshold checking
        self._log_to_redis(event_type, ip, metadata)

        # Log to database for long-term storage
        return self._log_to_database(
            event_type=event_type,
            severity=severity,
            user_id=username,  # Use username as user_id for auth events
            ip=ip,
            metadata=metadata,
        )

    def log_auth_success(
        self,
        ip: str,
        username: str,
    ) -> Optional[SecurityEvent]:
        """
        Log authentication success event.

        Args:
            ip: IP address of the request
            username: Username

        Returns:
            Created SecurityEvent object
        """
        event_type = SecurityEventType.AUTH_SUCCESS
        severity = self._get_event_severity(event_type)

        metadata = {
            "username": username,
        }

        # Log to Redis
        self._log_to_redis(event_type, ip, metadata)

        # Log to database
        return self._log_to_database(
            event_type=event_type,
            severity=severity,
            user_id=username,
            ip=ip,
            metadata=metadata,
        )

    def log_permission_denied(
        self,
        user_id: str,
        resource: str,
        action: str,
        ip: str,
    ) -> Optional[SecurityEvent]:
        """
        Log permission denied event.

        Args:
            user_id: User ID
            resource: Resource being accessed
            action: Action being attempted
            ip: IP address

        Returns:
            Created SecurityEvent object
        """
        event_type = SecurityEventType.PERMISSION_DENIED
        severity = self._get_event_severity(event_type)

        metadata = {
            "resource": resource,
            "action": action,
        }

        # Log to Redis
        self._log_to_redis(event_type, ip, metadata)

        # Log to database
        return self._log_to_database(
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            ip=ip,
            metadata=metadata,
        )

    def log_rate_limit_exceeded(
        self,
        ip: str,
        endpoint: str,
    ) -> Optional[SecurityEvent]:
        """
        Log rate limit exceeded event.

        Args:
            ip: IP address
            endpoint: API endpoint being accessed

        Returns:
            Created SecurityEvent object
        """
        event_type = SecurityEventType.RATE_LIMIT_EXCEEDED
        severity = self._get_event_severity(event_type)

        metadata = {
            "endpoint": endpoint,
        }

        # Log to Redis
        self._log_to_redis(event_type, ip, metadata)

        # Log to database (no user_id for rate limiting)
        return self._log_to_database(
            event_type=event_type,
            severity=severity,
            user_id=None,
            ip=ip,
            metadata=metadata,
        )

    def log_suspicious_activity(
        self,
        ip: str,
        activity_type: str,
        details: Optional[dict[str, Any]] = None,
    ) -> Optional[SecurityEvent]:
        """
        Log suspicious activity event.

        Args:
            ip: IP address
            activity_type: Type of suspicious activity
            details: Additional details

        Returns:
            Created SecurityEvent object
        """
        event_type = SecurityEventType.SUSPICIOUS_ACTIVITY
        severity = self._get_event_severity(event_type)

        metadata = {
            "activity_type": activity_type,
            "details": details or {},
        }

        # Log to Redis
        self._log_to_redis(event_type, ip, metadata)

        # Log to database
        return self._log_to_database(
            event_type=event_type,
            severity=severity,
            user_id=None,
            ip=ip,
            metadata=metadata,
        )

    def log_account_locked(
        self,
        username: str,
        ip: str,
        reason: str,
    ) -> Optional[SecurityEvent]:
        """
        Log account locked event.

        Args:
            username: Username
            ip: IP address
            reason: Reason for locking

        Returns:
            Created SecurityEvent object
        """
        event_type = SecurityEventType.ACCOUNT_LOCKED
        severity = self._get_event_severity(event_type)

        metadata = {
            "username": username,
            "reason": reason,
        }

        # Log to Redis
        self._log_to_redis(event_type, ip, metadata)

        # Log to database
        return self._log_to_database(
            event_type=event_type,
            severity=severity,
            user_id=username,
            ip=ip,
            metadata=metadata,
        )

    def should_alert(
        self,
        ip: str,
        event_type: SecurityEventType = SecurityEventType.AUTH_FAILURE,
        threshold: Optional[int] = None,
    ) -> bool:
        """
        Check if IP address has exceeded alert threshold.

        Args:
            ip: IP address to check
            event_type: Type of event to check
            threshold: Custom threshold (uses default if not provided)

        Returns:
            True if alert should be triggered
        """
        threshold = threshold or self.alert_threshold

        try:
            key = self._get_redis_key(event_type.value, ip)

            try:
                data = cache_manager.get("security_events", key)
                if asyncio.iscoroutine(data):
                    # It's a coroutine, can't check threshold without async context
                    return False
            except TypeError:
                return False

            if data is None:
                return False

            count = data.get("count", 0)
            return count >= threshold

        except Exception as e:
            logger.error(f"Failed to check alert threshold: {e}")
            return False

    def get_event_count(
        self,
        ip: str,
        event_type: SecurityEventType = SecurityEventType.AUTH_FAILURE,
    ) -> int:
        """
        Get event count for specific IP and event type.

        Args:
            ip: IP address
            event_type: Type of event

        Returns:
            Event count
        """
        try:
            key = self._get_redis_key(event_type.value, ip)

            try:
                data = cache_manager.get("security_events", key)
                if asyncio.iscoroutine(data):
                    # It's a coroutine, can't get count without async context
                    return 0
            except TypeError:
                return 0

            if data is None:
                return 0

            return data.get("count", 0)

        except Exception as e:
            logger.error(f"Failed to get event count: {e}")
            return 0


# Global instance
security_event_logger = SecurityEventLogger()
