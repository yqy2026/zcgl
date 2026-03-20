"""Helpers for narrowing request scope to a selected party/perspective."""

from __future__ import annotations

import logging
from typing import Literal

from fastapi import Depends, Request
from fastapi.params import Depends as DependsParam
from sqlalchemy.ext.asyncio import AsyncSession

from ..crud.query_builder import PartyFilter
from ..database import get_async_db
from ..middleware.auth import get_current_active_user
from ..models.auth import User
from .party_scope import resolve_user_party_filter

ViewPerspective = Literal["owner", "manager"]

_VIEW_PERSPECTIVE_HEADER = "X-View-Perspective"
_VIEW_PARTY_ID_HEADER = "X-View-Party-Id"
logger = logging.getLogger(__name__)


def _normalize_optional_str(value: object | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized if normalized != "" else None


def _build_narrowed_party_filter(
    *,
    perspective: ViewPerspective,
    party_id: str,
) -> PartyFilter:
    if perspective == "owner":
        return PartyFilter(
            party_ids=[party_id],
            filter_mode="owner",
            owner_party_ids=[party_id],
            manager_party_ids=[],
        )

    return PartyFilter(
        party_ids=[party_id],
        filter_mode="manager",
        owner_party_ids=[],
        manager_party_ids=[party_id],
    )


async def resolve_selected_view_party_filter(
    *,
    request: Request,
    db: AsyncSession,
    current_user_id: str | None,
    logger: logging.Logger,
) -> PartyFilter | None:
    perspective = _normalize_optional_str(request.headers.get(_VIEW_PERSPECTIVE_HEADER))
    party_id = _normalize_optional_str(request.headers.get(_VIEW_PARTY_ID_HEADER))

    if perspective is None and party_id is None:
        return None

    if perspective not in {"owner", "manager"} or party_id is None:
        logger.warning(
            "Invalid selected view headers for user %s: perspective=%s party_id=%s",
            current_user_id,
            perspective,
            party_id,
        )
        return PartyFilter(party_ids=[])

    if current_user_id is None or current_user_id.strip() == "":
        return PartyFilter(party_ids=[])

    caller_scope = await resolve_user_party_filter(
        db,
        current_user_id=current_user_id,
        party_filter=None,
        logger=logger,
        allow_legacy_default_organization_fallback=False,
    )
    if caller_scope is None:
        return _build_narrowed_party_filter(
            perspective=perspective,
            party_id=party_id,
        )

    allowed_owner_ids = {
        normalized
        for value in (caller_scope.owner_party_ids or [])
        if (normalized := _normalize_optional_str(value)) is not None
    }
    allowed_manager_ids = {
        normalized
        for value in (caller_scope.manager_party_ids or [])
        if (normalized := _normalize_optional_str(value)) is not None
    }

    if perspective == "owner" and party_id not in allowed_owner_ids:
        logger.warning(
            "Selected owner view party %s is outside caller scope for user %s",
            party_id,
            current_user_id,
        )
        return PartyFilter(party_ids=[])

    if perspective == "manager" and party_id not in allowed_manager_ids:
        logger.warning(
            "Selected manager view party %s is outside caller scope for user %s",
            party_id,
            current_user_id,
        )
        return PartyFilter(party_ids=[])

    return _build_narrowed_party_filter(
        perspective=perspective,
        party_id=party_id,
    )


async def resolve_selected_view_party_filter_dependency(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> PartyFilter | None:
    return await resolve_selected_view_party_filter(
        request=request,
        db=db,
        current_user_id=str(current_user.id),
        logger=logger,
    )


def coerce_selected_view_party_filter(value: object) -> PartyFilter | None:
    if isinstance(value, DependsParam):
        return None
    if value is None or isinstance(value, PartyFilter):
        return value
    return None
