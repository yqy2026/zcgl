"""
Security audit and audit trail loggers.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .logging_filters import SensitiveDataFilter, SecurityLogFormatter


class SecurityAuditor:
    """安全审计器"""

    def __init__(self) -> None:
        self.security_log_file = "logs/security.log"
        self.enabled = True
        self._setup_security_logger()
        self.sensitive_filter = SensitiveDataFilter()

    def _setup_security_logger(self) -> None:
        """设置安全日志记录器"""
        self.logger = logging.getLogger("security_audit")
        self.logger.setLevel(logging.INFO)

        if not self.logger.handlers:
            log_dir = Path(self.security_log_file).parent
            log_dir.mkdir(parents=True, exist_ok=True)

            file_handler = logging.FileHandler(self.security_log_file)
            formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
            file_handler.setFormatter(formatter)
            file_handler.addFilter(SensitiveDataFilter())

            self.logger.addHandler(file_handler)

    def log_security_event(
        self,
        event_type: str,
        message: str,
        **kwargs: Any,
    ) -> None:
        """记录安全事件"""
        if not self.enabled:
            return

        log_entry = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "message": message,
            "timestamp": datetime.now(UTC).isoformat(),
            **kwargs,
        }

        filtered_entry = self.sensitive_filter.filter_dict(log_entry)
        self.logger.info(json.dumps(filtered_entry, ensure_ascii=False))


class AuditTrailLogger:
    """审计日志记录器"""

    def __init__(self) -> None:
        self.logger = logging.getLogger("audit_trail")
        self.logger.setLevel(logging.INFO)

        if not self.logger.handlers:
            log_file = "logs/audit.log"
            log_dir = Path(log_file).parent
            log_dir.mkdir(parents=True, exist_ok=True)

            handler = logging.FileHandler(log_file)
            handler.setFormatter(SecurityLogFormatter())
            handler.addFilter(SensitiveDataFilter())
            self.logger.addHandler(handler)

    def log_audit(self, action: str, **kwargs: Any) -> None:
        if not self.logger.isEnabledFor(logging.INFO):
            return

        log_data = {
            "action": action,
            "timestamp": datetime.now(UTC).isoformat(),
            **kwargs,
        }

        filtered_data = SensitiveDataFilter().filter_dict(log_data)
        self.logger.info(json.dumps(filtered_data, ensure_ascii=False))
