"""
Contract renewal integration smoke tests (async-era aligned).
"""

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


@pytest.fixture
def authenticated_client(client: TestClient, test_data) -> TestClient:
    admin_user = test_data["admin"]
    response = client.post(
        "/api/v1/auth/login",
        json={"username": admin_user.username, "password": "Admin123!@#"},
    )
    assert response.status_code == 200
    auth_token = response.cookies.get("auth_token")
    csrf_token = response.cookies.get("csrf_token")
    assert auth_token is not None
    client.cookies.set("auth_token", auth_token)
    if csrf_token is not None:
        client.cookies.set("csrf_token", csrf_token)
    setattr(client, "_csrf_token", csrf_token)
    return client


@pytest.fixture
def csrf_headers(authenticated_client: TestClient) -> dict[str, str]:
    csrf_token = getattr(authenticated_client, "_csrf_token", None)
    if csrf_token is None:
        return {}
    return {"X-CSRF-Token": csrf_token}


def test_contract_list_endpoint_smoke(authenticated_client: TestClient) -> None:
    response = authenticated_client.get("/api/v1/rental-contracts/contracts")
    assert response.status_code == 200
    payload = response.json()
    assert payload.get("success") is True
    data = payload.get("data", {})
    assert isinstance(data.get("items"), list)
    assert isinstance(data.get("pagination"), dict)


def test_statistics_overview_endpoint_smoke(authenticated_client: TestClient) -> None:
    response = authenticated_client.get("/api/v1/rental-contracts/statistics/overview")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, dict)


def test_renew_contract_endpoint_input_validation(
    authenticated_client: TestClient, csrf_headers: dict[str, str]
) -> None:
    response = authenticated_client.post(
        "/api/v1/rental-contracts/contracts/nonexistent/renew",
        json={
            "contract_number": "REN-SMOKE-001",
            "contract_type": "lease_downstream",
            "tenant_name": "续签租户",
            "ownership_id": "ownership_001",
            "sign_date": "2027-01-01",
            "start_date": "2027-01-01",
            "end_date": "2027-12-31",
            "rent_terms": [
                {
                    "start_date": "2027-01-01",
                    "end_date": "2027-12-31",
                    "monthly_rent": 8000,
                }
            ],
        },
        params={"should_transfer_deposit": True},
        headers=csrf_headers,
    )
    assert response.status_code == 404
    payload = response.json()
    assert payload.get("success") is False


def test_terminate_contract_endpoint_input_validation(
    authenticated_client: TestClient, csrf_headers: dict[str, str]
) -> None:
    response = authenticated_client.post(
        "/api/v1/rental-contracts/contracts/nonexistent/terminate",
        params={
            "termination_date": "2026-06-30",
            "should_refund_deposit": True,
            "deduction_amount": 0,
            "termination_reason": "smoke",
        },
        headers=csrf_headers,
    )
    assert response.status_code == 404
    payload = response.json()
    assert payload.get("success") is False
