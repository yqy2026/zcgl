from typing import Any

import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta

from ...core.config import settings  # noqa: F401
from ...database import SessionLocal
from ...models.auth import AuditLog


class EnhancedAuditLogger:
    """Enhanced audit logging service."""

    def __init__(self):
        self.logger = logging.getLogger("audit")
        self.session = SessionLocal()
        # In-memory monitoring data
        self.security_events = defaultdict(list)
        self.user_activity = defaultdict(list)

    def log_security_event(
        self,
        user_id: str | None,
        username: str | None,
        user_role: str | None,
        action: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
        resource_name: str | None = None,
        api_endpoint: str | None = None,
        http_method: str | None = None,
        request_params: str | None = None,
        request_body: str | None = None,
        response_status: int | None = None,
        response_message: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        session_id: str | None = None,
        additional_data: dict[str, Any] | None = None,
    ) -> AuditLog | None:
        """Record a security event and persist audit log."""
        try:
            audit_log = AuditLog(
                user_id=user_id or "",
                username=username or "anonymous",
                user_role=user_role or "",
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_name=resource_name,
                api_endpoint=api_endpoint,
                http_method=http_method,
                request_params=request_params,
                request_body=request_body,
                response_status=response_status,
                response_message=response_message,
                ip_address=ip_address,
                user_agent=user_agent,
                session_id=session_id,
            )

            self.session.add(audit_log)
            self.session.commit()
            self.session.refresh(audit_log)

            log_data = {
                "timestamp": datetime.now().isoformat(),
                "user_id": user_id,
                "username": username,
                "action": action,
                "resource_type": resource_type,
                "api_endpoint": api_endpoint,
                "http_method": http_method,
                "ip_address": ip_address,
                "response_status": response_status,
                "additional_data": additional_data,
            }

            self.logger.info(
                f"Security Event: {json.dumps(log_data, ensure_ascii=False)}"
            )

            event_data = {
                "timestamp": datetime.now(),
                "user_id": user_id,
                "username": username,
                "action": action,
                "ip_address": ip_address,
                "resource_type": resource_type,
            }

            self.security_events[action].append(event_data)
            if user_id:
                self.user_activity[user_id].append(event_data)

            self._cleanup_expired_events()

            return audit_log

        except Exception as e:
            self.logger.error(f"Failed to record security event: {e}")
            self.session.rollback()
            return None

    def _cleanup_expired_events(self):
        """Cleanup in-memory monitoring data older than 24 hours."""
        cutoff_time = datetime.now() - timedelta(hours=24)

        for action in list(self.security_events.keys()):
            self.security_events[action] = [
                event
                for event in self.security_events[action]
                if event["timestamp"] > cutoff_time
            ]
            if not self.security_events[action]:
                del self.security_events[action]

        for user_id in list(self.user_activity.keys()):
            self.user_activity[user_id] = [
                event
                for event in self.user_activity[user_id]
                if event["timestamp"] > cutoff_time
            ]
            if not self.user_activity[user_id]:
                del self.user_activity[user_id]

    def get_user_activity_summary(
        self, user_id: str, hours: int = 24
    ) -> dict[str, Any]:
        """Return summary of recent user activity."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        user_events = [
            event
            for event in self.user_activity.get(user_id, [])
            if event["timestamp"] > cutoff_time
        ]

        action_counts = defaultdict(int)
        for event in user_events:
            action_counts[event["action"]] += 1

        return {
            "user_id": user_id,
            "total_events": len(user_events),
            "time_range_hours": hours,
            "action_counts": dict(action_counts),
            "unique_ips": len(
                set(event["ip_address"] for event in user_events if event["ip_address"])
            ),
            "most_active_resource": self._get_most_active_resource(user_events),
        }

    def _get_most_active_resource(self, events: list[dict]) -> str | None:
        """Return the most active resource type."""
        resource_counts = defaultdict(int)
        for event in events:
            if event["resource_type"]:
                resource_counts[event["resource_type"]] += 1

        if resource_counts:
            return max(resource_counts.items(), key=lambda x: x[1])[0]
        return None

    def detect_suspicious_activity(self, user_id: str) -> list[dict[str, Any]]:
        """Detect suspicious activity patterns for given user."""
        suspicious_events: list[dict[str, Any]] = []
        user_events = self.user_activity.get(user_id, [])

        if not user_events:
            return suspicious_events

        recent_events = [
            event
            for event in user_events
            if event["timestamp"] > datetime.now() - timedelta(minutes=5)
        ]

        if len(recent_events) > 50:
            suspicious_events.append(
                {
                    "type": "high_frequency_activity",
                    "description": (
                        f"User {user_id} performed {len(recent_events)} actions in 5 minutes"
                    ),
                    "severity": "medium",
                    "timestamp": datetime.now(),
                }
            )

__all__ = ["EnhancedAuditLogger"]