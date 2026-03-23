"""ABAC decision cache utilities."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any, Protocol

from ...core.cache_manager import cache_manager

AUTHZ_DECISION_NAMESPACE = "authz_decision"


def compute_roles_hash(role_ids: list[str]) -> str:
    normalized = ",".join(
        sorted({str(role_id) for role_id in role_ids if str(role_id)})
    )
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def build_policy_snapshot_key(user_id: str, roles_hash: str) -> str:
    return f"abac:subject:{user_id}:roles:{roles_hash}:policies"


def build_decision_key(
    *,
    user_id: str,
    resource_type: str,
    resource_id: str | None,
    action: str,
    perspective: str,
    context_hash: str,
) -> str:
    resource_token = resource_id or "-"
    return (
        f"abac:decision:{user_id}:{resource_type}:{resource_token}:"
        f"{action}:{perspective}:{context_hash}"
    )


@dataclass(frozen=True)
class CacheLookupResult:
    value: dict[str, Any] | None
    cache_hit: bool
    layer: str | None = None


@dataclass
class _CacheEntry:
    value: dict[str, Any]
    expires_at: float


class L2CacheBackend(Protocol):
    """Minimal backend contract for L2 cache persistence."""

    def get(self, key: str) -> dict[str, Any] | None: ...

    def set(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None: ...

    def invalidate(self, key_prefix: str | None = None) -> None: ...


class CoreCacheManagerBackend:
    """L2 cache backend adapter using the shared cache manager."""

    def __init__(self, *, namespace: str = AUTHZ_DECISION_NAMESPACE) -> None:
        self._namespace = namespace

    def get(self, key: str) -> dict[str, Any] | None:
        cached = cache_manager.get(key, namespace=self._namespace)
        if isinstance(cached, dict):
            return cached
        return None

    def set(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        cache_manager.set(key, value, ttl=ttl_seconds, namespace=self._namespace)

    def invalidate(self, key_prefix: str | None = None) -> None:
        if key_prefix is None:
            cache_manager.clear(namespace=self._namespace)
            return

        cache_manager.clear(pattern=f"{self._namespace}:{key_prefix}*")


class AuthzDecisionCache:
    """Two-level cache facade (L1 in-process, L2 shared cache backend)."""

    def __init__(
        self,
        *,
        l1_ttl_seconds: int = 5,
        l2_ttl_seconds: int = 300,
        l2_backend: L2CacheBackend | None = None,
    ) -> None:
        self._l1_ttl_seconds = l1_ttl_seconds
        self._l2_ttl_seconds = l2_ttl_seconds
        self._l2_backend = l2_backend or CoreCacheManagerBackend()
        self._l1: dict[str, _CacheEntry] = {}

    @staticmethod
    def hash_context(context: dict[str, Any] | None) -> str:
        normalized = json.dumps(context or {}, ensure_ascii=True, sort_keys=True)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def lookup(self, key: str) -> CacheLookupResult:
        l1_value = self.get_l1(key)
        if l1_value is not None:
            return CacheLookupResult(value=l1_value, cache_hit=True, layer="l1")

        l2_value = self._l2_backend.get(key)
        if isinstance(l2_value, dict):
            self.set_l1(key, l2_value)
            return CacheLookupResult(value=l2_value, cache_hit=True, layer="l2")

        return CacheLookupResult(value=None, cache_hit=False)

    def get_l1(self, key: str) -> dict[str, Any] | None:
        now = time.time()
        entry = self._l1.get(key)
        if entry is None:
            return None
        if entry.expires_at < now:
            self._l1.pop(key, None)
            return None
        return entry.value

    def _evict_expired_l1_entries(self, *, now: float) -> None:
        for cache_key in list(self._l1.keys()):
            entry = self._l1.get(cache_key)
            if entry is None:
                continue
            if entry.expires_at < now:
                self._l1.pop(cache_key, None)

    def set_l1(self, key: str, value: dict[str, Any]) -> None:
        now = time.time()
        self._evict_expired_l1_entries(now=now)
        self._l1[key] = _CacheEntry(
            value=value,
            expires_at=now + self._l1_ttl_seconds,
        )

    def set(self, key: str, value: dict[str, Any]) -> None:
        self.set_l1(key, value)
        self._l2_backend.set(key, value, self._l2_ttl_seconds)

    def invalidate_l1(self, key_prefix: str | None = None) -> None:
        if key_prefix is None:
            self._l1.clear()
            return
        for cache_key in list(self._l1.keys()):
            if cache_key.startswith(key_prefix):
                self._l1.pop(cache_key, None)

    def invalidate(self, key_prefix: str | None = None) -> None:
        self.invalidate_l1(key_prefix)
        self._l2_backend.invalidate(key_prefix)

    @property
    def l2_ttl_seconds(self) -> int:
        return self._l2_ttl_seconds
