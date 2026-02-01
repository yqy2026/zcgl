"""
Structured security logger.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .logging_filters import SecurityLogFormatter, SensitiveDataFilter


class StructuredSecurityLogger:
    """结构化安全日志记录器"""

    def __init__(self, name: str = "structured_security") -> None:
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        if not self.logger.handlers:
            log_file = "logs/security_structured.log"
            log_dir = Path(log_file).parent
            log_dir.mkdir(parents=True, exist_ok=True)

            handler = logging.FileHandler(log_file)
            handler.setFormatter(SecurityLogFormatter())
            handler.addFilter(SensitiveDataFilter())
            self.logger.addHandler(handler)

    def log_event(self, event_type: str, **kwargs: Any) -> None:
        if not self.logger.isEnabledFor(logging.INFO):
            return

        log_data = {
            "event_type": event_type,
            "timestamp": datetime.now(UTC).isoformat(),
            **kwargs,
        }

        filtered_data = SensitiveDataFilter().filter_dict(log_data)
        self.logger.info(json.dumps(filtered_data, ensure_ascii=False))
