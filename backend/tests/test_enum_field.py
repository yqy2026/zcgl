"""
枚举字段管理功能测试
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.main import app
from src.database import get_db
from src.models.enum_field import EnumFieldType, EnumFieldValue
from src.schemas.enum_field import EnumFieldTypeCreate, EnumFieldValueCreate

client = TestClient(app)


class TestEnumFieldType:
    """枚举字段类型测试"""
    
    def test_create_enum_field_type(self):
        """测试创建枚举字段类型"""
        import uuid
        unique_code = f"asset_status_{str(uuid.uuid4())[:8]}"
        
        data = {
            "name": "资产状态",
            "code": unique_code,
            "category": "资产管理",
            "description": "资产状态枚举",
            "is_multiple": False,
            "is_hierarchical": False,
            "status": "active"
        }
        
        response = client.post("/api/v1/enum-fields/types", json=data)
        assert response.status_code == 200
        
        result = response.json()
        assert result["name"] == data["name"]
        assert result["code"] == data["code"]
        assert result["status"] == data["status"]
        
        return result["id"]
    
    def test_get_enum_field_types(self):
        """测试获取枚举字段类型列表"""
        response = client.get("/api/v1/enum-fields/types")
        assert response.status_code == 200
        
        result = response.json()
        assert isinstance(result, list)
    
    def test_get_enum_field_type_by_id(self):
        """测试根据ID获取枚举字段类型"""
        # 先创建一个类型
        type_id = self.test_create_enum_field_type()
        
        response = client.get(f"/api/v1/enum-fields/types/{type_id}")
        assert response.status_code == 200
        
        result = response.json()
        assert result["id"] == type_id
    
    def test_update_enum_field_type(self):
        """测试更新枚举字段类型"""
        # 先创建一个类型
        type_id = self.test_create_enum_field_type()
        
        update_data = {
            "name": "资产状态（更新）",
            "description": "更新后的资产状态枚举"
        }
        
        response = client.put(f"/api/v1/enum-fields/types/{type_id}", json=update_data)
        assert response.status_code == 200
        
        result = response.json()
        assert result["name"] == update_data["name"]
        assert result["description"] == update_data["description"]
    
    def test_delete_enum_field_type(self):
        """测试删除枚举字段类型"""
        # 先创建一个类型
        type_id = self.test_create_enum_field_type()
        
        response = client.delete(f"/api/v1/enum-fields/types/{type_id}")
        assert response.status_code == 200
        
        # 验证删除后无法获取
        response = client.get(f"/api/v1/enum-fields/types/{type_id}")
        assert response.status_code == 404
    
    def test_get_enum_field_statistics(self):
        """测试获取枚举字段统计信息"""
        response = client.get("/api/v1/enum-fields/types/statistics")
        assert response.status_code == 200
        
        result = response.json()
        assert "total_types" in result
        assert "active_types" in result
        assert "total_values" in result
        assert "categories" in result


class TestEnumFieldValue:
    """枚举字段值测试"""
    
    def setup_method(self):
        """测试前准备：创建枚举类型"""
        data = {
            "name": "测试枚举类型",
            "code": "test_enum_type",
            "category": "测试",
            "status": "active"
        }
        
        response = client.post("/api/v1/enum-fields/types", json=data)
        assert response.status_code == 200
        
        self.type_id = response.json()["id"]
    
    def test_create_enum_field_value(self):
        """测试创建枚举字段值"""
        data = {
            "label": "正常",
            "value": "normal",
            "code": "NORMAL",
            "description": "正常状态",
            "sort_order": 1,
            "color": "#52c41a",
            "is_active": True,
            "is_default": True
        }
        
        response = client.post(f"/api/v1/enum-fields/types/{self.type_id}/values", json=data)
        assert response.status_code == 200
        
        result = response.json()
        assert result["label"] == data["label"]
        assert result["value"] == data["value"]
        assert result["enum_type_id"] == self.type_id
        
        return result["id"]
    
    def test_get_enum_field_values(self):
        """测试获取枚举字段值列表"""
        # 先创建一个值
        self.test_create_enum_field_value()
        
        response = client.get(f"/api/v1/enum-fields/types/{self.type_id}/values")
        assert response.status_code == 200
        
        result = response.json()
        assert isinstance(result, list)
        assert len(result) > 0
    
    def test_get_enum_field_values_tree(self):
        """测试获取枚举字段值树形结构"""
        response = client.get(f"/api/v1/enum-fields/types/{self.type_id}/values/tree")
        assert response.status_code == 200
        
        result = response.json()
        assert isinstance(result, list)
    
    def test_update_enum_field_value(self):
        """测试更新枚举字段值"""
        # 先创建一个值
        value_id = self.test_create_enum_field_value()
        
        update_data = {
            "label": "正常（更新）",
            "description": "更新后的正常状态"
        }
        
        response = client.put(f"/api/v1/enum-fields/values/{value_id}", json=update_data)
        assert response.status_code == 200
        
        result = response.json()
        assert result["label"] == update_data["label"]
        assert result["description"] == update_data["description"]
    
    def test_delete_enum_field_value(self):
        """测试删除枚举字段值"""
        # 先创建一个值
        value_id = self.test_create_enum_field_value()
        
        response = client.delete(f"/api/v1/enum-fields/values/{value_id}")
        assert response.status_code == 200
        
        # 验证删除后无法获取
        response = client.get(f"/api/v1/enum-fields/values/{value_id}")
        assert response.status_code == 404
    
    def test_batch_create_enum_field_values(self):
        """测试批量创建枚举字段值"""
        data = {
            "values": [
                {
                    "label": "启用",
                    "value": "enabled",
                    "sort_order": 1
                },
                {
                    "label": "禁用",
                    "value": "disabled",
                    "sort_order": 2
                }
            ]
        }
        
        response = client.post(f"/api/v1/enum-fields/types/{self.type_id}/values/batch", json=data)
        assert response.status_code == 200
        
        result = response.json()
        assert isinstance(result, list)
        assert len(result) == 2


class TestEnumFieldValidation:
    """枚举字段验证测试"""
    
    def test_create_enum_field_type_with_invalid_code(self):
        """测试使用无效编码创建枚举字段类型"""
        data = {
            "name": "测试枚举",
            "code": "invalid-code!",  # 包含无效字符
            "status": "active"
        }
        
        response = client.post("/api/v1/enum-fields/types", json=data)
        assert response.status_code == 422
    
    def test_create_duplicate_enum_field_type_code(self):
        """测试创建重复编码的枚举字段类型"""
        data = {
            "name": "测试枚举1",
            "code": "duplicate_code",
            "status": "active"
        }
        
        # 第一次创建
        response = client.post("/api/v1/enum-fields/types", json=data)
        assert response.status_code == 200
        
        # 第二次创建相同编码
        data["name"] = "测试枚举2"
        response = client.post("/api/v1/enum-fields/types", json=data)
        assert response.status_code == 400
    
    def test_create_enum_field_value_with_invalid_color(self):
        """测试使用无效颜色创建枚举字段值"""
        # 先创建枚举类型
        type_data = {
            "name": "颜色测试",
            "code": "color_test",
            "status": "active"
        }
        
        type_response = client.post("/api/v1/enum-fields/types", json=type_data)
        type_id = type_response.json()["id"]
        
        # 创建带无效颜色的枚举值
        value_data = {
            "label": "红色",
            "value": "red",
            "color": "invalid_color"  # 无效颜色格式
        }
        
        response = client.post(f"/api/v1/enum-fields/types/{type_id}/values", json=value_data)
        assert response.status_code == 422


class TestEnumFieldHistory:
    """枚举字段历史记录测试"""
    
    def test_get_enum_field_type_history(self):
        """测试获取枚举字段类型变更历史"""
        # 先创建一个类型
        data = {
            "name": "历史测试",
            "code": "history_test",
            "status": "active",
            "created_by": "test_user"
        }
        
        response = client.post("/api/v1/enum-fields/types", json=data)
        type_id = response.json()["id"]
        
        # 获取历史记录
        response = client.get(f"/api/v1/enum-fields/types/{type_id}/history")
        assert response.status_code == 200
        
        result = response.json()
        assert isinstance(result, list)
        # 应该至少有一条创建记录
        assert len(result) >= 1
        assert result[0]["action"] == "create"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])