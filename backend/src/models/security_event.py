"""
Security Event Model

Tracks security-related events including authentication failures,
permission denials, rate limiting, and other security events.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import JSON, DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class SecurityEventType(str, Enum):
    """Security event types"""

    AUTH_FAILURE = "auth_failure"
    AUTH_SUCCESS = "auth_success"
    PERMISSION_DENIED = "permission_denied"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    ACCOUNT_LOCKED = "account_locked"


class SecuritySeverity(str, Enum):
    """Security event severity levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityEvent(Base):
    """Security event model for tracking security-related events"""

    __tablename__ = "security_events"

    # Primary key
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # Event information
    event_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True, comment="Event type"
    )
    severity: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="Severity level"
    )

    # User information (nullable for events without user context)
    user_id: Mapped[str | None] = mapped_column(
        String, nullable=True, index=True, comment="User ID if applicable"
    )

    # Network information
    ip_address: Mapped[str | None] = mapped_column(
        String(45), nullable=True, index=True, comment="IP address (IPv4 or IPv6)"
    )

    # Event metadata (mapped to 'metadata' column in DB)
    event_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSON, comment="Event metadata (JSON)"
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.now,
        index=True,
        comment="Event timestamp",
    )

    # Table indexes for querying
    __table_args__ = (
        Index("ix_security_events_event_type_created_at", "event_type", "created_at"),
        Index("ix_security_events_user_id_created_at", "user_id", "created_at"),
        Index("ix_security_events_ip_created_at", "ip_address", "created_at"),
        Index("ix_security_events_severity_created_at", "severity", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<SecurityEvent(id={self.id}, type={self.event_type}, "
            f"severity={self.severity}, ip={self.ip_address})>"
        )
