from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

pytestmark = pytest.mark.asyncio


async def test_export_rows_should_follow_query_filters_and_column_order(mock_db) -> None:
    try:
        from src.services.contract import ledger_export_service as ledger_export_module
    except ModuleNotFoundError as exc:
        pytest.fail(f"ledger_export_service module missing: {exc}")

    service = getattr(ledger_export_module, "ledger_export_service", None)
    assert service is not None, "ledger_export_service 尚未实现"

    payload = {
        "items": [
            {
                "entry_id": "entry-001",
                "contract_id": "contract-001",
                "year_month": "2026-05",
                "due_date": "2026-05-01",
                "amount_due": "1000.00",
                "currency_code": "CNY",
                "is_tax_included": True,
                "tax_rate": "0.09",
                "payment_status": "unpaid",
                "paid_amount": "200.00",
                "notes": "first row",
                "created_at": None,
                "updated_at": None,
            }
        ],
        "total": 1,
        "offset": 0,
        "limit": 20,
    }
    params = SimpleNamespace(
        export_format="csv",
        asset_id=None,
        party_id=None,
        contract_id="contract-001",
        year_month_start="2026-05",
        year_month_end="2026-05",
        payment_status=None,
        include_voided=False,
        offset=0,
        limit=20,
    )

    with patch(
        "src.services.contract.ledger_export_service.ledger_service_v2.query_ledger_entries",
        new=AsyncMock(return_value=payload),
    ) as mock_query:
        result = await service.export_ledger_entries(mock_db, params=params)

    assert result.filename.startswith("ledger_entries_")
    assert result.media_type == "text/csv; charset=utf-8"
    csv_text = result.content.decode("utf-8")
    assert "entry_id,contract_id,year_month,due_date,amount_due" in csv_text
    assert "entry-001,contract-001,2026-05,2026-05-01,1000.00" in csv_text
    mock_query.assert_awaited_once_with(
        mock_db,
        asset_id=None,
        party_id=None,
        contract_id="contract-001",
        year_month_start="2026-05",
        year_month_end="2026-05",
        payment_status=None,
        include_voided=False,
        offset=0,
        limit=20,
    )
