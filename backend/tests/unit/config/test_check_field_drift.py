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


def test_legacy_contract_entity_is_not_a_current_spec_mapping() -> None:
    module = _load_module()

    assert "Contract" not in module.ENTITY_MODEL_MAP
    assert "ContractGroup" not in module.ENTITY_MODEL_MAP


def test_current_stable_entities_keep_their_model_mappings() -> None:
    module = _load_module()

    assert module.ENTITY_MODEL_MAP["Party"] == ("party.py", "Party")
    assert module.ENTITY_MODEL_MAP["Project"] == ("project.py", "Project")
    assert module.ENTITY_MODEL_MAP["PropertyCertificate"] == (
        "property_certificate.py",
        "PropertyCertificate",
    )


def test_compute_drifts_should_include_asset_unit_entity() -> None:
    module = _load_module()

    asset_unit_drift = next(
        drift for drift in module.compute_drifts() if drift.entity == "AssetUnit"
    )

    assert asset_unit_drift.model_file == "asset_unit.py::AssetUnit"


def test_compute_drifts_should_include_v5_asset_unit_related_entities() -> None:
    module = _load_module()

    drifts_by_entity = {drift.entity: drift for drift in module.compute_drifts()}

    assert (
        drifts_by_entity["AssetUnitBoundaryChange"].model_file
        == "asset_unit.py::AssetUnitBoundaryChange"
    )
    assert (
        drifts_by_entity["AssetUnitBoundarySource"].model_file
        == "asset_unit.py::AssetUnitBoundarySource"
    )
    assert (
        drifts_by_entity["PropertyCertificateAssetUnit"].model_file
        == "asset_unit.py::PropertyCertificateAssetUnit"
    )
    assert "Contract" not in drifts_by_entity


def test_v5_asset_unit_entities_map_to_the_new_model_module() -> None:
    module = _load_module()

    assert module.ENTITY_MODEL_MAP["AssetUnit"] == ("asset_unit.py", "AssetUnit")
    assert module.ENTITY_MODEL_MAP["AssetUnitBoundaryChange"] == (
        "asset_unit.py",
        "AssetUnitBoundaryChange",
    )
    assert module.ENTITY_MODEL_MAP["AssetUnitBoundarySource"] == (
        "asset_unit.py",
        "AssetUnitBoundarySource",
    )
    assert module.ENTITY_MODEL_MAP["PropertyCertificateAssetUnit"] == (
        "asset_unit.py",
        "PropertyCertificateAssetUnit",
    )


def test_v5_contract_entities_map_to_the_new_contract_module() -> None:
    module = _load_module()

    expected_classes = {
        "UpstreamContract",
        "UpstreamContractAssetUnit",
        "TerminalContract",
        "TerminalContractAssetUnit",
        "ContractRentSchedule",
        "ContractLifecycleEvent",
    }

    for class_name in expected_classes:
        assert module.ENTITY_MODEL_MAP[class_name] == (
            "asset_contract.py",
            class_name,
        )


def test_compute_drifts_should_include_v5_contract_entities() -> None:
    module = _load_module()

    drifts_by_entity = {drift.entity: drift for drift in module.compute_drifts()}

    for class_name in {
        "UpstreamContract",
        "UpstreamContractAssetUnit",
        "TerminalContract",
        "TerminalContractAssetUnit",
        "ContractLifecycleEvent",
    }:
        drift = drifts_by_entity[class_name]
        assert drift.model_file == f"asset_contract.py::{class_name}"
        assert drift.spec_only == []
        assert drift.orm_only == []


def test_rent_schedule_drift_is_limited_to_planned_v2_supersession_fields() -> None:
    module = _load_module()
    drift = next(
        drift
        for drift in module.compute_drifts()
        if drift.entity == "ContractRentSchedule"
    )

    # V2 PR-A plans these fields; retain the exact gap until its ORM migration.
    assert drift.model_file == "asset_contract.py::ContractRentSchedule"
    assert drift.spec_only == ["superseded_at", "superseded_correlation_id"]
    assert drift.orm_only == []
