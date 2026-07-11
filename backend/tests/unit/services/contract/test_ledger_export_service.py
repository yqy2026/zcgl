from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.crud.query_builder import PartyFilter

pytestmark = pytest.mark.asyncio


async def test_export_rows_should_follow_query_filters_and_column_order(
    mock_db,
) -> None:
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
                "ledger_views": ["terminal_collection", "operator_income"],
                "due_date": "2026-05-01",
                "amount_due": "1000.00",
                "currency_code": "CNY",
                "is_tax_included": True,
                "tax_rate": "0.09",
                "payment_status": "unpaid",
                "paid_amount": "200.00",
                "flow_occurred_on_dates": ["2026-05-10"],
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
        ledger_view="terminal_collection",
        project_id="project-001",
        asset_id=None,
        party_id=None,
        contract_id="contract-001",
        year_month_start="2026-05",
        year_month_end="2026-05",
        flow_occurred_on_start="2026-05-01",
        flow_occurred_on_end="2026-05-31",
        payment_status=None,
        include_voided=False,
        offset=0,
        limit=20,
    )

    party_filter = PartyFilter(
        party_ids=["operator-001"],
        filter_mode="manager",
        manager_party_ids=["operator-001"],
    )

    with patch(
        "src.services.contract.ledger_export_service.ledger_service_v2.query_ledger_entries",
        new=AsyncMock(return_value=payload),
    ) as mock_query:
        result = await service.export_ledger_entries(
            mock_db,
            params=params,
            current_user_id="user-001",
            party_filter=party_filter,
        )

    assert result.filename.startswith("ledger_entries_")
    assert result.media_type == "text/csv; charset=utf-8"
    csv_text = result.content.decode("utf-8")
    assert "entry_id,contract_id,year_month,ledger_views,due_date" in csv_text
    assert "flow_occurred_on_dates" in csv_text
    assert "terminal_collection;operator_income" in csv_text
    assert "2026-05-10" in csv_text
    mock_query.assert_awaited_once_with(
        mock_db,
        ledger_view="terminal_collection",
        project_id="project-001",
        asset_id=None,
        party_id=None,
        contract_id="contract-001",
        year_month_start="2026-05",
        year_month_end="2026-05",
        flow_occurred_on_start="2026-05-01",
        flow_occurred_on_end="2026-05-31",
        payment_status=None,
        include_voided=False,
        offset=0,
        limit=200,
        current_user_id="user-001",
        party_filter=party_filter,
    )


async def test_export_rows_should_page_through_the_full_filtered_result(
    mock_db,
) -> None:
    from src.services.contract.ledger_export_service import ledger_export_service

    first_page = [
        {"entry_id": f"entry-{index:03d}", "contract_id": "contract-001"}
        for index in range(200)
    ]
    final_page = [{"entry_id": "entry-200", "contract_id": "contract-001"}]
    params = SimpleNamespace(
        export_format="csv",
        ledger_view="terminal_collection",
        project_id="project-001",
        asset_id=None,
        party_id=None,
        contract_id=None,
        year_month_start=None,
        year_month_end=None,
        flow_occurred_on_start=None,
        flow_occurred_on_end=None,
        payment_status=None,
        include_voided=False,
        offset=0,
        limit=20,
    )

    with patch(
        "src.services.contract.ledger_export_service.ledger_service_v2.query_ledger_entries",
        new=AsyncMock(
            side_effect=[
                {"items": first_page, "total": 201, "offset": 0, "limit": 200},
                {"items": final_page, "total": 201, "offset": 200, "limit": 200},
            ]
        ),
    ) as mock_query:
        result = await ledger_export_service.export_ledger_entries(
            mock_db, params=params
        )

    assert mock_query.await_count == 2
    assert [call.kwargs["offset"] for call in mock_query.await_args_list] == [0, 200]
    assert result.content.decode("utf-8").count("contract-001") == 201
