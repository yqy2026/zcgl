from src.services.property_certificate.validator import PropertyCertificateValidator


def test_legacy_hard_save_gate_methods_are_removed() -> None:
    validator = PropertyCertificateValidator()

    for method_name in (
        "validate_certificate_data",
        "validate_certificate_number",
        "validate_area",
        "validate_issue_date",
        "validate_expiry_date",
        "validate_address",
        "validate_asset_name",
    ):
        assert not hasattr(validator, method_name)
