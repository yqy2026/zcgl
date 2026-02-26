from __future__ import annotations

import logging

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
    """Check whether user should bypass party scoping when no bindings are present."""
    try:
        from ..schemas.rbac import PermissionCheckRequest
        from .permission.rbac_service import RBACService

        rbac_service = RBACService(db)
        if await rbac_service.is_admin(current_user_id):
            return True

        response = await rbac_service.check_permission(
            current_user_id,
            PermissionCheckRequest(
                resource="organization",
                action="read",
                resource_id=None,
                context=None,
            ),
        )
        return bool(response.has_permission)
    except Exception:
        logger.exception(
            "Failed to resolve unrestricted party scope access for user %s",
            current_user_id,
        )
        return False


async def resolve_user_party_filter(
    db: AsyncSession,
    *,
    current_user_id: str | None,
    party_filter: PartyFilter | None,
    logger: logging.Logger,
) -> PartyFilter | None:
    """Resolve PartyFilter using party bindings with legacy org fallback.

    Notes:
    - Explicit ``party_filter`` from callers always wins.
    - Missing/blank ``current_user_id`` keeps behavior unchanged (returns None).
    - Resolution failure returns empty PartyFilter for fail-closed.
    - Binding relation is preserved for owner/manager scoped filtering.
    - No bindings checks privileged bypass before falling back to
      ``users.default_organization_id`` and mapped organization party scope.
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
                if relation_type in {"manager", "headquarters"}:
                    resolved_manager_party_ids.add(party_id)
                    continue
                resolved_generic_party_ids.add(party_id)
    except Exception:
        logger.exception(
            "Failed to resolve party bindings for user %s, fallback to fail-closed",
            current_user_id,
        )
        return PartyFilter(party_ids=[])

    if len(resolved_owner_party_ids) > 0 or len(resolved_manager_party_ids) > 0:
        owner_party_ids = sorted(resolved_owner_party_ids)
        manager_party_ids = sorted(resolved_manager_party_ids)
        merged_party_ids = sorted(
            resolved_owner_party_ids.union(resolved_manager_party_ids)
        )
        filter_mode = "any"
        if len(owner_party_ids) > 0 and len(manager_party_ids) == 0:
            filter_mode = "owner"
        elif len(manager_party_ids) > 0 and len(owner_party_ids) == 0:
            filter_mode = "manager"

        return PartyFilter(
            party_ids=merged_party_ids,
            filter_mode=filter_mode,
            owner_party_ids=owner_party_ids,
            manager_party_ids=manager_party_ids,
        )

    if len(resolved_generic_party_ids) > 0:
        return PartyFilter(party_ids=sorted(resolved_generic_party_ids))

    if await _has_unrestricted_party_scope_access(
        db,
        current_user_id=current_user_id,
        logger=logger,
    ):
        logger.info(
            "No party bindings/default organization for user %s; bypassing party scope for privileged account",
            current_user_id,
        )
        return None

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
            return PartyFilter(party_ids=[legacy_party_id])

        logger.warning(
            "No party bindings for user %s, legacy default organization %s has no mapped party scope; fail-closed",
            current_user_id,
            legacy_org_id,
        )

    return PartyFilter(party_ids=[])
