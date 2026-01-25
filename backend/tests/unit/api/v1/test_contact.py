"""
联系人管理API测试

Test coverage for Contact API endpoints:
- CRUD operations (Create, Read, Update, Delete)
- Entity-based contact management
- Primary contact handling
- Batch operations
- Pagination and filtering
- Error handling and validation
- Authentication and authorization
"""

import pytest
from fastapi import status
from sqlalchemy.orm import Session


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_ownership(db: Session):
    """创建测试权属单位"""
    from src.schemas.ownership import OwnershipCreate
    from src.crud.ownership import ownership_crud

    ownership = ownership_crud.create(
        db,
        obj_in=OwnershipCreate(
            name="Test Ownership",
            code="OWN-001",
            ownership_type="state",
            unified_social_credit_code="91110000123456789X"
        )
    )
    yield ownership
    try:
        ownership_crud.remove(db, id=ownership.id)
    except:
        pass


@pytest.fixture
def contact_data(db: Session, sample_ownership):
    """创建测试联系人数据"""
    from src.schemas.contact import ContactCreate
    from src.crud.contact import contact_crud

    contact = contact_crud.create(
        db,
        obj_in=ContactCreate(
            name="张三",
            phone="13800138000",
            email="zhangsan@example.com",
            entity_type="ownership",
            entity_id=sample_ownership.id,
            is_primary=True,
            position="经理"
        )
    )
    yield contact
    try:
        contact_crud.remove(db, id=contact.id)
    except:
        pass


@pytest.fixture
def admin_user_headers(client, admin_user):
    """管理员用户认证头"""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": admin_user.username, "password": "admin123"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ============================================================================
# Create Contact Tests
# ============================================================================

