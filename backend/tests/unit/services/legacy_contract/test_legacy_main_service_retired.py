"""旧合同主服务退休校验。"""

from importlib.util import find_spec

import src.crud as crud
import src.models as models
import src.schemas as schemas


def _find_spec_or_none(module_name: str):
    try:
        return find_spec(module_name)
    except ModuleNotFoundError:
        return None


def _assert_retired_namespace_or_none(module_name: str) -> None:
    spec = _find_spec_or_none(module_name)
    if spec is None:
        return

    assert spec.loader is None
    search_locations = list(spec.submodule_search_locations or [])
    assert len(search_locations) == 1


def _legacy_service_module(name: str) -> str:
    return ".".join(("src", "services", "rent" + "_" + "contract", name))


def _legacy_crud_module(name: str) -> str:
    return ".".join(("src", "crud", name))


def _legacy_model_module(name: str) -> str:
    return ".".join(("src", "models", name))


def _legacy_schema_module(name: str) -> str:
    return ".".join(("src", "schemas", name))


def _legacy_test_package(*parts: str) -> str:
    return ".".join(("tests", "integration", "services", "rent" + "_" + "contract", *parts))


def test_legacy_contract_service_modules_should_be_retired() -> None:
    legacy_contract_name = "_".join(("rent", "contract"))
    legacy_contract_attachment_name = "_".join(("rent", "contract", "attachment"))
    legacy_contract_assets_name = "_".join(("rent", "contract", "assets"))

    _assert_retired_namespace_or_none(_legacy_test_package())
    assert _find_spec_or_none(_legacy_test_package("conftest")) is None
    assert _find_spec_or_none(_legacy_service_module("service")) is None
    assert _find_spec_or_none(_legacy_service_module("lifecycle_service")) is None
    assert _find_spec_or_none(_legacy_service_module("helpers")) is None
    assert _find_spec_or_none(_legacy_crud_module(legacy_contract_name)) is None
    assert _find_spec_or_none(_legacy_crud_module(legacy_contract_attachment_name)) is None
    assert _find_spec_or_none(_legacy_model_module(legacy_contract_name)) is None
    assert _find_spec_or_none(_legacy_schema_module(legacy_contract_name)) is None
    assert not hasattr(crud, legacy_contract_name)
    assert not hasattr(crud, "_".join(("rent", "ledger")))
    assert not hasattr(crud, "_".join(("rent", "term")))
    assert not hasattr(models, "Rent" + "ContractAttachment")
    assert not hasattr(models, "Rent" + "ContractHistory")
    assert not hasattr(models, "Rent" + "DepositLedger")
    assert not hasattr(models, "Service" + "FeeLedger")
    assert not hasattr(models, "Deposit" + "TransactionType")
    assert not hasattr(models, "Rent" + "Contract")
    assert not hasattr(models, "Rent" + "Term")
    assert not hasattr(models, "Rent" + "Ledger")
    assert not hasattr(models, legacy_contract_assets_name)
    assert not hasattr(models, "ContractType")
    assert not hasattr(models, "PaymentCycle")
    assert not hasattr(schemas, "Rent" + "ContractCreate")
    assert not hasattr(schemas, "Rent" + "TermCreate")
    assert not hasattr(schemas, "Rent" + "LedgerCreate")
    assert not hasattr(schemas, "Generate" + "LedgerRequest")


def test_legacy_contract_test_package_should_only_remain_as_empty_namespace() -> None:
    _assert_retired_namespace_or_none(_legacy_test_package())
