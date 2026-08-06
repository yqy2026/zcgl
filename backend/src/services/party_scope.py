from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.exception_handler import PartyScopeForbiddenError
from ..crud.query_builder import PartyFilter
from .party_scope_resolver import party_scope_resolver


def _normalize_identifier(raw_value: object | None) -> str | None:
    if raw_value is None:
        return None
    value = str(raw_value).strip()
    return value if value != "" else None


def _normalize_identifier_sequence(values: Sequence[object] | None) -> list[str]:
    if values is None:
        return []

    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        identifier = _normalize_identifier(value)
        if identifier is None or identifier in seen:
            continue
        seen.add(identifier)
        normalized.append(identifier)
    return normalized


def build_party_filter_from_scope_context(
    scope_context: object,
) -> PartyFilter | None:
    scope_mode = getattr(scope_context, "scope_mode", None)
    if scope_mode == "all":
        owner_ids = _normalize_identifier_sequence(
            getattr(scope_context, "owner_party_ids", None)
        )
        manager_ids = _normalize_identifier_sequence(
            getattr(scope_context, "manager_party_ids", None)
        )
        if len(owner_ids) == 0 and len(manager_ids) == 0:
            return None

        merged_ids = sorted(set(owner_ids + manager_ids))
        return PartyFilter(
            party_ids=merged_ids,
            filter_mode="any",
            owner_party_ids=owner_ids,
            manager_party_ids=manager_ids,
        )

    effective_party_ids = _normalize_identifier_sequence(
        getattr(scope_context, "effective_party_ids", None)
    )
    if len(effective_party_ids) == 0:
        return None

    if scope_mode == "owner":
        return PartyFilter(
            party_ids=effective_party_ids,
            filter_mode="owner",
            owner_party_ids=effective_party_ids,
            manager_party_ids=[],
        )

    return PartyFilter(
        party_ids=effective_party_ids,
        filter_mode="manager",
        owner_party_ids=[],
        manager_party_ids=effective_party_ids,
    )


async def resolve_user_party_filter(
    db: AsyncSession,
    *,
    current_user_id: str | None,
    party_filter: PartyFilter | None,
    logger: logging.Logger,
    skip_invalid_scope: bool = False,
) -> PartyFilter | None:
    """Adapt the unified effective scope into legacy query-builder fields.

    Notes:
    - Explicit ``party_filter`` from callers always wins.
    - Missing/blank ``current_user_id`` keeps behavior unchanged (returns None).
    - Resolution failure returns an empty PartyFilter for fail-closed callers.
    - Only built-in admin/system_admin roles receive unrestricted scope.
    """
    if party_filter is not None:
        return party_filter
    if current_user_id is None or current_user_id.strip() == "":
        return None

    try:
        scope = await party_scope_resolver.resolve(
            db,
            user_id=current_user_id,
        )
    except Exception:
        logger.exception(
            "Failed to resolve Party scope for user %s; fail-closed",
            current_user_id,
        )
        return PartyFilter(party_ids=[])

    if scope.scope_mode == "unrestricted":
        return None

    if scope.error_code is None:
        filter_mode: Literal["owner", "manager", "any"]
        if scope.scope_mode == "all":
            filter_mode = "any"
        elif scope.scope_mode == "owner":
            filter_mode = "owner"
        elif scope.scope_mode == "manager":
            filter_mode = "manager"
        else:
            raise PartyScopeForbiddenError(
                code="PARTY_SCOPE_MISSING",
                message="当前主体范围缺失或配置无效",
            )
        return PartyFilter(
            party_ids=scope.effective_party_ids,
            filter_mode=filter_mode,
            owner_party_ids=scope.owner_party_ids,
            manager_party_ids=scope.manager_party_ids,
        )

    logger.warning(
        "Party scope denied for user %s: %s",
        current_user_id,
        scope.error_code,
    )
    if not skip_invalid_scope:
        raise PartyScopeForbiddenError(
            code=scope.error_code,
            message="当前主体范围缺失或配置无效",
        )
    return PartyFilter(party_ids=[])
