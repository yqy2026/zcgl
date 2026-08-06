"""Write-contract tests for user Party-scope batch requests."""

import pytest
from pydantic import ValidationError

from src.schemas.user_party_scope import (
    UserPartyScopeBatchCommitRequest,
    UserPartyScopeBatchPreviewRequest,
)


def test_user_party_scope_batch_requires_unique_multiple_users() -> None:
    with pytest.raises(ValidationError):
        UserPartyScopeBatchPreviewRequest.model_validate(
            {
                "items": [
                    {
                        "user_id": "user-1",
                        "operation": "create",
                        "party_id": "party-1",
                        "relation_type": "owner",
                    }
                ]
            }
        )

    with pytest.raises(ValidationError):
        UserPartyScopeBatchPreviewRequest.model_validate(
            {
                "items": [
                    {
                        "user_id": "user-1",
                        "operation": "create",
                        "party_id": "party-1",
                        "relation_type": "owner",
                    },
                    {
                        "user_id": "user-1",
                        "operation": "create",
                        "party_id": "party-2",
                        "relation_type": "manager",
                    },
                ]
            }
        )


def test_user_party_scope_batch_proposal_reuses_operation_shape_validation() -> None:
    with pytest.raises(ValidationError):
        UserPartyScopeBatchPreviewRequest.model_validate(
            {
                "items": [
                    {
                        "user_id": "user-1",
                        "operation": "create",
                        "party_id": "party-1",
                    },
                    {
                        "user_id": "user-2",
                        "operation": "create",
                        "party_id": "party-2",
                        "relation_type": "manager",
                    },
                ]
            }
        )


def test_user_party_scope_batch_commit_requires_non_blank_confirmation() -> None:
    with pytest.raises(ValidationError):
        UserPartyScopeBatchCommitRequest.model_validate(
            {
                "preview_token": "token-value",
                "reason": "   ",
                "idempotency_key": "request-1",
            }
        )
