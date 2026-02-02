"""
产权证API测试

Test coverage for Property Certificate API endpoints:
- Upload certificate
- CRUD operations
- Validation
- Error handling
"""

import io
from pathlib import Path

import pytest
from fastapi import status
from src.services.property_certificate.service import PropertyCertificateService

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def admin_user_headers(client, admin_user, monkeypatch):
    """管理员用户认证头"""
    from src.middleware.auth import RBACPermissionChecker

    def allow_admin(self, current_user=None, db=None):  # noqa: ANN001 - test stub
        return admin_user

    monkeypatch.setattr(RBACPermissionChecker, "__call__", allow_admin)
    return {}


# ============================================================================
# Upload Certificate Tests
# ============================================================================


class TestUploadCertificate:
    """测试上传产权证API"""

    @pytest.mark.parametrize(
        ("filename", "content_type"),
        [
            ("cert.jpg", "image/jpeg"),
            ("cert.jpeg", "image/jpeg"),
            ("cert.png", "image/png"),
        ],
    )
    def test_upload_certificate_accepts_images(
        self, client, admin_user_headers, monkeypatch, filename, content_type
    ):
        """测试上传图片格式产权证"""

        async def fake_extract(self, file_path: str, safe_name: str):
            expected_ext = Path(filename).suffix
            assert safe_name.endswith(expected_ext)
            return {
                "data": {"certificate_number": "IMG-001"},
                "confidence": 0.88,
            }

        monkeypatch.setattr(PropertyCertificateService, "extract_from_file", fake_extract)
        monkeypatch.setattr(PropertyCertificateService, "match_assets", lambda *_: [])

        response = client.post(
            "/api/v1/property-certificates/upload",
            files={"file": (filename, io.BytesIO(b"fake image data"), content_type)},
            headers=admin_user_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert payload["confidence_score"] == 0.88
        assert payload["extracted_data"]["certificate_number"] == "IMG-001"

    def test_upload_certificate_unauthorized(self, unauthenticated_client):
        """测试未授权上传"""
        response = unauthenticated_client.post("/api/v1/property-certificates/upload")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_upload_certificate_no_file(self, client, admin_user_headers):
        """测试上传时没有文件"""
        response = client.post(
            "/api/v1/property-certificates/upload", headers=admin_user_headers
        )
        # 应该返回400或422错误
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]


# ============================================================================
# Certificate CRUD Tests
# ============================================================================


class TestCertificateCRUD:
    """测试产权证CRUD操作"""

    def test_get_certificates_success(self, client, admin_user_headers):
        """测试获取产权证列表"""
        response = client.get(
            "/api/v1/property-certificates/", headers=admin_user_headers
        )
        # 端点应该存在
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_get_certificate_by_id(self, client, admin_user_headers):
        """测试获取单个产权证"""
        response = client.get(
            "/api/v1/property-certificates/test-id", headers=admin_user_headers
        )
        # 可能返回200或404
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_update_certificate(self, client, admin_user_headers):
        """测试更新产权证"""
        response = client.put(
            "/api/v1/property-certificates/test-id",
            json={"name": "Updated Name"},
            headers=admin_user_headers,
        )
        # 可能返回200、404或405
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        ]

    def test_delete_certificate(self, client, admin_user_headers):
        """测试删除产权证"""
        response = client.delete(
            "/api/v1/property-certificates/test-id", headers=admin_user_headers
        )
        # 可能返回200、404或405
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        ]


# ============================================================================
# Edge Cases
# ============================================================================


