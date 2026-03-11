"""
合同组 API 集成烟测

验证新合同组/合同生命周期路由已挂载到真实 app，
且退休的旧合同入口已下线。
"""

import pytest
from fastapi.testclient import TestClient

from src.models.organization import Organization
from src.models.ownership import Ownership
from src.models.party import Party, PartyReviewStatus, PartyType
from src.models.pdf_import_session import (
    PDFImportSession,
    ProcessingStep,
    SessionStatus,
)

pytestmark = pytest.mark.integration


def _retired_contract_routes_path() -> str:
    return "/".join(("", "api", "v1", "-".join(("rental", "contracts"))))


def _build_csrf_headers(client: TestClient) -> dict[str, str]:
    csrf_token = getattr(client, "_csrf_token", None)
    if csrf_token is None:
        return {}
    return {"X-CSRF-Token": csrf_token}


@pytest.fixture
def authenticated_client(client: TestClient, test_data) -> TestClient:
    """通过真实登录流程初始化认证 cookie。"""
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


class TestContractGroupRoutes:
    def test_registered_routes(self, authenticated_client: TestClient) -> None:
        response = authenticated_client.get("/openapi.json")
        assert response.status_code == 200

        paths = response.json()["paths"].keys()
        required_paths = [
            "/api/v1/contract-groups",
            "/api/v1/contract-groups/{group_id}",
            "/api/v1/contract-groups/{group_id}/contracts",
            "/api/v1/contract-groups/{group_id}/submit-review",
            "/api/v1/contracts/{contract_id}",
            "/api/v1/contracts/{contract_id}/submit-review",
            "/api/v1/contracts/{contract_id}/approve",
            "/api/v1/contracts/{contract_id}/reject",
            "/api/v1/contracts/{contract_id}/expire",
            "/api/v1/contracts/{contract_id}/terminate",
            "/api/v1/contracts/{contract_id}/void",
            "/api/v1/contracts/{contract_id}/rent-terms",
            "/api/v1/contracts/{contract_id}/rent-terms/{rent_term_id}",
            "/api/v1/contracts/{contract_id}/ledger",
            "/api/v1/contracts/{contract_id}/ledger/batch-update-status",
        ]

        for route in required_paths:
            assert route in paths

    def test_retired_contract_paths_are_not_registered(
        self, authenticated_client: TestClient
    ) -> None:
        response = authenticated_client.get(_retired_contract_routes_path())
        assert response.status_code == 404

    def test_missing_contract_group_maps_to_404(
        self, authenticated_client: TestClient
    ) -> None:
        response = authenticated_client.get("/api/v1/contract-groups/grp-notexist")
        assert response.status_code == 404

    def test_pdf_confirm_submit_review_approve_and_query_ledger_flow(
        self,
        authenticated_client: TestClient,
        db_session,
    ) -> None:
        operator = Organization(
            name="M2 集成测试运营方",
            code="M2-INT-OPERATOR",
            level=1,
            sort_order=0,
            type="department",
            status="active",
            path="/M2-INT-OPERATOR",
            created_by="integration_test",
            updated_by="integration_test",
        )
        lessee = Organization(
            name="M2 集成测试承租方",
            code="M2-INT-LESSEE",
            level=1,
            sort_order=0,
            type="department",
            status="active",
            path="/M2-INT-LESSEE",
            created_by="integration_test",
            updated_by="integration_test",
        )
        owner = Ownership(
            name="M2 集成测试产权方",
            code="M2-INT-OWNER",
            created_by="integration_test",
            updated_by="integration_test",
        )
        db_session.add_all([operator, lessee, owner])
        db_session.commit()
        db_session.refresh(operator)
        db_session.refresh(lessee)
        db_session.refresh(owner)

        operator_party = Party(
            party_type=PartyType.ORGANIZATION.value,
            name="M2 集成测试运营方 Party",
            code="M2-INT-OPERATOR-PARTY",
            external_ref=operator.id,
            status="active",
            review_status=PartyReviewStatus.APPROVED.value,
        )
        lessee_party = Party(
            party_type=PartyType.ORGANIZATION.value,
            name="M2 集成测试承租方 Party",
            code="M2-INT-LESSEE-PARTY",
            external_ref=lessee.id,
            status="active",
            review_status=PartyReviewStatus.APPROVED.value,
        )
        owner_party = Party(
            party_type=PartyType.LEGAL_ENTITY.value,
            name="M2 集成测试产权方 Party",
            code="M2-INT-OWNER-PARTY",
            external_ref=owner.id,
            status="active",
            review_status=PartyReviewStatus.APPROVED.value,
        )
        db_session.add_all([operator_party, lessee_party, owner_party])
        db_session.commit()
        db_session.refresh(operator_party)
        db_session.refresh(lessee_party)
        db_session.refresh(owner_party)

        import_session = PDFImportSession(
            session_id="session-m2-contract-ledger-flow",
            original_filename="m2-contract.pdf",
            file_size=1024,
            file_path="/tmp/m2-contract.pdf",
            content_type="application/pdf",
            status=SessionStatus.READY_FOR_REVIEW,
            current_step=ProcessingStep.FINAL_REVIEW,
            progress_percentage=96.0,
            extracted_data={},
            processing_result={},
            confidence_score=0.96,
            processing_method="mock",
            organization_id=None,
        )
        db_session.add(import_session)
        db_session.commit()
        db_session.refresh(import_session)

        csrf_headers = _build_csrf_headers(authenticated_client)
        confirm_response = authenticated_client.post(
            "/api/v1/pdf-import/confirm",
            json={
                "session_id": import_session.session_id,
                "confirmed_data": {
                    "contract_number": "M2-INT-20260309-001",
                    "tenant_name": "M2 集成测试租户",
                    "start_date": "2026-01-01",
                    "end_date": "2026-03-31",
                    "sign_date": "2026-01-01",
                    "monthly_rent_base": "10000.00",
                    "total_deposit": "5000.00",
                    "payment_cycle": "月付",
                    "revenue_mode": "LEASE",
                    "operator_party_id": operator_party.id,
                    "owner_party_id": owner_party.id,
                    "contract_direction": "LESSOR",
                    "group_relation_type": "UPSTREAM",
                    "lessor_party_id": owner_party.id,
                    "lessee_party_id": lessee_party.id,
                    "settlement_rule": {
                        "version": "v1",
                        "cycle": "月付",
                        "settlement_mode": "manual",
                        "amount_rule": {"basis": "fixed"},
                        "payment_rule": {"due_day": 1},
                    },
                    "rent_terms": [
                        {
                            "start_date": "2026-01-01",
                            "end_date": "2026-03-31",
                            "monthly_rent": "10000.00",
                            "management_fee": "500.00",
                            "other_fees": "0.00",
                            "notes": "集成测试租金条款",
                        }
                    ],
                },
            },
            headers=csrf_headers,
        )

        assert confirm_response.status_code == 200
        confirm_payload = confirm_response.json()
        assert confirm_payload["success"] is True
        contract_group_id = confirm_payload["contract_group_id"]
        contract_id = confirm_payload["contract_id"]
        assert isinstance(contract_group_id, str)
        assert contract_group_id.strip() != ""
        assert isinstance(contract_id, str)
        assert contract_id.strip() != ""
        assert confirm_payload["created_terms_count"] == 1

        detail_response = authenticated_client.get(f"/api/v1/contracts/{contract_id}")
        assert detail_response.status_code == 200
        detail_payload = detail_response.json()
        assert detail_payload["status"] == "草稿"
        assert detail_payload["review_status"] == "草稿"

        submit_response = authenticated_client.post(
            f"/api/v1/contracts/{contract_id}/submit-review",
            json={},
            headers=csrf_headers,
        )
        assert submit_response.status_code == 200
        submit_payload = submit_response.json()
        assert submit_payload["status"] == "待审"
        assert submit_payload["review_status"] == "待审"

        approve_response = authenticated_client.post(
            f"/api/v1/contracts/{contract_id}/approve",
            json={},
            headers=csrf_headers,
        )
        assert approve_response.status_code == 200
        approve_payload = approve_response.json()
        assert approve_payload["status"] == "生效"
        assert approve_payload["review_status"] == "已审"

        group_response = authenticated_client.get(
            f"/api/v1/contract-groups/{contract_group_id}"
        )
        assert group_response.status_code == 200
        group_payload = group_response.json()
        assert group_payload["derived_status"] == "生效中"
        assert len(group_payload["contracts"]) == 1
        assert group_payload["contracts"][0]["contract_id"] == contract_id

        ledger_response = authenticated_client.get(
            f"/api/v1/contracts/{contract_id}/ledger"
        )
        assert ledger_response.status_code == 200
        ledger_payload = ledger_response.json()
        assert ledger_payload["total"] == 3
        assert [item["year_month"] for item in ledger_payload["items"]] == [
            "2026-01",
            "2026-02",
            "2026-03",
        ]
        assert [item["due_date"] for item in ledger_payload["items"]] == [
            "2026-01-01",
            "2026-02-01",
            "2026-03-01",
        ]
        assert all(item["payment_status"] == "unpaid" for item in ledger_payload["items"])
