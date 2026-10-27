"""Reject invalid existing management terms before schema changes."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace

import pytest


def _migration():
    path = (
        Path(__file__).resolve().parents[3]
        / "alembic/versions/20261027_contract_field_rules.py"
    )
    spec = spec_from_file_location("contract_field_rules", path)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "invalid",
    [
        {
            "id": "bad-deposit",
            "contract_number": "UP-1",
            "has_deposit": True,
            "has_rent_schedules": False,
        },
        {
            "id": "bad-schedule",
            "contract_number": "UP-2",
            "has_deposit": False,
            "has_rent_schedules": True,
        },
    ],
)
def test_preflight_rejects_invalid_contract_before_ddl(monkeypatch, invalid):
    module = _migration()
    operations = []
    result = SimpleNamespace(mappings=lambda: SimpleNamespace(all=lambda: [invalid]))
    connection = SimpleNamespace(execute=lambda query: result)
    monkeypatch.setattr(
        module,
        "op",
        SimpleNamespace(
            get_bind=lambda: connection,
            create_check_constraint=lambda *args: operations.append(args),
        ),
    )
    with pytest.raises(RuntimeError, match=invalid["id"]):
        module.upgrade()
    assert operations == []


def test_valid_contracts_gain_deposit_constraint(monkeypatch):
    module = _migration()
    operations = []
    result = SimpleNamespace(mappings=lambda: SimpleNamespace(all=lambda: []))
    monkeypatch.setattr(
        module,
        "op",
        SimpleNamespace(
            get_bind=lambda: SimpleNamespace(execute=lambda query: result),
            create_check_constraint=lambda *args: operations.append(args),
        ),
    )
    module.upgrade()
    assert operations == [
        (
            "ck_upstream_contracts_management_deposit_zero",
            "upstream_contracts",
            "contract_type = 'lease' OR deposit_amount = 0",
        )
    ]
