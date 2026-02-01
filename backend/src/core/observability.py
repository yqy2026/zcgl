"""
Observability helpers (APM / error tracking).
"""

from __future__ import annotations

import logging
from typing import Any

from .config import settings

logger = logging.getLogger(__name__)

_sentry_initialized = False


def init_sentry() -> bool:
    """Initialize Sentry SDK if enabled and configured."""
    global _sentry_initialized
    if _sentry_initialized:
        return True

    if not settings.SENTRY_ENABLED or not settings.SENTRY_DSN:
        logger.info("Sentry disabled or DSN missing; skipping initialization")
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        logging_integration = LoggingIntegration(
            level=logging.INFO,
            event_level=logging.ERROR,
        )

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.SENTRY_ENVIRONMENT or settings.ENVIRONMENT,
            traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
            profiles_sample_rate=settings.SENTRY_PROFILES_SAMPLE_RATE,
            release=settings.APP_VERSION,
            send_default_pii=settings.SENTRY_SEND_DEFAULT_PII,
            integrations=[
                FastApiIntegration(),
                SqlalchemyIntegration(),
                logging_integration,
            ],
        )

        _sentry_initialized = True
        logger.info("Sentry initialized")
        return True

    except Exception as exc:  # pragma: no cover - optional dependency
        logger.warning(f"Sentry initialization failed: {exc}")
        return False


def send_security_alert(alert_type: str, severity: str, **context: Any) -> bool:
    """Send security alert to Sentry if available."""
    if not init_sentry():
        return False

    try:
        import sentry_sdk

        sentry_sdk.capture_message(
            f"Security Alert: {alert_type}",
            level=severity.lower(),
            extra=context,
        )
        return True

    except Exception as exc:  # pragma: no cover - optional dependency
        logger.warning(f"Failed to send security alert: {exc}")
        return False
