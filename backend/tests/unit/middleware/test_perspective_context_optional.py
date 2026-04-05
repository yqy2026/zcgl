from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.middleware.auth import require_perspective_context
from src.services.authz.context_builder import SubjectContext

from .test_perspective_context import _build_request, _UserStub

pytestmark = pytest.mark.asyncio


async def test_no_perspective_header_returns_all_binding_context() -> None:
    checker = require_perspective_context()
    request = _build_request(method="GET", path="/api/v1/assets/")

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
    assert result.source == "auto"


async def test_no_perspective_header_admin_bypass() -> None:
    checker = require_perspective_context(resource_type="project")
    request = _build_request(method="GET", path="/api/v1/projects/")

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
            "src.middleware.auth.RBACService.is_admin", new=AsyncMock(return_value=True)
        ),
    ):
        result = await checker(
            request=request,
            current_user=_UserStub("admin-1"),
            db=MagicMock(),
        )

    assert result is not None
    assert result.perspective == "all"
    assert result.effective_party_ids == []


async def test_perspective_all_header_returns_union_context() -> None:
    checker = require_perspective_context()
    request = _build_request(
        method="GET",
        path="/api/v1/assets/",
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


async def test_single_binding_user_no_header_returns_single_scope() -> None:
    checker = require_perspective_context()
    request = _build_request(method="GET", path="/api/v1/assets/")

    with (
        patch(
            "src.middleware.auth.authz_service.context_builder.build_subject_context",
            new=AsyncMock(
                return_value=SubjectContext(
                    user_id="user-1",
                    owner_party_ids=[],
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
    assert result.allowed_perspectives == ["manager"]
    assert result.effective_party_ids == ["manager-1"]


async def test_non_exempt_path_without_header_no_longer_400() -> None:
    checker = require_perspective_context()
    request = _build_request(method="GET", path="/api/v1/analytics/comprehensive")

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
