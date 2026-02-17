"""
V2 Contract API integration tests with real authentication flow.
"""

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


@pytest.fixture
def authenticated_client(client: TestClient, test_data) -> TestClient:
    """Authenticate via real login and inject cookie tokens."""
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
    """CSRF header required for state-changing requests in cookie-only auth."""
    csrf_token = getattr(authenticated_client, "_csrf_token", None)
    if csrf_token is None:
        return {}
    return {"X-CSRF-Token": csrf_token}


@pytest.fixture
def v2_contract_payload() -> dict:
    """Sample V2 contract payload for endpoint contract tests."""
    return {
        "contract_number": "V2TEST001",
        "contract_type": "lease_downstream",
        "upstream_contract_id": None,
        "tenant_name": "测试租户",
        "tenant_contact": "张三",
        "tenant_phone": "13800138000",
        "tenant_usage": "办公用途",
        "asset_ids": [],
        "ownership_id": "ownership_nonexistent",
        "sign_date": "2026-01-01",
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
        "total_deposit": 30000,
        "monthly_rent_base": 10000,
        "payment_cycle": "monthly",
        "rent_terms": [
            {
                "start_date": "2026-01-01",
                "end_date": "2026-12-31",
                "monthly_rent": 10000,
            },
        ],
    }


class TestContractV2API:
    """V2 contract API endpoint availability with real auth."""

    def test_create_contract_with_v2_fields(
        self,
        authenticated_client: TestClient,
        csrf_headers: dict[str, str],
        v2_contract_payload: dict,
    ) -> None:
        response = authenticated_client.post(
            "/api/v1/rental-contracts/contracts",
            json=v2_contract_payload,
            headers=csrf_headers,
        )
        assert response.status_code == 404
        payload = response.json()
        assert payload.get("success") is False

    def test_renew_contract_endpoint(
        self,
        authenticated_client: TestClient,
        csrf_headers: dict[str, str],
    ) -> None:
        renewal_payload = {
            "contract_number": "V2TEST002",
            "contract_type": "lease_downstream",
            "tenant_name": "测试租户",
            "asset_ids": [],
            "ownership_id": "ownership_nonexistent",
            "sign_date": "2027-01-01",
            "start_date": "2027-01-01",
            "end_date": "2027-12-31",
            "total_deposit": 30000,
            "rent_terms": [
                {
                    "start_date": "2027-01-01",
                    "end_date": "2027-12-31",
                    "monthly_rent": 9000,
                }
            ],
        }

        response = authenticated_client.post(
            "/api/v1/rental-contracts/contracts/original_001/renew",
            json=renewal_payload,
            params={"should_transfer_deposit": True},
            headers=csrf_headers,
        )
        assert response.status_code == 404
        payload = response.json()
        assert payload.get("success") is False

    def test_terminate_contract_endpoint(
        self,
        authenticated_client: TestClient,
        csrf_headers: dict[str, str],
    ) -> None:
        response = authenticated_client.post(
            "/api/v1/rental-contracts/contracts/contract_001/terminate",
            params={
                "termination_date": "2026-06-30",
                "should_refund_deposit": True,
                "deduction_amount": 5000,
                "termination_reason": "提前退租",
            },
            headers=csrf_headers,
        )
        assert response.status_code == 404
        payload = response.json()
        assert payload.get("success") is False


class TestContractV2Validation:
    """V2 contract schema validation rules."""

    def test_entrusted_contract_requires_service_fee_rate(self) -> None:
        from src.schemas.rent_contract import RentContractCreate, RentTermCreate

        valid_data = {
            "contract_number": "EN001",
            "contract_type": "entrusted",
            "service_fee_rate": 0.05,
            "tenant_name": "委托方",
            "ownership_id": "ownership_001",
            "sign_date": date(2026, 1, 1),
            "start_date": date(2026, 1, 1),
            "end_date": date(2026, 12, 31),
            "rent_terms": [
                RentTermCreate(
                    start_date=date(2026, 1, 1),
                    end_date=date(2026, 12, 31),
                    monthly_rent=5000.0,
                )
            ],
        }
        contract = RentContractCreate(**valid_data)
        assert contract.service_fee_rate == Decimal("0.05")

    def test_downstream_contract_allows_tenant_usage(self) -> None:
        from src.schemas.rent_contract import RentContractCreate, RentTermCreate

        data = {
            "contract_number": "DN001",
            "contract_type": "lease_downstream",
            "tenant_name": "终端租户",
            "tenant_usage": "餐饮用途",
            "ownership_id": "ownership_001",
            "sign_date": date(2026, 1, 1),
            "start_date": date(2026, 1, 1),
            "end_date": date(2026, 12, 31),
            "rent_terms": [
                RentTermCreate(
                    start_date=date(2026, 1, 1),
                    end_date=date(2026, 12, 31),
                    monthly_rent=5000.0,
                )
            ],
        }
        contract = RentContractCreate(**data)
        assert contract.tenant_usage == "餐饮用途"

    def test_payment_cycle_validation(self) -> None:
        from src.schemas.rent_contract import RentContractCreate, RentTermCreate

        for cycle in ["monthly", "quarterly", "semi_annual", "annual"]:
            data = {
                "contract_number": f"CY{cycle}",
                "contract_type": "lease_downstream",
                "tenant_name": "租户",
                "ownership_id": "ownership_001",
                "sign_date": date(2026, 1, 1),
                "start_date": date(2026, 1, 1),
                "end_date": date(2026, 12, 31),
                "payment_cycle": cycle,
                "rent_terms": [
                    RentTermCreate(
                        start_date=date(2026, 1, 1),
                        end_date=date(2026, 12, 31),
                        monthly_rent=5000.0,
                    )
                ],
            }
            contract = RentContractCreate(**data)
            assert contract.payment_cycle == cycle


class TestStatisticsV2API:
    """V2 statistics endpoints with real auth."""

    def test_ownership_statistics_endpoint(
        self,
        authenticated_client: TestClient,
    ) -> None:
        response = authenticated_client.get("/api/v1/rental-contracts/statistics/ownership")
        assert response.status_code == 200
        payload = response.json()
        assert isinstance(payload, list)

    def test_asset_statistics_endpoint(self, authenticated_client: TestClient) -> None:
        response = authenticated_client.get("/api/v1/rental-contracts/statistics/asset")
        assert response.status_code == 200
        payload = response.json()
        assert isinstance(payload, list)
