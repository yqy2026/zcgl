"""Tests for ABAC dependency helper in middleware.auth."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from src.middleware.auth import require_authz
from src.services.authz.context_builder import SubjectContext
from src.services.authz.engine import AuthzDecision

pytestmark = pytest.mark.asyncio


def _build_request(
    *,
    method: str,
    path: str,
    path_params: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
) -> Request:
    payload = b""
    headers: list[tuple[bytes, bytes]] = []
    if body is not None:
        payload = json.dumps(body).encode("utf-8")
        headers.append((b"content-type", b"application/json"))

    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": b"",
        "headers": headers,
        "path_params": path_params or {},
    }
    consumed = False

    async def receive() -> dict[str, Any]:
        nonlocal consumed
        if consumed:
            return {"type": "http.request", "body": b"", "more_body": False}
        consumed = True
        return {"type": "http.request", "body": payload, "more_body": False}

    return Request(scope, receive)


class _UserStub:
    def __init__(self, user_id: str) -> None:
        self.id = user_id


def _mapping_result(payload: dict[str, Any] | None) -> MagicMock:
    result = MagicMock()
    mappings = MagicMock()
    mappings.one_or_none.return_value = payload
    result.mappings.return_value = mappings
    return result


@pytest.mark.asyncio
async def test_require_authz_ignores_untrusted_body_scope_and_prefers_trusted_context() -> None:
    checker = require_authz(
        action="update",
        resource_type="asset",
        resource_id="{asset_id}",
    )
    request = _build_request(
        method="PUT",
        path="/api/v1/assets/asset-1",
        path_params={"asset_id": "asset-1"},
        body={
            "owner_party_id": "forged-owner-party",
            "manager_party_id": "forged-manager-party",
            "tenant_party_id": "forged-tenant-party",
        },
    )

    with (
        patch.object(
            checker,
            "_resolve_trusted_resource_context",
            new=AsyncMock(
                return_value={
                    "owner_party_id": "trusted-owner-party",
                    "manager_party_id": "trusted-manager-party",
                }
            ),
        ),
        patch(
            "src.middleware.auth.authz_service.check_access",
            new=AsyncMock(
                return_value=AuthzDecision(
                    allowed=True,
                    reason_code="allow",
                )
            ),
        ) as mock_check_access,
    ):
        result = await checker(
            request=request,
            current_user=_UserStub("user-1"),
            db=MagicMock(),
        )

    assert result.allowed is True
    assert result.resource_id == "asset-1"
    assert result.resource_context["owner_party_id"] == "trusted-owner-party"
    assert result.resource_context["manager_party_id"] == "trusted-manager-party"
    assert result.resource_context["asset_id"] == "asset-1"
    assert "forged-owner-party" not in result.resource_context.values()
    assert "forged-manager-party" not in result.resource_context.values()
    assert "tenant_party_id" not in result.resource_context
    assert mock_check_access.await_count == 1
    _args, kwargs = mock_check_access.await_args
    assert kwargs["user_id"] == "user-1"
    assert kwargs["resource_type"] == "asset"
    assert kwargs["action"] == "update"
    assert kwargs["resource_id"] == "asset-1"
    assert kwargs["resource"]["asset_id"] == "asset-1"
    assert kwargs["resource"]["owner_party_id"] == "trusted-owner-party"
    assert kwargs["resource"]["manager_party_id"] == "trusted-manager-party"


@pytest.mark.asyncio
async def test_require_authz_denied_read_maps_to_not_found() -> None:
    checker = require_authz(
        action="read",
        resource_type="asset",
        resource_id="{asset_id}",
        deny_as_not_found=True,
    )
    request = _build_request(
        method="GET",
        path="/api/v1/assets/asset-1",
        path_params={"asset_id": "asset-1"},
    )

    with patch(
        "src.middleware.auth.authz_service.check_access",
        new=AsyncMock(
            return_value=AuthzDecision(
                allowed=False,
                reason_code="deny",
            )
        ),
    ):
        with pytest.raises(Exception) as exc_info:
            await checker(
                request=request,
                current_user=_UserStub("user-1"),
                db=MagicMock(),
            )

    error = exc_info.value
    assert getattr(error, "status_code", None) == 404


@pytest.mark.asyncio
async def test_require_authz_denied_write_maps_to_forbidden() -> None:
    checker = require_authz(
        action="delete",
        resource_type="project",
        resource_id="{project_id}",
    )
    request = _build_request(
        method="DELETE",
        path="/api/v1/projects/project-1",
        path_params={"project_id": "project-1"},
    )

    with patch(
        "src.middleware.auth.authz_service.check_access",
        new=AsyncMock(
            return_value=AuthzDecision(
                allowed=False,
                reason_code="deny",
            )
        ),
    ):
        with pytest.raises(Exception) as exc_info:
            await checker(
                request=request,
                current_user=_UserStub("user-1"),
                db=MagicMock(),
            )

    error = exc_info.value
    assert getattr(error, "status_code", None) == 403


@pytest.mark.asyncio
async def test_load_organization_scope_context_includes_party_scope_fields() -> None:
    checker = require_authz(
        action="read",
        resource_type="organization",
        resource_id="{org_id}",
    )
    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock(
        side_effect=[
            _mapping_result(
                {
                    "organization_id": "org-1",
                    "organization_code": "ORG-001",
                    "organization_name": "Org One",
                }
            ),
            _mapping_result({"party_id": "party-1"}),
        ]
    )

    context = await checker._load_organization_scope_context(
        db=db,
        organization_id="org-1",
    )

    assert context["organization_id"] == "org-1"
    assert context["party_id"] == "party-1"
    assert context["owner_party_id"] == "party-1"
    assert context["manager_party_id"] == "party-1"


@pytest.mark.asyncio
async def test_load_organization_scope_context_falls_back_to_org_id_when_party_missing() -> None:
    checker = require_authz(
        action="read",
        resource_type="organization",
        resource_id="{org_id}",
    )
    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock(
        side_effect=[
            _mapping_result(
                {
                    "organization_id": "org-legacy",
                    "organization_code": "ORG-LEGACY",
                    "organization_name": "Legacy Org",
                }
            ),
            _mapping_result(None),
            _mapping_result(None),
            _mapping_result(None),
            _mapping_result(None),
        ]
    )

    context = await checker._load_organization_scope_context(
        db=db,
        organization_id="org-legacy",
    )

    assert context["organization_id"] == "org-legacy"
    assert context["party_id"] == "org-legacy"
    assert context["owner_party_id"] == "org-legacy"
    assert context["manager_party_id"] == "org-legacy"


@pytest.mark.asyncio
async def test_load_property_certificate_scope_context_includes_party_scope_fields() -> None:
    checker = require_authz(
        action="read",
        resource_type="property_certificate",
        resource_id="{certificate_id}",
    )
    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock(
        side_effect=[
            _mapping_result(
                {
                    "certificate_id": "cert-1",
                    "organization_id": "org-1",
                }
            ),
            _mapping_result({"party_id": "party-1"}),
        ]
    )

    context = await checker._load_property_certificate_scope_context(
        db=db,
        certificate_id="cert-1",
    )

    assert context["certificate_id"] == "cert-1"
    assert context["party_id"] == "party-1"
    assert context["owner_party_id"] == "party-1"
    assert context["manager_party_id"] == "party-1"


@pytest.mark.asyncio
async def test_load_property_certificate_scope_context_falls_back_to_unscoped_when_party_missing() -> None:
    checker = require_authz(
        action="read",
        resource_type="property_certificate",
        resource_id="{certificate_id}",
    )
    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock(
        side_effect=[
            _mapping_result(
                {
                    "certificate_id": "cert-legacy",
                    "organization_id": "org-legacy",
                }
            ),
            _mapping_result(None),
            _mapping_result(None),
        ]
    )

    context = await checker._load_property_certificate_scope_context(
        db=db,
        certificate_id="cert-legacy",
    )

    assert context["certificate_id"] == "cert-legacy"
    assert context["party_id"] == "__unscoped__:property_certificate:cert-legacy"
    assert context["owner_party_id"] == "__unscoped__:property_certificate:cert-legacy"
    assert context["manager_party_id"] == "__unscoped__:property_certificate:cert-legacy"


@pytest.mark.asyncio
async def test_load_asset_scope_context_uses_party_columns_directly() -> None:
    checker = require_authz(
        action="read",
        resource_type="asset",
        resource_id="{asset_id}",
    )
    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock(
        side_effect=[
            _mapping_result(
                {
                    "asset_id": "asset-1",
                    "owner_party_id": "owner-party-1",
                    "manager_party_id": "manager-party-1",
                }
            ),
        ]
    )

    context = await checker._load_asset_scope_context(
        db=db,
        asset_id="asset-1",
    )

    assert context["asset_id"] == "asset-1"
    assert context["owner_party_id"] == "owner-party-1"
    assert context["manager_party_id"] == "manager-party-1"
    assert context["party_id"] == "owner-party-1"


@pytest.mark.asyncio
async def test_load_project_scope_context_uses_manager_party_directly() -> None:
    checker = require_authz(
        action="read",
        resource_type="project",
        resource_id="{project_id}",
    )
    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock(
        side_effect=[
            _mapping_result(
                {
                    "project_id": "project-1",
                    "manager_party_id": "manager-party-1",
                }
            ),
        ]
    )

    context = await checker._load_project_scope_context(
        db=db,
        project_id="project-1",
    )

    assert context["project_id"] == "project-1"
    assert context["manager_party_id"] == "manager-party-1"
    assert context["party_id"] == "manager-party-1"


@pytest.mark.asyncio
async def test_load_rent_contract_scope_context_uses_party_columns_directly() -> None:
    checker = require_authz(
        action="read",
        resource_type="rent_contract",
        resource_id="{contract_id}",
    )
    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock(
        side_effect=[
            _mapping_result(
                {
                    "contract_id": "contract-1",
                    "owner_party_id": "owner-party-1",
                    "manager_party_id": "manager-party-1",
                    "tenant_party_id": "tenant-party-1",
                }
            ),
        ]
    )

    context = await checker._load_rent_contract_scope_context(
        db=db,
        contract_id="contract-1",
    )

    assert context["contract_id"] == "contract-1"
    assert context["tenant_party_id"] == "tenant-party-1"
    assert context["owner_party_id"] == "owner-party-1"
    assert context["manager_party_id"] == "manager-party-1"
    assert context["party_id"] == "owner-party-1"


@pytest.mark.asyncio
async def test_resolve_trusted_resource_context_loads_ownership_party_scope() -> None:
    checker = require_authz(
        action="read",
        resource_type="ownership",
        resource_id="{ownership_id}",
    )
    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock(
        side_effect=[
            _mapping_result(
                {
                    "ownership_id": "ownership-1",
                    "ownership_code": "OWN-001",
                    "ownership_name": "Ownership One",
                }
            ),
            _mapping_result({"party_id": "party-1"}),
        ]
    )

    context = await checker._resolve_trusted_resource_context(
        db=db,
        resource_id="ownership-1",
    )

    assert context["ownership_id"] == "ownership-1"
    assert context["party_id"] == "party-1"
    assert context["owner_party_id"] == "party-1"
    assert context["manager_party_id"] == "party-1"


@pytest.mark.asyncio
async def test_load_role_scope_context_uses_role_party_id_when_present() -> None:
    checker = require_authz(
        action="read",
        resource_type="role",
        resource_id="{role_id}",
    )
    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock(
        side_effect=[
            _mapping_result(
                {
                    "role_id": "role-1",
                    "party_id": "party-1",
                    "organization_id": None,
                }
            ),
        ]
    )

    context = await checker._load_role_scope_context(
        db=db,
        role_id="role-1",
    )

    assert context["role_id"] == "role-1"
    assert context["party_id"] == "party-1"
    assert context["owner_party_id"] == "party-1"
    assert context["manager_party_id"] == "party-1"


@pytest.mark.asyncio
async def test_load_role_scope_context_falls_back_to_unscoped_when_party_missing() -> None:
    checker = require_authz(
        action="read",
        resource_type="role",
        resource_id="{role_id}",
    )
    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock(
        side_effect=[
            _mapping_result(
                {
                    "role_id": "role-legacy",
                    "party_id": None,
                }
            ),
        ]
    )

    context = await checker._load_role_scope_context(
        db=db,
        role_id="role-legacy",
    )

    assert context["role_id"] == "role-legacy"
    assert context["party_id"] == "__unscoped__:role:role-legacy"
    assert context["owner_party_id"] == "__unscoped__:role:role-legacy"
    assert context["manager_party_id"] == "__unscoped__:role:role-legacy"


@pytest.mark.asyncio
async def test_load_user_scope_context_uses_user_binding_party_id_when_present() -> None:
    checker = require_authz(
        action="read",
        resource_type="user",
        resource_id="{user_id}",
    )
    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock(
        side_effect=[
            _mapping_result(
                {
                    "user_id": "user-1",
                    "default_organization_id": "org-1",
                }
            ),
            _mapping_result({"party_id": "party-1"}),
        ]
    )

    context = await checker._load_user_scope_context(
        db=db,
        user_id="user-1",
    )

    assert context["user_id"] == "user-1"
    assert context["organization_id"] == "org-1"
    assert context["party_id"] == "party-1"
    assert context["owner_party_id"] == "party-1"
    assert context["manager_party_id"] == "party-1"

    binding_stmt = db.execute.await_args_list[1].args[0]
    binding_stmt_sql = str(binding_stmt).lower()
    assert "user_party_bindings.valid_from <=" in binding_stmt_sql
    assert "user_party_bindings.valid_to is null" in binding_stmt_sql
    assert "user_party_bindings.valid_to >=" in binding_stmt_sql
    assert "user_party_bindings.valid_from desc" in binding_stmt_sql
    assert "user_party_bindings.created_at desc" in binding_stmt_sql
    assert "user_party_bindings.created_at asc" not in binding_stmt_sql


@pytest.mark.asyncio
async def test_load_user_scope_context_uses_unscoped_sentinel_when_no_party_scope() -> None:
    checker = require_authz(
        action="read",
        resource_type="user",
        resource_id="{user_id}",
    )
    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock(
        side_effect=[
            _mapping_result(
                {
                    "user_id": "user-no-scope",
                    "default_organization_id": None,
                }
            ),
            _mapping_result(None),
        ]
    )

    context = await checker._load_user_scope_context(
        db=db,
        user_id="user-no-scope",
    )

    assert context["user_id"] == "user-no-scope"
    assert context["party_id"] == "__unscoped__:user:user-no-scope"
    assert context["owner_party_id"] == "__unscoped__:user:user-no-scope"
    assert context["manager_party_id"] == "__unscoped__:user:user-no-scope"


@pytest.mark.asyncio
async def test_load_task_scope_context_uses_task_user_party_scope_when_present() -> None:
    checker = require_authz(
        action="read",
        resource_type="task",
        resource_id="{task_id}",
    )
    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock(
        return_value=_mapping_result(
            {
                "task_id": "task-1",
                "user_id": "user-1",
            }
        )
    )

    with patch.object(
        checker,
        "_load_user_scope_context",
        new=AsyncMock(
            return_value={
                "user_id": "user-1",
                "organization_id": "org-1",
                "party_id": "party-1",
                "owner_party_id": "owner-party-1",
                "manager_party_id": "manager-party-1",
            }
        ),
    ) as mock_load_user_scope:
        context = await checker._load_task_scope_context(
            db=db,
            task_id="task-1",
        )

    assert context["task_id"] == "task-1"
    assert context["user_id"] == "user-1"
    assert context["organization_id"] == "org-1"
    assert context["party_id"] == "party-1"
    assert context["owner_party_id"] == "owner-party-1"
    assert context["manager_party_id"] == "manager-party-1"
    mock_load_user_scope.assert_awaited_once_with(
        db=db,
        user_id="user-1",
    )


@pytest.mark.asyncio
async def test_load_task_scope_context_uses_unscoped_sentinel_when_task_user_missing() -> None:
    checker = require_authz(
        action="read",
        resource_type="task",
        resource_id="{task_id}",
    )
    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock(
        return_value=_mapping_result(
            {
                "task_id": "task-no-owner",
                "user_id": None,
            }
        )
    )

    context = await checker._load_task_scope_context(
        db=db,
        task_id="task-no-owner",
    )

    expected_sentinel = "__unscoped__:task:task-no-owner"
    assert context["task_id"] == "task-no-owner"
    assert context["party_id"] == expected_sentinel
    assert context["owner_party_id"] == expected_sentinel
    assert context["manager_party_id"] == expected_sentinel
    assert "user_id" not in context


@pytest.mark.asyncio
async def test_require_authz_collection_read_infers_party_scope_hint() -> None:
    checker = require_authz(
        action="read",
        resource_type="asset",
    )
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
                    owner_party_ids=["owner-party-1"],
                    manager_party_ids=["manager-party-1"],
                    headquarters_party_ids=[],
                    role_ids=[],
                )
            ),
        ),
        patch(
            "src.middleware.auth.authz_service.check_access",
            new=AsyncMock(
                return_value=AuthzDecision(
                    allowed=True,
                    reason_code="allow",
                )
            ),
        ) as mock_check_access,
    ):
        result = await checker(
            request=request,
            current_user=_UserStub("user-1"),
            db=MagicMock(),
        )

    assert result.allowed is True
    assert result.resource_id is None
    assert result.resource_context["owner_party_id"] == "owner-party-1"
    assert result.resource_context["manager_party_id"] == "manager-party-1"
    assert result.resource_context["party_id"] == "owner-party-1"
    assert result.resource_context["owner_party_ids"] == ["owner-party-1"]
    assert result.resource_context["manager_party_ids"] == ["manager-party-1"]

    _args, kwargs = mock_check_access.await_args
    assert kwargs["resource"]["owner_party_id"] == "owner-party-1"
    assert kwargs["resource"]["manager_party_id"] == "manager-party-1"
    assert kwargs["resource"]["party_id"] == "owner-party-1"
    assert kwargs["resource"]["owner_party_ids"] == ["owner-party-1"]
    assert kwargs["resource"]["manager_party_ids"] == ["manager-party-1"]


@pytest.mark.asyncio
async def test_require_authz_collection_read_keeps_explicit_scope_context() -> None:
    checker = require_authz(
        action="read",
        resource_type="asset",
        resource_context={"owner_party_id": "explicit-owner"},
    )
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
                    owner_party_ids=["owner-party-1"],
                    manager_party_ids=["manager-party-1"],
                    headquarters_party_ids=[],
                    role_ids=[],
                )
            ),
        ),
        patch(
            "src.middleware.auth.authz_service.check_access",
            new=AsyncMock(
                return_value=AuthzDecision(
                    allowed=True,
                    reason_code="allow",
                )
            ),
        ) as mock_check_access,
    ):
        result = await checker(
            request=request,
            current_user=_UserStub("user-1"),
            db=MagicMock(),
        )

    assert result.allowed is True
    assert result.resource_context["owner_party_id"] == "explicit-owner"
    assert result.resource_context["manager_party_id"] == "manager-party-1"
    assert result.resource_context["party_id"] == "owner-party-1"

    _args, kwargs = mock_check_access.await_args
    assert kwargs["resource"]["owner_party_id"] == "explicit-owner"
    assert kwargs["resource"]["manager_party_id"] == "manager-party-1"
