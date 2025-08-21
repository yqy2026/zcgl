"""
高级搜索和筛选功能测试
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta

from src.main import app
from src.database import Base, get_db
from src.models.asset import Asset


# 创建测试数据库
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_advanced_search.db"
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


@pytest.fixture
def sample_assets():
    """创建测试数据"""
    assets_data = [
        {
            "ownership_entity": "国资集团",
            "management_entity": "五羊公司",
            "property_name": "广州大道北550号",
            "address": "天河区广州大道北550号大院",
            "actual_property_area": 1106.14,
            "rentable_area": 1106.14,
            "rented_area": 1106.14,
            "unrented_area": 0,
            "non_commercial_area": 0,
            "ownership_status": "部分确权",
            "certificated_usage": "车间",
            "actual_usage": "仓储",
            "business_category": "园区",
            "usage_status": "出租",
            "is_litigated": "否",
            "property_nature": "经营类",
            "occupancy_rate": "100%",
            "tenant_name": "中山市秋东季服饰有限公司",
            "wuyang_project_name": "广州大道北",
            "description": "未签新承租合同"
        },
        {
            "ownership_entity": "国资集团",
            "management_entity": "五羊公司",
            "property_name": "北京路245、249号",
            "address": "北京路245号全幢、249号后座",
            "actual_property_area": 3648.54,
            "rentable_area": 3648.54,
            "rented_area": 3648.54,
            "unrented_area": 0,
            "non_commercial_area": 0,
            "ownership_status": "已确权",
            "certificated_usage": "非居住用房",
            "actual_usage": "商业",
            "business_category": "商业",
            "usage_status": "出租",
            "is_litigated": "否",
            "property_nature": "经营类",
            "occupancy_rate": "100%",
            "tenant_name": "名创优品（广州）有限责任公司",
            "wuyang_project_name": "北京路",
            "description": ""
        },
        {
            "ownership_entity": "国资集团",
            "management_entity": "五羊公司",
            "property_name": "富基南一街12号",
            "address": "海珠区富基南一街12号101铺",
            "actual_property_area": 279.0,
            "rentable_area": 279.0,
            "rented_area": 279.0,
            "unrented_area": 0,
            "non_commercial_area": 0,
            "ownership_status": "未确权",
            "certificated_usage": "",
            "actual_usage": "商业",
            "business_category": "商业",
            "usage_status": "出租",
            "is_litigated": "否",
            "property_nature": "经营类",
            "occupancy_rate": "100%",
            "tenant_name": "广州宏世投资咨询有限公司",
            "wuyang_project_name": "富基广场",
            "description": ""
        },
        {
            "ownership_entity": "国资集团",
            "management_entity": "五羊公司",
            "property_name": "府前大厦",
            "address": "越秀区府前路2号府前大厦7层",
            "actual_property_area": 1112.43,
            "rentable_area": 0,
            "rented_area": 0,
            "unrented_area": 0,
            "non_commercial_area": 1112.43,
            "ownership_status": "已确权",
            "certificated_usage": "办公",
            "actual_usage": "办公",
            "business_category": "办公",
            "usage_status": "自用",
            "is_litigated": "否",
            "property_nature": "经营类",
            "occupancy_rate": "0%",
            "tenant_name": "广州人才集团有限公司",
            "wuyang_project_name": "府前大厦",
            "description": "未签新承租合同"
        },
        {
            "ownership_entity": "市政府",
            "management_entity": "城投公司",
            "property_name": "市政大楼",
            "address": "越秀区中山路100号",
            "actual_property_area": 5000.0,
            "rentable_area": 3000.0,
            "rented_area": 1500.0,
            "unrented_area": 1500.0,
            "non_commercial_area": 2000.0,
            "ownership_status": "已确权",
            "certificated_usage": "办公",
            "actual_usage": "办公",
            "business_category": "办公",
            "usage_status": "闲置",
            "is_litigated": "是",
            "property_nature": "非经营类",
            "occupancy_rate": "50%",
            "tenant_name": "",
            "wuyang_project_name": "",
            "description": "涉及产权纠纷"
        }
    ]
    
    # 创建资产
    created_assets = []
    for asset_data in assets_data:
        response = client.post("/api/v1/assets/", json=asset_data)
        assert response.status_code == 201
        created_assets.append(response.json())
    
    return created_assets


def test_basic_search(sample_assets):
    """测试基础搜索功能"""
    
    # 搜索"广州"
    response = client.get("/api/v1/assets/?search=广州")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    
    # 验证搜索结果包含"广州"相关的资产
    found_guangzhou = any("广州" in asset["property_name"] or "广州" in asset["address"] 
                         for asset in data["data"])
    assert found_guangzhou
    
    # 搜索"北京路"
    response = client.get("/api/v1/assets/?search=北京路")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert any("北京路" in asset["property_name"] or "北京路" in asset["address"] 
              for asset in data["data"])


def test_ownership_status_filter(sample_assets):
    """测试确权状态筛选"""
    
    # 筛选已确权资产
    response = client.get("/api/v1/assets/?ownership_status=已确权")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    
    # 验证所有结果都是已确权
    for asset in data["data"]:
        assert asset["ownership_status"] == "已确权"
    
    # 筛选未确权资产
    response = client.get("/api/v1/assets/?ownership_status=未确权")
    assert response.status_code == 200
    data = response.json()
    
    # 验证所有结果都是未确权
    for asset in data["data"]:
        assert asset["ownership_status"] == "未确权"
    
    # 筛选部分确权资产
    response = client.get("/api/v1/assets/?ownership_status=部分确权")
    assert response.status_code == 200
    data = response.json()
    
    # 验证所有结果都是部分确权
    for asset in data["data"]:
        assert asset["ownership_status"] == "部分确权"


def test_property_nature_filter(sample_assets):
    """测试物业性质筛选"""
    
    # 筛选经营类物业
    response = client.get("/api/v1/assets/?property_nature=经营类")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    
    # 验证所有结果都是经营类
    for asset in data["data"]:
        assert asset["property_nature"] == "经营类"
    
    # 筛选非经营类物业
    response = client.get("/api/v1/assets/?property_nature=非经营类")
    assert response.status_code == 200
    data = response.json()
    
    # 验证所有结果都是非经营类
    for asset in data["data"]:
        assert asset["property_nature"] == "非经营类"


def test_usage_status_filter(sample_assets):
    """测试使用状态筛选"""
    
    # 筛选出租状态
    response = client.get("/api/v1/assets/?usage_status=出租")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    
    # 验证所有结果都是出租状态
    for asset in data["data"]:
        assert asset["usage_status"] == "出租"
    
    # 筛选自用状态
    response = client.get("/api/v1/assets/?usage_status=自用")
    assert response.status_code == 200
    data = response.json()
    
    # 验证所有结果都是自用状态
    for asset in data["data"]:
        assert asset["usage_status"] == "自用"
    
    # 筛选闲置状态
    response = client.get("/api/v1/assets/?usage_status=闲置")
    assert response.status_code == 200
    data = response.json()
    
    # 验证所有结果都是闲置状态
    for asset in data["data"]:
        assert asset["usage_status"] == "闲置"


def test_ownership_entity_filter(sample_assets):
    """测试权属方筛选"""
    
    # 筛选国资集团的资产
    response = client.get("/api/v1/assets/?ownership_entity=国资集团")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    
    # 验证所有结果都属于国资集团
    for asset in data["data"]:
        assert asset["ownership_entity"] == "国资集团"
    
    # 筛选市政府的资产
    response = client.get("/api/v1/assets/?ownership_entity=市政府")
    assert response.status_code == 200
    data = response.json()
    
    # 验证所有结果都属于市政府
    for asset in data["data"]:
        assert asset["ownership_entity"] == "市政府"


def test_area_range_filter(sample_assets):
    """测试面积范围筛选"""
    
    # 筛选面积大于1000平方米的资产
    response = client.get("/api/v1/assets/?min_area=1000")
    assert response.status_code == 200
    data = response.json()
    
    # 验证所有结果面积都大于等于1000
    for asset in data["data"]:
        assert asset["actual_property_area"] >= 1000
    
    # 筛选面积小于2000平方米的资产
    response = client.get("/api/v1/assets/?max_area=2000")
    assert response.status_code == 200
    data = response.json()
    
    # 验证所有结果面积都小于等于2000
    for asset in data["data"]:
        assert asset["actual_property_area"] <= 2000
    
    # 筛选面积在500-2000平方米之间的资产
    response = client.get("/api/v1/assets/?min_area=500&max_area=2000")
    assert response.status_code == 200
    data = response.json()
    
    # 验证所有结果面积都在范围内
    for asset in data["data"]:
        assert 500 <= asset["actual_property_area"] <= 2000


def test_litigation_filter(sample_assets):
    """测试涉诉状态筛选"""
    
    # 筛选未涉诉资产
    response = client.get("/api/v1/assets/?is_litigated=否")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    
    # 验证所有结果都未涉诉
    for asset in data["data"]:
        assert asset["is_litigated"] == "否"
    
    # 筛选涉诉资产
    response = client.get("/api/v1/assets/?is_litigated=是")
    assert response.status_code == 200
    data = response.json()
    
    # 验证所有结果都涉诉
    for asset in data["data"]:
        assert asset["is_litigated"] == "是"


def test_combined_filters(sample_assets):
    """测试组合筛选"""
    
    # 组合筛选：国资集团 + 已确权 + 经营类 + 出租
    response = client.get(
        "/api/v1/assets/?ownership_entity=国资集团&ownership_status=已确权&property_nature=经营类&usage_status=出租"
    )
    assert response.status_code == 200
    data = response.json()
    
    # 验证所有结果都符合组合条件
    for asset in data["data"]:
        assert asset["ownership_entity"] == "国资集团"
        assert asset["ownership_status"] == "已确权"
        assert asset["property_nature"] == "经营类"
        assert asset["usage_status"] == "出租"
    
    # 组合筛选：搜索 + 筛选
    response = client.get("/api/v1/assets/?search=广州&ownership_status=部分确权")
    assert response.status_code == 200
    data = response.json()
    
    # 验证结果既包含"广州"又是部分确权
    for asset in data["data"]:
        assert asset["ownership_status"] == "部分确权"
        assert ("广州" in asset["property_name"] or "广州" in asset["address"] or 
                "广州" in asset.get("wuyang_project_name", ""))


def test_sorting_functionality(sample_assets):
    """测试排序功能"""
    
    # 按面积升序排序
    response = client.get("/api/v1/assets/?sort_field=actual_property_area&sort_order=asc")
    assert response.status_code == 200
    data = response.json()
    
    # 验证排序结果
    if len(data["data"]) > 1:
        areas = [asset["actual_property_area"] for asset in data["data"]]
        assert areas == sorted(areas)
    
    # 按面积降序排序
    response = client.get("/api/v1/assets/?sort_field=actual_property_area&sort_order=desc")
    assert response.status_code == 200
    data = response.json()
    
    # 验证排序结果
    if len(data["data"]) > 1:
        areas = [asset["actual_property_area"] for asset in data["data"]]
        assert areas == sorted(areas, reverse=True)
    
    # 按物业名称升序排序
    response = client.get("/api/v1/assets/?sort_field=property_name&sort_order=asc")
    assert response.status_code == 200
    data = response.json()
    
    # 验证排序结果
    if len(data["data"]) > 1:
        names = [asset["property_name"] for asset in data["data"]]
        assert names == sorted(names)


def test_pagination_with_filters(sample_assets):
    """测试分页与筛选结合"""
    
    # 第一页，每页2条
    response = client.get("/api/v1/assets/?page=1&limit=2&ownership_entity=国资集团")
    assert response.status_code == 200
    data = response.json()
    
    assert len(data["data"]) <= 2
    assert data["page"] == 1
    assert data["limit"] == 2
    
    # 验证所有结果都属于国资集团
    for asset in data["data"]:
        assert asset["ownership_entity"] == "国资集团"
    
    # 如果有下一页，测试第二页
    if data["has_next"]:
        response = client.get("/api/v1/assets/?page=2&limit=2&ownership_entity=国资集团")
        assert response.status_code == 200
        data2 = response.json()
        
        assert data2["page"] == 2
        assert data2["has_prev"] is True
        
        # 验证第二页结果也都属于国资集团
        for asset in data2["data"]:
            assert asset["ownership_entity"] == "国资集团"


def test_search_in_multiple_fields(sample_assets):
    """测试多字段搜索"""
    
    # 搜索租户名称
    response = client.get("/api/v1/assets/?search=名创优品")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    
    # 搜索项目名称
    response = client.get("/api/v1/assets/?search=富基广场")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    
    # 搜索描述信息
    response = client.get("/api/v1/assets/?search=未签新承租合同")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1


def test_empty_search_results(sample_assets):
    """测试空搜索结果"""
    
    # 搜索不存在的内容
    response = client.get("/api/v1/assets/?search=不存在的物业")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["data"] == []
    
    # 使用不存在的筛选条件
    response = client.get("/api/v1/assets/?ownership_entity=不存在的权属方")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["data"] == []


def test_case_insensitive_search(sample_assets):
    """测试大小写不敏感搜索"""
    
    # 使用小写搜索
    response1 = client.get("/api/v1/assets/?search=guangzhou")
    assert response1.status_code == 200
    
    # 使用大写搜索
    response2 = client.get("/api/v1/assets/?search=GUANGZHOU")
    assert response2.status_code == 200
    
    # 使用混合大小写搜索
    response3 = client.get("/api/v1/assets/?search=GuangZhou")
    assert response3.status_code == 200
    
    # 注意：由于我们的测试数据是中文，这个测试主要验证搜索功能不会因大小写而报错


def test_invalid_sort_field(sample_assets):
    """测试无效的排序字段"""
    
    # 使用不存在的排序字段，应该使用默认排序
    response = client.get("/api/v1/assets/?sort_field=invalid_field")
    assert response.status_code == 200
    data = response.json()
    # 应该返回结果，使用默认排序
    assert isinstance(data["data"], list)


def test_business_category_filter(sample_assets):
    """测试业态类别筛选"""
    
    # 筛选商业类别
    response = client.get("/api/v1/assets/?business_category=商业")
    assert response.status_code == 200
    data = response.json()
    
    # 验证所有结果都是商业类别
    for asset in data["data"]:
        assert asset["business_category"] == "商业"
    
    # 筛选办公类别
    response = client.get("/api/v1/assets/?business_category=办公")
    assert response.status_code == 200
    data = response.json()
    
    # 验证所有结果都是办公类别
    for asset in data["data"]:
        assert asset["business_category"] == "办公"


def test_management_entity_filter(sample_assets):
    """测试经营管理方筛选"""
    
    # 筛选五羊公司管理的资产
    response = client.get("/api/v1/assets/?management_entity=五羊公司")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    
    # 验证所有结果都由五羊公司管理
    for asset in data["data"]:
        assert asset["management_entity"] == "五羊公司"
    
    # 筛选城投公司管理的资产
    response = client.get("/api/v1/assets/?management_entity=城投公司")
    assert response.status_code == 200
    data = response.json()
    
    # 验证所有结果都由城投公司管理
    for asset in data["data"]:
        assert asset["management_entity"] == "城投公司"