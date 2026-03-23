from pathlib import Path
from unittest.mock import ANY, AsyncMock, patch

import pytest

pytestmark = pytest.mark.api


def _module_source() -> str:
    from src.api.v1.contracts import ledger as mod

    return Path(mod.__file__).read_text(encoding="utf-8")


def test_ledger_module_should_not_import_crud_directly() -> None:
    source = _module_source()
    assert "contract_group_crud" not in source
    assert "contract_crud" not in source


def test_ledger_module_should_use_require_authz() -> None:
    source = _module_source()
    assert "require_authz" in source
    assert 'resource_id="{contract_id}"' in source


def test_get_ledger_entries_delegates_to_service(client) -> None:
    payload = {
        "items": [
            {
                "entry_id": "entry-001",
                "contract_id": "contract-001",
                "year_month": "2026-01",
                "due_date": "2026-01-01",
                "amount_due": "1000.00",
                "currency_code": "CNY",
                "is_tax_included": True,
                "tax_rate": "0.09",
                "payment_status": "unpaid",
                "paid_amount": "0",
                "notes": None,
                "created_at": None,
                "updated_at": None,
            }
        ],
        "total": 1,
        "offset": 0,
        "limit": 20,
    }

    with patch(
        "src.api.v1.contracts.ledger.ledger_service_v2.query_ledger_entries",
        new=AsyncMock(return_value=payload),
    ) as mock_query:
        response = client.get(
            "/api/v1/ledger/entries",
            params={"contract_id": "contract-001", "year_month_start": "2026-01"},
        )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    mock_query.assert_awaited_once_with(
        ANY,
        asset_id=None,
        party_id=None,
        contract_id="contract-001",
        year_month_start="2026-01",
        year_month_end=None,
        payment_status=None,
        include_voided=False,
        offset=0,
        limit=20,
    )


def test_get_ledger_entries_requires_at_least_one_core_filter(client) -> None:
    response = client.get("/api/v1/ledger/entries")

    assert response.status_code == 422


def test_recalculate_ledger_delegates_to_service(client) -> None:
    payload = {
        "created": 1,
        "updated": 2,
        "voided": 0,
        "skipped_entries": [],
    }

    with patch(
        "src.api.v1.contracts.ledger.ledger_service_v2.recalculate_ledger",
        new=AsyncMock(return_value=payload),
    ) as mock_recalculate:
        response = client.post("/api/v1/contracts/contract-001/ledger/recalculate")

    assert response.status_code == 200
    assert response.json() == payload
    mock_recalculate.assert_awaited_once_with(ANY, contract_id="contract-001")


def test_batch_update_ledger_rejects_voided_status(client) -> None:
    response = client.patch(
        "/api/v1/contracts/contract-001/ledger/batch-update-status",
        json={
            "entry_ids": ["entry-001"],
            "payment_status": "voided",
        },
    )

    assert response.status_code == 422

