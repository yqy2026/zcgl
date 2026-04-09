"""旧合同运行时入口下线校验。"""

from importlib.util import find_spec

from src.api.v1 import api_router


def _find_spec_or_none(module_name: str):
    try:
        return find_spec(module_name)
    except ModuleNotFoundError:
        return None


def _assert_retired_namespace_or_none(module_name: str) -> None:
    spec = _find_spec_or_none(module_name)
    if spec is None:
        return

    assert spec.loader is None or spec.loader.__class__.__name__ == "NamespaceLoader"
    search_locations = list(spec.submodule_search_locations or [])
    assert len(search_locations) == 1


def _legacy_contracts_api_module(*parts: str) -> str:
    return ".".join(("src", "api", "v1", "rent" + "_" + "contracts", *parts))


def test_api_router_should_not_expose_legacy_rental_contract_paths() -> None:
    legacy_contract_path_prefix = "/" + "-".join(("rental", "contracts"))
    paths = {
        route.path
        for route in api_router.routes  # type: ignore[attr-defined]
    }

    legacy_paths = {
        path for path in paths if path.startswith(legacy_contract_path_prefix)
    }

    assert legacy_paths == set(), f"旧路径仍被注册: {sorted(legacy_paths)}"
    assert "/contract-groups" in paths
    assert "/contracts/{contract_id}/ledger" in paths


def test_legacy_contract_api_package_should_be_retired() -> None:
    _assert_retired_namespace_or_none(_legacy_contracts_api_module())


def test_legacy_ledger_and_lifecycle_modules_should_be_retired() -> None:
    assert _find_spec_or_none(_legacy_contracts_api_module("ledger")) is None
    assert _find_spec_or_none(_legacy_contracts_api_module("lifecycle")) is None


def test_legacy_contracts_and_terms_modules_should_be_retired() -> None:
    assert _find_spec_or_none(_legacy_contracts_api_module("contract_groups")) is None
    assert _find_spec_or_none(_legacy_contracts_api_module("contracts")) is None
    assert _find_spec_or_none(_legacy_contracts_api_module("terms")) is None


def test_legacy_attachment_statistics_and_excel_modules_should_be_retired() -> None:
    assert _find_spec_or_none(_legacy_contracts_api_module("attachments")) is None
    assert _find_spec_or_none(_legacy_contracts_api_module("statistics")) is None
    assert _find_spec_or_none(_legacy_contracts_api_module("excel_ops")) is None


def test_legacy_contract_api_package_should_only_remain_as_empty_namespace() -> None:
    _assert_retired_namespace_or_none(_legacy_contracts_api_module())
