"""Startup cache warmup for low-churn datasets."""

import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from .organization.service import organization_service
from .system_dictionary.service import system_dictionary_service

logger = logging.getLogger(__name__)


WarmupTask = Callable[[], Awaitable[Any]]


class CacheWarmupService:
    """Preload selected cache keys to reduce first-request latency."""

    def _build_tasks(self, db: AsyncSession) -> list[tuple[str, WarmupTask]]:
        return [
            (
                "system_dictionary.types",
                lambda: system_dictionary_service.get_types_async(db),
            ),
            (
                "organization.statistics",
                lambda: organization_service.get_statistics(db),
            ),
        ]

    @staticmethod
    def _estimate_size(value: Any) -> int:
        if isinstance(value, dict):
            return len(value)
        if isinstance(value, (list, tuple, set, str)):
            return len(value)
        if value is None:
            return 0
        return 1

    async def warmup_low_churn_data(self, db: AsyncSession) -> dict[str, Any]:
        """Warmup dictionary and organization cache entries, best effort."""
        started_at = datetime.now(UTC)
        success_count = 0
        failure_count = 0
        items: dict[str, dict[str, Any]] = {}

        for task_name, task in self._build_tasks(db):
            try:
                result = await task()
                items[task_name] = {
                    "status": "success",
                    "size": self._estimate_size(result),
                }
                success_count += 1
            except Exception as exc:
                logger.warning("Cache warmup task failed: %s", task_name, exc_info=True)
                items[task_name] = {
                    "status": "failed",
                    "error": str(exc),
                }
                failure_count += 1

        finished_at = datetime.now(UTC)
        duration_ms = int((finished_at - started_at).total_seconds() * 1000)

        return {
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "duration_ms": duration_ms,
            "success_count": success_count,
            "failure_count": failure_count,
            "items": items,
        }


cache_warmup_service = CacheWarmupService()
