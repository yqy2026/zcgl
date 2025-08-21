"""
变更历史跟踪功能测试
"""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.main import app
from src.services.history_tracker import HistoryTracker, HistoryService
from src.models.asset import Asset, AssetHistory
from src.schemas.asset import AssetCreate, AssetUpdate
from src.database import get_db

client = TestClient(app)


class TestHistoryTracker:
    """测试历史跟踪器"""
    
    def test_get_field_changes(self):
        """测试字段变更检测"""
        old_data = {
            "property_name": "旧物业名称",
            "address": "旧地址",
            "actual_property_area": 1000.0,
            "ownership_status": "未确权",
            "created_at": datetime(2024, 1, 1),
            "id": "test-id"  # 应该被忽略
        }
        
        new_data = {
            "property_name": "新物业名称",
            "address": "旧地址",  # 未变更
            "actual_property_area": 1200.0,
            "ownership_status": "已确权",
            "created_at": datetime(2024, 1, 2),  # 应该被忽略
            "id": "test-id"  # 应该被忽略
        }
        
        changes = HistoryTracker.get_field_changes(old_data, new_data)
        
        # 验证变更检测
        assert "property_name" in changes
        assert changes["property_name"]["old"] == "旧物业名称"
        assert changes["property_name"]["new"] == "新物业名称"
        
        assert "actual_property_area" in changes
        assert changes["actual_property_area"]["old"] == 1000.0
        assert changes["actual_property_area"]["new"] == 1200.0
        
        assert "ownership_status" in changes
        assert changes["ownership_status"]["old"] == "未确权"
        assert changes["ownership_status"]["new"] == "已确权"
        
        # 验证未变更的字段不在结果中
        assert "address" not in changes
        
        # 验证忽略的字段不在结果中
        assert "id" not in changes
        assert "created_at" not in changes
    
    def test_get_field_changes_with_none_values(self):
        """测试包含None值的字段变更检测"""
        old_data = {
            "management_entity": None,
            "description": "",
            "land_area": 0.0
        }
        
        new_data = {
            "management_entity": "五羊公司",
            "description": "新描述",
            "land_area": None
        }
        
        changes = HistoryTracker.get_field_changes(old_data, new_data)
        
        # None和空字符串应该被视为相同
        assert "management_entity" in changes
        assert changes["management_entity"]["old"] is None
        assert changes["management_entity"]["new"] == "五羊公司"
        
        assert "description" in changes
        assert changes["description"]["old"] is None
        assert changes["description"]["new"] == "新描述"
        
        assert "land_area" in changes
        assert changes["land_area"]["old"] == 0.0
        assert changes["land_area"]["new"] is None
    
    def test_model_to_dict(self):
        """测试模型转字典"""
        # 创建模拟资产对象
        class MockAsset:
            def __init__(self):
                self.id = "test-id"
                self.property_name = "测试物业"
                self.address = "测试地址"
                self.actual_property_area = 1000.0
                self.created_at = datetime(2024, 1, 1)
            
            @property
            def __table__(self):
                class MockTable:
                    @property
                    def columns(self):
                        class MockColumn:
                            def __init__(self, name):
                                self.name = name
                        return [
                            MockColumn("id"),
                            MockColumn("property_name"),
                            MockColumn("address"),
                            MockColumn("actual_property_area"),
                            MockColumn("created_at")
                        ]
                return MockTable()
        
        mock_asset = MockAsset()
        data = HistoryTracker.model_to_dict(mock_asset)
        
        assert data["id"] == "test-id"
        assert data["property_name"] == "测试物业"
        assert data["address"] == "测试地址"
        assert data["actual_property_area"] == 1000.0
        assert data["created_at"] == "2024-01-01T00:00:00"  # 转换为ISO格式
    
    def test_model_to_dict_with_none(self):
        """测试None模型转字典"""
        data = HistoryTracker.model_to_dict(None)
        assert data == {}


