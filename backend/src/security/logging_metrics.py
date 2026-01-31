"""
Security metrics and monitoring utilities.
"""

from __future__ import annotations

from collections import defaultdict
from threading import Lock
from typing import Any

from .logging_audit import AuditTrailLogger
from .logging_structured import StructuredSecurityLogger


class SecurityMetrics:
    """安全指标记录器"""

    def __init__(self) -> None:
        self.metrics: dict[str, list[float]] = defaultdict(list)
        self.lock = Lock()

    def record_metric(self, name: str, value: float) -> None:
        with self.lock:
            self.metrics[name].append(value)

    def get_metrics(self) -> dict[str, dict[str, float]]:
        with self.lock:
            result: dict[str, dict[str, float]] = {}
            for name, values in self.metrics.items():
                if not values:
                    continue
                result[name] = {
                    "min": min(values),
                    "max": max(values),
                    "avg": sum(values) / len(values),
                    "count": len(values),
                }
            return result


class SecurityMonitor:
    """安全监控器"""

    def __init__(self) -> None:
        self.structured_logger = StructuredSecurityLogger()
        self.audit_logger = AuditTrailLogger()
        self.metrics = SecurityMetrics()

    def record_event(self, event_type: str, **kwargs: Any) -> None:
        self.structured_logger.log_event(event_type, **kwargs)

    def record_audit(self, action: str, **kwargs: Any) -> None:
        self.audit_logger.log_audit(action, **kwargs)

    def record_metric(self, name: str, value: float) -> None:
        self.metrics.record_metric(name, value)

    def get_metrics(self) -> dict[str, dict[str, float]]:
        return self.metrics.get_metrics()
