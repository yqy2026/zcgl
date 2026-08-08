"""Write-contract tests for an Organization's represented Party."""

import pytest
from pydantic import ValidationError

from src.schemas.organization import (
    OrganizationCreate,
    OrganizationPartyScopeBatchPreviewRequest,
    OrganizationPartyScopeCommitRequest,
    OrganizationPartyScopeProposal,
    OrganizationResponse,
    OrganizationUpdate,
)


def test_only_response_and_dedicated_proposal_expose_represented_party_pair() -> None:
    for schema in (OrganizationCreate, OrganizationUpdate):
        assert "represented_party_id" not in schema.model_fields
        assert "represented_party_perspective" not in schema.model_fields

    for schema in (OrganizationResponse, OrganizationPartyScopeProposal):
        assert "represented_party_id" in schema.model_fields
        assert "represented_party_perspective" in schema.model_fields


def test_organization_update_rejects_sensitive_party_scope_fields() -> None:
    with pytest.raises(ValidationError):
        OrganizationUpdate.model_validate({"represented_party_id": "party-1"})


def test_organization_party_scope_proposal_can_clear_represented_party_pair() -> None:
    proposal = OrganizationPartyScopeProposal.model_validate(
        {
            "represented_party_id": None,
            "represented_party_perspective": None,
        }
    )

    assert proposal.represented_party_id is None
    assert proposal.represented_party_perspective is None


def test_organization_party_scope_proposal_requires_the_complete_pair() -> None:
    with pytest.raises(ValidationError):
        OrganizationPartyScopeProposal.model_validate(
            {"represented_party_id": "party-1"}
        )


def test_organization_party_scope_commit_requires_reason_and_idempotency_key() -> None:
    with pytest.raises(ValidationError):
        OrganizationPartyScopeCommitRequest.model_validate(
            {
                "preview_token": "token-value",
                "reason": "   ",
                "idempotency_key": "request-1",
            }
        )


def test_organization_party_scope_batch_requires_unique_multiple_organizations() -> (
    None
):
    with pytest.raises(ValidationError):
        OrganizationPartyScopeBatchPreviewRequest.model_validate(
            {
                "items": [
                    {
                        "organization_id": "organization-1",
                        "represented_party_id": "party-1",
                        "represented_party_perspective": "owner",
                    }
                ]
            }
        )

    with pytest.raises(ValidationError):
        OrganizationPartyScopeBatchPreviewRequest.model_validate(
            {
                "items": [
                    {
                        "organization_id": "organization-1",
                        "represented_party_id": "party-1",
                        "represented_party_perspective": "owner",
                    },
                    {
                        "organization_id": "organization-1",
                        "represented_party_id": "party-2",
                        "represented_party_perspective": "manager",
                    },
                ]
            }
        )
