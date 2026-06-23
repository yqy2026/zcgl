from src.services.asset.validators import AssetBatchValidator


def _required_import_row() -> dict[str, str]:
    return {
        "asset_name": "Asset A",
        "address": "Building 1",
        "ownership_status": "confirmed",
        "property_nature": "commercial",
        "usage_status": "vacant",
    }


def test_missing_owner_reference_is_required_for_import_rows() -> None:
    errors = AssetBatchValidator.validate_required_fields(_required_import_row())

    assert any(error["field"] == "owner_party_id" for error in errors)


def test_legacy_ownership_id_satisfies_owner_reference_during_import() -> None:
    data = _required_import_row()
    data["ownership_id"] = "legacy-owner-1"

    errors = AssetBatchValidator.validate_required_fields(data)

    assert not any(error["field"] == "owner_party_id" for error in errors)
