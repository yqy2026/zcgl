"""
End-to-End contract workflow tests.
"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.models.ownership import Ownership

pytestmark = pytest.mark.e2e


def _create_ownership(db_session, suffix: str) -> Ownership:
    ownership = Ownership(
        name=f"E2E合同权属方-{suffix}",
        code=f"E2E-CON-OWN-{suffix}",
        short_name=f"EC{suffix[:4]}",
        data_status="正常",
    )
    db_session.add(ownership)
    db_session.commit()
    db_session.refresh(ownership)
    return ownership


def _create_contract_payload(*, suffix: str, ownership_id: str) -> dict[str, object]:
    return {
        "contract_number": f"E2E-CON-{suffix}",
        "contract_type": "lease_downstream",
        "tenant_name": f"E2E租户-{suffix}",
        "tenant_contact": "张三",
        "tenant_phone": "13800138000",
        "tenant_usage": "办公",
        "asset_ids": [],
        "ownership_id": ownership_id,
        "sign_date": "2026-01-01",
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
        "total_deposit": 10000,
        "monthly_rent_base": 5000,
        "payment_cycle": "monthly",
        "rent_terms": [
            {
                "start_date": "2026-01-01",
                "end_date": "2026-12-31",
                "monthly_rent": 5000,
            }
        ],
    }


def _create_asset_payload(*, suffix: str, ownership_id: str) -> dict[str, object]:
    return {
        "ownership_id": ownership_id,
        "property_name": f"E2E合同资产-{suffix}",
        "address": f"E2E合同资产地址-{suffix}",
        "ownership_status": "已确权",
        "property_nature": "经营类",
        "usage_status": "出租",
        "business_category": f"E2E合同业态-{suffix}",
        "data_status": "正常",
        "created_by": "e2e_contract_test",
    }


def _extract_contract_ids_from_list_response(payload: dict[str, object]) -> set[str]:
    data = payload.get("data", {})
    if not isinstance(data, dict):
        return set()
    items = data.get("items", [])
    if not isinstance(items, list):
        return set()
    return {
        item.get("id")
        for item in items
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }


def test_contract_list_endpoint_e2e(authenticated_client: TestClient) -> None:
    response = authenticated_client.get("/api/v1/rental-contracts/contracts")
    assert response.status_code == 200

    payload = response.json()
    assert payload.get("success") is True
    data = payload.get("data", {})
    assert isinstance(data.get("items"), list)
    assert isinstance(data.get("pagination"), dict)


def test_contract_list_filter_by_number_and_tenant_name_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    suffix = uuid4().hex[:8]
    ownership = _create_ownership(db_session, suffix)

    payload_a = _create_contract_payload(
        suffix=f"{suffix}a",
        ownership_id=ownership.id,
    )
    payload_a["tenant_name"] = f"E2E筛选租户A-{suffix}"
    payload_b = _create_contract_payload(
        suffix=f"{suffix}b",
        ownership_id=ownership.id,
    )
    payload_b["tenant_name"] = f"E2E筛选租户B-{suffix}"

    create_a = authenticated_client.post(
        "/api/v1/rental-contracts/contracts",
        json=payload_a,
        headers=csrf_headers,
    )
    assert create_a.status_code == 200
    contract_a_id = create_a.json().get("id")
    assert isinstance(contract_a_id, str)

    create_b = authenticated_client.post(
        "/api/v1/rental-contracts/contracts",
        json=payload_b,
        headers=csrf_headers,
    )
    assert create_b.status_code == 200
    contract_b_id = create_b.json().get("id")
    assert isinstance(contract_b_id, str)

    filter_by_number = authenticated_client.get(
        "/api/v1/rental-contracts/contracts",
        params={
            "page": 1,
            "page_size": 20,
            "contract_number": payload_a["contract_number"],
        },
    )
    assert filter_by_number.status_code == 200
    by_number_payload = filter_by_number.json()
    assert by_number_payload.get("success") is True
    by_number_ids = _extract_contract_ids_from_list_response(by_number_payload)
    assert contract_a_id in by_number_ids
    assert contract_b_id not in by_number_ids

    filter_by_tenant = authenticated_client.get(
        "/api/v1/rental-contracts/contracts",
        params={
            "page": 1,
            "page_size": 20,
            "tenant_name": payload_b["tenant_name"],
        },
    )
    assert filter_by_tenant.status_code == 200
    by_tenant_payload = filter_by_tenant.json()
    assert by_tenant_payload.get("success") is True
    by_tenant_ids = _extract_contract_ids_from_list_response(by_tenant_payload)
    assert contract_b_id in by_tenant_ids
    assert contract_a_id not in by_tenant_ids


def test_contract_list_filter_by_status_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    suffix = uuid4().hex[:8]
    ownership = _create_ownership(db_session, suffix)
    payload = _create_contract_payload(
        suffix=f"{suffix}status",
        ownership_id=ownership.id,
    )

    create_response = authenticated_client.post(
        "/api/v1/rental-contracts/contracts",
        json=payload,
        headers=csrf_headers,
    )
    assert create_response.status_code == 200
    contract_id = create_response.json().get("id")
    assert isinstance(contract_id, str)

    terminate_response = authenticated_client.post(
        f"/api/v1/rental-contracts/contracts/{contract_id}/terminate",
        params={
            "termination_date": "2026-06-30",
            "should_refund_deposit": True,
            "deduction_amount": 0,
            "termination_reason": "status filter",
        },
        headers=csrf_headers,
    )
    assert terminate_response.status_code == 200

    terminated_list_response = authenticated_client.get(
        "/api/v1/rental-contracts/contracts",
        params={"page": 1, "page_size": 20, "contract_status": "TERMINATED"},
    )
    assert terminated_list_response.status_code == 200
    terminated_payload = terminated_list_response.json()
    assert terminated_payload.get("success") is True
    terminated_ids = _extract_contract_ids_from_list_response(terminated_payload)
    assert contract_id in terminated_ids


def test_contract_list_filter_by_asset_id_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    suffix = uuid4().hex[:8]
    ownership = _create_ownership(db_session, suffix)

    asset_a_response = authenticated_client.post(
        "/api/v1/assets",
        json=_create_asset_payload(
            suffix=f"{suffix}asset-a",
            ownership_id=ownership.id,
        ),
        headers=csrf_headers,
    )
    assert asset_a_response.status_code == 201
    asset_a_id = asset_a_response.json().get("id")
    assert isinstance(asset_a_id, str)

    asset_b_response = authenticated_client.post(
        "/api/v1/assets",
        json=_create_asset_payload(
            suffix=f"{suffix}asset-b",
            ownership_id=ownership.id,
        ),
        headers=csrf_headers,
    )
    assert asset_b_response.status_code == 201
    asset_b_id = asset_b_response.json().get("id")
    assert isinstance(asset_b_id, str)

    payload_a = _create_contract_payload(
        suffix=f"{suffix}asset-contract-a",
        ownership_id=ownership.id,
    )
    payload_a["asset_ids"] = [asset_a_id]
    create_a = authenticated_client.post(
        "/api/v1/rental-contracts/contracts",
        json=payload_a,
        headers=csrf_headers,
    )
    assert create_a.status_code == 200
    contract_a_id = create_a.json().get("id")
    assert isinstance(contract_a_id, str)

    payload_b = _create_contract_payload(
        suffix=f"{suffix}asset-contract-b",
        ownership_id=ownership.id,
    )
    payload_b["asset_ids"] = [asset_b_id]
    create_b = authenticated_client.post(
        "/api/v1/rental-contracts/contracts",
        json=payload_b,
        headers=csrf_headers,
    )
    assert create_b.status_code == 200
    contract_b_id = create_b.json().get("id")
    assert isinstance(contract_b_id, str)

    filter_response = authenticated_client.get(
        "/api/v1/rental-contracts/contracts",
        params={"page": 1, "page_size": 20, "asset_id": asset_a_id},
    )
    assert filter_response.status_code == 200
    filter_payload = filter_response.json()
    assert filter_payload.get("success") is True
    filtered_ids = _extract_contract_ids_from_list_response(filter_payload)
    assert contract_a_id in filtered_ids
    assert contract_b_id not in filtered_ids


def test_contract_list_pagination_semantics_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    suffix = uuid4().hex[:8]
    marker = f"E2E分页租户-{suffix}"
    ownership = _create_ownership(db_session, suffix)

    created_ids: set[str] = set()
    for idx in range(3):
        payload = _create_contract_payload(
            suffix=f"{suffix}page-{idx}",
            ownership_id=ownership.id,
        )
        payload["tenant_name"] = f"{marker}-{idx}"
        create_response = authenticated_client.post(
            "/api/v1/rental-contracts/contracts",
            json=payload,
            headers=csrf_headers,
        )
        assert create_response.status_code == 200
        contract_id = create_response.json().get("id")
        assert isinstance(contract_id, str)
        created_ids.add(contract_id)

    page1_response = authenticated_client.get(
        "/api/v1/rental-contracts/contracts",
        params={"page": 1, "page_size": 1, "tenant_name": marker},
    )
    assert page1_response.status_code == 200
    page1_payload = page1_response.json()
    assert page1_payload.get("success") is True
    page1_ids = _extract_contract_ids_from_list_response(page1_payload)
    assert len(page1_ids) == 1
    page1_id = next(iter(page1_ids))
    assert page1_id in created_ids

    page1_pagination = page1_payload.get("data", {}).get("pagination", {})
    assert isinstance(page1_pagination, dict)
    assert page1_pagination.get("page") == 1
    assert page1_pagination.get("page_size") == 1
    assert page1_pagination.get("total") == 3
    assert page1_pagination.get("total_pages") == 3
    assert page1_pagination.get("has_next") is True
    assert page1_pagination.get("has_prev") is False

    page2_response = authenticated_client.get(
        "/api/v1/rental-contracts/contracts",
        params={"page": 2, "page_size": 1, "tenant_name": marker},
    )
    assert page2_response.status_code == 200
    page2_payload = page2_response.json()
    assert page2_payload.get("success") is True
    page2_ids = _extract_contract_ids_from_list_response(page2_payload)
    assert len(page2_ids) == 1
    page2_id = next(iter(page2_ids))
    assert page2_id in created_ids
    assert page2_id != page1_id

    page2_pagination = page2_payload.get("data", {}).get("pagination", {})
    assert isinstance(page2_pagination, dict)
    assert page2_pagination.get("page") == 2
    assert page2_pagination.get("page_size") == 1
    assert page2_pagination.get("total") == 3
    assert page2_pagination.get("total_pages") == 3
    assert page2_pagination.get("has_next") is True
    assert page2_pagination.get("has_prev") is True


def test_contract_list_filter_by_owner_party_id_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    suffix = uuid4().hex[:8]
    ownership_a = _create_ownership(db_session, f"{suffix}owner-a")
    ownership_b = _create_ownership(db_session, f"{suffix}owner-b")

    payload_a = _create_contract_payload(
        suffix=f"{suffix}owner-a-contract",
        ownership_id=ownership_a.id,
    )
    create_a = authenticated_client.post(
        "/api/v1/rental-contracts/contracts",
        json=payload_a,
        headers=csrf_headers,
    )
    assert create_a.status_code == 200
    contract_a_id = create_a.json().get("id")
    assert isinstance(contract_a_id, str)

    payload_b = _create_contract_payload(
        suffix=f"{suffix}owner-b-contract",
        ownership_id=ownership_b.id,
    )
    create_b = authenticated_client.post(
        "/api/v1/rental-contracts/contracts",
        json=payload_b,
        headers=csrf_headers,
    )
    assert create_b.status_code == 200
    contract_b_id = create_b.json().get("id")
    assert isinstance(contract_b_id, str)

    filter_response = authenticated_client.get(
        "/api/v1/rental-contracts/contracts",
        params={
            "page": 1,
            "page_size": 20,
            "owner_party_id": ownership_a.id,
        },
    )
    assert filter_response.status_code == 200
    filter_payload = filter_response.json()
    assert filter_payload.get("success") is True
    filtered_ids = _extract_contract_ids_from_list_response(filter_payload)
    assert contract_a_id in filtered_ids
    assert contract_b_id not in filtered_ids


def test_contract_list_filter_by_date_range_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    suffix = uuid4().hex[:8]
    marker = f"E2E日期筛选租户-{suffix}"
    ownership = _create_ownership(db_session, suffix)

    payload_2026 = _create_contract_payload(
        suffix=f"{suffix}date-2026",
        ownership_id=ownership.id,
    )
    payload_2026["tenant_name"] = f"{marker}-2026"
    create_2026 = authenticated_client.post(
        "/api/v1/rental-contracts/contracts",
        json=payload_2026,
        headers=csrf_headers,
    )
    assert create_2026.status_code == 200
    contract_2026_id = create_2026.json().get("id")
    assert isinstance(contract_2026_id, str)

    payload_2028 = _create_contract_payload(
        suffix=f"{suffix}date-2028",
        ownership_id=ownership.id,
    )
    payload_2028["tenant_name"] = f"{marker}-2028"
    payload_2028["sign_date"] = "2028-01-01"
    payload_2028["start_date"] = "2028-01-01"
    payload_2028["end_date"] = "2028-12-31"
    payload_2028["rent_terms"] = [
        {
            "start_date": "2028-01-01",
            "end_date": "2028-12-31",
            "monthly_rent": 5200,
        }
    ]
    create_2028 = authenticated_client.post(
        "/api/v1/rental-contracts/contracts",
        json=payload_2028,
        headers=csrf_headers,
    )
    assert create_2028.status_code == 200
    contract_2028_id = create_2028.json().get("id")
    assert isinstance(contract_2028_id, str)

    filter_response = authenticated_client.get(
        "/api/v1/rental-contracts/contracts",
        params={
            "page": 1,
            "page_size": 20,
            "tenant_name": marker,
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
        },
    )
    assert filter_response.status_code == 200
    filter_payload = filter_response.json()
    assert filter_payload.get("success") is True
    filtered_ids = _extract_contract_ids_from_list_response(filter_payload)
    assert contract_2026_id in filtered_ids
    assert contract_2028_id not in filtered_ids


def test_contract_list_filter_by_status_and_tenant_name_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    suffix = uuid4().hex[:8]
    marker = f"E2E组合筛选租户-{suffix}"
    ownership = _create_ownership(db_session, suffix)

    active_payload = _create_contract_payload(
        suffix=f"{suffix}combo-active",
        ownership_id=ownership.id,
    )
    active_payload["tenant_name"] = f"{marker}-active"
    create_active = authenticated_client.post(
        "/api/v1/rental-contracts/contracts",
        json=active_payload,
        headers=csrf_headers,
    )
    assert create_active.status_code == 200
    active_contract_id = create_active.json().get("id")
    assert isinstance(active_contract_id, str)

    terminated_payload = _create_contract_payload(
        suffix=f"{suffix}combo-terminated",
        ownership_id=ownership.id,
    )
    terminated_payload["tenant_name"] = f"{marker}-terminated"
    create_terminated = authenticated_client.post(
        "/api/v1/rental-contracts/contracts",
        json=terminated_payload,
        headers=csrf_headers,
    )
    assert create_terminated.status_code == 200
    terminated_contract_id = create_terminated.json().get("id")
    assert isinstance(terminated_contract_id, str)

    terminate_response = authenticated_client.post(
        f"/api/v1/rental-contracts/contracts/{terminated_contract_id}/terminate",
        params={
            "termination_date": "2026-06-30",
            "should_refund_deposit": True,
            "deduction_amount": 0,
            "termination_reason": "combo filter",
        },
        headers=csrf_headers,
    )
    assert terminate_response.status_code == 200

    filter_response = authenticated_client.get(
        "/api/v1/rental-contracts/contracts",
        params={
            "page": 1,
            "page_size": 20,
            "tenant_name": marker,
            "contract_status": "TERMINATED",
        },
    )
    assert filter_response.status_code == 200
    filter_payload = filter_response.json()
    assert filter_payload.get("success") is True
    filtered_ids = _extract_contract_ids_from_list_response(filter_payload)
    assert terminated_contract_id in filtered_ids
    assert active_contract_id not in filtered_ids


def test_contract_list_pagination_out_of_range_returns_empty_items_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    suffix = uuid4().hex[:8]
    marker = f"E2E越界分页租户-{suffix}"
    ownership = _create_ownership(db_session, suffix)

    for idx in range(2):
        payload = _create_contract_payload(
            suffix=f"{suffix}overflow-{idx}",
            ownership_id=ownership.id,
        )
        payload["tenant_name"] = f"{marker}-{idx}"
        create_response = authenticated_client.post(
            "/api/v1/rental-contracts/contracts",
            json=payload,
            headers=csrf_headers,
        )
        assert create_response.status_code == 200

    overflow_response = authenticated_client.get(
        "/api/v1/rental-contracts/contracts",
        params={
            "page": 3,
            "page_size": 2,
            "tenant_name": marker,
        },
    )
    assert overflow_response.status_code == 200
    overflow_payload = overflow_response.json()
    assert overflow_payload.get("success") is True
    overflow_items = overflow_payload.get("data", {}).get("items", [])
    assert isinstance(overflow_items, list)
    assert len(overflow_items) == 0

    pagination = overflow_payload.get("data", {}).get("pagination", {})
    assert isinstance(pagination, dict)
    assert pagination.get("page") == 3
    assert pagination.get("page_size") == 2
    assert pagination.get("total") == 2
    assert pagination.get("total_pages") == 1
    assert pagination.get("has_next") is False
    assert pagination.get("has_prev") is True


def test_contract_list_rejects_invalid_pagination_params_e2e(
    authenticated_client: TestClient,
) -> None:
    response = authenticated_client.get(
        "/api/v1/rental-contracts/contracts",
        params={"page": 0, "page_size": 101},
    )
    assert response.status_code == 422
    payload = response.json()
    assert payload.get("success") is False
    error = payload.get("error", {})
    assert isinstance(error, dict)
    assert error.get("code") == "VALIDATION_ERROR"


def test_contract_list_filter_with_invalid_status_returns_empty_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    suffix = uuid4().hex[:8]
    marker = f"E2E非法状态筛选租户-{suffix}"
    ownership = _create_ownership(db_session, suffix)

    payload = _create_contract_payload(
        suffix=f"{suffix}invalid-status",
        ownership_id=ownership.id,
    )
    payload["tenant_name"] = marker
    create_response = authenticated_client.post(
        "/api/v1/rental-contracts/contracts",
        json=payload,
        headers=csrf_headers,
    )
    assert create_response.status_code == 200

    filter_response = authenticated_client.get(
        "/api/v1/rental-contracts/contracts",
        params={
            "page": 1,
            "page_size": 20,
            "tenant_name": marker,
            "contract_status": "INVALID_STATUS_E2E",
        },
    )
    assert filter_response.status_code == 200
    filter_payload = filter_response.json()
    assert filter_payload.get("success") is True
    filtered_ids = _extract_contract_ids_from_list_response(filter_payload)
    assert len(filtered_ids) == 0


def test_contract_list_filter_by_single_sided_date_range_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    suffix = uuid4().hex[:8]
    marker = f"E2E单侧日期筛选租户-{suffix}"
    ownership = _create_ownership(db_session, suffix)

    payload_2026 = _create_contract_payload(
        suffix=f"{suffix}single-date-2026",
        ownership_id=ownership.id,
    )
    payload_2026["tenant_name"] = f"{marker}-2026"
    create_2026 = authenticated_client.post(
        "/api/v1/rental-contracts/contracts",
        json=payload_2026,
        headers=csrf_headers,
    )
    assert create_2026.status_code == 200
    contract_2026_id = create_2026.json().get("id")
    assert isinstance(contract_2026_id, str)

    payload_2028 = _create_contract_payload(
        suffix=f"{suffix}single-date-2028",
        ownership_id=ownership.id,
    )
    payload_2028["tenant_name"] = f"{marker}-2028"
    payload_2028["sign_date"] = "2028-01-01"
    payload_2028["start_date"] = "2028-01-01"
    payload_2028["end_date"] = "2028-12-31"
    payload_2028["rent_terms"] = [
        {
            "start_date": "2028-01-01",
            "end_date": "2028-12-31",
            "monthly_rent": 5200,
        }
    ]
    create_2028 = authenticated_client.post(
        "/api/v1/rental-contracts/contracts",
        json=payload_2028,
        headers=csrf_headers,
    )
    assert create_2028.status_code == 200
    contract_2028_id = create_2028.json().get("id")
    assert isinstance(contract_2028_id, str)

    start_only_response = authenticated_client.get(
        "/api/v1/rental-contracts/contracts",
        params={
            "page": 1,
            "page_size": 20,
            "tenant_name": marker,
            "start_date": "2027-01-01",
        },
    )
    assert start_only_response.status_code == 200
    start_only_payload = start_only_response.json()
    assert start_only_payload.get("success") is True
    start_only_ids = _extract_contract_ids_from_list_response(start_only_payload)
    assert contract_2028_id in start_only_ids
    assert contract_2026_id not in start_only_ids

    end_only_response = authenticated_client.get(
        "/api/v1/rental-contracts/contracts",
        params={
            "page": 1,
            "page_size": 20,
            "tenant_name": marker,
            "end_date": "2027-12-31",
        },
    )
    assert end_only_response.status_code == 200
    end_only_payload = end_only_response.json()
    assert end_only_payload.get("success") is True
    end_only_ids = _extract_contract_ids_from_list_response(end_only_payload)
    assert contract_2026_id in end_only_ids
    assert contract_2028_id not in end_only_ids


def test_contract_list_filter_by_owner_and_status_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    suffix = uuid4().hex[:8]
    ownership_a = _create_ownership(db_session, f"{suffix}combo-owner-a")
    ownership_b = _create_ownership(db_session, f"{suffix}combo-owner-b")

    active_a_payload = _create_contract_payload(
        suffix=f"{suffix}combo-active-a",
        ownership_id=ownership_a.id,
    )
    create_active_a = authenticated_client.post(
        "/api/v1/rental-contracts/contracts",
        json=active_a_payload,
        headers=csrf_headers,
    )
    assert create_active_a.status_code == 200
    active_a_id = create_active_a.json().get("id")
    assert isinstance(active_a_id, str)

    terminated_a_payload = _create_contract_payload(
        suffix=f"{suffix}combo-terminated-a",
        ownership_id=ownership_a.id,
    )
    create_terminated_a = authenticated_client.post(
        "/api/v1/rental-contracts/contracts",
        json=terminated_a_payload,
        headers=csrf_headers,
    )
    assert create_terminated_a.status_code == 200
    terminated_a_id = create_terminated_a.json().get("id")
    assert isinstance(terminated_a_id, str)

    terminated_b_payload = _create_contract_payload(
        suffix=f"{suffix}combo-terminated-b",
        ownership_id=ownership_b.id,
    )
    create_terminated_b = authenticated_client.post(
        "/api/v1/rental-contracts/contracts",
        json=terminated_b_payload,
        headers=csrf_headers,
    )
    assert create_terminated_b.status_code == 200
    terminated_b_id = create_terminated_b.json().get("id")
    assert isinstance(terminated_b_id, str)

    for contract_id in (terminated_a_id, terminated_b_id):
        terminate_response = authenticated_client.post(
            f"/api/v1/rental-contracts/contracts/{contract_id}/terminate",
            params={
                "termination_date": "2026-06-30",
                "should_refund_deposit": True,
                "deduction_amount": 0,
                "termination_reason": "owner+status combo filter",
            },
            headers=csrf_headers,
        )
        assert terminate_response.status_code == 200

    filter_response = authenticated_client.get(
        "/api/v1/rental-contracts/contracts",
        params={
            "page": 1,
            "page_size": 20,
            "owner_party_id": ownership_a.id,
            "contract_status": "TERMINATED",
        },
    )
    assert filter_response.status_code == 200
    filter_payload = filter_response.json()
    assert filter_payload.get("success") is True
    filtered_ids = _extract_contract_ids_from_list_response(filter_payload)
    assert terminated_a_id in filtered_ids
    assert active_a_id not in filtered_ids
    assert terminated_b_id not in filtered_ids


def test_contract_list_filter_by_asset_and_date_range_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    suffix = uuid4().hex[:8]
    ownership = _create_ownership(db_session, f"{suffix}asset-date")

    asset_response = authenticated_client.post(
        "/api/v1/assets",
        json=_create_asset_payload(
            suffix=f"{suffix}combo-asset",
            ownership_id=ownership.id,
        ),
        headers=csrf_headers,
    )
    assert asset_response.status_code == 201
    asset_id = asset_response.json().get("id")
    assert isinstance(asset_id, str)

    contract_2026_payload = _create_contract_payload(
        suffix=f"{suffix}asset-date-2026",
        ownership_id=ownership.id,
    )
    contract_2026_payload["asset_ids"] = [asset_id]
    create_2026 = authenticated_client.post(
        "/api/v1/rental-contracts/contracts",
        json=contract_2026_payload,
        headers=csrf_headers,
    )
    assert create_2026.status_code == 200
    contract_2026_id = create_2026.json().get("id")
    assert isinstance(contract_2026_id, str)

    contract_2028_payload = _create_contract_payload(
        suffix=f"{suffix}asset-date-2028",
        ownership_id=ownership.id,
    )
    contract_2028_payload["asset_ids"] = [asset_id]
    contract_2028_payload["sign_date"] = "2028-01-01"
    contract_2028_payload["start_date"] = "2028-01-01"
    contract_2028_payload["end_date"] = "2028-12-31"
    contract_2028_payload["rent_terms"] = [
        {
            "start_date": "2028-01-01",
            "end_date": "2028-12-31",
            "monthly_rent": 5200,
        }
    ]
    create_2028 = authenticated_client.post(
        "/api/v1/rental-contracts/contracts",
        json=contract_2028_payload,
        headers=csrf_headers,
    )
    assert create_2028.status_code == 200
    contract_2028_id = create_2028.json().get("id")
    assert isinstance(contract_2028_id, str)

    filter_response = authenticated_client.get(
        "/api/v1/rental-contracts/contracts",
        params={
            "page": 1,
            "page_size": 20,
            "asset_id": asset_id,
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
        },
    )
    assert filter_response.status_code == 200
    filter_payload = filter_response.json()
    assert filter_payload.get("success") is True
    filtered_ids = _extract_contract_ids_from_list_response(filter_payload)
    assert contract_2026_id in filtered_ids
    assert contract_2028_id not in filtered_ids


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


def test_contract_update_not_found_semantics_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
) -> None:
    response = authenticated_client.put(
        "/api/v1/rental-contracts/contracts/nonexistent",
        json={"tenant_name": "E2E更新不存在合同"},
        headers=csrf_headers,
    )
    assert response.status_code == 404

    payload = response.json()
    assert payload.get("success") is False
    error = payload.get("error", {})
    assert isinstance(error, dict)
    assert error.get("code") == "RESOURCE_NOT_FOUND"


def test_contract_delete_not_found_semantics_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
) -> None:
    response = authenticated_client.delete(
        "/api/v1/rental-contracts/contracts/nonexistent",
        headers=csrf_headers,
    )
    assert response.status_code == 404

    payload = response.json()
    assert payload.get("success") is False
    error = payload.get("error", {})
    assert isinstance(error, dict)
    assert error.get("code") == "RESOURCE_NOT_FOUND"


def test_contract_create_requires_csrf_header_e2e(
    authenticated_client: TestClient,
    db_session,
) -> None:
    suffix = uuid4().hex[:8]
    ownership = _create_ownership(db_session, suffix)
    payload = _create_contract_payload(
        suffix=f"{suffix}csrf",
        ownership_id=ownership.id,
    )

    response = authenticated_client.post("/api/v1/rental-contracts/contracts", json=payload)
    assert response.status_code == 403


def test_contract_create_requires_owner_reference_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
) -> None:
    payload: dict[str, object] = {
        "contract_number": f"E2E-CON-MISSING-OWNER-{uuid4().hex[:8]}",
        "contract_type": "lease_downstream",
        "tenant_name": "E2E缺少权属引用",
        "tenant_contact": "张三",
        "tenant_phone": "13800138000",
        "asset_ids": [],
        "sign_date": "2026-01-01",
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
        "total_deposit": 10000,
        "monthly_rent_base": 5000,
        "payment_cycle": "monthly",
        "rent_terms": [
            {
                "start_date": "2026-01-01",
                "end_date": "2026-12-31",
                "monthly_rent": 5000,
            }
        ],
    }

    response = authenticated_client.post(
        "/api/v1/rental-contracts/contracts",
        json=payload,
        headers=csrf_headers,
    )
    assert response.status_code == 422
    body = response.json()
    assert body.get("success") is False
    error = body.get("error", {})
    assert isinstance(error, dict)
    assert error.get("code") == "VALIDATION_ERROR"


def test_contract_create_rejects_invalid_date_range_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    suffix = uuid4().hex[:8]
    ownership = _create_ownership(db_session, suffix)
    payload = _create_contract_payload(
        suffix=f"{suffix}invalid-date",
        ownership_id=ownership.id,
    )
    payload["end_date"] = payload["start_date"]
    payload["rent_terms"] = [
        {
            "start_date": "2026-01-01",
            "end_date": "2026-01-01",
            "monthly_rent": 5000,
        }
    ]

    response = authenticated_client.post(
        "/api/v1/rental-contracts/contracts",
        json=payload,
        headers=csrf_headers,
    )
    assert response.status_code == 422
    body = response.json()
    assert body.get("success") is False
    error = body.get("error", {})
    assert isinstance(error, dict)
    assert error.get("code") == "VALIDATION_ERROR"


def test_contract_create_rejects_noncontinuous_rent_terms_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    suffix = uuid4().hex[:8]
    ownership = _create_ownership(db_session, suffix)
    payload = _create_contract_payload(
        suffix=f"{suffix}invalid-terms",
        ownership_id=ownership.id,
    )
    payload["rent_terms"] = [
        {
            "start_date": "2026-01-01",
            "end_date": "2026-06-30",
            "monthly_rent": 5000,
        },
        {
            "start_date": "2026-07-01",
            "end_date": "2026-12-31",
            "monthly_rent": 5200,
        },
    ]

    response = authenticated_client.post(
        "/api/v1/rental-contracts/contracts",
        json=payload,
        headers=csrf_headers,
    )
    assert response.status_code == 422
    body = response.json()
    assert body.get("success") is False
    error = body.get("error", {})
    assert isinstance(error, dict)
    assert error.get("code") == "VALIDATION_ERROR"


def test_contract_create_rejects_nonexistent_asset_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    suffix = uuid4().hex[:8]
    ownership = _create_ownership(db_session, suffix)
    payload = _create_contract_payload(
        suffix=f"{suffix}missing-asset",
        ownership_id=ownership.id,
    )
    payload["asset_ids"] = [f"missing-asset-{suffix}"]

    response = authenticated_client.post(
        "/api/v1/rental-contracts/contracts",
        json=payload,
        headers=csrf_headers,
    )
    assert response.status_code == 404
    body = response.json()
    assert body.get("success") is False
    error = body.get("error", {})
    assert isinstance(error, dict)
    assert error.get("code") == "RESOURCE_NOT_FOUND"


def test_contract_create_rejects_nonexistent_ownership_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
) -> None:
    suffix = uuid4().hex[:8]
    payload = _create_contract_payload(
        suffix=f"{suffix}missing-ownership",
        ownership_id=f"missing-ownership-{suffix}",
    )

    response = authenticated_client.post(
        "/api/v1/rental-contracts/contracts",
        json=payload,
        headers=csrf_headers,
    )
    assert response.status_code == 404
    body = response.json()
    assert body.get("success") is False
    error = body.get("error", {})
    assert isinstance(error, dict)
    assert error.get("code") == "RESOURCE_NOT_FOUND"


def test_contract_update_requires_csrf_header_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    suffix = uuid4().hex[:8]
    ownership = _create_ownership(db_session, suffix)
    payload = _create_contract_payload(
        suffix=f"{suffix}update-csrf",
        ownership_id=ownership.id,
    )

    create_response = authenticated_client.post(
        "/api/v1/rental-contracts/contracts",
        json=payload,
        headers=csrf_headers,
    )
    assert create_response.status_code == 200
    contract_id = create_response.json().get("id")
    assert isinstance(contract_id, str)

    update_response = authenticated_client.put(
        f"/api/v1/rental-contracts/contracts/{contract_id}",
        json={"tenant_name": f"E2E租户更新-{suffix}"},
    )
    assert update_response.status_code == 403


def test_contract_delete_requires_csrf_header_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    suffix = uuid4().hex[:8]
    ownership = _create_ownership(db_session, suffix)
    payload = _create_contract_payload(
        suffix=f"{suffix}delete-csrf",
        ownership_id=ownership.id,
    )

    create_response = authenticated_client.post(
        "/api/v1/rental-contracts/contracts",
        json=payload,
        headers=csrf_headers,
    )
    assert create_response.status_code == 200
    contract_id = create_response.json().get("id")
    assert isinstance(contract_id, str)

    delete_without_csrf = authenticated_client.delete(
        f"/api/v1/rental-contracts/contracts/{contract_id}"
    )
    assert delete_without_csrf.status_code == 403

    cleanup_response = authenticated_client.delete(
        f"/api/v1/rental-contracts/contracts/{contract_id}",
        headers=csrf_headers,
    )
    assert cleanup_response.status_code == 200


def test_contract_renew_requires_csrf_header_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    suffix = uuid4().hex[:8]
    ownership = _create_ownership(db_session, suffix)
    original_payload = _create_contract_payload(
        suffix=f"{suffix}renew-csrf-orig",
        ownership_id=ownership.id,
    )

    create_response = authenticated_client.post(
        "/api/v1/rental-contracts/contracts",
        json=original_payload,
        headers=csrf_headers,
    )
    assert create_response.status_code == 200
    original_contract_id = create_response.json().get("id")
    assert isinstance(original_contract_id, str)

    renew_payload = _create_contract_payload(
        suffix=f"{suffix}renew-csrf-new",
        ownership_id=ownership.id,
    )
    renew_payload["sign_date"] = "2027-01-01"
    renew_payload["start_date"] = "2027-01-01"
    renew_payload["end_date"] = "2027-12-31"
    renew_payload["rent_terms"] = [
        {
            "start_date": "2027-01-01",
            "end_date": "2027-12-31",
            "monthly_rent": 5200,
        }
    ]

    renew_without_csrf = authenticated_client.post(
        f"/api/v1/rental-contracts/contracts/{original_contract_id}/renew",
        json=renew_payload,
        params={"should_transfer_deposit": True},
    )
    assert renew_without_csrf.status_code == 403


def test_contract_terminate_requires_csrf_header_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    suffix = uuid4().hex[:8]
    ownership = _create_ownership(db_session, suffix)
    payload = _create_contract_payload(
        suffix=f"{suffix}terminate-csrf",
        ownership_id=ownership.id,
    )

    create_response = authenticated_client.post(
        "/api/v1/rental-contracts/contracts",
        json=payload,
        headers=csrf_headers,
    )
    assert create_response.status_code == 200
    contract_id = create_response.json().get("id")
    assert isinstance(contract_id, str)

    terminate_without_csrf = authenticated_client.post(
        f"/api/v1/rental-contracts/contracts/{contract_id}/terminate",
        params={
            "termination_date": "2026-06-30",
            "should_refund_deposit": True,
            "deduction_amount": 100,
            "termination_reason": "csrf required",
        },
    )
    assert terminate_without_csrf.status_code == 403


def test_contract_create_detail_and_delete_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    suffix = uuid4().hex[:8]
    ownership = _create_ownership(db_session, suffix)
    payload = _create_contract_payload(
        suffix=f"{suffix}crud",
        ownership_id=ownership.id,
    )

    create_response = authenticated_client.post(
        "/api/v1/rental-contracts/contracts",
        json=payload,
        headers=csrf_headers,
    )
    assert create_response.status_code == 200
    created = create_response.json()
    contract_id = created.get("id")
    assert isinstance(contract_id, str)
    assert created.get("contract_number") == payload["contract_number"]

    detail_response = authenticated_client.get(
        f"/api/v1/rental-contracts/contracts/{contract_id}"
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail.get("id") == contract_id

    delete_response = authenticated_client.delete(
        f"/api/v1/rental-contracts/contracts/{contract_id}",
        headers=csrf_headers,
    )
    assert delete_response.status_code == 200
    delete_payload = delete_response.json()
    assert delete_payload.get("message") == "合同删除成功"

    deleted_detail_response = authenticated_client.get(
        f"/api/v1/rental-contracts/contracts/{contract_id}"
    )
    assert deleted_detail_response.status_code == 404
    deleted_payload = deleted_detail_response.json()
    assert deleted_payload.get("success") is False
    error = deleted_payload.get("error", {})
    assert isinstance(error, dict)
    assert error.get("code") == "RESOURCE_NOT_FOUND"


def test_contract_update_lifecycle_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    suffix = uuid4().hex[:8]
    ownership = _create_ownership(db_session, suffix)
    payload = _create_contract_payload(
        suffix=f"{suffix}update",
        ownership_id=ownership.id,
    )

    create_response = authenticated_client.post(
        "/api/v1/rental-contracts/contracts",
        json=payload,
        headers=csrf_headers,
    )
    assert create_response.status_code == 200
    contract = create_response.json()
    contract_id = contract.get("id")
    assert isinstance(contract_id, str)

    update_payload = {
        "tenant_name": f"E2E更新租户-{suffix}",
        "monthly_rent_base": 5300,
    }
    update_response = authenticated_client.put(
        f"/api/v1/rental-contracts/contracts/{contract_id}",
        json=update_payload,
        headers=csrf_headers,
    )
    assert update_response.status_code == 200, update_response.text
    updated = update_response.json()
    assert updated.get("tenant_name") == update_payload["tenant_name"]

    detail_response = authenticated_client.get(
        f"/api/v1/rental-contracts/contracts/{contract_id}"
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail.get("tenant_name") == update_payload["tenant_name"]
    assert detail.get("monthly_rent_base") is not None
    assert float(detail["monthly_rent_base"]) == 5300.0


def test_contract_update_rent_terms_lifecycle_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    suffix = uuid4().hex[:8]
    ownership = _create_ownership(db_session, suffix)
    payload = _create_contract_payload(
        suffix=f"{suffix}update-terms",
        ownership_id=ownership.id,
    )

    create_response = authenticated_client.post(
        "/api/v1/rental-contracts/contracts",
        json=payload,
        headers=csrf_headers,
    )
    assert create_response.status_code == 200
    contract = create_response.json()
    contract_id = contract.get("id")
    assert isinstance(contract_id, str)

    update_payload = {
        "rent_terms": [
            {
                "start_date": "2026-01-01",
                "end_date": "2026-12-31",
                "monthly_rent": 5200,
                "management_fee": 200,
                "other_fees": 100,
                "total_monthly_amount": 5500,
            }
        ]
    }
    update_response = authenticated_client.put(
        f"/api/v1/rental-contracts/contracts/{contract_id}",
        json=update_payload,
        headers=csrf_headers,
    )
    assert update_response.status_code == 200, update_response.text
    updated = update_response.json()
    updated_terms = updated.get("rent_terms")
    assert isinstance(updated_terms, list)
    assert len(updated_terms) == 1

    updated_term = updated_terms[0]
    assert isinstance(updated_term, dict)
    assert updated_term.get("start_date") == "2026-01-01"
    assert updated_term.get("end_date") == "2026-12-31"
    assert updated_term.get("monthly_rent") is not None
    assert float(updated_term["monthly_rent"]) == 5200.0

    detail_response = authenticated_client.get(
        f"/api/v1/rental-contracts/contracts/{contract_id}"
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()
    detail_terms = detail.get("rent_terms")
    assert isinstance(detail_terms, list)
    assert len(detail_terms) == 1
    detail_term = detail_terms[0]
    assert isinstance(detail_term, dict)
    assert detail_term.get("monthly_rent") is not None
    assert float(detail_term["monthly_rent"]) == 5200.0


def test_contract_renew_lifecycle_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    suffix = uuid4().hex[:8]
    ownership = _create_ownership(db_session, suffix)
    original_payload = _create_contract_payload(
        suffix=f"{suffix}orig",
        ownership_id=ownership.id,
    )

    original_create_response = authenticated_client.post(
        "/api/v1/rental-contracts/contracts",
        json=original_payload,
        headers=csrf_headers,
    )
    assert original_create_response.status_code == 200
    original_contract = original_create_response.json()
    original_contract_id = original_contract.get("id")
    assert isinstance(original_contract_id, str)

    renew_payload = _create_contract_payload(
        suffix=f"{suffix}renew",
        ownership_id=ownership.id,
    )
    renew_payload["sign_date"] = "2027-01-01"
    renew_payload["start_date"] = "2027-01-01"
    renew_payload["end_date"] = "2027-12-31"
    renew_payload["rent_terms"] = [
        {
            "start_date": "2027-01-01",
            "end_date": "2027-12-31",
            "monthly_rent": 5200,
        }
    ]

    renew_response = authenticated_client.post(
        f"/api/v1/rental-contracts/contracts/{original_contract_id}/renew",
        json=renew_payload,
        params={"should_transfer_deposit": True},
        headers=csrf_headers,
    )
    assert renew_response.status_code == 200
    renewed_contract = renew_response.json()
    renewed_contract_id = renewed_contract.get("id")
    assert isinstance(renewed_contract_id, str)
    assert renewed_contract_id != original_contract_id

    original_after_renew = authenticated_client.get(
        f"/api/v1/rental-contracts/contracts/{original_contract_id}"
    )
    assert original_after_renew.status_code == 200
    original_after_payload = original_after_renew.json()
    assert original_after_payload.get("contract_status") == "TERMINATED"


def test_contract_renew_updates_original_end_date_when_new_start_earlier_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    suffix = uuid4().hex[:8]
    ownership = _create_ownership(db_session, f"{suffix}renew-end-date")
    original_payload = _create_contract_payload(
        suffix=f"{suffix}renew-end-date-orig",
        ownership_id=ownership.id,
    )

    original_create_response = authenticated_client.post(
        "/api/v1/rental-contracts/contracts",
        json=original_payload,
        headers=csrf_headers,
    )
    assert original_create_response.status_code == 200
    original_contract = original_create_response.json()
    original_contract_id = original_contract.get("id")
    assert isinstance(original_contract_id, str)

    renewal_start_date = "2026-06-01"
    renew_payload = _create_contract_payload(
        suffix=f"{suffix}renew-end-date-new",
        ownership_id=ownership.id,
    )
    renew_payload["sign_date"] = "2026-06-01"
    renew_payload["start_date"] = renewal_start_date
    renew_payload["end_date"] = "2027-05-31"
    renew_payload["rent_terms"] = [
        {
            "start_date": renewal_start_date,
            "end_date": "2027-05-31",
            "monthly_rent": 5200,
        }
    ]

    renew_response = authenticated_client.post(
        f"/api/v1/rental-contracts/contracts/{original_contract_id}/renew",
        json=renew_payload,
        params={"should_transfer_deposit": True},
        headers=csrf_headers,
    )
    assert renew_response.status_code == 200
    renewed = renew_response.json()
    renewed_contract_id = renewed.get("id")
    assert isinstance(renewed_contract_id, str)
    assert renewed_contract_id != original_contract_id
    assert renewed.get("start_date") == renewal_start_date

    original_after_renew = authenticated_client.get(
        f"/api/v1/rental-contracts/contracts/{original_contract_id}"
    )
    assert original_after_renew.status_code == 200
    original_after_payload = original_after_renew.json()
    assert original_after_payload.get("contract_status") == "TERMINATED"
    assert original_after_payload.get("end_date") == renewal_start_date


def test_contract_renew_keeps_original_end_date_when_new_start_later_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    suffix = uuid4().hex[:8]
    ownership = _create_ownership(db_session, f"{suffix}renew-keep-end-date")
    original_payload = _create_contract_payload(
        suffix=f"{suffix}renew-keep-end-date-orig",
        ownership_id=ownership.id,
    )

    original_create_response = authenticated_client.post(
        "/api/v1/rental-contracts/contracts",
        json=original_payload,
        headers=csrf_headers,
    )
    assert original_create_response.status_code == 200
    original_contract = original_create_response.json()
    original_contract_id = original_contract.get("id")
    assert isinstance(original_contract_id, str)
    original_end_date = original_contract.get("end_date")
    assert original_end_date == "2026-12-31"

    renew_payload = _create_contract_payload(
        suffix=f"{suffix}renew-keep-end-date-new",
        ownership_id=ownership.id,
    )
    renew_payload["sign_date"] = "2027-01-01"
    renew_payload["start_date"] = "2027-01-01"
    renew_payload["end_date"] = "2027-12-31"
    renew_payload["rent_terms"] = [
        {
            "start_date": "2027-01-01",
            "end_date": "2027-12-31",
            "monthly_rent": 5200,
        }
    ]

    renew_response = authenticated_client.post(
        f"/api/v1/rental-contracts/contracts/{original_contract_id}/renew",
        json=renew_payload,
        params={"should_transfer_deposit": True},
        headers=csrf_headers,
    )
    assert renew_response.status_code == 200

    original_after_renew = authenticated_client.get(
        f"/api/v1/rental-contracts/contracts/{original_contract_id}"
    )
    assert original_after_renew.status_code == 200
    original_after_payload = original_after_renew.json()
    assert original_after_payload.get("contract_status") == "TERMINATED"
    assert original_after_payload.get("end_date") == original_end_date


def test_contract_terminate_lifecycle_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    suffix = uuid4().hex[:8]
    ownership = _create_ownership(db_session, suffix)
    payload = _create_contract_payload(
        suffix=f"{suffix}term",
        ownership_id=ownership.id,
    )

    create_response = authenticated_client.post(
        "/api/v1/rental-contracts/contracts",
        json=payload,
        headers=csrf_headers,
    )
    assert create_response.status_code == 200
    contract = create_response.json()
    contract_id = contract.get("id")
    assert isinstance(contract_id, str)

    terminate_response = authenticated_client.post(
        f"/api/v1/rental-contracts/contracts/{contract_id}/terminate",
        params={
            "termination_date": "2026-06-30",
            "should_refund_deposit": True,
            "deduction_amount": 100,
            "termination_reason": "e2e terminate",
        },
        headers=csrf_headers,
    )
    assert terminate_response.status_code == 200
    terminated = terminate_response.json()
    assert terminated.get("id") == contract_id
    assert terminated.get("contract_status") == "TERMINATED"

    detail_response = authenticated_client.get(
        f"/api/v1/rental-contracts/contracts/{contract_id}"
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail.get("contract_status") == "TERMINATED"
    notes = detail.get("contract_notes")
    assert isinstance(notes, str)
    assert "e2e terminate" in notes


def test_contract_terminate_appends_existing_notes_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    suffix = uuid4().hex[:8]
    ownership = _create_ownership(db_session, f"{suffix}terminate-notes")
    payload = _create_contract_payload(
        suffix=f"{suffix}terminate-notes-contract",
        ownership_id=ownership.id,
    )
    payload["contract_notes"] = f"E2E初始备注-{suffix}"

    create_response = authenticated_client.post(
        "/api/v1/rental-contracts/contracts",
        json=payload,
        headers=csrf_headers,
    )
    assert create_response.status_code == 200
    contract_id = create_response.json().get("id")
    assert isinstance(contract_id, str)

    terminate_response = authenticated_client.post(
        f"/api/v1/rental-contracts/contracts/{contract_id}/terminate",
        params={
            "termination_date": "2026-06-30",
            "should_refund_deposit": False,
            "deduction_amount": 200,
            "termination_reason": "追加备注测试",
        },
        headers=csrf_headers,
    )
    assert terminate_response.status_code == 200

    detail_response = authenticated_client.get(
        f"/api/v1/rental-contracts/contracts/{contract_id}"
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()
    notes = detail.get("contract_notes")
    assert isinstance(notes, str)
    assert f"E2E初始备注-{suffix}" in notes
    assert "追加备注测试" in notes
    assert "退押金: 否" in notes
    assert "扣减金额: 200" in notes


def test_contract_detail_includes_assets_and_terms_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    suffix = uuid4().hex[:8]
    ownership = _create_ownership(db_session, f"{suffix}detail")

    asset_response = authenticated_client.post(
        "/api/v1/assets",
        json=_create_asset_payload(
            suffix=f"{suffix}detail-asset",
            ownership_id=ownership.id,
        ),
        headers=csrf_headers,
    )
    assert asset_response.status_code == 201
    asset_id = asset_response.json().get("id")
    assert isinstance(asset_id, str)

    payload = _create_contract_payload(
        suffix=f"{suffix}detail-contract",
        ownership_id=ownership.id,
    )
    payload["asset_ids"] = [asset_id]

    create_response = authenticated_client.post(
        "/api/v1/rental-contracts/contracts",
        json=payload,
        headers=csrf_headers,
    )
    assert create_response.status_code == 200
    contract_id = create_response.json().get("id")
    assert isinstance(contract_id, str)

    detail_response = authenticated_client.get(
        f"/api/v1/rental-contracts/contracts/{contract_id}"
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()

    assets = detail.get("assets")
    assert isinstance(assets, list)
    assert len(assets) >= 1
    asset_ids = {
        item.get("id")
        for item in assets
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    assert asset_id in asset_ids

    rent_terms = detail.get("rent_terms")
    assert isinstance(rent_terms, list)
    assert len(rent_terms) == 1
    term = rent_terms[0]
    assert isinstance(term, dict)
    assert term.get("start_date") == "2026-01-01"
    assert term.get("end_date") == "2026-12-31"
    assert term.get("monthly_rent") is not None
    assert float(term["monthly_rent"]) == 5000.0


def test_contract_terminate_updates_end_date_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    suffix = uuid4().hex[:8]
    ownership = _create_ownership(db_session, f"{suffix}end-date")
    payload = _create_contract_payload(
        suffix=f"{suffix}end-date-contract",
        ownership_id=ownership.id,
    )

    create_response = authenticated_client.post(
        "/api/v1/rental-contracts/contracts",
        json=payload,
        headers=csrf_headers,
    )
    assert create_response.status_code == 200
    contract_id = create_response.json().get("id")
    assert isinstance(contract_id, str)

    terminate_response = authenticated_client.post(
        f"/api/v1/rental-contracts/contracts/{contract_id}/terminate",
        params={
            "termination_date": "2026-05-31",
            "should_refund_deposit": True,
            "deduction_amount": 0,
            "termination_reason": "end date assertion",
        },
        headers=csrf_headers,
    )
    assert terminate_response.status_code == 200
    terminated = terminate_response.json()
    assert terminated.get("contract_status") == "TERMINATED"
    assert terminated.get("end_date") == "2026-05-31"

    detail_response = authenticated_client.get(
        f"/api/v1/rental-contracts/contracts/{contract_id}"
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail.get("contract_status") == "TERMINATED"
    assert detail.get("end_date") == "2026-05-31"
