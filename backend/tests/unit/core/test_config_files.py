from importlib import import_module
from importlib.util import find_spec

from src.core.config_files import FileUploadSettings


def test_file_upload_settings_use_contract_attachment_subdir() -> None:
    settings = FileUploadSettings()

    assert settings.CONTRACT_ATTACHMENT_SUBDIR == "contracts"
    assert "CONTRACT_ATTACHMENT_SUBDIR" in FileUploadSettings.model_fields
    assert "RENT_CONTRACT_ATTACHMENT_SUBDIR" not in FileUploadSettings.model_fields
    assert FileUploadSettings.model_fields["CONTRACT_ATTACHMENT_SUBDIR"].json_schema_extra == {
        "env": "CONTRACT_ATTACHMENT_SUBDIR"
    }

    constants_module = import_module("src.constants.contract_constants")
    assert constants_module.CONTRACT_ATTACHMENT_SUBDIR == "contracts"
    assert constants_module.PaymentStatus.UNPAID == "未支付"
    assert constants_module.SettlementStatus.UNSETTLED == "待结算"


def test_legacy_contract_constants_module_retired() -> None:
    legacy_module_name = ".".join(
        ("src", "constants", "rent" + "_" + "contract" + "_" + "constants")
    )

    assert find_spec(legacy_module_name) is None
