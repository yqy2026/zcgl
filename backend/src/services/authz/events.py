"""ABAC cache invalidation events."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from threading import Event, Lock, Thread
from typing import Any, Protocol
from uuid import uuid4

from .cache import AuthzDecisionCache

logger = logging.getLogger(__name__)

AUTHZ_ROLE_POLICY_UPDATED = "authz.role_policy.updated"
AUTHZ_USER_ROLE_UPDATED = "authz.user_role.updated"
AUTHZ_POLICY_UPDATED = "authz.policy.updated"
AUTHZ_USER_SCOPE_UPDATED = "authz.user_scope.updated"
AUTHZ_INVALIDATION_CHANNEL = "authz:invalidation:events"


@dataclass(frozen=True)
class AuthzInvalidationEvent:
    event_type: str
    payload: dict[str, Any]
    hierarchy_version: int


class EventSubscriber(Protocol):
    def __call__(self, event: AuthzInvalidationEvent) -> None: ...


class ExternalEventSubscriber(Protocol):
    def __call__(
        self, event: AuthzInvalidationEvent, source_instance_id: str
    ) -> None: ...


class AuthzInvalidationTransport(Protocol):
    def start(
        self,
        subscriber: ExternalEventSubscriber,
        *,
        instance_id: str,
    ) -> None: ...

    def publish(
        self,
        event: AuthzInvalidationEvent,
        *,
        source_instance_id: str,
    ) -> None: ...

    def stop(self) -> None: ...


class RedisAuthzInvalidationTransport:
    """Redis pub/sub transport for authz invalidation events."""

    def __init__(
        self,
        *,
        redis_client: Any,
        channel: str = AUTHZ_INVALIDATION_CHANNEL,
        poll_interval_seconds: float = 0.5,
    ) -> None:
        self._redis_client = redis_client
        self._channel = channel
        self._poll_interval_seconds = max(float(poll_interval_seconds), 0.1)
        self._subscriber: ExternalEventSubscriber | None = None
        self._listener_thread: Thread | None = None
        self._stop_event = Event()

    def start(
        self,
        subscriber: ExternalEventSubscriber,
        *,
        instance_id: str,
    ) -> None:
        del instance_id  # instance identity is carried in published payloads.
        self._subscriber = subscriber
        if self._listener_thread is not None and self._listener_thread.is_alive():
            return

        self._stop_event.clear()
        self._listener_thread = Thread(
            target=self._listen_loop,
            name="authz-invalidation-listener",
            daemon=True,
        )
        self._listener_thread.start()

    def publish(
        self,
        event: AuthzInvalidationEvent,
        *,
        source_instance_id: str,
    ) -> None:
        payload = {
            "instance_id": source_instance_id,
            "event_type": event.event_type,
            "payload": event.payload,
            "hierarchy_version": event.hierarchy_version,
        }
        self._redis_client.publish(
            self._channel,
            json.dumps(payload, ensure_ascii=True, sort_keys=True),
        )

    def stop(self) -> None:
        self._stop_event.set()
        listener = self._listener_thread
        if listener is not None and listener.is_alive():
            listener.join(timeout=2.0)
        self._listener_thread = None
        self._subscriber = None

    def _listen_loop(self) -> None:
        pubsub = None
        try:
            pubsub = self._redis_client.pubsub(ignore_subscribe_messages=True)
            pubsub.subscribe(self._channel)
            while not self._stop_event.is_set():
                message = pubsub.get_message(timeout=self._poll_interval_seconds)
                if not isinstance(message, dict):
                    continue
                decoded = self._decode_message(message.get("data"))
                if decoded is None:
                    continue
                source_instance_id, event = decoded
                subscriber = self._subscriber
                if subscriber is None:
                    continue
                subscriber(event, source_instance_id)
        except Exception:
            logger.exception("Redis authz invalidation listener stopped unexpectedly")
        finally:
            if pubsub is not None:
                try:
                    pubsub.close()
                except Exception:
                    logger.debug("Failed to close redis pubsub client", exc_info=True)

    @staticmethod
    def _decode_message(
        raw_message: Any,
    ) -> tuple[str, AuthzInvalidationEvent] | None:
        if isinstance(raw_message, bytes):
            raw_message = raw_message.decode("utf-8", errors="ignore")
        if not isinstance(raw_message, str):
            return None

        try:
            payload = json.loads(raw_message)
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, dict):
            return None

        source_instance_id = str(payload.get("instance_id") or "").strip()
        event_type = str(payload.get("event_type") or "").strip()
        if source_instance_id == "" or event_type == "":
            return None

        hierarchy_version_raw = payload.get("hierarchy_version", 0)
        try:
            hierarchy_version = int(hierarchy_version_raw)
        except (TypeError, ValueError):
            hierarchy_version = 0

        event_payload = payload.get("payload")
        normalized_payload = event_payload if isinstance(event_payload, dict) else {}

        return (
            source_instance_id,
            AuthzInvalidationEvent(
                event_type=event_type,
                payload=normalized_payload,
                hierarchy_version=hierarchy_version,
            ),
        )


class AuthzEventBus:
    """Authz invalidation event bus with optional cross-process propagation."""

    def __init__(
        self,
        *,
        invalidation_transport: AuthzInvalidationTransport | None = None,
        instance_id: str | None = None,
    ) -> None:
        self._subscribers: list[EventSubscriber] = []
        self._hierarchy_version = 0
        self._lock = Lock()
        self._invalidation_transport = invalidation_transport
        self._instance_id = (instance_id or str(uuid4())).strip() or str(uuid4())
        if self._invalidation_transport is not None:
            try:
                self._invalidation_transport.start(
                    self._handle_external_event,
                    instance_id=self._instance_id,
                )
            except Exception:
                logger.exception(
                    "Failed to start authz invalidation transport; "
                    "falling back to in-process bus",
                )
                self._invalidation_transport = None

    @property
    def hierarchy_version(self) -> int:
        return self._hierarchy_version

    def subscribe(self, subscriber: EventSubscriber) -> None:
        if subscriber not in self._subscribers:
            self._subscribers.append(subscriber)

    def unsubscribe(self, subscriber: EventSubscriber) -> None:
        if subscriber in self._subscribers:
            self._subscribers.remove(subscriber)

    def publish(
        self,
        event: AuthzInvalidationEvent,
        *,
        propagate: bool = True,
    ) -> None:
        self._sync_hierarchy_version(event.hierarchy_version)
        logger.info(
            "Publish authz invalidation event: type=%s hierarchy_version=%s payload=%s",
            event.event_type,
            event.hierarchy_version,
            event.payload,
        )
        self._dispatch_to_subscribers(event)
        if propagate and self._invalidation_transport is not None:
            try:
                self._invalidation_transport.publish(
                    event,
                    source_instance_id=self._instance_id,
                )
            except Exception:
                logger.exception(
                    "Failed to publish authz invalidation through transport: type=%s",
                    event.event_type,
                )

    def publish_invalidation(
        self,
        *,
        event_type: str,
        payload: dict[str, Any] | None = None,
    ) -> AuthzInvalidationEvent:
        with self._lock:
            self._hierarchy_version += 1
            version = self._hierarchy_version

        event = AuthzInvalidationEvent(
            event_type=event_type,
            payload=payload or {},
            hierarchy_version=version,
        )
        self.publish(event, propagate=True)
        return event

    def close(self) -> None:
        if self._invalidation_transport is None:
            return
        try:
            self._invalidation_transport.stop()
        except Exception:
            logger.exception("Failed to stop authz invalidation transport")
        finally:
            self._invalidation_transport = None

    def _dispatch_to_subscribers(self, event: AuthzInvalidationEvent) -> None:
        for subscriber in list(self._subscribers):
            try:
                subscriber(event)
            except Exception:
                logger.exception(
                    "Authz event subscriber failed: type=%s subscriber=%s",
                    event.event_type,
                    getattr(subscriber, "__name__", subscriber.__class__.__name__),
                )

    def _sync_hierarchy_version(self, incoming_version: int) -> None:
        with self._lock:
            if incoming_version > self._hierarchy_version:
                self._hierarchy_version = incoming_version

    def _handle_external_event(
        self,
        event: AuthzInvalidationEvent,
        source_instance_id: str,
    ) -> None:
        if source_instance_id == self._instance_id:
            return
        self._sync_hierarchy_version(event.hierarchy_version)
        logger.info(
            "Receive external authz invalidation event: source=%s type=%s "
            "hierarchy_version=%s payload=%s",
            source_instance_id,
            event.event_type,
            event.hierarchy_version,
            event.payload,
        )
        self._dispatch_to_subscribers(event)


class AuthzCacheInvalidationHandler:
    """Invalidate authz decision cache after authz-related events."""

    def __init__(self, decision_cache: AuthzDecisionCache) -> None:
        self._decision_cache = decision_cache

    def __call__(self, event: AuthzInvalidationEvent) -> None:
        key_prefix = self._resolve_key_prefix(event)
        self._decision_cache.invalidate(key_prefix=key_prefix)

    @staticmethod
    def _resolve_key_prefix(event: AuthzInvalidationEvent) -> str | None:
        payload = event.payload
        explicit_prefix = payload.get("cache_key_prefix")
        if isinstance(explicit_prefix, str) and explicit_prefix.strip() != "":
            return explicit_prefix

        user_id = payload.get("user_id")
        if isinstance(user_id, str) and user_id.strip() != "":
            return f"abac:decision:{user_id}:"

        return None
