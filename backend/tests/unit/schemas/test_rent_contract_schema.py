"""Unit tests for rent contract schema owner reference validation."""

from datetime import date

import pytest
from pydantic import ValidationError

from src.schemas.rent_contract import RentContractCreate


def _build_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "contract_number": "HT-TEST-001",
        "asset_ids": ["asset-001"],
        "owner_party_id": "party-001",
        "ownership_id": None,
        "tenant_name": "测试租户",
        "sign_date": date(2026, 1, 1),
        "start_date": date(2026, 1, 1),
        "end_date": date(2026, 12, 31),
        "rent_terms": [
            {
                "start_date": date(2026, 1, 1),
                "end_date": date(2026, 12, 31),
                "monthly_rent": 1000,
            }
        ],
    }
    payload.update(overrides)
    return payload


def test_create_rejects_blank_owner_party_id_when_ownership_id_missing() -> None:
    with pytest.raises(ValidationError) as exc_info:
        RentContractCreate.model_validate(
            _build_payload(
                owner_party_id="   ",
                ownership_id=None,
            )
        )

    assert "owner_party_id 或 ownership_id 至少提供一个" in str(exc_info.value)


def test_create_keeps_legacy_ownership_id_when_owner_party_id_blank() -> None:
    model = RentContractCreate.model_validate(
        _build_payload(
            owner_party_id="   ",
            ownership_id="  own-001  ",
        )
    )

    assert model.owner_party_id is None
    assert model.ownership_id == "own-001"
