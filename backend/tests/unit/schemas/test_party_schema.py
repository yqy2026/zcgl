"""Unit tests for party write schemas."""

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from src.schemas import party as party_schema
from src.schemas.party import (
    PartyCreate,
    PartyResponse,
    PartyUpdate,
    UserPartyBindingCreate,
    UserPartyBindingResponse,
    UserPartyBindingUpdate,
    UserPartyBindingUpsert,
)


def test_party_create_accepts_public_metadata_field() -> None:
    payload = {
        "party_type": "legal_entity",
        "name": "总部",
        "identifier_type": "unified_social_credit_code",
        "identifier_value": "91440101-231229726P",
        "metadata": {"source": "api"},
    }

    party = PartyCreate.model_validate(payload)

    assert party.metadata == {"source": "api"}
    assert "code" not in PartyCreate.model_fields


def test_party_create_rejects_client_supplied_code() -> None:
    with pytest.raises(ValidationError):
        PartyCreate.model_validate(
            {
                "party_type": "legal_entity",
                "name": "总部",
                "code": "LE-999999",
            }
        )


def test_party_update_accepts_public_metadata_field() -> None:
    party = PartyUpdate.model_validate({"metadata": {"source": "api"}})

    assert party.metadata == {"source": "api"}
    assert "code" not in PartyUpdate.model_fields
    assert "party_type" not in PartyUpdate.model_fields


def test_party_identifier_fields_must_be_supplied_as_a_pair() -> None:
    with pytest.raises(ValidationError):
        PartyCreate.model_validate(
            {
                "party_type": "individual",
                "name": "张三",
                "identifier_type": "national_id",
            }
        )


def test_party_response_reads_metadata_json_from_attributes() -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    party_obj = SimpleNamespace(
        id="party-1",
        party_type="legal_entity",
        name="总部",
        code="LE-000001",
        identifier_type="unified_social_credit_code",
        identifier_value="91440101231229726P",
        identifier_fingerprint=None,
        external_ref=None,
        status="active",
        metadata_json={"source": "db"},
        metadata=object(),
        created_at=now,
        updated_at=now,
    )

    response = PartyResponse.model_validate(party_obj)

    assert response.metadata == {"source": "db"}
    assert response.identifier_type == "unified_social_credit_code"
    assert response.identifier_display is None
    assert "identifier_value" not in response.model_dump()


def test_party_hierarchy_schemas_are_removed() -> None:
    assert not hasattr(party_schema, "PartyHierarchyCreate")
    assert not hasattr(party_schema, "PartyHierarchyResponse")


def test_user_party_binding_schemas_do_not_expose_primary_state() -> None:
    for schema in (
        UserPartyBindingCreate,
        UserPartyBindingUpsert,
        UserPartyBindingUpdate,
        UserPartyBindingResponse,
    ):
        assert "is_primary" not in schema.model_fields
