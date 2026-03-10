from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType


def _load_module() -> ModuleType:
    script_path = (
        Path(__file__).resolve().parents[4] / "scripts" / "check_field_drift.py"
    )
    spec = spec_from_file_location("check_field_drift", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_contract_entity_should_map_to_new_contract_model() -> None:
    module = _load_module()

    assert module.ENTITY_MODEL_MAP["Contract"] == ("contract_group.py", "Contract")


def test_compute_drifts_should_include_contract_entity() -> None:
    module = _load_module()

    contract_drift = next(
        drift for drift in module.compute_drifts() if drift.entity == "Contract"
    )

    assert contract_drift.model_file == "contract_group.py::Contract"


def test_compute_drifts_should_include_new_contract_related_entities() -> None:
    module = _load_module()

    drifts_by_entity = {drift.entity: drift for drift in module.compute_drifts()}

    assert drifts_by_entity["ContractGroup"].model_file == "contract_group.py::ContractGroup"
    assert (
        drifts_by_entity["LeaseContractDetail"].model_file
        == "contract_group.py::LeaseContractDetail"
    )
    assert (
        drifts_by_entity["AgencyAgreementDetail"].model_file
        == "contract_group.py::AgencyAgreementDetail"
    )
    assert (
        drifts_by_entity["ContractRelation"].model_file
        == "contract_group.py::ContractRelation"
    )
