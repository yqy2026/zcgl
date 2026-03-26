from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..crud.party import party_crud
from ..crud.query_builder import PartyFilter
from ..models.auth import User


def _normalize_identifier(raw_value: object | None) -> str | None:
    if raw_value is None:
        return None
    value = str(raw_value).strip()
    return value if value != "" else None


def _normalize_relation_type(raw_value: object | None) -> str | None:
    normalized = _normalize_identifier(raw_value)
    if normalized is None:
        return None
    return normalized.lower()


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


def build_party_filter_from_perspective_context(
    perspective_context: object,
) -> PartyFilter | None:
    perspective = getattr(perspective_context, "perspective", None)
    effective_party_ids = _normalize_identifier_sequence(
        getattr(perspective_context, "effective_party_ids", None)
    )
    if len(effective_party_ids) == 0:
        return None

    if perspective == "owner":
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


async def _resolve_legacy_default_organization_id(
    db: AsyncSession, *, current_user_id: str, logger: logging.Logger
) -> str | None:
    try:
        stmt = (
            select(User.default_organization_id)
            .where(User.id == current_user_id)
            .limit(1)
        )
        default_org_id = (await db.execute(stmt)).scalar_one_or_none()
    except Exception:
        logger.exception(
            "Failed to resolve legacy default_organization_id for user %s",
            current_user_id,
        )
        return None
    return _normalize_identifier(default_org_id)


async def _resolve_legacy_default_organization_party_id(
    db: AsyncSession,
    *,
    current_user_id: str,
    organization_id: str,
    logger: logging.Logger,
) -> str | None:
    try:
        return await party_crud.resolve_organization_party_id(
            db,
            organization_id=organization_id,
        )
    except Exception:
        logger.exception(
            "Failed to resolve legacy default organization party mapping for user %s (organization_id=%s)",
            current_user_id,
            organization_id,
        )
        return None


async def _has_unrestricted_party_scope_access(
    db: AsyncSession,
    *,
    current_user_id: str,
    logger: logging.Logger,
) -> bool:
    """Only administrators may bypass party scoping."""
    try:
        from .permission.rbac_service import RBACService

        rbac_service = RBACService(db)
        return bool(await rbac_service.is_admin(current_user_id))
    except Exception:
        logger.exception(
            "Failed to resolve unrestricted party scope access for user %s",
            current_user_id,
        )
        return False


async def _resolve_relation_legacy_organization_scope_ids(
    db: AsyncSession,
    *,
    owner_party_ids: set[str],
    manager_party_ids: set[str],
    current_user_id: str,
    logger: logging.Logger,
) -> tuple[list[str], list[str]]:
    relation_party_ids = sorted(owner_party_ids.union(manager_party_ids))
    if len(relation_party_ids) == 0:
        return [], []

    try:
        scope_ids_by_party_id = (
            await party_crud.resolve_legacy_organization_scope_ids_by_party_ids(
                db,
                party_ids=relation_party_ids,
            )
        )
    except Exception:
        logger.exception(
            "Failed to resolve relation legacy organization scope ids for user %s",
            current_user_id,
        )
        return [], []

    def _collect_scope_ids(scoped_party_ids: set[str]) -> list[str]:
        resolved_scope_ids: set[str] = set()
        for scoped_party_id in scoped_party_ids:
            resolved_scope_ids.update(scope_ids_by_party_id.get(scoped_party_id, []))
        return sorted(resolved_scope_ids)

    return (
        _collect_scope_ids(owner_party_ids),
        _collect_scope_ids(manager_party_ids),
    )


async def _resolve_generic_legacy_organization_scope_ids(
    db: AsyncSession,
    *,
    party_ids: set[str],
    current_user_id: str,
    logger: logging.Logger,
) -> list[str]:
    if len(party_ids) == 0:
        return []

    try:
        scope_ids_by_party_id = (
            await party_crud.resolve_legacy_organization_scope_ids_by_party_ids(
                db,
                party_ids=sorted(party_ids),
            )
        )
    except Exception:
        logger.exception(
            "Failed to resolve generic legacy organization scope ids for user %s",
            current_user_id,
        )
        return []

    resolved_scope_ids: set[str] = set()
    for party_id in party_ids:
        resolved_scope_ids.update(scope_ids_by_party_id.get(party_id, []))
    return sorted(resolved_scope_ids)


