"""Keep legacy lifecycle unit fakes focused on their contract boundary.

Rent integration tests exercise the real reconciliation and token fingerprint;
these older tests use a fake contract repository without a SQL session.
"""

from unittest.mock import AsyncMock

import pytest


@pytest.fixture(autouse=True)
def contract_deposit_boundary(request, monkeypatch):
    if not request.node.path.name.startswith("test_contract_"):
        return
    from src.services.asset_operations.deposit_entry_service import (
        deposit_entry_service,
    )

    monkeypatch.setattr(
        deposit_entry_service, "ensure_entry", AsyncMock(return_value=None)
    )


@pytest.fixture(autouse=True)
def lifecycle_rent_boundary(request, monkeypatch):
    if request.node.path.name == "test_contract_query_views.py":
        from src.services.asset_operations.rent_ledger_query_service import (
            rent_ledger_query_service,
        )

        monkeypatch.setattr(
            rent_ledger_query_service, "contract_summary", AsyncMock(return_value={})
        )
    if not request.node.path.name.startswith("test_contract_lifecycle_"):
        return
    from src.services.asset_operations.deposit_settlement_service import (
        deposit_settlement_service,
    )

    monkeypatch.setattr(
        deposit_settlement_service, "preview", AsyncMock(return_value={})
    )
    monkeypatch.setattr(
        deposit_settlement_service, "apply", AsyncMock(return_value=None)
    )
    monkeypatch.setattr(
        deposit_settlement_service, "reverse", AsyncMock(return_value=None)
    )
    monkeypatch.setattr(
        deposit_settlement_service, "prelock", AsyncMock(return_value=None)
    )
    from src.crud.asset_contract import asset_contract_repository
    from src.crud.rent_commands import rent_command_repository

    receipts = {}

    async def add_receipt(db, *, receipt):
        receipts[(receipt.actor_id, receipt.idempotency_key)] = receipt

    async def get_receipt(db, *, actor_id, idempotency_key):
        return receipts.get((actor_id, idempotency_key))

    monkeypatch.setattr(rent_command_repository, "add_receipt", add_receipt)
    monkeypatch.setattr(asset_contract_repository, "get_write_receipt", get_receipt)
    from types import SimpleNamespace

    from src.services.asset_operations.contract_lifecycle_command_service import (
        default_unit_repository,
    )

    monkeypatch.setattr(
        default_unit_repository,
        "lock_for_write",
        AsyncMock(
            side_effect=lambda db, *, unit_ids, scope: tuple(
                SimpleNamespace(id=value) for value in unit_ids
            )
        ),
    )
    from src.services.asset_operations.rent_obligation_service import (
        RentObligationPlan,
        rent_obligation_service,
    )

    monkeypatch.setattr(
        rent_obligation_service, "preview", AsyncMock(return_value=RentObligationPlan())
    )
    monkeypatch.setattr(
        rent_obligation_service, "fingerprint", AsyncMock(return_value="rent-state")
    )
    monkeypatch.setattr(
        rent_obligation_service, "replan", AsyncMock(return_value=RentObligationPlan())
    )