class TestHistoryService:
    """测试历史服务"""
    
    @pytest.fixture
    def history_service(self):
        """创建历史服务实例"""
        return HistoryService()
    
    @pytest.fixture
    def sample_asset(self, db_session):
        """创建示例资产"""
        asset_data = AssetCreate(
            ownership_entity="国资集团",
            property_name="测试物业",
            address="测试地址",
            actual_property_area=1000.0,
            rentable_area=800.0,
            rented_area=600.0,
            unrented_area=200.0,
            non_commercial_area=200.0,
            ownership_status="已确权",
            actual_usage="商业",
            usage_status="出租",
            is_litigated="否",
            property_nature="经营类",
            occupancy_rate="75%"
        )
        
        from src.crud.asset import CRUDAsset
        asset_crud = CRUDAsset(Asset)
        asset = asset_crud.create_with_history(
            db_session, 
            obj_in=asset_data,
            changed_by="test_user",
            reason="测试创建"
        )
        
        return asset
    
    def test_get_asset_history(self, history_service, sample_asset, db_session):
        """测试获取资产历史"""
        result = history_service.get_asset_history(
            db=db_session,
            asset_id=sample_asset.id,
            skip=0,
            limit=10
        )
        
        assert result["total"] >= 1  # 至少有创建记录
        assert len(result["data"]) >= 1
        assert result["page"] == 1
        assert result["limit"] == 10
        
        # 验证历史记录内容
        history = result["data"][0]
        assert history.asset_id == sample_asset.id
        assert history.change_type == "create"
        assert history.changed_by == "test_user"
        assert history.reason == "测试创建"
    
    def test_get_asset_history_with_filter(self, history_service, sample_asset, db_session):
        """测试按类型筛选历史记录"""
        # 更新资产以创建更多历史记录
        from src.crud.asset import CRUDAsset
        asset_crud = CRUDAsset(Asset)
        
        update_data = AssetUpdate(property_name="更新后的物业名称")
        asset_crud.update_with_history(
            db_session,
            db_obj=sample_asset,
            obj_in=update_data,
            changed_by="test_user",
            reason="测试更新"
        )
        
        # 获取创建类型的历史记录
        result = history_service.get_asset_history(
            db=db_session,
            asset_id=sample_asset.id,
            change_type="create"
        )
        
        assert result["total"] == 1
        assert result["data"][0].change_type == "create"
        
        # 获取更新类型的历史记录
        result = history_service.get_asset_history(
            db=db_session,
            asset_id=sample_asset.id,
            change_type="update"
        )
        
        assert result["total"] == 1
        assert result["data"][0].change_type == "update"
    
    def test_get_field_history(self, history_service, sample_asset, db_session):
        """测试获取字段历史"""
        # 多次更新同一字段
        from src.crud.asset import CRUDAsset
        asset_crud = CRUDAsset(Asset)
        
        # 第一次更新
        update_data1 = AssetUpdate(property_name="第一次更新")
        asset_crud.update_with_history(
            db_session,
            db_obj=sample_asset,
            obj_in=update_data1,
            changed_by="user1"
        )
        
        # 第二次更新
        update_data2 = AssetUpdate(property_name="第二次更新")
        updated_asset = asset_crud.update_with_history(
            db_session,
            db_obj=sample_asset,
            obj_in=update_data2,
            changed_by="user2"
        )
        
        # 获取字段历史
        field_history = history_service.get_field_history(
            db=db_session,
            asset_id=sample_asset.id,
            field_name="property_name",
            limit=5
        )
        
        assert len(field_history) == 2  # 两次更新
        
        # 验证历史顺序（最新的在前）
        assert field_history[0]["new_value"] == "第二次更新"
        assert field_history[0]["changed_by"] == "user2"
        
        assert field_history[1]["new_value"] == "第一次更新"
        assert field_history[1]["changed_by"] == "user1"
    
    def test_get_change_statistics(self, history_service, sample_asset, db_session):
        """测试获取变更统计"""
        # 创建一些变更记录
        from src.crud.asset import CRUDAsset
        asset_crud = CRUDAsset(Asset)
        
        # 更新资产
        update_data = AssetUpdate(
            property_name="更新物业",
            actual_property_area=1200.0
        )
        asset_crud.update_with_history(
            db_session,
            db_obj=sample_asset,
            obj_in=update_data,
            changed_by="test_user"
        )
        
        # 获取统计信息
        stats = history_service.get_change_statistics(
            db=db_session,
            asset_id=sample_asset.id,
            days=30
        )
        
        assert stats["total_changes"] >= 2  # 至少有创建和更新
        assert "create" in stats["change_types"]
        assert "update" in stats["change_types"]
        assert "test_user" in stats["changed_by"]
        assert "property_name" in stats["most_changed_fields"]
        assert stats["period"]["days"] == 30


