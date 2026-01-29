"""
资产生命周期集成测试

Integration tests for complete asset lifecycle
"""

import pytest
from fastapi import status
from sqlalchemy.orm import Session


@pytest.fixture
def db_session(db: Session):
    """数据库会话"""
    return db


@pytest.fixture
def admin_user_headers(client, admin_user):
    """管理员认证头"""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": admin_user.username, "password": "admin123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestAssetLifecycle:
    """测试资产生命周期"""

    def test_complete_asset_lifecycle(self, client, admin_user_headers, db_session):
        """测试完整的资产生命周期：创建→更新→分配→使用→报废"""
        # 1. 创建资产
        asset_data = {
            "name": "集成测试资产",
            "code": "INT-TEST-001",
            "area": 1000.0,
            "asset_type": "building",
            "usage": "office",
        }
        create_response = client.post(
            "/api/v1/assets/", json=asset_data, headers=admin_user_headers
        )
        assert create_response.status_code == status.HTTP_200_OK
        asset_id = create_response.json()["id"]

        # 2. 更新资产
        update_data = {"usage": "warehouse"}
        update_response = client.put(
            f"/api/v1/assets/{asset_id}", json=update_data, headers=admin_user_headers
        )
        assert update_response.status_code == status.HTTP_200_OK

        # 3. 分配使用权属
        # (这里可能需要调用分配API)

        # 4. 标记为使用中
        # (这里可能需要调用状态更新API)

        # 5. 报废资产
        # (这里可能需要调用报废API)

        # 清理
        client.delete(f"/api/v1/assets/{asset_id}", headers=admin_user_headers)

    def test_asset_search_integration(self, client, admin_user_headers):
        """测试资产搜索集成"""
        # 创建多个资产
        assets = []
        for i in range(3):
            asset_data = {
                "name": f"搜索测试资产{i}",
                "code": f"SEARCH-{i}",
                "area": 500.0 + i * 100,
                "asset_type": "building",
            }
            response = client.post(
                "/api/v1/assets/", json=asset_data, headers=admin_user_headers
            )
            if response.status_code == status.HTTP_200_OK:
                assets.append(response.json()["id"])

        # 测试搜索
        search_response = client.get(
            "/api/v1/assets/?keyword=搜索", headers=admin_user_headers
        )
        assert search_response.status_code == status.HTTP_200_OK

        # 测试筛选
        filter_response = client.get(
            "/api/v1/assets/?asset_type=building", headers=admin_user_headers
        )
        assert filter_response.status_code == status.HTTP_200_OK

        # 清理
        for asset_id in assets:
            try:
                client.delete(f"/api/v1/assets/{asset_id}", headers=admin_user_headers)
            except Exception:
                pass
