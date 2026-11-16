"""Export endpoint contract for annual ledger workbooks."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from src.schemas.management_fee_matrix import ManagementFeeMatrixView
from src.schemas.rent_queries import RentMatrixView
from src.services.party_scope_resolver import EffectivePartyScope

pytestmark = pytest.mark.unit

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _scope() -> EffectivePartyScope:
    return EffectivePartyScope(
        user_id="actor", source="unrestricted", scope_mode="unrestricted"
    )


def _rent_view() -> RentMatrixView:
    return RentMatrixView(
        ledger_type="terminal_rent",
        year=2026,
        current_month=11,
        rows=[],
        total_due_amount=Decimal("0"),
        total_paid_amount=Decimal("0"),
        total_remaining_amount=Decimal("0"),
    )


def test_export_rent_ledger_returns_xlsx_attachment(client: TestClient, monkeypatch):
    from src.api.v1 import rent_ledger_queries as api

    monkeypatch.setattr(
        api.party_scope_resolver, "resolve", AsyncMock(return_value=_scope())
    )
    reader = AsyncMock(return_value=_rent_view())
    monkeypatch.setattr(api.rent_ledger_query_service, "matrix", reader)
    response = client.get(
        "/api/v1/rent-ledgers/export?ledger_type=upstream_rent&year=2026"
    )
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith(XLSX)
    assert (
        response.headers["content-disposition"]
        == 'attachment; filename="upstream_rent-ledger-2026.xlsx"'
    )
    assert response.content[:2] == b"PK"
    assert reader.await_args.kwargs["ledger_type"] == "upstream_rent"
    assert reader.await_args.kwargs["year"] == 2026


def test_export_management_fee_ledger_uses_fee_matrix(client: TestClient, monkeypatch):
    from src.api.v1 import rent_ledger_queries as api

    monkeypatch.setattr(
        api.party_scope_resolver, "resolve", AsyncMock(return_value=_scope())
    )
    reader = AsyncMock(
        return_value=ManagementFeeMatrixView(
            year=2026, current_month=11, rows=[], total_confirmed_amount=Decimal("0")
        )
    )
    monkeypatch.setattr(api.management_fee_matrix_service, "matrix", reader)
    response = client.get(
        "/api/v1/rent-ledgers/export?ledger_type=management_fee&year=2026"
    )
    assert response.status_code == 200, response.text
    assert (
        response.headers["content-disposition"]
        == 'attachment; filename="management-fee-ledger-2026.xlsx"'
    )
    assert reader.await_args.kwargs["year"] == 2026


def test_export_rejects_out_of_range_year(client: TestClient):
    assert client.get("/api/v1/rent-ledgers/export?year=9999").status_code == 422
