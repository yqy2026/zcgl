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


@pytest.fixture(autouse=True)
def disable_contact_field_encryption(monkeypatch):
    """在联系人 API 单测中关闭字段加密，避免环境密钥导致长度溢出干扰接口行为验证。"""
    from src.crud.contact import contact_crud

    monkeypatch.setattr(
        contact_crud.sensitive_data_handler,
        "encryption_enabled",
        False,
    )


@pytest.fixture
def sample_ownership(db_session: Session):
    """创建测试权属单位"""
    from src.models.ownership import Ownership

    ownership_record = Ownership(
        name="Test Ownership",
        code="OW2501001",
        created_by="tester",
        updated_by="tester",
    )
    db_session.add(ownership_record)
    db_session.commit()
    db_session.refresh(ownership_record)

    yield ownership_record
    existing_ownership = (
        db_session.query(Ownership)
        .filter(Ownership.id == ownership_record.id)
        .one_or_none()
    )
    if existing_ownership is not None:
        db_session.delete(existing_ownership)
        db_session.commit()


@pytest.fixture
def contact_data(db_session: Session, sample_ownership):
    """创建测试联系人数据"""
    from src.models.contact import Contact

    contact = Contact(
        name="张三",
        phone="13800138000",
        email="zhangsan@example.com",
        entity_type="ownership",
        entity_id=sample_ownership.id,
        is_primary=True,
        title="经理",
        created_by="tester",
        updated_by="tester",
    )
    db_session.add(contact)
    db_session.commit()
    db_session.refresh(contact)

    yield contact
    existing_contact = (
        db_session.query(Contact).filter(Contact.id == contact.id).one_or_none()
    )
    if existing_contact is not None:
        db_session.delete(existing_contact)
        db_session.commit()


