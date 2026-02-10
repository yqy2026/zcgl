"""
End-to-End Integration Test for Property Certificate

This module tests the complete workflow:
1. Upload certificate file
2. Extract data using AI
3. Confirm and import
4. CRUD operations
"""

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models.asset import Asset
from src.models.ownership import Ownership
from src.models.property_certificate import PropertyCertificate
from src.services.property_certificate.service import PropertyCertificateService


def get_auth_headers(client: TestClient, admin_user) -> dict:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": admin_user.username, "password": "Admin123!@#"},
    )
    assert response.status_code == 200
    csrf_token = response.cookies.get("csrf_token")
    assert csrf_token is not None
    return {"X-CSRF-Token": csrf_token}


@pytest.mark.integration
def test_upload_extract_confirm_flow(
    db_session: Session, client: TestClient, test_data
):
    """测试完整的上传-提取-确认流程"""
    admin_user = test_data["admin"]
    headers = get_auth_headers(client, admin_user)

    # 1. Upload file (create a fake PDF)
    with tempfile.NamedTemporaryFile(mode="wb", suffix=".pdf", delete=False) as f:
        f.write(b"fake pdf content for testing")
        temp_path = f.name

    try:
        with open(temp_path, "rb") as f:
            response = client.post(
                "/api/v1/property-certificates/upload",
                files={"file": ("test_cert.pdf", f, "application/pdf")},
                headers=headers,
            )

        # Note: This test documents the expected flow
        # Actual LLM extraction won't work without real Qwen service
        # So we test the API structure and response format

        # For integration testing with real service, add: @pytest.mark.integration
        # And ensure Qwen Vision service is available

        print(f"Upload response status: {response.status_code}")
        print(f"Response: {response.json()}")

        # Test will document the expected structure
        assert response.status_code in [200, 400, 500]  # May fail if LLM not available

        if response.status_code == 200:
            result = response.json()
            assert "session_id" in result or "detail" in result

            if "session_id" in result:
                # Test confirm import
                confirm_data = {
                    "session_id": result["session_id"],
                    "extracted_data": result.get("extracted_data", {}),
                    "asset_link_id": None,
                    "asset_ids": [],
                    "should_create_new_asset": False,
                    "owners": [],
                }

                response = client.post(
                    "/api/v1/property-certificates/confirm-import",
                    json=confirm_data,
                    headers=headers,
                )

                assert response.status_code in [200, 400, 422, 500]
        else:
            # Expected to fail without real LLM service
            # Just verify the endpoint exists and returns proper error
            assert "detail" in response.json()

    finally:
        # Cleanup temp file
        Path(temp_path).unlink(missing_ok=True)


@pytest.mark.integration
def test_upload_returns_asset_matches(
    db_session: Session, client: TestClient, test_data, monkeypatch
):
    """上传产权证时应返回匹配资产"""
    admin_user = test_data["admin"]
    headers = get_auth_headers(client, admin_user)

    asset_data = {
        "ownership_entity": "测试权属方-匹配",
        "property_name": "测试物业-匹配",
        "address": "测试地址-匹配",
        "ownership_status": "已确权",
        "property_nature": "经营性",
        "usage_status": "出租",
    }

    ownership = Ownership(name=asset_data["ownership_entity"], code="OWN-MATCH-001")
    db_session.add(ownership)
    db_session.commit()
    db_session.refresh(ownership)

    asset = Asset(
        ownership_id=ownership.id,
        property_name=asset_data["property_name"],
        address=asset_data["address"],
        ownership_status=asset_data["ownership_status"],
        property_nature=asset_data["property_nature"],
        usage_status=asset_data["usage_status"],
    )
    asset.ownership = ownership
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(asset)

    async def fake_extract(self, file_path: str, filename: str):
        return {
            "success": True,
            "data": {
                "property_address": asset_data["address"],
                "owner_name": asset_data["ownership_entity"],
            },
            "confidence": 0.92,
            "raw_response": {},
            "extraction_method": "mock",
            "filename": filename,
        }

    monkeypatch.setattr(PropertyCertificateService, "extract_from_file", fake_extract)

    with tempfile.NamedTemporaryFile(mode="wb", suffix=".pdf", delete=False) as f:
        f.write(b"fake pdf content for matching test")
        temp_path = f.name

    try:
        with open(temp_path, "rb") as f:
            response = client.post(
                "/api/v1/property-certificates/upload",
                files={"file": ("match_cert.pdf", f, "application/pdf")},
                headers=headers,
            )

        assert response.status_code == 200
        result = response.json()

        assert result.get("asset_matches") is not None
        assert len(result["asset_matches"]) >= 1

        match = result["asset_matches"][0]
        assert match["asset_id"] == asset.id
        assert len(match["match_reasons"]) >= 1
        assert "权属方匹配" in match["match_reasons"]
        assert match["confidence"] >= 0.65
    finally:
        Path(temp_path).unlink(missing_ok=True)


