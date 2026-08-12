from datetime import datetime

from src.services.property_certificate.risks import (
    AssetOwnerSnapshot,
    HolderRelationSnapshot,
    calculate_holder_owner_mismatch,
    calculate_incomplete_certificate_info,
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


def test_incomplete_real_estate_missing_fields_warns_per_linked_asset() -> None:
    result = calculate_incomplete_certificate_info(
        certificate_id="cert-1",
        certificate_number="CERT-001",
        certificate_type="real_estate",
        building_area=None,
        land_area="",
        land_use_term_start="2020-01-01",
        land_use_term_end=None,
        restrictions="无",
        assets=[
            AssetOwnerSnapshot(asset_id="asset-a", owner_party_id="party-1"),
            AssetOwnerSnapshot(asset_id="asset-b", owner_party_id="party-1"),
        ],
    )

    assert result.missing_field_keys == (
        "building_area",
        "land_area",
        "land_use_term_end",
    )
    assert [warning.asset_id for warning in result.warnings] == ["asset-a", "asset-b"]
    warning = result.warnings[0]
    assert warning.risk_type == "incomplete_certificate_info"
    assert warning.severity == "warning"
    assert (
        warning.risk_id
        == "property-certificate:cert-1:asset:asset-a:incomplete_certificate_info"
    )
    assert "证载建筑面积" in warning.message
    assert "证载土地面积" in warning.message
    assert "土地使用期限止" in warning.message


def test_incomplete_checks_type_conditioned_field_sets() -> None:
    house = calculate_incomplete_certificate_info(
        certificate_id="cert-house",
        certificate_number="HOUSE-001",
        certificate_type="house_ownership",
        building_area="120.5",
        restrictions="抵押",
        land_area=None,  # 非适用字段：不检查
        land_use_term_start=None,
        land_use_term_end=None,
        assets=[AssetOwnerSnapshot(asset_id="asset-1", owner_party_id="party-1")],
    )
    assert house.warnings == ()

    land = calculate_incomplete_certificate_info(
        certificate_id="cert-land",
        certificate_number="LAND-001",
        certificate_type="land_use",
        land_area="500",
        land_use_term_start="2020-01-01",
        land_use_term_end="2070-01-01",
        restrictions=None,
        building_area=None,  # 非适用字段：不检查
        assets=[AssetOwnerSnapshot(asset_id="asset-1", owner_party_id="party-1")],
    )
    assert [warning.risk_type for warning in land.warnings] == [
        "incomplete_certificate_info"
    ]
    assert land.missing_field_keys == ("restrictions",)


def test_incomplete_other_type_only_checks_restrictions() -> None:
    result = calculate_incomplete_certificate_info(
        certificate_id="cert-other",
        certificate_number="OTHER-001",
        certificate_type="other",
        restrictions="  ",
        assets=[AssetOwnerSnapshot(asset_id="asset-1", owner_party_id="party-1")],
    )
    assert result.missing_field_keys == ("restrictions",)
    assert len(result.warnings) == 1


def test_incomplete_unknown_type_checks_only_restrictions_conservatively() -> None:
    result = calculate_incomplete_certificate_info(
        certificate_id="cert-x",
        certificate_number="X-001",
        certificate_type="unknown_value",
        building_area=None,
        land_area=None,
        restrictions="无",
        assets=[AssetOwnerSnapshot(asset_id="asset-1", owner_party_id="party-1")],
    )
    assert result.warnings == ()
    assert result.missing_field_keys == ()


def test_incomplete_whitespace_string_counts_as_missing() -> None:
    result = calculate_incomplete_certificate_info(
        certificate_id="cert-1",
        certificate_number="CERT-001",
        certificate_type="house_ownership",
        building_area="  ",
        restrictions="无",
        assets=[AssetOwnerSnapshot(asset_id="asset-1", owner_party_id="party-1")],
    )
    assert result.missing_field_keys == ("building_area",)
    assert len(result.warnings) == 1


def test_incomplete_complete_certificate_has_no_warnings() -> None:
    result = calculate_incomplete_certificate_info(
        certificate_id="cert-1",
        certificate_number="CERT-001",
        certificate_type="real_estate",
        building_area="120.5",
        land_area="500",
        land_use_term_start="2020-01-01",
        land_use_term_end="2070-01-01",
        restrictions="无",
        assets=[AssetOwnerSnapshot(asset_id="asset-1", owner_party_id="party-1")],
    )
    assert result.warnings == ()
    assert result.missing_field_keys == ()


def test_incomplete_no_linked_assets_derives_no_warning() -> None:
    result = calculate_incomplete_certificate_info(
        certificate_id="cert-1",
        certificate_number="CERT-001",
        certificate_type="real_estate",
        building_area=None,
        restrictions=None,
        assets=[],
    )
    # 字段缺失仍被识别，但无关联资产承载时不派生 warning（与 holder_owner_mismatch 一致）
    assert len(result.missing_field_keys) == 5
    assert result.warnings == ()
