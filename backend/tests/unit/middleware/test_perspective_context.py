from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.requests import Request

from src.middleware.auth import require_perspective_context
from src.services.authz.context_builder import SubjectContext

pytestmark = pytest.mark.asyncio


def _build_request(
    *,
    method: str,
    path: str,
    headers: list[tuple[bytes, bytes]] | None = None,
) -> Request:
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": b"",
        "headers": headers or [],
        "path_params": {},
    }

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(scope, receive)


class _UserStub:
    def __init__(self, user_id: str) -> None:
        self.id = user_id
        self.is_active = True


async def test_require_perspective_context_should_build_union_context_when_header_missing() -> (
    None
):
    checker = require_perspective_context()
    request = _build_request(
        method="GET",
        path="/api/v1/analytics/comprehensive",
    )

    with (
        patch(
            "src.middleware.auth.authz_service.context_builder.build_subject_context",
            new=AsyncMock(
                return_value=SubjectContext(
                    user_id="user-1",
                    owner_party_ids=["owner-1"],
                    manager_party_ids=["manager-1"],
                    headquarters_party_ids=[],
                    role_ids=[],
                )
            ),
        ),
        patch(
            "src.middleware.auth.RBACService.is_admin",
            new=AsyncMock(return_value=False),
        ),
    ):
        result = await checker(
            request=request,
            current_user=_UserStub("user-1"),
            db=MagicMock(),
        )

    assert result is not None
    assert result.perspective == "all"
    assert result.allowed_perspectives == ["owner", "manager"]
    assert result.effective_party_ids == ["manager-1", "owner-1"]
    assert result.source == "auto"


async def test_require_perspective_context_should_allow_neutral_auth_endpoint_without_header() -> (
    None
):
    checker = require_perspective_context()
    request = _build_request(
        method="GET",
        path="/api/v1/auth/me/capabilities",
    )

    result = await checker(
        request=request,
        current_user=_UserStub("user-1"),
        db=MagicMock(),
    )

    assert result is None


async def test_require_perspective_context_should_reject_invalid_header_value() -> None:
    checker = require_perspective_context()
    request = _build_request(
        method="GET",
        path="/api/v1/analytics/comprehensive",
        headers=[(b"x-perspective", b"tenant")],
    )

    with pytest.raises(Exception) as exc_info:
        await checker(
            request=request,
            current_user=_UserStub("user-1"),
            db=MagicMock(),
        )

    error = exc_info.value
    assert getattr(error, "status_code", None) == 400


async def test_require_perspective_context_should_build_owner_effective_party_ids() -> (
    None
):
    checker = require_perspective_context()
    request = _build_request(
        method="GET",
        path="/api/v1/analytics/comprehensive",
        headers=[(b"x-perspective", b"owner")],
    )

    with (
        patch(
            "src.middleware.auth.authz_service.context_builder.build_subject_context",
            new=AsyncMock(
                return_value=SubjectContext(
                    user_id="user-1",
                    owner_party_ids=["owner-1"],
                    manager_party_ids=["manager-1"],
                    headquarters_party_ids=[],
                    role_ids=[],
                )
            ),
        ),
        patch(
            "src.middleware.auth.RBACService.is_admin",
            new=AsyncMock(return_value=False),
        ),
    ):
        result = await checker(
            request=request,
            current_user=_UserStub("user-1"),
            db=MagicMock(),
        )

    assert result is not None
    assert result.perspective == "owner"
    assert result.allowed_perspectives == ["owner", "manager"]
    assert result.effective_party_ids == ["owner-1"]


async def test_require_perspective_context_should_allow_admin_without_header() -> None:
    checker = require_perspective_context(resource_type="project")
    request = _build_request(
        method="GET",
        path="/api/v1/projects/",
    )

    with (
        patch(
            "src.middleware.auth.authz_service.context_builder.build_subject_context",
            new=AsyncMock(
                return_value=SubjectContext(
                    user_id="admin-1",
                    owner_party_ids=[],
                    manager_party_ids=[],
                    headquarters_party_ids=[],
                    role_ids=[],
                )
            ),
        ),
        patch(
            "src.middleware.auth.RBACService.is_admin",
            new=AsyncMock(return_value=True),
        ),
    ):
        result = await checker(
            request=request,
            current_user=_UserStub("admin-1"),
            db=MagicMock(),
        )

    assert result is not None
    assert result.perspective == "all"
    assert result.allowed_perspectives == ["owner", "manager"]
    assert result.effective_party_ids == []
    assert result.source == "auto"


async def test_require_perspective_context_should_allow_all_header_union() -> None:
    checker = require_perspective_context()
    request = _build_request(
        method="GET",
        path="/api/v1/projects/",
        headers=[(b"x-perspective", b"all")],
    )

    with (
        patch(
            "src.middleware.auth.authz_service.context_builder.build_subject_context",
            new=AsyncMock(
                return_value=SubjectContext(
                    user_id="user-1",
                    owner_party_ids=["owner-1"],
                    manager_party_ids=["manager-1"],
                    headquarters_party_ids=[],
                    role_ids=[],
                )
            ),
        ),
        patch(
            "src.middleware.auth.RBACService.is_admin",
            new=AsyncMock(return_value=False),
        ),
    ):
        result = await checker(
            request=request,
            current_user=_UserStub("user-1"),
            db=MagicMock(),
        )

    assert result is not None
    assert result.perspective == "all"
    assert result.effective_party_ids == ["manager-1", "owner-1"]
    assert result.source == "header"


async def test_require_perspective_context_should_build_single_scope_when_single_binding_header_missing() -> (
    None
):
    checker = require_perspective_context()
    request = _build_request(
        method="GET",
        path="/api/v1/projects/",
    )

    with (
        patch(
            "src.middleware.auth.authz_service.context_builder.build_subject_context",
            new=AsyncMock(
                return_value=SubjectContext(
                    user_id="user-1",
                    owner_party_ids=["owner-1"],
                    manager_party_ids=[],
                    headquarters_party_ids=[],
                    role_ids=[],
                )
            ),
        ),
        patch(
            "src.middleware.auth.RBACService.is_admin",
            new=AsyncMock(return_value=False),
        ),
    ):
        result = await checker(
            request=request,
            current_user=_UserStub("user-1"),
            db=MagicMock(),
        )

    assert result is not None
    assert result.perspective == "all"
    assert result.allowed_perspectives == ["owner"]
    assert result.effective_party_ids == ["owner-1"]
