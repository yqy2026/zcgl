"""
Pydantic数据验证模型测试
"""

import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError

from src.schemas.asset import (
    AssetCreate,
    AssetUpdate,
    AssetResponse,
    AssetSearchParams,
    AssetHistoryResponse,
    AssetDocumentResponse,
    AssetListResponse,
    OwnershipStatus,
    UsageStatus,
    PropertyNature,
)


def test_asset_create_valid():
    """测试创建有效的资产数据"""
    asset_data = {
        "ownership_entity": "国资集团",
        "management_entity": "五羊公司",
        "property_name": "测试物业",
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
    
    asset = AssetCreate(**asset_data)
    
    assert asset.ownership_entity == "国资集团"
    assert asset.property_name == "测试物业"
    assert asset.actual_property_area == 1000.0
    assert asset.ownership_status == OwnershipStatus.CONFIRMED
    assert asset.usage_status == UsageStatus.RENTED
    assert asset.property_nature == PropertyNature.COMMERCIAL


def test_asset_create_validation_errors():
    """测试资产创建时的验证错误"""
    
    # 测试必填字段缺失
    with pytest.raises(ValidationError) as exc_info:
        AssetCreate()
    
    errors = exc_info.value.errors()
    required_fields = [error['loc'][0] for error in errors if error['type'] == 'missing']
    assert 'ownership_entity' in required_fields
    assert 'property_name' in required_fields
    assert 'address' in required_fields
    
    # 测试面积验证
    with pytest.raises(ValidationError) as exc_info:
        AssetCreate(
            ownership_entity="测试",
            property_name="测试物业",
            address="测试地址",
            actual_property_area=-100.0,  # 负数面积
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
    
    # 测试已出租面积超过可出租面积
    with pytest.raises(ValidationError) as exc_info:
        AssetCreate(
            ownership_entity="测试",
            property_name="测试物业",
            address="测试地址",
            actual_property_area=1000.0,
            rentable_area=800.0,
            rented_area=900.0,  # 超过可出租面积
            unrented_area=200.0,
            non_commercial_area=200.0,
            ownership_status="已确权",
            actual_usage="商业",
            usage_status="出租",
            is_litigated="否",
            property_nature="经营类",
            occupancy_rate="75%"
        )
    
    assert "已出租面积不能超过可出租面积" in str(exc_info.value)


def test_asset_create_enum_validation():
    """测试枚举字段验证"""
    
    # 测试无效的确权状态
    with pytest.raises(ValidationError):
        AssetCreate(
            ownership_entity="测试",
            property_name="测试物业",
            address="测试地址",
            actual_property_area=1000.0,
            rentable_area=800.0,
            rented_area=600.0,
            unrented_area=200.0,
            non_commercial_area=200.0,
            ownership_status="无效状态",  # 无效枚举值
            actual_usage="商业",
            usage_status="出租",
            is_litigated="否",
            property_nature="经营类",
            occupancy_rate="75%"
        )
    
    # 测试无效的涉诉状态
    with pytest.raises(ValidationError):
        AssetCreate(
            ownership_entity="测试",
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
            is_litigated="可能",  # 无效值，只能是"是"或"否"
            property_nature="经营类",
            occupancy_rate="75%"
        )


def test_asset_create_date_validation():
    """测试日期字段验证"""
    
    start_date = datetime.now()
    end_date = start_date - timedelta(days=30)  # 结束日期早于开始日期
    
    # 测试合同日期验证
    with pytest.raises(ValidationError) as exc_info:
        AssetCreate(
            ownership_entity="测试",
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
            occupancy_rate="75%",
            current_contract_start_date=start_date,
            current_contract_end_date=end_date  # 结束日期早于开始日期
        )
    
    assert "合同结束日期必须晚于开始日期" in str(exc_info.value)


def test_asset_update_partial():
    """测试资产部分更新"""
    
    # 只更新部分字段
    update_data = {
        "property_name": "更新后的物业名称",
        "actual_property_area": 1200.0,
        "occupancy_rate": "80%"
    }
    
    asset_update = AssetUpdate(**update_data)
    
    assert asset_update.property_name == "更新后的物业名称"
    assert asset_update.actual_property_area == 1200.0
    assert asset_update.occupancy_rate == "80%"
    
    # 未设置的字段应该为None
    assert asset_update.ownership_entity is None
    assert asset_update.address is None


def test_asset_response_model():
    """测试资产响应模型"""
    
    response_data = {
        "id": "test-id-123",
        "ownership_entity": "国资集团",
        "property_name": "测试物业",
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
        "occupancy_rate": "75%",
        "version": 1,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
    
    asset_response = AssetResponse(**response_data)
    
    assert asset_response.id == "test-id-123"
    assert asset_response.version == 1
    assert isinstance(asset_response.created_at, datetime)


def test_asset_search_params():
    """测试资产搜索参数模型"""
    
    # 测试默认值
    search_params = AssetSearchParams()
    assert search_params.page == 1
    assert search_params.limit == 20
    assert search_params.sort_field == "created_at"
    assert search_params.sort_order == "desc"
    
    # 测试自定义参数
    search_params = AssetSearchParams(
        page=2,
        limit=50,
        search="测试关键词",
        ownership_status="已确权",
        property_nature="经营类",
        sort_field="property_name",
        sort_order="asc"
    )
    
    assert search_params.page == 2
    assert search_params.limit == 50
    assert search_params.search == "测试关键词"
    assert search_params.ownership_status == OwnershipStatus.CONFIRMED
    assert search_params.property_nature == PropertyNature.COMMERCIAL
    assert search_params.sort_field == "property_name"
    assert search_params.sort_order == "asc"


def test_asset_search_params_validation():
    """测试搜索参数验证"""
    
    # 测试页码验证
    with pytest.raises(ValidationError):
        AssetSearchParams(page=0)  # 页码必须大于等于1
    
    # 测试限制数量验证
    with pytest.raises(ValidationError):
        AssetSearchParams(limit=0)  # 限制数量必须大于等于1
    
    with pytest.raises(ValidationError):
        AssetSearchParams(limit=101)  # 限制数量不能超过100
    
    # 测试排序方向验证
    with pytest.raises(ValidationError):
        AssetSearchParams(sort_order="invalid")  # 只能是asc或desc


def test_string_strip_whitespace():
    """测试字符串自动去除空白字符"""
    
    asset_data = {
        "ownership_entity": "  国资集团  ",  # 前后有空格
        "property_name": "\t测试物业\n",    # 前后有制表符和换行符
        "address": "  测试地址  ",
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
    
    asset = AssetCreate(**asset_data)
    
    # 验证空白字符被自动去除
    assert asset.ownership_entity == "国资集团"
    assert asset.property_name == "测试物业"
    assert asset.address == "测试地址"


def test_enum_values():
    """测试枚举值"""
    
    # 测试确权状态枚举
    assert OwnershipStatus.CONFIRMED == "已确权"
    assert OwnershipStatus.UNCONFIRMED == "未确权"
    assert OwnershipStatus.PARTIAL == "部分确权"
    
    # 测试使用状态枚举
    assert UsageStatus.RENTED == "出租"
    assert UsageStatus.VACANT == "闲置"
    assert UsageStatus.SELF_USE == "自用"
    assert UsageStatus.PUBLIC == "公房"
    assert UsageStatus.OTHER == "其他"
    
    # 测试物业性质枚举
    assert PropertyNature.COMMERCIAL == "经营类"
    assert PropertyNature.NON_COMMERCIAL == "非经营类"


def test_asset_create_comprehensive_validation():
    """测试资产创建的综合验证"""
    
    # 测试字符串长度限制
    with pytest.raises(ValidationError) as exc_info:
        AssetCreate(
            ownership_entity="x" * 101,  # 超过100字符限制
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
    
    errors = exc_info.value.errors()
    assert any("String should have at most 100 characters" in str(error) for error in errors)
    
    # 测试空字符串验证
    with pytest.raises(ValidationError):
        AssetCreate(
            ownership_entity="",  # 空字符串
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


def test_asset_area_consistency_validation():
    """测试面积数据一致性验证"""
    
    # 测试未出租面积超过可出租面积（单独验证）
    with pytest.raises(ValidationError) as exc_info:
        AssetCreate(
            ownership_entity="测试",
            property_name="测试物业",
            address="测试地址",
            actual_property_area=1000.0,
            rentable_area=800.0,
            rented_area=0.0,  # 设为0，只测试未出租面积
            unrented_area=900.0,  # 超过可出租面积
            non_commercial_area=200.0,
            ownership_status="已确权",
            actual_usage="商业",
            usage_status="出租",
            is_litigated="否",
            property_nature="经营类",
            occupancy_rate="75%"
        )
    
    assert "未出租面积不能超过可出租面积" in str(exc_info.value)
    
    # 测试已出租面积和未出租面积之和超过可出租面积
    with pytest.raises(ValidationError) as exc_info:
        AssetCreate(
            ownership_entity="测试",
            property_name="测试物业",
            address="测试地址",
            actual_property_area=1000.0,
            rentable_area=800.0,
            rented_area=600.0,
            unrented_area=300.0,  # 600 + 300 = 900 > 800
            non_commercial_area=200.0,
            ownership_status="已确权",
            actual_usage="商业",
            usage_status="出租",
            is_litigated="否",
            property_nature="经营类",
            occupancy_rate="75%"
        )
    
    assert "已出租面积和未出租面积之和不能超过可出租面积" in str(exc_info.value)


def test_asset_update_validation():
    """测试资产更新验证"""
    
    # 测试更新时的字段验证
    with pytest.raises(ValidationError):
        AssetUpdate(
            ownership_entity="",  # 空字符串不允许
        )
    
    # 测试更新时的面积验证
    with pytest.raises(ValidationError):
        AssetUpdate(
            actual_property_area=-100.0  # 负数不允许
        )
    
    # 测试更新时的枚举验证
    with pytest.raises(ValidationError):
        AssetUpdate(
            ownership_status="无效状态"  # 无效枚举值
        )


def test_asset_optional_fields():
    """测试可选字段的处理"""
    
    # 创建只包含必填字段的资产
    minimal_asset = AssetCreate(
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
    
    # 验证可选字段为None
    assert minimal_asset.management_entity is None
    assert minimal_asset.ownership_category is None
    assert minimal_asset.land_area is None
    assert minimal_asset.certificated_usage is None
    assert minimal_asset.business_category is None
    assert minimal_asset.business_model is None
    assert minimal_asset.include_in_occupancy_rate is None
    assert minimal_asset.lease_contract is None
    assert minimal_asset.current_contract_start_date is None
    assert minimal_asset.current_contract_end_date is None
    assert minimal_asset.tenant_name is None
    assert minimal_asset.current_lease_contract is None
    assert minimal_asset.current_terminal_contract is None
    assert minimal_asset.wuyang_project_name is None
    assert minimal_asset.agreement_start_date is None
    assert minimal_asset.agreement_end_date is None
    assert minimal_asset.description is None
    assert minimal_asset.notes is None


def test_asset_model_config():
    """测试模型配置"""
    
    # 测试枚举值使用
    asset = AssetCreate(
        ownership_entity="国资集团",
        property_name="测试物业",
        address="测试地址",
        actual_property_area=1000.0,
        rentable_area=800.0,
        rented_area=600.0,
        unrented_area=200.0,
        non_commercial_area=200.0,
        ownership_status=OwnershipStatus.CONFIRMED,  # 使用枚举对象
        actual_usage="商业",
        usage_status=UsageStatus.RENTED,  # 使用枚举对象
        is_litigated="否",
        property_nature=PropertyNature.COMMERCIAL,  # 使用枚举对象
        occupancy_rate="75%"
    )
    
    # 验证枚举值被正确处理
    assert asset.ownership_status == "已确权"
    assert asset.usage_status == "出租"
    assert asset.property_nature == "经营类"


def test_asset_history_response():
    """测试资产变更历史响应模型"""
    
    history_data = {
        "id": "history-id-123",
        "asset_id": "asset-id-456",
        "change_type": "update",
        "changed_fields": ["property_name", "actual_property_area"],
        "old_values": {"property_name": "旧物业名称", "actual_property_area": 800.0},
        "new_values": {"property_name": "新物业名称", "actual_property_area": 1000.0},
        "changed_by": "admin",
        "changed_at": datetime.now(),
        "reason": "信息更新"
    }
    
    history = AssetHistoryResponse(**history_data)
    
    assert history.id == "history-id-123"
    assert history.asset_id == "asset-id-456"
    assert history.change_type == "update"
    assert len(history.changed_fields) == 2
    assert "property_name" in history.changed_fields
    assert history.old_values["property_name"] == "旧物业名称"
    assert history.new_values["property_name"] == "新物业名称"
    assert history.changed_by == "admin"
    assert isinstance(history.changed_at, datetime)
    assert history.reason == "信息更新"


def test_asset_document_response():
    """测试资产文档响应模型"""
    
    document_data = {
        "id": "doc-id-123",
        "asset_id": "asset-id-456",
        "file_name": "合同文件.pdf",
        "file_path": "/uploads/documents/合同文件.pdf",
        "file_size": 1024000,
        "mime_type": "application/pdf",
        "uploaded_at": datetime.now()
    }
    
    document = AssetDocumentResponse(**document_data)
    
    assert document.id == "doc-id-123"
    assert document.asset_id == "asset-id-456"
    assert document.file_name == "合同文件.pdf"
    assert document.file_path == "/uploads/documents/合同文件.pdf"
    assert document.file_size == 1024000
    assert document.mime_type == "application/pdf"
    assert isinstance(document.uploaded_at, datetime)


def test_asset_list_response():
    """测试资产列表响应模型"""
    
    # 创建测试资产数据
    asset_data = {
        "id": "test-id-123",
        "ownership_entity": "国资集团",
        "property_name": "测试物业",
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
        "occupancy_rate": "75%",
        "version": 1,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
    
    list_data = {
        "data": [AssetResponse(**asset_data)],
        "total": 100,
        "page": 1,
        "limit": 20,
        "has_next": True,
        "has_prev": False
    }
    
    asset_list = AssetListResponse(**list_data)
    
    assert len(asset_list.data) == 1
    assert asset_list.total == 100
    assert asset_list.page == 1
    assert asset_list.limit == 20
    assert asset_list.has_next is True
    assert asset_list.has_prev is False
    assert isinstance(asset_list.data[0], AssetResponse)


def test_asset_search_params_edge_cases():
    """测试搜索参数的边界情况"""
    
    # 测试最小值
    search_params = AssetSearchParams(page=1, limit=1)
    assert search_params.page == 1
    assert search_params.limit == 1
    
    # 测试最大值
    search_params = AssetSearchParams(page=999999, limit=100)
    assert search_params.page == 999999
    assert search_params.limit == 100
    
    # 测试长搜索关键词
    long_search = "x" * 100  # 100字符，应该通过验证
    search_params = AssetSearchParams(search=long_search)
    assert search_params.search == long_search
    
    # 测试超长搜索关键词
    with pytest.raises(ValidationError):
        AssetSearchParams(search="x" * 101)  # 超过100字符限制


def test_asset_create_with_all_optional_fields():
    """测试创建包含所有可选字段的资产"""
    
    now = datetime.now()
    future_date = now + timedelta(days=365)
    
    asset_data = {
        "ownership_entity": "国资集团",
        "management_entity": "五羊公司",
        "ownership_category": "国有资产",
        "property_name": "完整测试物业",
        "address": "广州市天河区测试路123号",
        "land_area": 1200.0,
        "actual_property_area": 1000.0,
        "rentable_area": 800.0,
        "rented_area": 600.0,
        "unrented_area": 200.0,
        "non_commercial_area": 200.0,
        "ownership_status": "已确权",
        "certificated_usage": "商业用途",
        "actual_usage": "商业",
        "business_category": "零售",
        "usage_status": "出租",
        "is_litigated": "否",
        "property_nature": "经营类",
        "business_model": "直营",
        "include_in_occupancy_rate": "是",
        "occupancy_rate": "75%",
        "lease_contract": "合同编号ABC123",
        "current_contract_start_date": now,
        "current_contract_end_date": future_date,
        "tenant_name": "测试租户",
        "current_lease_contract": "租赁合同DEF456",
        "current_terminal_contract": "终端合同GHI789",
        "wuyang_project_name": "五羊测试项目",
        "agreement_start_date": now,
        "agreement_end_date": future_date,
        "description": "这是一个测试物业的详细描述",
        "notes": "备注信息"
    }
    
    asset = AssetCreate(**asset_data)
    
    # 验证所有字段都被正确设置
    assert asset.ownership_entity == "国资集团"
    assert asset.management_entity == "五羊公司"
    assert asset.ownership_category == "国有资产"
    assert asset.land_area == 1200.0
    assert asset.certificated_usage == "商业用途"
    assert asset.business_category == "零售"
    assert asset.business_model == "直营"
    assert asset.include_in_occupancy_rate == "是"
    assert asset.lease_contract == "合同编号ABC123"
    assert asset.current_contract_start_date == now
    assert asset.current_contract_end_date == future_date
    assert asset.tenant_name == "测试租户"
    assert asset.current_lease_contract == "租赁合同DEF456"
    assert asset.current_terminal_contract == "终端合同GHI789"
    assert asset.wuyang_project_name == "五羊测试项目"
    assert asset.agreement_start_date == now
    assert asset.agreement_end_date == future_date
    assert asset.description == "这是一个测试物业的详细描述"
    assert asset.notes == "备注信息"