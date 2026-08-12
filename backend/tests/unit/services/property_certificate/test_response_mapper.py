import logging
from datetime import datetime
from types import SimpleNamespace

from src.models.certificate_party_relation import CertificateRelationRole
from src.services.property_certificate.service import map_property_certificate_response


def _certificate(*, holder_relations: list[object], assets: list[object]) -> object:
    return SimpleNamespace(
        id="cert-1",
        certificate_number="CERT-001",
        certificate_type="real_estate",
        registration_date=None,
        property_address="Test address",
        property_type=None,
        building_area=None,
        floor_info=None,
        land_area=None,
        land_use_type=None,
        land_use_term_start=None,
        land_use_term_end=None,
        co_ownership=None,
        restrictions=None,
        remarks=None,
        created_at=datetime(2026, 1, 1),
        updated_at=datetime(2026, 1, 2),
        created_by="user-1",
        party_relations=holder_relations,
        assets=assets,
    )


def test_mapper_explicitly_projects_current_holders_assets_and_warnings() -> None:
    response = map_property_certificate_response(
        _certificate(
            holder_relations=[
                SimpleNamespace(
                    party_id="party-holder",
                    relation_role=CertificateRelationRole.OWNER,
                    valid_from=datetime(2026, 1, 1),
                    valid_to=None,
                ),
                SimpleNamespace(
                    party_id="party-expired",
                    relation_role=CertificateRelationRole.CO_OWNER,
                    valid_from=datetime(2025, 1, 1),
                    valid_to=datetime(2025, 12, 31),
                ),
            ],
            assets=[
                SimpleNamespace(
                    id="asset-1",
                    asset_name="Asset One",
                    owner_party_id="party-other",
                )
            ],
        ),
        as_of=datetime(2026, 8, 12),
    )

    assert response.asset_ids == ["asset-1"]
    assert response.holder_party_ids == ["party-holder"]
    assert len(response.data_quality_warnings) == 1
    assert response.data_quality_warnings[0].asset_id == "asset-1"
    assert response.data_quality_warnings[0].risk_type == "holder_owner_mismatch"


def test_mapper_logs_missing_comparison_inputs_without_warning(
    caplog,
) -> None:
    caplog.set_level(logging.WARNING)

    response = map_property_certificate_response(
        _certificate(
            holder_relations=[],
            assets=[
                SimpleNamespace(
                    id="asset-1",
                    asset_name="Asset One",
                    owner_party_id=None,
                )
            ],
        ),
        as_of=datetime(2026, 8, 12),
    )

    assert response.data_quality_warnings == []
    assert "no current OWNER/CO_OWNER holder" in caplog.text
    assert "asset has no owner_party_id" in caplog.text