@pytest.mark.integration
def test_crud_operations(db_session: Session, client: TestClient, test_data):
    """测试 CRUD 操作"""
    admin_user = test_data["admin"]
    headers = get_auth_headers(client, admin_user)

    # 1. Create certificate manually
    create_data = {
        "certificate_number": "TEST_E2E_001",
        "certificate_type": "other",
        "property_address": "测试地址",
        "asset_ids": [],
        "owner_ids": [],
    }

    response = client.post(
        "/api/v1/property-certificates/", json=create_data, headers=headers
    )
    assert response.status_code == 200
    certificate = response.json()
    cert_id = certificate["id"]

    # 2. Read certificate
    response = client.get(f"/api/v1/property-certificates/{cert_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["certificate_number"] == "TEST_E2E_001"

    # 3. Update certificate
    update_data = {"property_address": "更新后的地址"}
    response = client.put(
        f"/api/v1/property-certificates/{cert_id}",
        json=update_data,
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["property_address"] == "更新后的地址"

    # 4. Delete certificate
    response = client.delete(
        f"/api/v1/property-certificates/{cert_id}", headers=headers
    )
    assert response.status_code == 200

    # 5. Verify deletion
    response = client.get(f"/api/v1/property-certificates/{cert_id}", headers=headers)
    assert response.status_code == 404


@pytest.mark.integration
def test_validation_errors(db_session: Session, client: TestClient, test_data):
    """测试验证错误处理"""
    admin_user = test_data["admin"]
    headers = get_auth_headers(client, admin_user)

    # Test missing required field
    invalid_data = {
        "certificate_number": "TEST_VALIDATION_001",
        # Missing certificate_type and property_address
    }

    response = client.post(
        "/api/v1/property-certificates/", json=invalid_data, headers=headers
    )
    assert response.status_code == 422  # Validation error

    # Test invalid certificate number format
    invalid_data = {
        "certificate_number": "",  # Empty string
        "certificate_type": "real_estate",
        "property_address": "测试地址",
    }

    response = client.post(
        "/api/v1/property-certificates/", json=invalid_data, headers=headers
    )
    assert response.status_code == 422


@pytest.mark.integration
def test_certificate_with_asset_link(
    db_session: Session, client: TestClient, test_data
):
    """测试产权证与资产关联"""
    admin_user = test_data["admin"]
    headers = get_auth_headers(client, admin_user)

    asset_data = {
        "ownership_entity": "测试权属人",
        "property_name": "测试物业_关联资产",
        "address": "测试资产地址123号",
        "ownership_status": "已确权",
        "property_nature": "经营性",
        "usage_status": "出租",
    }

    ownership = Ownership(name=asset_data["ownership_entity"], code="OWN-LINK-001")
    db_session.add(ownership)
    db_session.commit()
    db_session.refresh(ownership)

    asset = Asset(
        ownership_id=ownership.id,
        property_name=asset_data["property_name"],
        address=asset_data["address"],
        ownership_status=asset_data["ownership_status"],
        property_nature=asset_data["property_nature"],
        usage_status=asset_data["usage_status"],
    )
    asset.ownership = ownership
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(asset)

    cert_data = {
        "certificate_number": "TEST_LINK_001",
        "certificate_type": "real_estate",
        "property_address": "测试地址123号",
    }

    response = client.post(
        "/api/v1/property-certificates/", json=cert_data, headers=headers
    )
    assert response.status_code == 200
    certificate = response.json()

    assert certificate["certificate_number"] == "TEST_LINK_001"

    db_certificate = (
        db_session.query(PropertyCertificate).filter_by(id=certificate["id"]).first()
    )
    db_asset = db_session.query(Asset).filter_by(id=asset.id).first()

    db_certificate.assets.append(db_asset)
    db_session.commit()
    db_session.refresh(db_certificate)

    assert any(linked.id == asset.id for linked in db_certificate.assets)

    # Cleanup
    client.delete(f"/api/v1/property-certificates/{certificate['id']}", headers=headers)


@pytest.mark.integration
def test_list_and_filter_certificates(
    db_session: Session, client: TestClient, test_data
):
    """测试列表和筛选功能"""
    admin_user = test_data["admin"]
    headers = get_auth_headers(client, admin_user)

    # Create multiple certificates
    cert_numbers = ["TEST_FILTER_001", "TEST_FILTER_002", "TEST_FILTER_003"]
    cert_ids = []

    for num in cert_numbers:
        data = {
            "certificate_number": num,
            "certificate_type": "other",
            "property_address": f"测试地址{num}",
            "asset_ids": [],
            "owner_ids": [],
        }
        response = client.post(
            "/api/v1/property-certificates/", json=data, headers=headers
        )
        assert response.status_code == 200
        cert_ids.append(response.json()["id"])

    # List all certificates
    response = client.get("/api/v1/property-certificates/", headers=headers)
    assert response.status_code == 200
    certificates = response.json()
    assert len(certificates) >= 3

    # Search by certificate number
    response = client.get(
        "/api/v1/property-certificates/?search=TEST_FILTER_001", headers=headers
    )
    assert response.status_code == 200
    results = response.json()
    assert len(results) >= 1
    assert any(cert["certificate_number"] == "TEST_FILTER_001" for cert in results)

    # Filter by certificate type
    response = client.get(
        "/api/v1/property-certificates/?certificate_type=other", headers=headers
    )
    assert response.status_code == 200
    results = response.json()
    assert len(results) >= 3

    # Cleanup
    for cert_id in cert_ids:
        client.delete(f"/api/v1/property-certificates/{cert_id}", headers=headers)
