from pathlib import Path


def test_create_certificate_endpoint_does_not_use_extraction_validator_as_save_gate() -> None:
    from src.api.v1.assets import property_certificate as module

    source = Path(module.__file__).read_text(encoding="utf-8")
    create_block = source.split("async def create_certificate", 1)[1].split(
        "@router.put", 1
    )[0]

    assert "validate_extracted_fields" not in create_block
    assert "PropertyCertificateValidator" not in create_block