class TestCreateContact:
    """测试创建联系人API"""

    def test_create_contact_success(self, client, admin_user_headers, sample_ownership):
        """测试成功创建联系人"""
        contact_data = {
            "name": "李四",
            "phone": "13900139000",
            "email": "lisi@example.com",
            "entity_type": "ownership",
            "entity_id": sample_ownership.id,
            "is_primary": False,
            "position": "主管"
        }

        response = client.post(
            "/api/v1/contact/",
            json=contact_data,
            headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "李四"
        assert data["phone"] == "13900139000"
        assert data["email"] == "lisi@example.com"
        assert "id" in data

    def test_create_primary_contact_success(self, client, admin_user_headers, sample_ownership):
        """测试创建主要联系人"""
        contact_data = {
            "name": "王五",
            "phone": "13700137000",
            "entity_type": "ownership",
            "entity_id": sample_ownership.id,
            "is_primary": True,
            "position": "负责人"
        }

        response = client.post(
            "/api/v1/contact/",
            json=contact_data,
            headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_primary"] is True

    def test_create_contact_unauthorized(self, client, sample_ownership):
        """测试未授权创建联系人"""
        contact_data = {
            "name": "赵六",
            "phone": "13600136000",
            "entity_type": "ownership",
            "entity_id": sample_ownership.id
        }

        response = client.post(
            "/api/v1/contact/",
            json=contact_data
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_contact_invalid_phone(self, client, admin_user_headers, sample_ownership):
        """测试创建联系人时手机号格式错误"""
        contact_data = {
            "name": "测试用户",
            "phone": "invalid_phone",
            "entity_type": "ownership",
            "entity_id": sample_ownership.id
        }

        response = client.post(
            "/api/v1/contact/",
            json=contact_data,
            headers=admin_user_headers
        )

        # 可能通过验证或返回验证错误
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_422_UNPROCESSABLE_ENTITY]

    def test_create_contact_missing_required_fields(self, client, admin_user_headers):
        """测试缺少必填字段"""
        contact_data = {
            "name": "测试用户"
            # 缺少 entity_type 和 entity_id
        }

        response = client.post(
            "/api/v1/contact/",
            json=contact_data,
            headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_contact_invalid_email(self, client, admin_user_headers, sample_ownership):
        """测试创建联系人时邮箱格式错误"""
        contact_data = {
            "name": "测试用户",
            "phone": "13800138000",
            "email": "invalid_email_format",
            "entity_type": "ownership",
            "entity_id": sample_ownership.id
        }

        response = client.post(
            "/api/v1/contact/",
            json=contact_data,
            headers=admin_user_headers
        )

        # Pydantic应该验证邮箱格式
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_422_UNPROCESSABLE_ENTITY]


# ============================================================================
# Get Contact by ID Tests
# ============================================================================

class TestGetContact:
    """测试获取单个联系人API"""

    def test_get_contact_success(self, client, admin_user_headers, contact_data):
        """测试成功获取联系人"""
        response = client.get(
            f"/api/v1/contact/{contact_data.id}",
            headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == contact_data.id
        assert data["name"] == contact_data.name

    def test_get_contact_not_found(self, client, admin_user_headers):
        """测试获取不存在的联系人"""
        response = client.get(
            "/api/v1/contact/non-existent-id",
            headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_contact_unauthorized(self, client, contact_data):
        """测试未授权获取联系人"""
        response = client.get(f"/api/v1/contact/{contact_data.id}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ============================================================================
# Get Entity Contacts Tests
# ============================================================================

class TestGetEntityContacts:
    """测试获取实体联系人列表API"""

    def test_get_entity_contacts_default(self, client, admin_user_headers, contact_data):
        """测试获取实体联系人列表（默认参数）"""
        response = client.get(
            f"/api/v1/contact/entity/ownership/{contact_data.entity_id}",
            headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data

    def test_get_entity_contacts_with_pagination(self, client, admin_user_headers, sample_ownership):
        """测试分页功能"""
        response = client.get(
            f"/api/v1/contact/entity/ownership/{sample_ownership.id}?page=1&page_size=10",
            headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 10

    def test_get_entity_contacts_unauthorized(self, client, contact_data):
        """测试未授权获取实体联系人"""
        response = client.get(f"/api/v1/contact/entity/ownership/{contact_data.entity_id}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_entity_contacts_invalid_entity_type(self, client, admin_user_headers):
        """测试无效的实体类型"""
        response = client.get(
            "/api/v1/contact/entity/invalid_type/entity-123",
            headers=admin_user_headers
        )

        # 应该返回404或错误
        assert response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_400_BAD_REQUEST]


# ============================================================================
# Get Primary Contact Tests
# ============================================================================

class TestGetPrimaryContact:
    """测试获取主要联系人API"""

    def test_get_primary_contact_success(self, client, admin_user_headers, contact_data):
        """测试成功获取主要联系人"""
        response = client.get(
            f"/api/v1/contact/entity/ownership/{contact_data.entity_id}/primary",
            headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_primary"] is True
        assert data["id"] == contact_data.id

    def test_get_primary_contact_not_found(self, client, admin_user_headers, sample_ownership):
        """测试获取不存在的主要联系人"""
        # 创建没有主要联系人的实体
        response = client.get(
            f"/api/v1/contact/entity/ownership/{sample_ownership.id}/primary",
            headers=admin_user_headers
        )

        # 应该返回404
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_primary_contact_unauthorized(self, client, contact_data):
        """测试未授权获取主要联系人"""
        response = client.get(f"/api/v1/contact/entity/ownership/{contact_data.entity_id}/primary")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ============================================================================
# Update Contact Tests
# ============================================================================

class TestUpdateContact:
    """测试更新联系人API"""

    def test_update_contact_success(self, client, admin_user_headers, contact_data):
        """测试成功更新联系人"""
        update_data = {
            "name": "更新后的姓名",
            "position": "高级经理"
        }

        response = client.put(
            f"/api/v1/contact/{contact_data.id}",
            json=update_data,
            headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "更新后的姓名"
        assert data["position"] == "高级经理"

    def test_update_contact_not_found(self, client, admin_user_headers):
        """测试更新不存在的联系人"""
        update_data = {"name": "Updated Name"}

        response = client.put(
            "/api/v1/contact/non-existent-id",
            json=update_data,
            headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_contact_promote_to_primary(self, client, admin_user_headers, contact_data):
        """测试将联系人升级为主要联系人"""
        update_data = {"is_primary": True}

        response = client.put(
            f"/api/v1/contact/{contact_data.id}",
            json=update_data,
            headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_primary"] is True


# ============================================================================
# Delete Contact Tests
# ============================================================================

class TestDeleteContact:
    """测试删除联系人API"""

    def test_delete_contact_success(self, client, admin_user_headers, db: Session, sample_ownership):
        """测试成功删除联系人（软删除）"""
        from src.schemas.contact import ContactCreate
        from src.crud.contact import contact_crud

        # 创建临时联系人用于删除
        temp_contact = contact_crud.create(
            db,
            obj_in=ContactCreate(
                name="临时联系人",
                phone="13800138000",
                entity_type="ownership",
                entity_id=sample_ownership.id
            )
        )

        response = client.delete(
            f"/api/v1/contact/{temp_contact.id}",
            headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # 软删除 - 联系人仍存在但is_active=False
        assert data["id"] == temp_contact.id

    def test_delete_contact_not_found(self, client, admin_user_headers):
        """测试删除不存在的联系人"""
        response = client.delete(
            "/api/v1/contact/non-existent-id",
            headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_contact_unauthorized(self, client, contact_data):
        """测试未授权删除联系人"""
        response = client.delete(f"/api/v1/contact/{contact_data.id}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ============================================================================
# Batch Create Contacts Tests
# ============================================================================

class TestBatchCreateContacts:
    """测试批量创建联系人API"""

    def test_batch_create_contacts_success(self, client, admin_user_headers, sample_ownership):
        """测试批量创建联系人"""
        contacts_data = [
            {
                "name": "批量联系人1",
                "phone": "13800138001",
                "entity_type": "ownership",
                "entity_id": sample_ownership.id
            },
            {
                "name": "批量联系人2",
                "phone": "13800138002",
                "entity_type": "ownership",
                "entity_id": sample_ownership.id
            }
        ]

        response = client.post(
            f"/api/v1/contact/batch/ownership/{sample_ownership.id}",
            json=contacts_data,
            headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2

    def test_batch_create_contacts_empty_list(self, client, admin_user_headers, sample_ownership):
        """测试批量创建空列表"""
        response = client.post(
            f"/api/v1/contact/batch/ownership/{sample_ownership.id}",
            json=[],
            headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_batch_create_contacts_unauthorized(self, client, sample_ownership):
        """测试未授权批量创建"""
        contacts_data = [
            {"name": "测试", "phone": "13800138000"}
        ]

        response = client.post(
            f"/api/v1/contact/batch/ownership/{sample_ownership.id}",
            json=contacts_data
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

class TestContactAPIEdgeCases:
    """测试API边界情况和错误处理"""

    def test_contact_with_special_characters_in_name(self, client, admin_user_headers, sample_ownership):
        """测试姓名中的特殊字符"""
        contact_data = {
            "name": "张三·李四-Wang",
            "phone": "13800138000",
            "entity_type": "ownership",
            "entity_id": sample_ownership.id
        }

        response = client.post(
            "/api/v1/contact/",
            json=contact_data,
            headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK

    def test_contact_with_unicode(self, client, admin_user_headers, sample_ownership):
        """测试Unicode支持"""
        contact_data = {
            "name": "测试联系人姓名",
            "phone": "13800138000",
            "email": "测试@example.com",
            "entity_type": "ownership",
            "entity_id": sample_ownership.id,
            "position": "职位名称"
        }

        response = client.post(
            "/api/v1/contact/",
            json=contact_data,
            headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "测试联系人姓名"

    def test_contact_very_long_name(self, client, admin_user_headers, sample_ownership):
        """测试超长姓名"""
        long_name = "A" * 200

        contact_data = {
            "name": long_name,
            "phone": "13800138000",
            "entity_type": "ownership",
            "entity_id": sample_ownership.id
        }

        response = client.post(
            "/api/v1/contact/",
            json=contact_data,
            headers=admin_user_headers
        )

        # 应该成功或有合理的长度限制
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_422_UNPROCESSABLE_ENTITY]