@pytest.fixture
def admin_user_headers(client, admin_user):
    """管理员用户认证头"""
    # client fixture already bypasses authentication
    return {}


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
            "title": "主管",
        }

        response = client.post(
            "/api/v1/contacts/", json=contact_data, headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "李四"
        assert data["phone"] == "13900139000"
        assert data["email"] == "lisi@example.com"
        assert "id" in data

    def test_create_primary_contact_success(
        self, client, admin_user_headers, sample_ownership
    ):
        """测试创建主要联系人"""
        contact_data = {
            "name": "王五",
            "phone": "13700137000",
            "entity_type": "ownership",
            "entity_id": sample_ownership.id,
            "is_primary": True,
            "title": "负责人",
        }

        response = client.post(
            "/api/v1/contacts/", json=contact_data, headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_primary"] is True

    def test_create_contact_unauthorized(
        self, unauthenticated_client, sample_ownership
    ):
        """测试未授权创建联系人"""
        contact_data = {
            "name": "赵六",
            "phone": "13600136000",
            "entity_type": "ownership",
            "entity_id": sample_ownership.id,
        }

        response = unauthenticated_client.post("/api/v1/contacts/", json=contact_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_contact_invalid_phone(
        self, client, admin_user_headers, sample_ownership
    ):
        """测试创建联系人时手机号格式错误"""
        contact_data = {
            "name": "测试用户",
            "phone": "invalid_phone",
            "entity_type": "ownership",
            "entity_id": sample_ownership.id,
        }

        response = client.post(
            "/api/v1/contacts/", json=contact_data, headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK

    def test_create_contact_missing_required_fields(self, client, admin_user_headers):
        """测试缺少必填字段"""
        contact_data = {
            "name": "测试用户"
            # 缺少 entity_type 和 entity_id
        }

        response = client.post(
            "/api/v1/contacts/", json=contact_data, headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_create_contact_invalid_email(
        self, client, admin_user_headers, sample_ownership
    ):
        """测试创建联系人时邮箱格式错误"""
        contact_data = {
            "name": "测试用户",
            "phone": "13800138000",
            "email": "invalid_email_format",
            "entity_type": "ownership",
            "entity_id": sample_ownership.id,
        }

        response = client.post(
            "/api/v1/contacts/", json=contact_data, headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


# ============================================================================
# Get Contact by ID Tests
# ============================================================================


class TestGetContact:
    """测试获取单个联系人API"""

    def test_get_contact_success(self, client, admin_user_headers, contact_data):
        """测试成功获取联系人"""
        response = client.get(
            f"/api/v1/contacts/{contact_data.id}", headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == contact_data.id
        assert data["name"] == contact_data.name

    def test_get_contact_not_found(self, client, admin_user_headers):
        """测试获取不存在的联系人"""
        response = client.get(
            "/api/v1/contacts/non-existent-id", headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_contact_unauthorized(self, unauthenticated_client, contact_data):
        """测试未授权获取联系人"""
        response = unauthenticated_client.get(f"/api/v1/contacts/{contact_data.id}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ============================================================================
# Get Entity Contacts Tests
# ============================================================================


class TestGetEntityContacts:
    """测试获取实体联系人列表API"""

    def test_get_entity_contacts_default(
        self, client, admin_user_headers, contact_data
    ):
        """测试获取实体联系人列表（默认参数）"""
        response = client.get(
            f"/api/v1/contacts/entity/ownership/{contact_data.entity_id}",
            headers=admin_user_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        payload = data["data"]
        assert "items" in payload
        assert "pagination" in payload
        assert "page" in payload["pagination"]
        assert "page_size" in payload["pagination"]

    def test_get_entity_contacts_with_pagination(
        self, client, admin_user_headers, sample_ownership
    ):
        """测试分页功能"""
        response = client.get(
            f"/api/v1/contacts/entity/ownership/{sample_ownership.id}?page=1&page_size=10",
            headers=admin_user_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        pagination = data["data"]["pagination"]
        assert pagination["page"] == 1
        assert pagination["page_size"] == 10

    def test_get_entity_contacts_unauthorized(
        self, unauthenticated_client, contact_data
    ):
        """测试未授权获取实体联系人"""
        response = unauthenticated_client.get(
            f"/api/v1/contacts/entity/ownership/{contact_data.entity_id}"
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_entity_contacts_invalid_entity_type(self, client, admin_user_headers):
        """测试无效的实体类型"""
        response = client.get(
            "/api/v1/contacts/entity/invalid_type/entity-123",
            headers=admin_user_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()["data"]
        assert payload["items"] == []
        assert payload["pagination"]["total"] == 0


# ============================================================================
# Get Primary Contact Tests
# ============================================================================


class TestGetPrimaryContact:
    """测试获取主要联系人API"""

    def test_get_primary_contact_success(
        self, client, admin_user_headers, contact_data
    ):
        """测试成功获取主要联系人"""
        response = client.get(
            f"/api/v1/contacts/entity/ownership/{contact_data.entity_id}/primary",
            headers=admin_user_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == contact_data.id
        assert data["name"] == contact_data.name

    def test_get_primary_contact_not_found(
        self, client, admin_user_headers, sample_ownership
    ):
        """测试获取不存在的主要联系人"""
        # 创建没有主要联系人的实体
        response = client.get(
            f"/api/v1/contacts/entity/ownership/{sample_ownership.id}/primary",
            headers=admin_user_headers,
        )

        # 应该返回404
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_primary_contact_unauthorized(
        self, unauthenticated_client, contact_data
    ):
        """测试未授权获取主要联系人"""
        response = unauthenticated_client.get(
            f"/api/v1/contacts/entity/ownership/{contact_data.entity_id}/primary"
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ============================================================================
# Update Contact Tests
# ============================================================================


class TestUpdateContact:
    """测试更新联系人API"""

    def test_update_contact_success(self, client, admin_user_headers, contact_data):
        """测试成功更新联系人"""
        update_data = {"name": "更新后的姓名", "title": "高级经理"}

        response = client.put(
            f"/api/v1/contacts/{contact_data.id}",
            json=update_data,
            headers=admin_user_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "更新后的姓名"
        assert data["title"] == "高级经理"

    def test_update_contact_not_found(self, client, admin_user_headers):
        """测试更新不存在的联系人"""
        update_data = {"name": "Updated Name"}

        response = client.put(
            "/api/v1/contacts/non-existent-id",
            json=update_data,
            headers=admin_user_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_contact_promote_to_primary(
        self, client, admin_user_headers, contact_data
    ):
        """测试将联系人升级为主要联系人"""
        update_data = {"is_primary": True}

        response = client.put(
            f"/api/v1/contacts/{contact_data.id}",
            json=update_data,
            headers=admin_user_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_primary"] is True


# ============================================================================
# Delete Contact Tests
# ============================================================================


class TestDeleteContact:
    """测试删除联系人API"""

    def test_delete_contact_success(
        self, client, admin_user_headers, db_session: Session, sample_ownership
    ):
        """测试成功删除联系人（软删除）"""
        from src.models.contact import Contact

        # 创建临时联系人用于删除
        temp_contact = Contact(
            name="临时联系人",
            phone="13800138000",
            entity_type="ownership",
            entity_id=sample_ownership.id,
            created_by="tester",
            updated_by="tester",
        )
        db_session.add(temp_contact)
        db_session.commit()
        db_session.refresh(temp_contact)

        response = client.delete(
            f"/api/v1/contacts/{temp_contact.id}", headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # 软删除 - 联系人仍存在但is_active=False
        assert data["id"] == temp_contact.id

    def test_delete_contact_not_found(self, client, admin_user_headers):
        """测试删除不存在的联系人"""
        response = client.delete(
            "/api/v1/contacts/non-existent-id", headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_contact_unauthorized(self, unauthenticated_client, contact_data):
        """测试未授权删除联系人"""
        response = unauthenticated_client.delete(f"/api/v1/contacts/{contact_data.id}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ============================================================================
# Batch Create Contacts Tests
# ============================================================================


class TestBatchCreateContacts:
    """测试批量创建联系人API"""

    def test_batch_create_contacts_success(
        self, client, admin_user_headers, sample_ownership
    ):
        """测试批量创建联系人"""
        contacts_data = [
            {
                "name": "批量联系人1",
                "phone": "13800138001",
                "entity_type": "ownership",
                "entity_id": sample_ownership.id,
            },
            {
                "name": "批量联系人2",
                "phone": "13800138002",
                "entity_type": "ownership",
                "entity_id": sample_ownership.id,
            },
        ]

        response = client.post(
            f"/api/v1/contacts/batch/ownership/{sample_ownership.id}",
            json=contacts_data,
            headers=admin_user_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2

    def test_batch_create_contacts_empty_list(
        self, client, admin_user_headers, sample_ownership
    ):
        """测试批量创建空列表"""
        response = client.post(
            f"/api/v1/contacts/batch/ownership/{sample_ownership.id}",
            json=[],
            headers=admin_user_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_batch_create_contacts_unauthorized(
        self, unauthenticated_client, sample_ownership
    ):
        """测试未授权批量创建"""
        contacts_data = [{"name": "测试", "phone": "13800138000"}]

        response = unauthenticated_client.post(
            f"/api/v1/contacts/batch/ownership/{sample_ownership.id}",
            json=contacts_data,
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


class TestContactAPIEdgeCases:
    """测试API边界情况和错误处理"""

    def test_contact_with_special_characters_in_name(
        self, client, admin_user_headers, sample_ownership
    ):
        """测试姓名中的特殊字符"""
        contact_data = {
            "name": "张三·李四-Wang",
            "phone": "13800138000",
            "entity_type": "ownership",
            "entity_id": sample_ownership.id,
        }

        response = client.post(
            "/api/v1/contacts/", json=contact_data, headers=admin_user_headers
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
            "title": "职位名称",
        }

        response = client.post(
            "/api/v1/contacts/", json=contact_data, headers=admin_user_headers
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
            "entity_id": sample_ownership.id,
        }

        response = client.post(
            "/api/v1/contacts/", json=contact_data, headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
