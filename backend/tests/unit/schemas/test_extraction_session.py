"""Contract tests for unified document extraction session schemas."""

import pytest
from pydantic import ValidationError

from src.schemas.extraction_session import ExtractionSessionConfirmRequest


def test_confirm_accepts_only_explicit_field_actions_and_existing_ids():
    payload = ExtractionSessionConfirmRequest.model_validate(
        {
            "actions": [
                {
                    "field_key": "contract_number",
                    "action": "manual",
                    "value": "HT-2026-001",
                }
            ],
            "party_ids": {
                "operator_party_id": "party-1",
                "owner_party_id": "party-2",
                "lessor_party_id": "party-3",
                "lessee_party_id": "party-4",
            },
            "asset_ids": ["asset-1"],
        }
    )

    assert payload.actions[0].action == "manual"
    assert payload.party_ids.operator_party_id == "party-1"


@pytest.mark.parametrize("forbidden_key", ["field_sources", "accept_all", "confirmed_field_keys"])
def test_confirm_rejects_client_owned_sources_and_bulk_confirmation(forbidden_key):
    with pytest.raises(ValidationError):
        ExtractionSessionConfirmRequest.model_validate(
            {
                "actions": [],
                forbidden_key: {"contract_number": "manual"},
            }
        )
