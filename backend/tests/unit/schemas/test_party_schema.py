"""Unit tests for party write schemas."""

from datetime import UTC, datetime
from types import SimpleNamespace

from src.schemas.party import PartyCreate, PartyResponse, PartyUpdate


def test_party_create_accepts_public_metadata_field() -> None:
    payload = {
        "party_type": "organization",
        "name": "总部",
        "code": "HQ",
        "metadata": {"source": "api"},
    }

    party = PartyCreate.model_validate(payload)

    assert party.metadata == {"source": "api"}


def test_party_create_accepts_legacy_metadata_json_field() -> None:
    payload = {
        "party_type": "organization",
        "name": "总部",
        "code": "HQ",
        "metadata_json": {"source": "legacy"},
    }

    party = PartyCreate.model_validate(payload)

    assert party.metadata == {"source": "legacy"}


def test_party_update_accepts_public_metadata_field() -> None:
    party = PartyUpdate.model_validate({"metadata": {"source": "api"}})

    assert party.metadata == {"source": "api"}


def test_party_response_reads_metadata_json_from_attributes() -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    party_obj = SimpleNamespace(
        id="party-1",
        party_type="organization",
        name="总部",
        code="HQ",
        external_ref=None,
        status="active",
        metadata_json={"source": "db"},
        metadata=object(),
        created_at=now,
        updated_at=now,
    )

    response = PartyResponse.model_validate(party_obj)

    assert response.metadata == {"source": "db"}