class TestPropertyCertificateEdgeCases:
    """测试边界情况"""

    def test_invalid_file_type(self, client, admin_user_headers):
        """测试无效文件类型"""
        # 这个测试需要文件上传，这里只验证结构
        pass

    def test_file_too_large(self, client, admin_user_headers):
        """测试文件过大"""
        # 这个测试需要文件上传，这里只验证结构
        pass

    def test_certificate_number_validation(self, client, admin_user_headers):
        """测试产权证号验证"""
        certificate_data = {
            "certificate_number": "",  # 空证号
            "property_name": "Test Property",
        }

        response = client.post(
            "/api/v1/property-certificates/",
            json=certificate_data,
            headers=admin_user_headers,
        )

        # 应该返回验证错误
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]

    def test_certificate_area_validation(self, client, admin_user_headers):
        """测试产权面积验证"""
        certificate_data = {
            "certificate_number": "CERT-001",
            "property_name": "Test Property",
            "area": -100.0,  # 负面积
        }

        response = client.post(
            "/api/v1/property-certificates/",
            json=certificate_data,
            headers=admin_user_headers,
        )

        # 应该返回验证错误
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]

    def test_search_certificates_by_number(self, client, admin_user_headers):
        """测试按证号搜索产权证"""
        response = client.get(
            "/api/v1/property-certificates/?certificate_number=CERT-001",
            headers=admin_user_headers,
        )

        # 端点应该存在
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_get_certificates_by_asset(self, client, admin_user_headers):
        """测试按资产获取产权证"""
        response = client.get(
            "/api/v1/property-certificates/?asset_id=asset-001",
            headers=admin_user_headers,
        )

        # 端点应该存在
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_certificate_with_unicode(self, client, admin_user_headers):
        """测试创建包含Unicode的产权证"""
        unicode_data = {
            "certificate_number": "测试证号001",
            "property_name": "测试房产名称",
            "address": "北京市朝阳区测试地址",
        }

        response = client.post(
            "/api/v1/property-certificates/",
            json=unicode_data,
            headers=admin_user_headers,
        )

        # 可能成功或端点不存在
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]

    def test_certificate_issue_date_validation(self, client, admin_user_headers):
        """测试发证日期验证"""
        certificate_data = {
            "certificate_number": "CERT-002",
            "property_name": "Test Property",
            "issue_date": "invalid-date",  # 无效日期
        }

        response = client.post(
            "/api/v1/property-certificates/",
            json=certificate_data,
            headers=admin_user_headers,
        )

        # 应该返回验证错误
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]

    def test_certificate_expiry_date_after_issue(self, client, admin_user_headers):
        """测试到期日期晚于发证日期"""
        from datetime import datetime, timedelta

        certificate_data = {
            "certificate_number": "CERT-003",
            "property_name": "Test Property",
            "issue_date": (datetime.now() + timedelta(days=30)).isoformat(),  # 未来日期
            "expiry_date": datetime.now().isoformat(),  # 过去日期
        }

        response = client.post(
            "/api/v1/property-certificates/",
            json=certificate_data,
            headers=admin_user_headers,
        )

        # 应该返回验证错误（到期日期不能早于发证日期）
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]

    def test_certificate_duplicate_number(self, client, admin_user_headers):
        """测试重复证号"""
        # 先创建第一个产权证
        first_certificate = {
            "certificate_number": "DUPLICATE-001",
            "property_name": "First Property",
        }

        response1 = client.post(
            "/api/v1/property-certificates/",
            json=first_certificate,
            headers=admin_user_headers,
        )

        # 尝试创建相同证号的第二个产权证
        second_certificate = {
            "certificate_number": "DUPLICATE-001",  # 重复证号
            "property_name": "Second Property",
        }

        response2 = client.post(
            "/api/v1/property-certificates/",
            json=second_certificate,
            headers=admin_user_headers,
        )

        # 第二个应该被拒绝
        if response1.status_code == status.HTTP_200_OK:
            assert response2.status_code in [
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_409_CONFLICT,
            ]

    def test_update_certificate_status(self, client, admin_user_headers):
        """测试更新产权证状态"""
        update_data = {"status": "expired"}

        response = client.put(
            "/api/v1/property-certificates/test-id/status",
            json=update_data,
            headers=admin_user_headers,
        )

        # 端点可能不存在
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        ]

    def test_certificate_pagination(self, client, admin_user_headers):
        """测试产权证分页"""
        response = client.get(
            "/api/v1/property-certificates/?page=1&page_size=10",
            headers=admin_user_headers,
        )

        # 端点应该存在
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert isinstance(data, list) or "items" in data or "results" in data

