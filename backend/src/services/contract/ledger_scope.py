"""Party-scope helpers for operational ledger reads and writes."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exception_handler import ResourceNotFoundError
from src.crud.query_builder import PartyFilter
from src.services.party_scope import resolve_user_party_filter

logger = logging.getLogger(__name__)


def _normalize_ids(values: Sequence[Any] | None) -> set[str]:
    return {
        normalized for value in values or [] if (normalized := str(value).strip()) != ""
    }


def party_filter_scope_ids(party_filter: PartyFilter) -> tuple[set[str], set[str]]:
    """Return owner and manager IDs without widening relation-aware scopes."""
    general_ids = _normalize_ids(party_filter.party_ids)
    owner_ids = (
        _normalize_ids(party_filter.owner_party_ids)
        if party_filter.owner_party_ids is not None
        else general_ids
    )
    manager_ids = (
        _normalize_ids(party_filter.manager_party_ids)
        if party_filter.manager_party_ids is not None
        else general_ids
    )
    if party_filter.filter_mode == "owner":
        return owner_ids, set()
    if party_filter.filter_mode == "manager":
        return set(), manager_ids
    return owner_ids, manager_ids


async def resolve_ledger_party_filter(
    db: AsyncSession,
    *,
    current_user_id: str | None,
    party_filter: PartyFilter | None,
) -> PartyFilter | None:
    return await resolve_user_party_filter(
        db,
        current_user_id=current_user_id,
        party_filter=party_filter,
        logger=logger,
    )


def assert_attribution_in_scope(
    *,
    owner_party_id: Any,
    operator_party_id: Any,
    party_filter: PartyFilter | None,
    resource_type: str,
    resource_id: str,
) -> None:
    """Fail as not-found when a frozen ledger attribution is outside scope."""
    if is_attribution_in_scope(
        owner_party_id=owner_party_id,
        operator_party_id=operator_party_id,
        party_filter=party_filter,
    ):
        return
    raise ResourceNotFoundError(resource_type, resource_id)


def is_attribution_in_scope(
    *,
    owner_party_id: Any,
    operator_party_id: Any,
    party_filter: PartyFilter | None,
) -> bool:
    if party_filter is None:
        return True
    owner_ids, manager_ids = party_filter_scope_ids(party_filter)
    normalized_owner_id = str(owner_party_id or "").strip()
    normalized_operator_id = str(operator_party_id or "").strip()
    return normalized_owner_id in owner_ids or normalized_operator_id in manager_ids


def assert_resource_in_scope(
    resource: Any,
    *,
    party_filter: PartyFilter | None,
    resource_type: str,
    resource_id: str,
) -> None:
    assert_attribution_in_scope(
        owner_party_id=getattr(
            resource,
            "attributed_owner_party_id",
            getattr(resource, "owner_party_id", None),
        ),
        operator_party_id=getattr(
            resource,
            "attributed_operator_party_id",
            getattr(resource, "operator_party_id", None),
        ),
        party_filter=party_filter,
        resource_type=resource_type,
        resource_id=resource_id,
    )


def is_resource_in_scope(resource: Any, *, party_filter: PartyFilter | None) -> bool:
    return is_attribution_in_scope(
        owner_party_id=getattr(
            resource,
            "attributed_owner_party_id",
            getattr(resource, "owner_party_id", None),
        ),
        operator_party_id=getattr(
            resource,
            "attributed_operator_party_id",
            getattr(resource, "operator_party_id", None),
        ),
        party_filter=party_filter,
    )
