"""
Security Event Logger

Centralized logging system for security-related events including
authentication failures, permission denials, rate limiting, and more.

Uses database for all storage (synchronous operations).
Threshold checking is done via database queries for reliability.

Note: Redis caching will be added in Phase 4 with proper async handling.
"""

import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from src.core.exception_handler import InternalServerError
from src.models.security_event import (
    SecurityEvent,
    SecurityEventType,
    SecuritySeverity,
)

logger = logging.getLogger(__name__)


class SecurityEventLogger:
    """
    Centralized security event logging system.

    Tracks security events in the database for long-term storage,
    auditing, and threshold checking.
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
        db: Session | None = None,
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

    def _get_event_severity(self, event_type: SecurityEventType) -> SecuritySeverity:
        """
        Get severity level for an event type.

        Args:
            event_type: Type of security event

        Returns:
            Severity level
        """
        return self.EVENT_SEVERITY_MAP.get(event_type, SecuritySeverity.MEDIUM)

    def _log_to_database(
        self,
        event_type: SecurityEventType,
        severity: SecuritySeverity,
        user_id: str | None,
        ip: str | None,
        metadata: dict[str, Any],
    ) -> SecurityEvent | None:
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
                # SessionLocal should never be None at runtime
                if SessionLocal is None:
                    raise InternalServerError(
                        "Database not initialized. Call init_database() first."
                    )
                db = SessionLocal()
                should_close = True

            try:
                event = SecurityEvent()
                event.event_type = event_type.value
                event.severity = severity.value
                event.user_id = user_id
                event.ip_address = ip
                event.event_metadata = metadata
                event.created_at = datetime.now()

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
        username: str | None = None,
        reason: str | None = None,
    ) -> SecurityEvent | None:
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
    ) -> SecurityEvent | None:
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
    ) -> SecurityEvent | None:
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
    ) -> SecurityEvent | None:
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
        details: dict[str, Any] | None = None,
    ) -> SecurityEvent | None:
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
    ) -> SecurityEvent | None:
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
        threshold: int | None = None,
    ) -> bool:
        """
        Check if IP address has exceeded alert threshold.

        Uses database query to count events within time window.

        Args:
            ip: IP address to check
            event_type: Type of event to check
            threshold: Custom threshold (uses default if not provided)

        Returns:
            True if alert should be triggered
        """
        threshold = threshold or self.alert_threshold

        try:
            from src.database import SessionLocal

            # Use provided session or create new one
            if self.db is not None:
                db = self.db
                should_close = False
            else:
                # SessionLocal should never be None at runtime
                if SessionLocal is None:
                    raise InternalServerError(
                        "Database not initialized. Call init_database() first."
                    )
                db = SessionLocal()
                should_close = True

            try:
                # Calculate time window
                window_start = datetime.now() - timedelta(
                    minutes=self.alert_window_minutes
                )

                # Query events within window for this IP and event type
                count = (
                    db.query(SecurityEvent)
                    .filter(
                        SecurityEvent.ip_address == ip,
                        SecurityEvent.event_type == event_type.value,
                        SecurityEvent.created_at >= window_start,
                    )
                    .count()
                )

                return count >= threshold

            finally:
                if should_close:
                    db.close()

        except Exception as e:
            logger.error(f"Failed to check alert threshold: {e}")
            return False

    def get_event_count(
        self,
        ip: str,
        event_type: SecurityEventType = SecurityEventType.AUTH_FAILURE,
    ) -> int:
        """
        Get event count for specific IP and event type within time window.

        Args:
            ip: IP address
            event_type: Type of event

        Returns:
            Event count
        """
        try:
            from src.database import SessionLocal

            # Use provided session or create new one
            if self.db is not None:
                db = self.db
                should_close = False
            else:
                # SessionLocal should never be None at runtime
                if SessionLocal is None:
                    raise InternalServerError(
                        "Database not initialized. Call init_database() first."
                    )
                db = SessionLocal()
                should_close = True

            try:
                # Calculate time window
                window_start = datetime.now() - timedelta(
                    minutes=self.alert_window_minutes
                )

                # Query events within window for this IP and event type
                count = (
                    db.query(SecurityEvent)
                    .filter(
                        SecurityEvent.ip_address == ip,
                        SecurityEvent.event_type == event_type.value,
                        SecurityEvent.created_at >= window_start,
                    )
                    .count()
                )

                return count

            finally:
                if should_close:
                    db.close()

        except Exception as e:
            logger.error(f"Failed to get event count: {e}")
            return 0


# Global instance
security_event_logger = SecurityEventLogger()
