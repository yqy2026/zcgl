"""Tests for request-scoped selected view narrowing helpers."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.requests import Request

from src.crud.query_builder import PartyFilter
from src.services.view_scope import resolve_selected_view_party_filter


def _build_request(headers: dict[str, str] | None = None) -> Request:
    raw_headers = []
    for key, value in (headers or {}).items():
        raw_headers.append((key.lower().encode("utf-8"), value.encode("utf-8")))

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/assets",
        "query_string": b"",
        "headers": raw_headers,
        "path_params": {},
    }

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(scope, receive)


@pytest.mark.asyncio
async def test_resolve_selected_view_party_filter_should_return_none_without_headers() -> None:
    result = await resolve_selected_view_party_filter(
        request=_build_request(),
        db=MagicMock(),
        current_user_id="user-1",
        logger=logging.getLogger(__name__),
    )

    assert result is None


@pytest.mark.asyncio
async def test_resolve_selected_view_party_filter_should_fail_closed_for_invalid_perspective() -> None:
    with patch(
        "src.services.view_scope.resolve_user_party_filter",
        new=AsyncMock(return_value=PartyFilter(party_ids=["party-1"])),
    ):
        result = await resolve_selected_view_party_filter(
            request=_build_request(
                {
                    "X-View-Perspective": "invalid",
                    "X-View-Party-Id": "party-1",
                }
            ),
            db=MagicMock(),
            current_user_id="user-1",
            logger=logging.getLogger(__name__),
        )

    assert result == PartyFilter(party_ids=[])


@pytest.mark.asyncio
async def test_resolve_selected_view_party_filter_should_narrow_to_selected_owner_scope() -> None:
    with patch(
        "src.services.view_scope.resolve_user_party_filter",
        new=AsyncMock(
            return_value=PartyFilter(
                party_ids=["party-1", "party-2"],
                owner_party_ids=["party-1", "party-2"],
                manager_party_ids=[],
            )
        ),
    ):
        result = await resolve_selected_view_party_filter(
            request=_build_request(
                {
                    "X-View-Perspective": "owner",
                    "X-View-Party-Id": "party-2",
                }
            ),
            db=MagicMock(),
            current_user_id="user-1",
            logger=logging.getLogger(__name__),
        )

    assert result == PartyFilter(
        party_ids=["party-2"],
        filter_mode="owner",
        owner_party_ids=["party-2"],
        manager_party_ids=[],
    )


@pytest.mark.asyncio
async def test_resolve_selected_view_party_filter_should_fail_closed_when_selected_party_not_in_scope(
) -> None:
    with patch(
        "src.services.view_scope.resolve_user_party_filter",
        new=AsyncMock(
            return_value=PartyFilter(
                party_ids=["party-1"],
                owner_party_ids=["party-1"],
                manager_party_ids=[],
            )
        ),
    ):
        result = await resolve_selected_view_party_filter(
            request=_build_request(
                {
                    "X-View-Perspective": "owner",
                    "X-View-Party-Id": "party-2",
                }
            ),
            db=MagicMock(),
            current_user_id="user-1",
            logger=logging.getLogger(__name__),
        )

    assert result == PartyFilter(party_ids=[])
