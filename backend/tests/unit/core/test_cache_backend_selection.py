"""Cache backend selection must honor explicitly enabled Redis."""

from __future__ import annotations

import pytest

from src.core import cache_manager as cache_module
from src.core.exception_handler import ConfigurationError


def test_enabled_redis_connection_failure_is_not_downgraded_to_memory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An explicit Redis configuration is a runtime requirement, not a hint."""

    monkeypatch.setattr(cache_module.settings, "REDIS_ENABLED", True)
    monkeypatch.setattr(cache_module.settings, "REDIS_HOST", "127.0.0.1")
    monkeypatch.setattr(cache_module.settings, "REDIS_PORT", 16379)
    monkeypatch.setattr(cache_module.settings, "REDIS_DB", 0)
    monkeypatch.setattr(cache_module.settings, "REDIS_PASSWORD", None)

    def fail_to_connect(**_: object) -> cache_module.RedisCache:
        raise ConnectionError("redis unavailable")

    monkeypatch.setattr(cache_module, "RedisCache", fail_to_connect)

    with pytest.raises(ConfigurationError, match="Redis 已启用但连接失败") as exc_info:
        cache_module._create_default_backend()

    assert exc_info.value.details == {
        "config_key": "REDIS_ENABLED",
        "host": "127.0.0.1",
        "port": 16379,
        "db": 0,
    }


def test_disabled_redis_uses_process_local_memory_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cache_module.settings, "REDIS_ENABLED", False)

    backend = cache_module._create_default_backend()

    assert isinstance(backend, cache_module.MemoryCache)
