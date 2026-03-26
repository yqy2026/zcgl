"""Backend truth for resource-level allowed perspectives."""

from __future__ import annotations

from typing import Final

from ...schemas.authz import PerspectiveName

ResourcePerspectiveMap = dict[str, tuple[PerspectiveName, ...]]

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


__all__ = [
    "RESOURCE_PERSPECTIVE_REGISTRY",
    "get_registered_perspectives",
    "resolve_capability_perspectives",
    "resource_requires_perspective",
]
