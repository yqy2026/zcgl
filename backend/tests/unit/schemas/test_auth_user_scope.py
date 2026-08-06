from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.schemas.auth import UserCreate, UserResponse, UserUpdate


def _user_create_payload() -> dict[str, object]:
    return {
        "username": "new-user",
        "email": "new-user@example.com",
        "phone": "13800000001",
        "full_name": "New User",
        "password": "SecurePass123!",
    }


@pytest.mark.parametrize("field", ["account_type", "organization_id"])
def test_general_user_create_rejects_scope_managed_fields(field: str) -> None:
    payload = _user_create_payload()
    payload[field] = "human" if field == "account_type" else "org-1"

    with pytest.raises(ValidationError):
        UserCreate.model_validate(payload)


@pytest.mark.parametrize("field", ["account_type", "organization_id"])
def test_general_user_update_rejects_scope_managed_fields(field: str) -> None:
    value = "human" if field == "account_type" else "org-1"

    with pytest.raises(ValidationError):
        UserUpdate.model_validate({field: value})


def test_user_response_exposes_immutable_account_and_organization_fields() -> None:
    now = datetime.now(UTC)

    response = UserResponse.model_validate(
        {
            "id": "user-1",
            "username": "user-1",
            "email": "user-1@example.com",
            "phone": "13800000001",
            "full_name": "User One",
            "is_active": True,
            "is_locked": False,
            "last_login_at": None,
            "account_type": "human",
            "organization_id": "org-1",
            "created_at": now,
            "updated_at": now,
        }
    )

    payload = response.model_dump()
    assert payload["account_type"] == "human"
    assert payload["organization_id"] == "org-1"
    assert "default_organization_id" not in payload