class TestHistoryAPI:
    """测试历史API"""
    
    @pytest.fixture
    def sample_asset_with_history(self, db_session):
        """创建带历史记录的示例资产"""
        # 创建资产
        asset_data = {
            "ownership_entity": "国资集团",
            "property_name": "API测试物业",
            "address": "API测试地址",
            "actual_property_area": 1000.0,
            "rentable_area": 800.0,
            "rented_area": 600.0,
            "unrented_area": 200.0,
            "non_commercial_area": 200.0,
            "ownership_status": "已确权",
            "actual_usage": "商业",
            "usage_status": "出租",
            "is_litigated": "否",
            "property_nature": "经营类",
            "occupancy_rate": "75%"
        }
        
        response = client.post("/api/v1/assets/", json=asset_data)
        assert response.status_code == 201
        asset = response.json()
        
        # 更新资产以创建历史记录
        update_data = {"property_name": "更新后的API测试物业"}
        response = client.put(f"/api/v1/assets/{asset['id']}", json=update_data)
        assert response.status_code == 200
        
        return asset
    
    def test_get_asset_history_api(self, sample_asset_with_history):
        """测试获取资产历史API"""
        asset_id = sample_asset_with_history["id"]
        
        response = client.get(f"/api/v1/assets/{asset_id}/history")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "data" in data
        assert "total" in data
        assert "page" in data
        assert data["total"] >= 1
        assert len(data["data"]) >= 1
        
        # 验证历史记录结构
        history = data["data"][0]
        assert "id" in history
        assert "asset_id" in history
        assert "change_type" in history
        assert "changed_fields" in history
        assert "changed_by" in history
        assert "changed_at" in history
    
    def test_get_asset_history_with_pagination(self, sample_asset_with_history):
        """测试分页获取历史记录"""
        asset_id = sample_asset_with_history["id"]
        
        response = client.get(f"/api/v1/assets/{asset_id}/history?page=1&limit=1")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["page"] == 1
        assert data["limit"] == 1
        assert len(data["data"]) <= 1
    
    def test_get_asset_history_with_filter(self, sample_asset_with_history):
        """测试按类型筛选历史记录"""
        asset_id = sample_asset_with_history["id"]
        
        response = client.get(f"/api/v1/assets/{asset_id}/history?change_type=update")
        
        assert response.status_code == 200
        data = response.json()
        
        # 应该至少有一个更新记录
        assert data["total"] >= 1
        for history in data["data"]:
            assert history["change_type"] == "update"
    
    def test_get_nonexistent_asset_history(self):
        """测试获取不存在资产的历史"""
        response = client.get("/api/v1/assets/nonexistent-id/history")
        
        assert response.status_code == 404
        data = response.json()
        assert "资产不存在" in data["detail"]
    
    def test_get_recent_changes_api(self):
        """测试获取最近变更API"""
        response = client.get("/api/v1/history/recent?limit=10")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "data" in data
        assert "total" in data
        assert "message" in data
        assert isinstance(data["data"], list)
    
    def test_get_change_statistics_api(self):
        """测试获取变更统计API"""
        response = client.get("/api/v1/history/statistics?days=30")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "statistics" in data
        assert "message" in data
        
        stats = data["statistics"]
        assert "total_changes" in stats
        assert "change_types" in stats
        assert "changed_by" in stats
        assert "period" in stats
    
    def test_get_field_history_api(self, sample_asset_with_history):
        """测试获取字段历史API"""
        asset_id = sample_asset_with_history["id"]
        
        response = client.get(f"/api/v1/assets/{asset_id}/field-history/property_name")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["asset_id"] == asset_id
        assert data["field_name"] == "property_name"
        assert "history" in data
        assert "total_changes" in data
        assert isinstance(data["history"], list)


class TestHistoryIntegration:
    """测试历史跟踪集成"""
    
    def test_create_asset_with_history(self):
        """测试创建资产时自动记录历史"""
        asset_data = {
            "ownership_entity": "集成测试集团",
            "property_name": "集成测试物业",
            "address": "集成测试地址",
            "actual_property_area": 1000.0,
            "rentable_area": 800.0,
            "rented_area": 600.0,
            "unrented_area": 200.0,
            "non_commercial_area": 200.0,
            "ownership_status": "已确权",
            "actual_usage": "商业",
            "usage_status": "出租",
            "is_litigated": "否",
            "property_nature": "经营类",
            "occupancy_rate": "75%"
        }
        
        # 创建资产
        response = client.post("/api/v1/assets/", json=asset_data)
        assert response.status_code == 201
        asset = response.json()
        
        # 检查历史记录
        response = client.get(f"/api/v1/assets/{asset['id']}/history")
        assert response.status_code == 200
        
        history_data = response.json()
        assert history_data["total"] == 1
        
        history = history_data["data"][0]
        assert history["change_type"] == "create"
        assert history["asset_id"] == asset["id"]
        assert len(history["changed_fields"]) > 0
    
    def test_update_asset_with_history(self):
        """测试更新资产时自动记录历史"""
        # 先创建资产
        asset_data = {
            "ownership_entity": "更新测试集团",
            "property_name": "更新测试物业",
            "address": "更新测试地址",
            "actual_property_area": 1000.0,
            "rentable_area": 800.0,
            "rented_area": 600.0,
            "unrented_area": 200.0,
            "non_commercial_area": 200.0,
            "ownership_status": "已确权",
            "actual_usage": "商业",
            "usage_status": "出租",
            "is_litigated": "否",
            "property_nature": "经营类",
            "occupancy_rate": "75%"
        }
        
        response = client.post("/api/v1/assets/", json=asset_data)
        asset = response.json()
        
        # 更新资产
        update_data = {
            "property_name": "更新后的物业名称",
            "actual_property_area": 1200.0
        }
        
        response = client.put(f"/api/v1/assets/{asset['id']}", json=update_data)
        assert response.status_code == 200
        
        # 检查历史记录
        response = client.get(f"/api/v1/assets/{asset['id']}/history")
        assert response.status_code == 200
        
        history_data = response.json()
        assert history_data["total"] == 2  # 创建 + 更新
        
        # 最新的记录应该是更新记录
        update_history = history_data["data"][0]
        assert update_history["change_type"] == "update"
        assert "property_name" in update_history["changed_fields"]
        assert "actual_property_area" in update_history["changed_fields"]
        
        # 验证变更值
        assert update_history["old_values"]["property_name"] == "更新测试物业"
        assert update_history["new_values"]["property_name"] == "更新后的物业名称"
        assert update_history["old_values"]["actual_property_area"] == 1000.0
        assert update_history["new_values"]["actual_property_area"] == 1200.0