async def resolve_user_party_filter(
    db: AsyncSession,
    *,
    current_user_id: str | None,
    party_filter: PartyFilter | None,
    logger: logging.Logger,
    allow_legacy_default_organization_fallback: bool = True,
) -> PartyFilter | None:
    """Resolve PartyFilter using party bindings with legacy org fallback.

    Notes:
    - Explicit ``party_filter`` from callers always wins.
    - Missing/blank ``current_user_id`` keeps behavior unchanged (returns None).
    - Resolution failure returns empty PartyFilter for fail-closed.
    - Binding relation is preserved for owner/manager scoped filtering.
    - Privileged users bypass party scope regardless of resolved bindings.
    - Legacy ``users.default_organization_id`` mapping is optional and used only when
      no scope bindings are available for non-privileged users.
    """
    if party_filter is not None:
        return party_filter
    if current_user_id is None or current_user_id.strip() == "":
        return None

    resolved_owner_party_ids: set[str] = set()
    resolved_manager_party_ids: set[str] = set()
    resolved_generic_party_ids: set[str] = set()
    try:
        bindings = await party_crud.get_user_bindings(
            db,
            user_id=current_user_id,
            active_only=True,
        )
        for binding in bindings:
            party_id = _normalize_identifier(getattr(binding, "party_id", None))
            if party_id is not None:
                relation_type = _normalize_relation_type(
                    getattr(binding, "relation_type", None)
                )
                if relation_type == "owner":
                    resolved_owner_party_ids.add(party_id)
                    continue
                if relation_type == "manager":
                    resolved_manager_party_ids.add(party_id)
                    continue
                if relation_type == "headquarters":
                    try:
                        descendants = await party_crud.get_descendants(
                            db,
                            party_id=party_id,
                            include_self=True,
                        )
                    except Exception:
                        logger.exception(
                            "Failed to resolve headquarters descendants for user %s party %s",
                            current_user_id,
                            party_id,
                        )
                        resolved_manager_party_ids.add(party_id)
                        continue

                    normalized_descendants = _normalize_identifier_sequence(descendants)
                    if len(normalized_descendants) == 0:
                        resolved_manager_party_ids.add(party_id)
                        continue

                    resolved_manager_party_ids.update(normalized_descendants)
                    continue
                resolved_generic_party_ids.add(party_id)
    except Exception:
        logger.exception(
            "Failed to resolve party bindings for user %s, fallback to fail-closed",
            current_user_id,
        )
        return PartyFilter(party_ids=[])

    if await _has_unrestricted_party_scope_access(
        db,
        current_user_id=current_user_id,
        logger=logger,
    ):
        logger.info(
            "Bypassing party scope for privileged user %s",
            current_user_id,
        )
        return None

    if len(resolved_owner_party_ids) > 0 or len(resolved_manager_party_ids) > 0:
        owner_party_ids = sorted(resolved_owner_party_ids)
        manager_party_ids = sorted(resolved_manager_party_ids)
        (
            owner_legacy_org_ids,
            manager_legacy_org_ids,
        ) = await _resolve_relation_legacy_organization_scope_ids(
            db,
            owner_party_ids=resolved_owner_party_ids,
            manager_party_ids=resolved_manager_party_ids,
            current_user_id=current_user_id,
            logger=logger,
        )
        merged_party_ids = sorted(
            resolved_owner_party_ids.union(resolved_manager_party_ids)
        )
        filter_mode: Literal["owner", "manager", "any"] = "any"
        if len(owner_party_ids) > 0 and len(manager_party_ids) == 0:
            filter_mode = "owner"
        elif len(manager_party_ids) > 0 and len(owner_party_ids) == 0:
            filter_mode = "manager"

        legacy_org_ids = sorted(set(owner_legacy_org_ids).union(manager_legacy_org_ids))
        return PartyFilter(
            party_ids=merged_party_ids,
            legacy_org_ids=legacy_org_ids if len(legacy_org_ids) > 0 else None,
            filter_mode=filter_mode,
            owner_party_ids=owner_party_ids,
            manager_party_ids=manager_party_ids,
            owner_legacy_org_ids=owner_legacy_org_ids,
            manager_legacy_org_ids=manager_legacy_org_ids,
        )

    if len(resolved_generic_party_ids) > 0:
        generic_party_ids = sorted(resolved_generic_party_ids)
        legacy_org_ids = await _resolve_generic_legacy_organization_scope_ids(
            db,
            party_ids=resolved_generic_party_ids,
            current_user_id=current_user_id,
            logger=logger,
        )
        return PartyFilter(
            party_ids=generic_party_ids,
            legacy_org_ids=legacy_org_ids if len(legacy_org_ids) > 0 else None,
        )

    if not allow_legacy_default_organization_fallback:
        logger.info(
            "No party bindings for user %s and legacy fallback disabled; fail-closed",
            current_user_id,
        )
        return PartyFilter(party_ids=[])

    legacy_org_id = await _resolve_legacy_default_organization_id(
        db,
        current_user_id=current_user_id,
        logger=logger,
    )
    if legacy_org_id is not None:
        legacy_party_id = await _resolve_legacy_default_organization_party_id(
            db,
            current_user_id=current_user_id,
            organization_id=legacy_org_id,
            logger=logger,
        )
        if legacy_party_id is not None:
            logger.info(
                "No party bindings for user %s, fallback to mapped legacy default organization party scope",
                current_user_id,
            )
            return PartyFilter(
                party_ids=[legacy_party_id],
                legacy_org_ids=[legacy_org_id],
            )

        logger.warning(
            "No party bindings for user %s, legacy default organization %s has no mapped party scope; fail-closed",
            current_user_id,
            legacy_org_id,
        )

    return PartyFilter(party_ids=[])
