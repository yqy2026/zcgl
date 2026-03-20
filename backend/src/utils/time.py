"""Shared time utilities."""

from datetime import UTC, datetime


def utcnow_naive() -> datetime:
    """返回 UTC 当前时间（naive，无 tzinfo）。"""
    return datetime.now(UTC).replace(tzinfo=None)
