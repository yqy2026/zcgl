from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.schemas.organization import (
    OrganizationPartyScopeCommitRequest,
    OrganizationPartyScopeCommitResponse,
    OrganizationPartyScopeImpact,
    OrganizationPartyScopePreviewResponse,
    OrganizationPartyScopeProposal,
    OrganizationPartyScopeState,
)

pytestmark = pytest.mark.api


@pytest.mark.asyncio
async def test_preview_endpoint_passes_actor_and_proposal_to_sensitive_service() -> None:
    from src.api.v1.auth import organization as module

    preview = OrganizationPartyScopePreviewResponse(
        organization_id="org-1",
        before_scope=OrganizationPartyScopeState(),
        after_scope=OrganizationPartyScopeState(
            represented_party_id="party-1",
            represented_party_perspective="owner",
            effective_party_id="party-1",
            effective_party_perspective="owner",
            source_organization_id="org-1",
        ),
        impact=OrganizationPartyScopeImpact(
            organization_count=1,
            organization_scope_change_count=1,
            user_count=1,
            user_scope_change_count=1,
        ),
        preview_token="opaque-token",
        expires_at=datetime.now(UTC),
    )
    service = MagicMock()
    service.preview = AsyncMock(return_value=preview)
    proposal = OrganizationPartyScopeProposal(
        represented_party_id="party-1",
        represented_party_perspective="owner",
    )
    db = MagicMock()

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "organization_party_scope_service", service)
        result = await module.preview_organization_party_scope(
            org_id="org-1",
            proposal=proposal,
            db=db,
            current_user=MagicMock(id="actor-1"),
            _authz_ctx=MagicMock(),
        )

    assert result is preview
    service.preview.assert_awaited_once_with(
        db,
        organization_id="org-1",
        proposal=proposal,
        actor_id="actor-1",
    )


@pytest.mark.asyncio
async def test_commit_endpoint_passes_actor_and_request_to_sensitive_service() -> None:
    from src.api.v1.auth import organization as module

    commit = OrganizationPartyScopeCommitResponse.model_validate(
        {
            "organization": {
                "id": "org-1",
                "name": "Root",
                "code": "ORG-1",
                "level": 1,
                "sort_order": 0,
                "parent_id": None,
                "type": "headquarter",
                "status": "active",
                "description": None,
                "path": "/org-1",
                "is_deleted": False,
                "created_at": "2026-08-04T12:00:00",
                "updated_at": "2026-08-04T12:00:00",
                "created_by": None,
                "updated_by": "actor-1",
                "represented_party_id": "party-1",
                "represented_party_perspective": "owner",
                "children": [],
            },
            "before_scope": {},
            "after_scope": {
                "represented_party_id": "party-1",
                "represented_party_perspective": "owner",
                "effective_party_id": "party-1",
                "effective_party_perspective": "owner",
                "source_organization_id": "org-1",
            },
            "impact": {
                "organization_count": 1,
                "organization_scope_change_count": 1,
                "user_count": 1,
                "user_scope_change_count": 1,
            },
            "committed_at": "2026-08-04T12:00:00",
            "idempotent": False,
        }
    )
    service = MagicMock()
    service.commit = AsyncMock(return_value=commit)
    request = OrganizationPartyScopeCommitRequest(
        preview_token="opaque-token",
        reason="组织权属调整",
        idempotency_key="request-1",
    )
    db = MagicMock()

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "organization_party_scope_service", service)
        result = await module.commit_organization_party_scope(
            org_id="org-1",
            request=request,
            db=db,
            current_user=MagicMock(id="actor-1"),
            _authz_ctx=MagicMock(),
        )

    assert result is commit
    service.commit.assert_awaited_once_with(
        db,
        organization_id="org-1",
        request=request,
        actor_id="actor-1",
    )
