"""Data-scope middleware must fail business paths with stable Party scope 403."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from starlette.requests import Request

from src.core.exception_handler import PartyScopeForbiddenError
from src.middleware.auth import require_data_scope_context
from src.services.authz.context_builder import SubjectContext

pytestmark = pytest.mark.asyncio


def _build_request(*, method: str, path: str) -> Request:
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": b"",
        "headers": [],
        "path_params": {},
    }

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(scope, receive)


class _UserStub:
    def __init__(self, user_id: str) -> None:
        self.id = user_id
        self.is_active = True


async def test_data_scope_rejects_invalid_party_scope_with_stable_403() -> None:
    checker = require_data_scope_context(resource_type="asset")
    request = _build_request(
        method="GET",
        path="/api/v1/assets",
    )

    with (
        patch(
            "src.middleware.auth.authz_service.context_builder.build_subject_context",
            new=AsyncMock(
                return_value=SubjectContext(
                    user_id="user-1",
                    owner_party_ids=[],
                    manager_party_ids=[],
                    role_ids=[],
                    scope_error_code="PARTY_SCOPE_MISSING",
                )
            ),
        ),
        patch(
            "src.middleware.auth.RBACService.is_admin",
            new=AsyncMock(return_value=False),
        ),
        pytest.raises(PartyScopeForbiddenError) as exc_info,
    ):
        await checker(
            request=request,
            current_user=_UserStub("user-1"),
            db=AsyncMock(),
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "PARTY_SCOPE_MISSING"
