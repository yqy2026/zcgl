"""
组织架构管理功能测试
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import uuid
from datetime import datetime

from src.main import app
from src.database import get_db
from src.models.organization import Organization, OrganizationHistory
from src.schemas.organization import OrganizationCreate, OrganizationUpdate
from src.crud.organization import get_organization_crud

client = TestClient(app)


class TestOrganizationManagement:
    """组织架构管理测试类"""
    
    def setup_method(self):
        """测试前置设置"""
        self.test_organizations = []
        self.db = next(get_db())
        self.crud = get_organization_crud(self.db)
    
    def teardown_method(self):
        """测试后清理"""
        # 清理测试数据
        for org in self.test_organizations:
            try:
                self.crud.delete(org.id)
            except:
                pass
        self.db.close()
    
    def create_test_organization(self, **kwargs) -> Organization:
        """创建测试组织"""
        default_data = {
            "name": f"测试组织_{uuid.uuid4().hex[:8]}",
            "created_by": "test_user"
        }
        default_data.update(kwargs)
        
        org_create = OrganizationCreate(**default_data)
        organization = self.crud.create(org_create)
        self.test_organizations.append(organization)
        return organization
    
    def test_create_organization_success(self):
        """测试成功创建组织"""
        org_data = {
            "name": "测试部门",
            "description": "这是一个测试部门"
        }
        
        response = client.post("/api/v1/organizations/", json=org_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == org_data["name"]
        assert data["code"] == org_data["code"]
        assert data["type"] == org_data["type"]
        assert data["status"] == org_data["status"]
        assert "id" in data
        assert "created_at" in data
    
    def test_create_organization_duplicate_code(self):
        """测试创建重复编码的组织"""
        # 先创建一个组织
        org1 = self.create_test_organization(code="DUPLICATE_CODE")
        
        # 尝试创建相同编码的组织
        org_data = {
            "name": "重复编码组织",
            "code": "DUPLICATE_CODE",
            "type": "department",
            "status": "active"
        }
        
        response = client.post("/api/v1/organizations/", json=org_data)
        assert response.status_code == 400
        assert "已存在" in response.json()["detail"]
    
    def test_create_organization_invalid_type(self):
        """测试创建无效类型的组织"""
        org_data = {
            "name": "无效类型组织",
            "code": "INVALID_TYPE",
            "type": "invalid_type",
            "status": "active"
        }
        
        response = client.post("/api/v1/organizations/", json=org_data)
        assert response.status_code == 422
    
    def test_get_organization_list(self):
        """测试获取组织列表"""
        # 创建测试组织
        org1 = self.create_test_organization(name="组织1")
        org2 = self.create_test_organization(name="组织2")
        
        response = client.get("/api/v1/organizations/")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2
        
        # 验证创建的组织在列表中
        org_ids = [org["id"] for org in data]
        assert org1.id in org_ids
        assert org2.id in org_ids
    
    def test_get_organization_by_id(self):
        """测试根据ID获取组织"""
        org = self.create_test_organization(
            name="测试组织详情",
            description="详细描述"
        )
        
        response = client.get(f"/api/v1/organizations/{org.id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == org.id
        assert data["name"] == org.name
        assert data["description"] == org.description
    
    def test_get_organization_not_found(self):
        """测试获取不存在的组织"""
        fake_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/organizations/{fake_id}")
        assert response.status_code == 404
    
    def test_update_organization_success(self):
        """测试成功更新组织"""
        org = self.create_test_organization()
        
        update_data = {
            "name": "更新后的组织名称",
            "description": "更新后的描述",
            "status": "inactive",
            "updated_by": "test_updater"
        }
        
        response = client.put(f"/api/v1/organizations/{org.id}", json=update_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["description"] == update_data["description"]
        assert data["status"] == update_data["status"]
    
    def test_update_organization_duplicate_code(self):
        """测试更新组织为重复编码"""
        org1 = self.create_test_organization(code="CODE1")
        org2 = self.create_test_organization(code="CODE2")
        
        update_data = {"code": "CODE1"}
        
        response = client.put(f"/api/v1/organizations/{org2.id}", json=update_data)
        assert response.status_code == 400
        assert "已存在" in response.json()["detail"]
    
    def test_delete_organization_success(self):
        """测试成功删除组织"""
        org = self.create_test_organization()
        
        response = client.delete(f"/api/v1/organizations/{org.id}")
        assert response.status_code == 200
        
        # 验证组织已被软删除
        deleted_org = self.crud.get(org.id)
        assert deleted_org is None
    
    def test_delete_organization_with_children(self):
        """测试删除有子组织的组织"""
        parent_org = self.create_test_organization(name="父组织")
        child_org = self.create_test_organization(
            name="子组织",
            parent_id=parent_org.id
        )
        
        response = client.delete(f"/api/v1/organizations/{parent_org.id}")
        assert response.status_code == 400
        assert "子组织" in response.json()["detail"]
    
    def test_get_organization_tree(self):
        """测试获取组织树形结构"""
        # 创建层级组织结构
        root_org = self.create_test_organization(name="根组织")
        child1 = self.create_test_organization(
            name="子组织1",
            parent_id=root_org.id
        )
        child2 = self.create_test_organization(
            name="子组织2",
            parent_id=root_org.id
        )
        grandchild = self.create_test_organization(
            name="孙组织",
            parent_id=child1.id
        )
        
        response = client.get("/api/v1/organizations/tree")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        
        # 验证树形结构
        root_nodes = [node for node in data if node["id"] == root_org.id]
        assert len(root_nodes) == 1
        
        root_node = root_nodes[0]
        assert len(root_node["children"]) == 2
        
        # 验证子节点
        child_ids = [child["id"] for child in root_node["children"]]
        assert child1.id in child_ids
        assert child2.id in child_ids
    
    def test_search_organizations(self):
        """测试搜索组织"""
        org1 = self.create_test_organization(
            name="搜索测试组织1",
            description="包含关键词的描述"
        )
        org2 = self.create_test_organization(
            name="其他组织",
            description="不相关的描述"
        )
        
        response = client.get("/api/v1/organizations/search?keyword=搜索测试")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        
        # 验证搜索结果
        found_ids = [org["id"] for org in data]
        assert org1.id in found_ids
        assert org2.id not in found_ids
    
    def test_get_organization_statistics(self):
        """测试获取组织统计信息"""
        # 创建不同状态的组织
        active_org = self.create_test_organization(status="active")
        inactive_org = self.create_test_organization(status="inactive")
        
        response = client.get("/api/v1/organizations/statistics")
        assert response.status_code == 200
        
        data = response.json()
        assert "total" in data
        assert "active" in data
        assert "inactive" in data
        assert "by_type" in data
        assert "by_level" in data
        
        assert data["total"] >= 2
        assert data["active"] >= 1
        assert data["inactive"] >= 1
    
    def test_get_organization_children(self):
        """测试获取组织子组织"""
        parent_org = self.create_test_organization(name="父组织")
        child1 = self.create_test_organization(
            name="子组织1",
            parent_id=parent_org.id
        )
        child2 = self.create_test_organization(
            name="子组织2",
            parent_id=parent_org.id
        )
        
        response = client.get(f"/api/v1/organizations/{parent_org.id}/children")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        
        child_ids = [child["id"] for child in data]
        assert child1.id in child_ids
        assert child2.id in child_ids
    
    def test_get_organization_path(self):
        """测试获取组织路径"""
        # 创建多层级组织
        level1 = self.create_test_organization(name="一级组织")
        level2 = self.create_test_organization(
            name="二级组织",
            parent_id=level1.id
        )
        level3 = self.create_test_organization(
            name="三级组织",
            parent_id=level2.id
        )
        
        response = client.get(f"/api/v1/organizations/{level3.id}/path")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3
        
        # 验证路径顺序
        assert data[0]["id"] == level1.id
        assert data[1]["id"] == level2.id
        assert data[2]["id"] == level3.id
    
    def test_move_organization(self):
        """测试移动组织"""
        org1 = self.create_test_organization(name="组织1")
        org2 = self.create_test_organization(name="组织2")
        target_org = self.create_test_organization(name="目标父组织")
        
        move_data = {
            "target_parent_id": target_org.id,
            "updated_by": "test_mover"
        }
        
        response = client.post(f"/api/v1/organizations/{org1.id}/move", json=move_data)
        assert response.status_code == 200
        
        # 验证移动结果
        moved_org = self.crud.get(org1.id)
        assert moved_org.parent_id == target_org.id
    
    def test_move_organization_circular_reference(self):
        """测试移动组织形成循环引用"""
        parent_org = self.create_test_organization(name="父组织")
        child_org = self.create_test_organization(
            name="子组织",
            parent_id=parent_org.id
        )
        
        # 尝试将父组织移动到子组织下
        move_data = {
            "target_parent_id": child_org.id,
            "updated_by": "test_mover"
        }
        
        response = client.post(f"/api/v1/organizations/{parent_org.id}/move", json=move_data)
        assert response.status_code == 400
        assert "循环" in response.json()["detail"]
    
    def test_batch_organization_operations(self):
        """测试批量组织操作"""
        org1 = self.create_test_organization(status="active")
        org2 = self.create_test_organization(status="active")
        
        batch_data = {
            "organization_ids": [org1.id, org2.id],
            "action": "deactivate",
            "updated_by": "test_batch_user"
        }
        
        response = client.post("/api/v1/organizations/batch", json=batch_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "results" in data
        assert "errors" in data
        assert len(data["results"]) == 2
        
        # 验证批量操作结果
        updated_org1 = self.crud.get(org1.id)
        updated_org2 = self.crud.get(org2.id)
        assert updated_org1.status == "inactive"
        assert updated_org2.status == "inactive"
    
    def test_organization_history_tracking(self):
        """测试组织历史记录跟踪"""
        org = self.create_test_organization(name="历史测试组织")
        
        # 更新组织以产生历史记录
        update_data = {
            "name": "更新后的名称",
            "description": "新的描述",
            "updated_by": "test_history_user"
        }
        
        response = client.put(f"/api/v1/organizations/{org.id}", json=update_data)
        assert response.status_code == 200
        
        # 获取历史记录
        history_response = client.get(f"/api/v1/organizations/{org.id}/history")
        assert history_response.status_code == 200
        
        history_data = history_response.json()
        assert isinstance(history_data, list)
        assert len(history_data) >= 1
        
        # 验证历史记录内容
        history_record = history_data[0]
        assert history_record["organization_id"] == org.id
        assert history_record["action"] == "update"
        assert history_record["created_by"] == "test_history_user"
    
    def test_organization_validation(self):
        """测试组织数据验证"""
        # 测试无效的组织编码格式
        invalid_code_data = {
            "name": "测试组织",
            "code": "invalid code with spaces",
            "type": "department",
            "status": "active"
        }
        
        response = client.post("/api/v1/organizations/", json=invalid_code_data)
        assert response.status_code == 422
        
        # 测试无效的邮箱格式
        invalid_email_data = {
            "name": "测试组织",
            "code": "VALID_CODE",
            "type": "department",
            "status": "active",
            "email": "invalid-email"
        }
        
        response = client.post("/api/v1/organizations/", json=invalid_email_data)
        assert response.status_code == 422
    
    def test_organization_level_calculation(self):
        """测试组织层级计算"""
        # 创建多层级组织
        root_org = self.create_test_organization(name="根组织")
        assert root_org.level == 1
        
        child_org = self.create_test_organization(
            name="子组织",
            parent_id=root_org.id
        )
        assert child_org.level == 2
        
        grandchild_org = self.create_test_organization(
            name="孙组织",
            parent_id=child_org.id
        )
        assert grandchild_org.level == 3
    
    def test_organization_path_calculation(self):
        """测试组织路径计算"""
        root_org = self.create_test_organization(name="根组织")
        child_org = self.create_test_organization(
            name="子组织",
            parent_id=root_org.id
        )
        
        # 验证路径计算
        assert root_org.path == f"/{root_org.id}"
        assert child_org.path == f"/{root_org.id}/{child_org.id}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])