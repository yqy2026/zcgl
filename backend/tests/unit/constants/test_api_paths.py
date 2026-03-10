from src.constants import api_constants as api_constants_module
from src.constants import api_paths as api_paths_module


def test_contract_paths_replace_legacy_rental_paths() -> None:
    assert hasattr(api_paths_module, "ContractPaths")
    assert not hasattr(api_paths_module, "RentalPaths")

    assert api_paths_module.ContractPaths.GROUPS["BASE"] == "/contract-groups"
    assert api_paths_module.ContractPaths.CONTRACTS["DETAIL"] == "/contracts/{contract_id}"
    assert (
        api_paths_module.ContractPaths.CONTRACTS["LEDGER"]
        == "/contracts/{contract_id}/ledger"
    )

    assert api_paths_module.PREFIX_MAPPING["contract_groups"] == "/contract-groups"
    assert api_paths_module.PREFIX_MAPPING["contracts"] == "/contracts"
    assert "rental_contracts" not in api_paths_module.PREFIX_MAPPING
    assert "rental_ledger" not in api_paths_module.PREFIX_MAPPING
    assert "rental" not in api_paths_module.API_PATHS
    assert api_paths_module.API_PATHS["contracts"] is api_paths_module.ContractPaths


def test_api_constants_export_contract_paths_only() -> None:
    assert hasattr(api_constants_module, "ContractPaths")
    assert not hasattr(api_constants_module, "RentalPaths")
    assert "ContractPaths" in api_constants_module.__all__
    assert "RentalPaths" not in api_constants_module.__all__
