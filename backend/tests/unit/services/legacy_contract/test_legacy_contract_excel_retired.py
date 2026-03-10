"""旧合同 Excel 文档服务退休校验。"""

from importlib.util import find_spec


def test_legacy_contract_excel_service_module_should_be_retired() -> None:
    legacy_module_name = ".".join(
        ("src", "services", "document", "rent" + "_" + "contract" + "_" + "excel")
    )

    assert find_spec(legacy_module_name) is None
