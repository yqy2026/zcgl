"""Unit tests for authz decision cache helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import patch

from src.services.authz.cache import AuthzDecisionCache, compute_roles_hash


@dataclass
class FakeL2CacheBackend:
    store: dict[str, dict[str, Any]] = field(default_factory=dict)
    invalidated_prefixes: list[str | None] = field(default_factory=list)

    def get(self, key: str) -> dict[str, Any] | None:
        return self.store.get(key)

    def set(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        del ttl_seconds
        self.store[key] = dict(value)

    def invalidate(self, key_prefix: str | None = None) -> None:
        self.invalidated_prefixes.append(key_prefix)
        if key_prefix is None:
            self.store.clear()
            return
        for key in list(self.store.keys()):
            if key.startswith(key_prefix):
                self.store.pop(key, None)


def test_compute_roles_hash_is_order_independent() -> None:
    left = compute_roles_hash(["r2", "r1", "r1"])
    right = compute_roles_hash(["r1", "r2"])
    assert left == right


def test_authz_decision_cache_l2_backfill_after_l1_miss() -> None:
    backend = FakeL2CacheBackend()
    cache = AuthzDecisionCache(
        l1_ttl_seconds=5,
        l2_ttl_seconds=300,
        l2_backend=backend,
    )
    key = "abac:decision:u1:asset:res1:read:owner:ctx"
    value = {"allowed": True, "reason_code": "policy_allow"}

    cache.set(key, value)
    first_lookup = cache.lookup(key)
    assert first_lookup.cache_hit is True
    assert first_lookup.layer == "l1"

    cache.invalidate_l1(key_prefix=key)
    second_lookup = cache.lookup(key)
    assert second_lookup.cache_hit is True
    assert second_lookup.layer == "l2"
    assert second_lookup.value == value
    assert cache.get_l1(key) == value


def test_authz_decision_cache_invalidate_prefix() -> None:
    backend = FakeL2CacheBackend()
    cache = AuthzDecisionCache(l2_backend=backend)
    key_user1 = "abac:decision:user1:asset:a:read:-:ctx1"
    key_user2 = "abac:decision:user2:asset:a:read:-:ctx2"
    cache.set(key_user1, {"allowed": True, "reason_code": "policy_allow"})
    cache.set(key_user2, {"allowed": True, "reason_code": "policy_allow"})

    cache.invalidate(key_prefix="abac:decision:user1:")

    assert cache.lookup(key_user1).cache_hit is False
    assert cache.lookup(key_user2).cache_hit is True
    assert backend.invalidated_prefixes[-1] == "abac:decision:user1:"


def test_authz_decision_cache_set_l1_evicts_expired_entries_on_insert() -> None:
    backend = FakeL2CacheBackend()
    cache = AuthzDecisionCache(
        l1_ttl_seconds=1,
        l2_ttl_seconds=300,
        l2_backend=backend,
    )

    with patch(
        "src.services.authz.cache.time.time",
        side_effect=[100.0, 102.0],
    ):
        cache.set_l1("k1", {"allowed": True, "reason_code": "policy_allow"})
        cache.set_l1("k2", {"allowed": True, "reason_code": "policy_allow"})

    assert "k1" not in cache._l1
    assert "k2" in cache._l1
