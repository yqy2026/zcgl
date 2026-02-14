"""
End-to-End contract workflow tests.
"""

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.e2e


def test_contract_list_endpoint_e2e(authenticated_client: TestClient) -> None:
    response = authenticated_client.get("/api/v1/rental-contracts/contracts")
    assert response.status_code == 200

    payload = response.json()
    assert payload.get("success") is True
    data = payload.get("data", {})
    assert isinstance(data.get("items"), list)
    assert isinstance(data.get("pagination"), dict)


def test_contract_detail_not_found_semantics_e2e(
    authenticated_client: TestClient,
) -> None:
    response = authenticated_client.get("/api/v1/rental-contracts/contracts/nonexistent")
    assert response.status_code == 404

    payload = response.json()
    assert payload.get("success") is False
    error = payload.get("error", {})
    assert isinstance(error, dict)
    assert error.get("code") == "RESOURCE_NOT_FOUND"


def test_contract_renew_not_found_semantics_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
) -> None:
    response = authenticated_client.post(
        "/api/v1/rental-contracts/contracts/nonexistent/renew",
        json={
            "contract_number": "E2E-RENEW-001",
            "contract_type": "lease_downstream",
            "tenant_name": "E2E续签租户",
            "ownership_id": "ownership_001",
            "sign_date": "2027-01-01",
            "start_date": "2027-01-01",
            "end_date": "2027-12-31",
            "rent_terms": [
                {
                    "start_date": "2027-01-01",
                    "end_date": "2027-12-31",
                    "monthly_rent": 9800,
                }
            ],
        },
        params={"should_transfer_deposit": True},
        headers=csrf_headers,
    )
    assert response.status_code == 404

    payload = response.json()
    assert payload.get("success") is False
    error = payload.get("error", {})
    assert isinstance(error, dict)
    assert error.get("code") == "RESOURCE_NOT_FOUND"


def test_contract_terminate_not_found_semantics_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
) -> None:
    response = authenticated_client.post(
        "/api/v1/rental-contracts/contracts/nonexistent/terminate",
        params={
            "termination_date": "2026-12-31",
            "should_refund_deposit": True,
            "deduction_amount": 0,
            "termination_reason": "e2e test",
        },
        headers=csrf_headers,
    )
    assert response.status_code == 404

    payload = response.json()
    assert payload.get("success") is False
    error = payload.get("error", {})
    assert isinstance(error, dict)
    assert error.get("code") == "RESOURCE_NOT_FOUND"
