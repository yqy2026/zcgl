"""旧合同台账子服务退休校验。"""

from importlib.util import find_spec


def _find_spec_or_none(module_name: str):
    try:
        return find_spec(module_name)
    except ModuleNotFoundError:
        return None


def test_legacy_contract_ledger_service_module_should_be_retired() -> None:
    legacy_module_name = ".".join(
        ("src", "services", "rent" + "_" + "contract", "ledger_service")
    )

    assert _find_spec_or_none(legacy_module_name) is None
