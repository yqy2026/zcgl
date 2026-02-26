"""Unit tests for authz invalidation event flow."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from src.services.authz.cache import AuthzDecisionCache
from src.services.authz.events import (
    AUTHZ_POLICY_UPDATED,
    AUTHZ_USER_ROLE_UPDATED,
    AUTHZ_USER_SCOPE_UPDATED,
    AuthzCacheInvalidationHandler,
    AuthzEventBus,
    AuthzInvalidationEvent,
)


@dataclass
class FakeL2CacheBackend:
    store: dict[str, dict[str, Any]] = field(default_factory=dict)

    def get(self, key: str) -> dict[str, Any] | None:
        return self.store.get(key)

    def set(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        del ttl_seconds
        self.store[key] = dict(value)

    def invalidate(self, key_prefix: str | None = None) -> None:
        if key_prefix is None:
            self.store.clear()
            return
        for key in list(self.store.keys()):
            if key.startswith(key_prefix):
                self.store.pop(key, None)


@dataclass
class FakeTransportHub:
    handlers: dict[str, Callable[[AuthzInvalidationEvent, str], None]] = field(
        default_factory=dict
    )

    def register(
        self,
        instance_id: str,
        handler: Callable[[AuthzInvalidationEvent, str], None],
    ) -> None:
        self.handlers[instance_id] = handler

    def unregister(self, instance_id: str) -> None:
        self.handlers.pop(instance_id, None)

    def broadcast(self, source_instance_id: str, event: AuthzInvalidationEvent) -> None:
        for instance_id, handler in list(self.handlers.items()):
            if instance_id == source_instance_id:
                continue
            handler(event, source_instance_id)


class FakeCrossProcessTransport:
    def __init__(self, hub: FakeTransportHub) -> None:
        self._hub = hub
        self._instance_id: str | None = None

    def start(
        self,
        handler: Callable[[AuthzInvalidationEvent, str], None],
        *,
        instance_id: str,
    ) -> None:
        self._instance_id = instance_id
        self._hub.register(instance_id, handler)

    def publish(
        self,
        event: AuthzInvalidationEvent,
        *,
        source_instance_id: str,
    ) -> None:
        self._hub.broadcast(source_instance_id, event)

    def stop(self) -> None:
        if self._instance_id is not None:
            self._hub.unregister(self._instance_id)
            self._instance_id = None


def test_user_scope_event_invalidates_only_target_user_keys() -> None:
    backend = FakeL2CacheBackend()
    cache = AuthzDecisionCache(l2_backend=backend)
    event_bus = AuthzEventBus()
    event_bus.subscribe(AuthzCacheInvalidationHandler(cache))

    user1_key = "abac:decision:user-1:asset:a:read:owner:ctx"
    user2_key = "abac:decision:user-2:asset:a:read:owner:ctx"
    cache.set(user1_key, {"allowed": True, "reason_code": "policy_allow"})
    cache.set(user2_key, {"allowed": True, "reason_code": "policy_allow"})

    event = event_bus.publish_invalidation(
        event_type=AUTHZ_USER_ROLE_UPDATED,
        payload={"user_id": "user-1"},
    )
    assert event.hierarchy_version == 1
    assert event_bus.hierarchy_version == 1
    assert cache.lookup(user1_key).cache_hit is False
    assert cache.lookup(user2_key).cache_hit is True


def test_user_scope_updated_event_invalidates_only_target_user_keys() -> None:
    backend = FakeL2CacheBackend()
    cache = AuthzDecisionCache(l2_backend=backend)
    event_bus = AuthzEventBus()
    event_bus.subscribe(AuthzCacheInvalidationHandler(cache))

    user1_key = "abac:decision:user-1:asset:a:read:owner:ctx"
    user2_key = "abac:decision:user-2:asset:a:read:owner:ctx"
    cache.set(user1_key, {"allowed": True, "reason_code": "policy_allow"})
    cache.set(user2_key, {"allowed": True, "reason_code": "policy_allow"})

    event = event_bus.publish_invalidation(
        event_type=AUTHZ_USER_SCOPE_UPDATED,
        payload={"user_id": "user-1"},
    )
    assert event.hierarchy_version == 1
    assert event_bus.hierarchy_version == 1
    assert cache.lookup(user1_key).cache_hit is False
    assert cache.lookup(user2_key).cache_hit is True


def test_policy_update_event_invalidates_all_authz_cache() -> None:
    backend = FakeL2CacheBackend()
    cache = AuthzDecisionCache(l2_backend=backend)
    event_bus = AuthzEventBus()
    event_bus.subscribe(AuthzCacheInvalidationHandler(cache))

    key = "abac:decision:user-1:asset:a:list:owner:ctx"
    cache.set(key, {"allowed": True, "reason_code": "policy_allow"})
    assert cache.lookup(key).cache_hit is True

    event = event_bus.publish_invalidation(
        event_type=AUTHZ_POLICY_UPDATED,
        payload={},
    )
    assert event.hierarchy_version == 1
    assert cache.lookup(key).cache_hit is False


def test_cross_process_invalidation_propagates_to_other_worker_cache() -> None:
    hub = FakeTransportHub()

    cache_worker1 = AuthzDecisionCache(l2_backend=FakeL2CacheBackend())
    cache_worker2 = AuthzDecisionCache(l2_backend=FakeL2CacheBackend())

    bus_worker1 = AuthzEventBus(
        invalidation_transport=FakeCrossProcessTransport(hub),
        instance_id="worker-1",
    )
    bus_worker2 = AuthzEventBus(
        invalidation_transport=FakeCrossProcessTransport(hub),
        instance_id="worker-2",
    )
    bus_worker1.subscribe(AuthzCacheInvalidationHandler(cache_worker1))
    bus_worker2.subscribe(AuthzCacheInvalidationHandler(cache_worker2))

    cache_key = "abac:decision:user-1:asset:a:read:owner:ctx"
    payload = {"allowed": True, "reason_code": "policy_allow"}
    cache_worker1.set(cache_key, payload)
    cache_worker2.set(cache_key, payload)

    event = bus_worker1.publish_invalidation(
        event_type=AUTHZ_USER_ROLE_UPDATED,
        payload={"user_id": "user-1"},
    )

    assert event.hierarchy_version == 1
    assert bus_worker1.hierarchy_version == 1
    assert bus_worker2.hierarchy_version == 1
    assert cache_worker1.lookup(cache_key).cache_hit is False
    assert cache_worker2.lookup(cache_key).cache_hit is False

    bus_worker1.close()
    bus_worker2.close()
