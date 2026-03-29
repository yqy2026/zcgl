"""Backend truth for resource-level allowed perspectives."""

from __future__ import annotations

from typing import Final

from ...schemas.authz import AuthzAction, PerspectiveName

ResourcePerspectiveMap = dict[str, tuple[PerspectiveName, ...]]
AuthenticatedDefaultActionMap = dict[str, tuple[AuthzAction, ...]]

RESOURCE_PERSPECTIVE_REGISTRY: Final[ResourcePerspectiveMap] = {
    "analytics": ("owner", "manager"),
    "asset": ("owner", "manager"),
    "contract": ("owner", "manager"),
    "contract_group": ("owner", "manager"),
    "project": ("manager",),
    "property_certificate": ("owner",),
    "backup": (),
    "collection": (),
    "contact": (),
    "custom_field": (),
    "dictionary": (),
    "enum_field": (),
    "error_recovery": (),
    "excel_config": (),
    "history": (),
    "ledger": (),
    "llm_prompt": (),
    "notification": (),
    "occupancy": (),
    "operation_log": (),
    "organization": (),
    "ownership": (),
    "party": (),
    "role": (),
    "system": (),
    "system_monitoring": (),
    "system_settings": (),
    "task": (),
    "user": (),
}

AUTHENTICATED_DEFAULT_ACTIONS: Final[AuthenticatedDefaultActionMap] = {
    "notification": ("read",),
}


def get_registered_perspectives(resource: str) -> tuple[PerspectiveName, ...]:
    """Return the registered perspective set for a resource."""
    return RESOURCE_PERSPECTIVE_REGISTRY.get(resource, ())


def resolve_capability_perspectives(
    resource: str,
    subject_perspectives: list[PerspectiveName],
) -> list[PerspectiveName]:
    """Intersect subject perspectives with resource-level allowed perspectives."""
    registered_perspectives = get_registered_perspectives(resource)
    if len(registered_perspectives) == 0:
        return []

    subject_set = set(subject_perspectives)
    return [item for item in registered_perspectives if item in subject_set]


def resource_requires_perspective(resource: str) -> bool:
    """Whether the resource is perspective-scoped."""
    return len(get_registered_perspectives(resource)) > 0


def get_authenticated_default_actions(resource: str) -> tuple[AuthzAction, ...]:
    """Return actions granted to any authenticated user for a resource."""
    return AUTHENTICATED_DEFAULT_ACTIONS.get(resource, ())


def iter_authenticated_default_actions() -> AuthenticatedDefaultActionMap:
    """Return a copy of the authenticated-default action registry."""
    return dict(AUTHENTICATED_DEFAULT_ACTIONS)


def action_is_authenticated_default(resource: str, action: str) -> bool:
    """Whether an action is granted to any authenticated user."""
    return action in get_authenticated_default_actions(resource)


__all__ = [
    "AUTHENTICATED_DEFAULT_ACTIONS",
    "action_is_authenticated_default",
    "get_authenticated_default_actions",
    "iter_authenticated_default_actions",
    "RESOURCE_PERSPECTIVE_REGISTRY",
    "get_registered_perspectives",
    "resolve_capability_perspectives",
    "resource_requires_perspective",
]
