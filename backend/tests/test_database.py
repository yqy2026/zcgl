"""
数据库模型和CRUD操作测试
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

from src.database import Base
from src.models.asset import Asset, AssetHistory, AssetDocument
from src.crud.asset import asset_crud


# 创建测试数据库
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db():
    """创建测试数据库会话"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_create_asset(db):
    """测试创建资产"""
    asset_data = {
        "ownership_entity": "国资集团",
        "property_name": "测试物业",
        "address": "测试地址",
        "actual_property_area": 100.0,
        "rentable_area": 80.0,
        "rented_area": 60.0,
        "unrented_area": 20.0,
        "non_commercial_area": 20.0,
        "ownership_status": "已确权",
        "actual_usage": "商业",
        "usage_status": "出租",
        "is_litigated": False,
        "property_nature": "经营类",
        "occupancy_rate": 75.0
    }
    
    asset = Asset(**asset_data)
    db.add(asset)
    db.commit()
    db.refresh(asset)
    
    assert asset.id is not None
    assert asset.property_name == "测试物业"
    assert asset.ownership_entity == "国资集团"
    assert asset.actual_property_area == 100.0


def test_asset_relationships(db):
    """测试资产关联关系"""
    # 创建资产
    asset = Asset(
        ownership_entity="国资集团",
        property_name="测试物业",
        address="测试地址",
        actual_property_area=100.0,
        rentable_area=80.0,
        rented_area=60.0,
        unrented_area=20.0,
        non_commercial_area=20.0,
        ownership_status="已确权",
        actual_usage="商业",
        usage_status="出租",
        is_litigated=False,
        property_nature="经营类",
        occupancy_rate=75.0
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    
    # 创建历史记录
    history = AssetHistory(
        asset_id=asset.id,
        operation_type="create",
        field_name="property_name",
        old_value="",
        new_value="测试物业",
        operator="test_user"
    )
    db.add(history)
    
    # 创建文档记录
    document = AssetDocument(
        asset_id=asset.id,
        document_name="test.pdf",
        document_type="PDF",
        file_path="/test/test.pdf",
        file_size=1024,
        mime_type="application/pdf"
    )
    db.add(document)
    db.commit()
    
    # 验证关联关系
    assert len(asset.history_records) == 1
    assert len(asset.documents) == 1
    assert asset.history_records[0].operation_type == "create"
    assert asset.documents[0].document_name == "test.pdf"


def test_asset_crud_operations(db):
    """测试资产CRUD操作"""
    # 测试数据
    asset_data = {
        "ownership_entity": "国资集团",
        "property_name": "CRUD测试物业",
        "address": "CRUD测试地址",
        "actual_property_area": 200.0,
        "rentable_area": 160.0,
        "rented_area": 120.0,
        "unrented_area": 40.0,
        "non_commercial_area": 40.0,
        "ownership_status": "已确权",
        "actual_usage": "办公",
        "usage_status": "出租",
        "is_litigated": False,
        "property_nature": "经营类",
        "occupancy_rate": 75.0
    }
    
    # 创建资产
    asset = Asset(**asset_data)
    db.add(asset)
    db.commit()
    db.refresh(asset)
    
    # 测试获取
    retrieved_asset = asset_crud.get(db, id=asset.id)
    assert retrieved_asset is not None
    assert retrieved_asset.property_name == "CRUD测试物业"
    
    # 测试按名称获取
    asset_by_name = asset_crud.get_by_name(db, property_name="CRUD测试物业")
    assert asset_by_name is not None
    assert asset_by_name.id == asset.id
    
    # 测试获取多个
    assets = asset_crud.get_multi(db, skip=0, limit=10)
    assert len(assets) >= 1
    
    # 测试搜索
    search_results = asset_crud.get_multi_with_search(db, search="CRUD")
    assert len(search_results) >= 1
    
    # 测试计数
    count = asset_crud.count(db)
    assert count >= 1


def test_asset_search_and_filter(db):
    """测试资产搜索和筛选功能"""
    # 创建测试数据
    assets_data = [
        {
            "ownership_entity": "国资集团",
            "property_name": "商业物业A",
            "address": "广州市天河区",
            "actual_property_area": 100.0,
            "rentable_area": 80.0,
            "rented_area": 60.0,
            "unrented_area": 20.0,
            "non_commercial_area": 20.0,
            "ownership_status": "已确权",
            "actual_usage": "商业",
            "usage_status": "出租",
            "is_litigated": False,
            "property_nature": "经营类",
            "occupancy_rate": 75.0
        },
        {
            "ownership_entity": "市政府",
            "property_name": "办公物业B",
            "address": "广州市越秀区",
            "actual_property_area": 200.0,
            "rentable_area": 160.0,
            "rented_area": 100.0,
            "unrented_area": 60.0,
            "non_commercial_area": 40.0,
            "ownership_status": "未确权",
            "actual_usage": "办公",
            "usage_status": "闲置",
            "is_litigated": True,
            "property_nature": "非经营类",
            "occupancy_rate": 62.5
        }
    ]
    
    for asset_data in assets_data:
        asset = Asset(**asset_data)
        db.add(asset)
    db.commit()
    
    # 测试搜索
    search_results, total = asset_crud.get_multi_with_search(db, search="商业物业A")
    assert len(search_results) == 1
    assert total == 1
    assert search_results[0].property_name == "商业物业A"
    
    # 测试筛选
    filter_results, filter_total = asset_crud.get_multi_with_search(
        db,
        filters={"ownership_status": "已确权"}
    )
    assert len(filter_results) == 1
    assert filter_total == 1
    assert filter_results[0].ownership_status == "已确权"

    # 测试组合筛选
    combined_results, combined_total = asset_crud.get_multi_with_search(
        db,
        search="物业",
        filters={"property_nature": "经营类"}
    )
    assert len(combined_results) == 1
    assert combined_total == 1
    assert combined_results[0].property_nature == "经营类"