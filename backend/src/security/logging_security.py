"""
Security logging facade.
Provides sensitive data filtering, structured logging, and audit helpers.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..core.config import settings
from .logging_audit import AuditTrailLogger, SecurityAuditor
from .logging_filters import SecurityLogFormatter, SensitiveDataFilter
from .logging_metrics import SecurityMetrics, SecurityMonitor
from .logging_request import RequestLogger
from .logging_structured import StructuredSecurityLogger

security_monitor = SecurityMonitor()
security_auditor: SecurityAuditor = SecurityAuditor()
request_logger: RequestLogger = RequestLogger()


def setup_logging_security() -> logging.Logger:
    """设置日志安全"""
    log_level = settings.LOG_LEVEL
    log_file = settings.LOG_FILE or "logs/app.log"

    log_dir = Path(log_file).parent
    log_dir.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
    )

    for handler in logging.getLogger().handlers:
        handler.addFilter(SensitiveDataFilter())

    logger = logging.getLogger(__name__)
    logger.info("日志安全设置完成")

    return logger


def log_security_event(event_type: str, message: str, **kwargs: Any) -> None:
    """记录安全事件的便捷函数"""
    security_auditor.log_security_event(event_type, message, **kwargs)


def log_request_info(**kwargs: Any) -> None:
    """记录请求信息的便捷函数"""
    request_logger.log_request(**kwargs)


def get_request_context() -> dict[str, str]:
    """获取请求上下文"""
    return {"request_id": str(uuid.uuid4()), "timestamp": datetime.now(UTC).isoformat()}


__all__ = [
    "SensitiveDataFilter",
    "SecurityLogFormatter",
    "SecurityAuditor",
    "AuditTrailLogger",
    "RequestLogger",
    "StructuredSecurityLogger",
    "SecurityMetrics",
    "SecurityMonitor",
    "security_monitor",
    "security_auditor",
    "request_logger",
    "setup_logging_security",
    "log_security_event",
    "log_request_info",
    "get_request_context",
]


if __name__ == "__main__":
    setup_logging_security()

    logger = logging.getLogger(__name__)
    logger.info("测试敏感数据过滤: password=secret123, email=user@example.com")

    log_security_event(
        "TEST_EVENT", "测试安全事件", user_id="user123", ip_address="192.168.1.1"
    )

    log_request_info(
        method="POST",
        path="/api/v1/login",
        status_code=200,
        response_time=0.1,
        user_id="user123",
        ip_address="192.168.1.1",
    )
