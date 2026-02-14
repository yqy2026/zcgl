"""
End-to-End asset lifecycle tests.
"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.models.ownership import Ownership

pytestmark = pytest.mark.e2e


def _create_ownership(db_session, suffix: str) -> Ownership:
    ownership = Ownership(
        name=f"E2E权属方-{suffix}",
        code=f"E2E-OWN-{suffix}",
        short_name=f"E2E{suffix[:4]}",
        data_status="正常",
    )
    db_session.add(ownership)
    db_session.commit()
    db_session.refresh(ownership)
    return ownership


def _create_asset_payload(
    *,
    suffix: str,
    ownership_id: str,
    usage_status: str = "出租",
) -> dict[str, object]:
    return {
        "ownership_id": ownership_id,
        "property_name": f"E2E资产-{suffix}",
        "address": f"E2E地址-{suffix}",
        "ownership_status": "已确权",
        "property_nature": "经营类",
        "usage_status": usage_status,
        "business_category": f"E2E业态-{suffix}",
        "data_status": "正常",
        "created_by": "e2e_test",
    }


def test_asset_complete_lifecycle_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    suffix = uuid4().hex[:8]
    ownership = _create_ownership(db_session, suffix)
    payload = _create_asset_payload(
        suffix=suffix,
        ownership_id=ownership.id,
    )

    create_response = authenticated_client.post(
        "/api/v1/assets",
        json=payload,
        headers=csrf_headers,
    )
    assert create_response.status_code == 201
    created = create_response.json()
    asset_id = created.get("id")
    assert isinstance(asset_id, str)
    assert created.get("property_name") == payload["property_name"]

    detail_response = authenticated_client.get(f"/api/v1/assets/{asset_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail.get("id") == asset_id

    update_response = authenticated_client.put(
        f"/api/v1/assets/{asset_id}",
        json={"usage_status": "自用", "updated_by": "e2e_test"},
        headers=csrf_headers,
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated.get("usage_status") == "自用"

    delete_response = authenticated_client.delete(
        f"/api/v1/assets/{asset_id}",
        headers=csrf_headers,
    )
    assert delete_response.status_code == 204

    deleted_detail_response = authenticated_client.get(f"/api/v1/assets/{asset_id}")
    assert deleted_detail_response.status_code == 404


def test_asset_search_and_filter_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    suffix = uuid4().hex[:8]
    ownership = _create_ownership(db_session, suffix)

    payload_a = _create_asset_payload(
        suffix=f"{suffix}a",
        ownership_id=ownership.id,
        usage_status="出租",
    )
    payload_b = _create_asset_payload(
        suffix=f"{suffix}b",
        ownership_id=ownership.id,
        usage_status="闲置",
    )

    created_asset_ids: list[str] = []
    for payload in (payload_a, payload_b):
        response = authenticated_client.post(
            "/api/v1/assets",
            json=payload,
            headers=csrf_headers,
        )
        assert response.status_code == 201
        created = response.json()
        created_id = created.get("id")
        assert isinstance(created_id, str)
        created_asset_ids.append(created_id)

    search_response = authenticated_client.get(
        f"/api/v1/assets?page=1&page_size=20&search={suffix}"
    )
    assert search_response.status_code == 200
    search_payload = search_response.json()
    assert search_payload.get("success") is True
    search_items = search_payload.get("data", {}).get("items", [])
    assert isinstance(search_items, list)
    search_item_ids = {
        item.get("id")
        for item in search_items
        if isinstance(item, dict) and item.get("id") is not None
    }
    assert set(created_asset_ids).issubset(search_item_ids)

    filter_response = authenticated_client.get(
        f"/api/v1/assets?page=1&page_size=20&search={suffix}&usage_status=闲置"
    )
    assert filter_response.status_code == 200
    filter_payload = filter_response.json()
    assert filter_payload.get("success") is True
    filter_items = filter_payload.get("data", {}).get("items", [])
    assert isinstance(filter_items, list)
    assert any(
        item.get("id") in created_asset_ids
        for item in filter_items
        if isinstance(item, dict)
    )

    for asset_id in created_asset_ids:
        response = authenticated_client.delete(
            f"/api/v1/assets/{asset_id}",
            headers=csrf_headers,
        )
        assert response.status_code == 204
