from datetime import datetime

from src.services.property_certificate.risks import (
    AssetOwnerSnapshot,
    HolderRelationSnapshot,
    calculate_holder_owner_mismatch,
)

AS_OF = datetime(2026, 8, 12, 12, 0, 0)


def test_mismatch_uses_only_current_owner_and_co_owner_relations_per_asset() -> None:
    result = calculate_holder_owner_mismatch(
        certificate_id="cert-1",
        certificate_number="CERT-001",
        holder_relations=[
            HolderRelationSnapshot(
                party_id="party-current-owner",
                relation_role="owner",
                valid_from=datetime(2026, 1, 1),
                valid_to=None,
            ),
            HolderRelationSnapshot(
                party_id="party-current-co-owner",
                relation_role="co_owner",
                valid_from=datetime(2026, 8, 1),
                valid_to=datetime(2026, 12, 31),
            ),
            HolderRelationSnapshot(
                party_id="party-expired",
                relation_role="owner",
                valid_from=datetime(2025, 1, 1),
                valid_to=datetime(2025, 12, 31),
            ),
            HolderRelationSnapshot(
                party_id="party-custodian",
                relation_role="custodian",
                valid_from=datetime(2026, 1, 1),
                valid_to=None,
            ),
        ],
        assets=[
            AssetOwnerSnapshot(
                asset_id="asset-match", owner_party_id="party-current-co-owner"
            ),
            AssetOwnerSnapshot(asset_id="asset-mismatch", owner_party_id="party-other"),
        ],
        as_of=AS_OF,
    )

    assert result.current_holder_party_ids == (
        "party-current-co-owner",
        "party-current-owner",
    )
    assert [warning.asset_id for warning in result.warnings] == ["asset-mismatch"]
    warning = result.warnings[0]
    assert warning.risk_type == "holder_owner_mismatch"
    assert warning.severity == "warning"
    assert (
        warning.risk_id
        == "property-certificate:cert-1:asset:asset-mismatch:holder_owner_mismatch"
    )


def test_missing_holder_or_asset_owner_does_not_fabricate_mismatch() -> None:
    no_holders = calculate_holder_owner_mismatch(
        certificate_id="cert-1",
        certificate_number="CERT-001",
        holder_relations=[],
        assets=[AssetOwnerSnapshot(asset_id="asset-1", owner_party_id="party-1")],
        as_of=AS_OF,
    )
    missing_asset_owner = calculate_holder_owner_mismatch(
        certificate_id="cert-1",
        certificate_number="CERT-001",
        holder_relations=[
            HolderRelationSnapshot(
                party_id="party-1",
                relation_role="owner",
                valid_from=datetime(2026, 1, 1),
                valid_to=None,
            )
        ],
        assets=[AssetOwnerSnapshot(asset_id="asset-1", owner_party_id=None)],
        as_of=AS_OF,
    )

    assert no_holders.warnings == ()
    assert no_holders.missing_current_holders is True
    assert missing_asset_owner.warnings == ()
    assert missing_asset_owner.asset_ids_missing_owner == ("asset-1",)


def test_holder_relation_expires_at_valid_to_boundary() -> None:
    result = calculate_holder_owner_mismatch(
        certificate_id="cert-1",
        certificate_number="CERT-001",
        holder_relations=[
            HolderRelationSnapshot(
                party_id="party-1",
                relation_role="owner",
                valid_from=datetime(2026, 1, 1),
                valid_to=AS_OF,
            )
        ],
        assets=[AssetOwnerSnapshot(asset_id="asset-1", owner_party_id="party-1")],
        as_of=AS_OF,
    )

    assert result.current_holder_party_ids == ()
    assert result.missing_current_holders is True


def test_risk_id_is_stable_when_party_order_and_display_text_change() -> None:
    relations = [
        HolderRelationSnapshot(
            party_id="party-2",
            relation_role="co_owner",
            valid_from=datetime(2026, 1, 1),
            valid_to=None,
        ),
        HolderRelationSnapshot(
            party_id="party-1",
            relation_role="owner",
            valid_from=datetime(2026, 1, 1),
            valid_to=None,
        ),
    ]
    first = calculate_holder_owner_mismatch(
        certificate_id="cert-1",
        certificate_number="CERT-001",
        holder_relations=relations,
        assets=[
            AssetOwnerSnapshot(
                asset_id="asset-1", owner_party_id="party-3", asset_name="旧名称"
            )
        ],
        as_of=AS_OF,
    )
    second = calculate_holder_owner_mismatch(
        certificate_id="cert-1",
        certificate_number="RENAMED",
        holder_relations=list(reversed(relations)),
        assets=[
            AssetOwnerSnapshot(
                asset_id="asset-1", owner_party_id="party-3", asset_name="新名称"
            )
        ],
        as_of=AS_OF,
    )

    assert first.warnings[0].risk_id == second.warnings[0].risk_id
