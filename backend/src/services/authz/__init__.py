"""Authz service package exports."""

from ...core.cache_manager import RedisCache, cache_manager
from .cache import AuthzDecisionCache
from .context_builder import AuthzContextBuilder, SubjectContext
from .data_policy_service import DATA_POLICY_TEMPLATES, DataPolicyService
from .engine import AuthzDecision, AuthzEngine
from .events import (
    AUTHZ_POLICY_UPDATED,
    AUTHZ_ROLE_POLICY_UPDATED,
    AUTHZ_USER_ROLE_UPDATED,
    AUTHZ_USER_SCOPE_UPDATED,
    AuthzCacheInvalidationHandler,
    AuthzEventBus,
    AuthzInvalidationEvent,
    RedisAuthzInvalidationTransport,
)
from .service import AuthzService


def _build_authz_invalidation_transport() -> RedisAuthzInvalidationTransport | None:
    backend = cache_manager.backend
    if isinstance(backend, RedisCache):
        return RedisAuthzInvalidationTransport(redis_client=backend.client)
    return None


authz_decision_cache = AuthzDecisionCache()
authz_event_bus = AuthzEventBus(
    invalidation_transport=_build_authz_invalidation_transport(),
)
authz_event_bus.subscribe(AuthzCacheInvalidationHandler(authz_decision_cache))
authz_service = AuthzService(
    decision_cache=authz_decision_cache,
    event_bus=authz_event_bus,
)

__all__ = [
    "AuthzContextBuilder",
    "SubjectContext",
    "AuthzDecision",
    "AuthzEngine",
    "AuthzDecisionCache",
    "DATA_POLICY_TEMPLATES",
    "DataPolicyService",
    "AuthzCacheInvalidationHandler",
    "AuthzInvalidationEvent",
    "AuthzEventBus",
    "RedisAuthzInvalidationTransport",
    "AUTHZ_ROLE_POLICY_UPDATED",
    "AUTHZ_USER_ROLE_UPDATED",
    "AUTHZ_POLICY_UPDATED",
    "AUTHZ_USER_SCOPE_UPDATED",
    "AuthzService",
    "authz_decision_cache",
    "authz_event_bus",
    "authz_service",
]
