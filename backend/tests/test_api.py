"""
FastAPI API端点测试
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

from src.main import app
from src.database import Base, get_db
from src.models.asset import Asset


# 创建测试数据库
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_api.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """覆盖数据库依赖"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


# 覆盖数据库依赖
app.dependency_overrides[get_db] = override_get_db

# 创建测试客户端
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    """设置测试数据库"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def test_root_endpoint():
    """测试根路径端点"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data
    assert "timestamp" in data
    assert data["version"] == "0.1.0"


def test_health_check():
    """测试健康检查端点"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "land-property-management"
    assert data["version"] == "0.1.0"


def test_app_info():
    """测试应用信息端点"""
    response = client.get("/info")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "土地物业资产管理系统"
    assert data["version"] == "0.1.0"
    assert data["docs_url"] == "/docs"


def test_get_assets_empty():
    """测试获取空资产列表"""
    response = client.get("/api/v1/assets/")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["data"] == []
    assert data["page"] == 1
    assert data["limit"] == 20
    assert data["has_next"] is False
    assert data["has_prev"] is False


def test_create_asset():
    """测试创建资产"""
    asset_data = {
        "ownership_entity": "国资集团",
        "management_entity": "五羊公司",
        "property_name": "测试物业API",
        "address": "广州市天河区测试路123号",
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
    data = response.json()
    assert data["property_name"] == "测试物业API"
    assert data["ownership_entity"] == "国资集团"
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data
    
    return data["id"]


def test_get_asset_by_id():
    """测试根据ID获取资产"""
    # 先创建一个资产
    asset_id = test_create_asset()
    
    # 获取资产
    response = client.get(f"/api/v1/assets/{asset_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == asset_id
    assert data["property_name"] == "测试物业API"


def test_get_nonexistent_asset():
    """测试获取不存在的资产"""
    response = client.get("/api/v1/assets/nonexistent-id")
    assert response.status_code == 404
    data = response.json()
    assert data["error"] == "Asset Not Found"


def test_update_asset():
    """测试更新资产"""
    # 先创建一个资产
    asset_id = test_create_asset()
    
    # 更新资产
    update_data = {
        "property_name": "更新后的物业名称",
        "actual_property_area": 1200.0,
        "occupancy_rate": "80%"
    }
    
    response = client.put(f"/api/v1/assets/{asset_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["property_name"] == "更新后的物业名称"
    assert data["actual_property_area"] == 1200.0
    assert data["occupancy_rate"] == "80%"


def test_delete_asset():
    """测试删除资产"""
    # 先创建一个资产
    asset_id = test_create_asset()
    
    # 删除资产
    response = client.delete(f"/api/v1/assets/{asset_id}")
    assert response.status_code == 204
    
    # 验证资产已被删除
    response = client.get(f"/api/v1/assets/{asset_id}")
    assert response.status_code == 404


def test_create_duplicate_asset():
    """测试创建重复资产"""
    asset_data = {
        "ownership_entity": "国资集团",
        "property_name": "重复物业名称",
        "address": "测试地址",
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
    
    # 创建第一个资产
    response = client.post("/api/v1/assets/", json=asset_data)
    assert response.status_code == 201
    
    # 尝试创建同名资产
    response = client.post("/api/v1/assets/", json=asset_data)
    assert response.status_code == 409
    data = response.json()
    assert data["error"] == "Duplicate Asset"


def test_create_asset_validation_error():
    """测试创建资产时的验证错误"""
    # 缺少必填字段
    invalid_data = {
        "ownership_entity": "国资集团",
        # 缺少 property_name
        "address": "测试地址",
    }
    
    response = client.post("/api/v1/assets/", json=invalid_data)
    assert response.status_code == 422
    data = response.json()
    assert data["error"] == "Request Validation Error"


def test_get_assets_with_pagination():
    """测试分页获取资产"""
    # 创建多个资产
    for i in range(5):
        asset_data = {
            "ownership_entity": "国资集团",
            "property_name": f"测试物业{i}",
            "address": f"测试地址{i}",
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
        client.post("/api/v1/assets/", json=asset_data)
    
    # 测试分页
    response = client.get("/api/v1/assets/?page=1&limit=3")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["data"]) == 3
    assert data["page"] == 1
    assert data["limit"] == 3
    assert data["has_next"] is True
    assert data["has_prev"] is False


def test_search_assets():
    """测试搜索资产"""
    # 创建测试资产
    asset_data = {
        "ownership_entity": "国资集团",
        "property_name": "特殊搜索物业",
        "address": "广州市天河区",
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
    client.post("/api/v1/assets/", json=asset_data)
    
    # 搜索测试
    response = client.get("/api/v1/assets/?search=特殊搜索")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["data"][0]["property_name"] == "特殊搜索物业"


def test_filter_assets():
    """测试筛选资产"""
    # 创建不同状态的资产
    asset_data_1 = {
        "ownership_entity": "国资集团",
        "property_name": "已确权物业",
        "address": "测试地址1",
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
    
    asset_data_2 = {
        "ownership_entity": "市政府",
        "property_name": "未确权物业",
        "address": "测试地址2",
        "actual_property_area": 1000.0,
        "rentable_area": 800.0,
        "rented_area": 600.0,
        "unrented_area": 200.0,
        "non_commercial_area": 200.0,
        "ownership_status": "未确权",
        "actual_usage": "办公",
        "usage_status": "闲置",
        "is_litigated": "否",
        "property_nature": "非经营类",
        "occupancy_rate": "0%"
    }
    
    client.post("/api/v1/assets/", json=asset_data_1)
    client.post("/api/v1/assets/", json=asset_data_2)
    
    # 按确权状态筛选
    response = client.get("/api/v1/assets/?ownership_status=已确权")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["data"][0]["ownership_status"] == "已确权"


def test_get_asset_stats():
    """测试获取资产统计"""
    # 创建测试数据
    asset_data = {
        "ownership_entity": "国资集团",
        "property_name": "统计测试物业",
        "address": "测试地址",
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
    client.post("/api/v1/assets/", json=asset_data)
    
    # 获取统计信息
    response = client.get("/api/v1/assets/stats/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_assets" in data
    assert "ownership_status" in data
    assert "property_nature" in data
    assert "usage_status" in data
    assert data["total_assets"] >= 1


def test_openapi_docs():
    """测试OpenAPI文档端点"""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert data["info"]["title"] == "土地物业资产管理系统"
    assert data["info"]["version"] == "0.1.0"


def test_docs_endpoint():
    """测试Swagger文档端点"""
    response = client.get("/docs")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]