"""
合同工作流集成测试

Integration tests for complete contract workflow
"""

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


@pytest.fixture
def authenticated_client(client: TestClient, test_data) -> TestClient:
    """通过真实登录流程注入认证 cookie。"""
    admin_user = test_data["admin"]
    response = client.post(
        "/api/v1/auth/login",
        json={"identifier": admin_user.username, "password": "Admin123!@#"},
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
    """返回 cookie-only 场景下写操作所需 CSRF 头。"""
    csrf_token = getattr(authenticated_client, "_csrf_token", None)
    if csrf_token is None:
        return {}
    return {"X-CSRF-Token": csrf_token}


class TestContractWorkflow:
    """租赁合同流程关键路径契约测试。"""

    def test_contract_list_endpoint_contract(
        self, authenticated_client: TestClient
    ) -> None:
        response = authenticated_client.get("/api/v1/rental-contracts/contracts")
        assert response.status_code == 200
        payload = response.json()
        assert payload.get("success") is True
        data = payload.get("data", {})
        assert isinstance(data.get("items"), list)
        assert isinstance(data.get("pagination"), dict)

    def test_contract_detail_not_found_semantics(
        self, authenticated_client: TestClient
    ) -> None:
        response = authenticated_client.get(
            "/api/v1/rental-contracts/contracts/nonexistent"
        )
        assert response.status_code == 404
        payload = response.json()
        assert payload.get("success") is False
        error = payload.get("error", {})
        assert isinstance(error, dict)
        assert error.get("code") == "RESOURCE_NOT_FOUND"

    def test_contract_renew_not_found_semantics(
        self, authenticated_client: TestClient, csrf_headers: dict[str, str]
    ) -> None:
        response = authenticated_client.post(
            "/api/v1/rental-contracts/contracts/nonexistent/renew",
            json={
                "contract_number": "WF-RENEW-001",
                "contract_type": "lease_downstream",
                "tenant_name": "工作流续签租户",
                "ownership_id": "ownership_001",
                "sign_date": "2027-01-01",
                "start_date": "2027-01-01",
                "end_date": "2027-12-31",
                "rent_terms": [
                    {
                        "start_date": "2027-01-01",
                        "end_date": "2027-12-31",
                        "monthly_rent": 8500,
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

    def test_contract_terminate_not_found_semantics(
        self, authenticated_client: TestClient, csrf_headers: dict[str, str]
    ) -> None:
        response = authenticated_client.post(
            "/api/v1/rental-contracts/contracts/nonexistent/terminate",
            params={
                "termination_date": "2026-06-30",
                "should_refund_deposit": True,
                "deduction_amount": 0,
                "termination_reason": "workflow test",
            },
            headers=csrf_headers,
        )
        assert response.status_code == 404
        payload = response.json()
        assert payload.get("success") is False
        error = payload.get("error", {})
        assert isinstance(error, dict)
        assert error.get("code") == "RESOURCE_NOT_FOUND"
