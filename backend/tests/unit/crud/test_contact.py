"""
联系人 CRUD 操作单元测试
"""

from unittest.mock import MagicMock, patch

import pytest

from src.crud.contact import ContactCRUD, contact_crud
from src.models.contact import Contact, ContactType


@pytest.fixture
def crud():
    """创建 CRUD 实例"""
    return ContactCRUD()


@pytest.fixture
def mock_contact():
    """模拟联系人对象"""
    # Create a simple object instead of MagicMock to avoid _mock_methods issues
    from types import SimpleNamespace

    contact = SimpleNamespace(
        id="contact_123",
        entity_type="asset",
        entity_id="asset_123",
        name="张三",
        phone="13800138000",
        office_phone="010-12345678",
        is_primary=True,
        is_active=True,
        contact_type=ContactType.PRIMARY,
    )
    return contact


# ============================================================================
# ContactCRUD.get 测试
# ============================================================================
class TestGet:
    """测试获取单个联系人"""

    def test_get_success(self, crud, mock_db, mock_contact):
        """测试成功获取联系人"""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_contact

        with patch.object(crud.sensitive_data_handler, "decrypt_data"):
            result = crud.get(mock_db, "contact_123")

        assert result == mock_contact
        mock_db.query.assert_called_once_with(Contact)

    def test_get_not_found(self, crud, mock_db):
        """测试联系人不存在"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = crud.get(mock_db, "nonexistent")

        assert result is None

    def test_get_decrypts_sensitive_data(self, crud, mock_db, mock_contact):
        """测试获取时解密敏感数据"""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_contact

        with patch.object(crud.sensitive_data_handler, "decrypt_data") as mock_decrypt:
            crud.get(mock_db, "contact_123")
            mock_decrypt.assert_called_once()


# ============================================================================
# ContactCRUD.get_multi 测试
# ============================================================================
class TestGetMulti:
    """测试获取多个联系人"""

    def test_get_multi_success(self, crud, mock_db, mock_contact):
        """测试成功获取联系人列表"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [mock_contact]

        with patch.object(crud.sensitive_data_handler, "decrypt_data"):
            contacts, total = crud.get_multi(mock_db, "asset", "asset_123")

        assert len(contacts) == 1
        assert total == 1

    def test_get_multi_with_pagination(self, crud, mock_db):
        """测试带分页的列表查询"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        contacts, total = crud.get_multi(
            mock_db, "asset", "asset_123", skip=10, limit=20
        )

        mock_query.offset.assert_called_with(10)
        mock_query.limit.assert_called_with(20)

    def test_get_multi_empty_result(self, crud, mock_db):
        """测试空结果"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        contacts, total = crud.get_multi(mock_db, "asset", "asset_123")

        assert contacts == []
        assert total == 0


# ============================================================================
# ContactCRUD.get_primary 测试
# ============================================================================
class TestGetPrimary:
    """测试获取主要联系人"""

    def test_get_primary_success(self, crud, mock_db, mock_contact):
        """测试成功获取主要联系人"""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_contact

        with patch.object(crud.sensitive_data_handler, "decrypt_data"):
            result = crud.get_primary(mock_db, "asset", "asset_123")

        assert result == mock_contact

    def test_get_primary_not_found(self, crud, mock_db):
        """测试没有主要联系人"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = crud.get_primary(mock_db, "asset", "asset_123")

        assert result is None


# ============================================================================
# ContactCRUD.create 测试
# ============================================================================
class TestCreate:
    """测试创建联系人"""

    def test_create_success(self, crud, mock_db):
        """测试成功创建联系人"""
        contact_data = {
            "entity_type": "asset",
            "entity_id": "asset_123",
            "name": "张三",
            "phone": "13800138000",
            "is_primary": False,
        }

        with patch.object(
            crud.sensitive_data_handler, "encrypt_data", return_value=contact_data
        ):
            with patch.object(crud.sensitive_data_handler, "decrypt_data"):
                crud.create(mock_db, contact_data)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_create_as_primary_clears_other_primary(self, crud, mock_db):
        """测试创建为主要联系人时清除其他主要联系人"""
        contact_data = {
            "entity_type": "asset",
            "entity_id": "asset_123",
            "name": "张三",
            "phone": "13800138000",
            "is_primary": True,
        }

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query

        with patch.object(
            crud.sensitive_data_handler, "encrypt_data", return_value=contact_data
        ):
            with patch.object(crud.sensitive_data_handler, "decrypt_data"):
                crud.create(mock_db, contact_data)

        # 验证更新了其他主要联系人
        mock_query.update.assert_called_once()

    def test_create_encrypts_sensitive_data(self, crud, mock_db):
        """测试创建时加密敏感数据"""
        contact_data = {
            "entity_type": "asset",
            "entity_id": "asset_123",
            "name": "张三",
            "phone": "13800138000",
        }

        with patch.object(crud.sensitive_data_handler, "encrypt_data") as mock_encrypt:
            mock_encrypt.return_value = contact_data
            with patch.object(crud.sensitive_data_handler, "decrypt_data"):
                crud.create(mock_db, contact_data)

            mock_encrypt.assert_called_once()


# ============================================================================
# ContactCRUD.update 测试
# ============================================================================
class TestUpdate:
    """测试更新联系人"""

    def test_update_success(self, crud, mock_db, mock_contact):
        """测试成功更新联系人"""
        update_data = {"name": "李四"}

        with patch.object(crud.sensitive_data_handler, "decrypt_data"):
            result = crud.update(mock_db, mock_contact, update_data)

        mock_db.commit.assert_called_once()
        assert result == mock_contact

    def test_update_to_primary_clears_other_primary(self, crud, mock_db, mock_contact):
        """测试更新为主要联系人时清除其他主要联系人"""
        mock_contact.is_primary = False
        update_data = {"is_primary": True}

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query

        with patch.object(crud.sensitive_data_handler, "decrypt_data"):
            crud.update(mock_db, mock_contact, update_data)

        mock_query.update.assert_called_once()


# ============================================================================
# ContactCRUD.delete 测试
# ============================================================================
class TestDelete:
    """测试删除联系人"""

    def test_delete_success(self, crud, mock_db, mock_contact):
        """测试成功软删除联系人"""
        with patch.object(crud, "get", return_value=mock_contact):
            result = crud.delete(mock_db, "contact_123")

        mock_db.commit.assert_called_once()
        assert result == mock_contact

    def test_delete_not_found(self, crud, mock_db):
        """测试删除不存在的联系人"""
        with patch.object(crud, "get", return_value=None):
            result = crud.delete(mock_db, "nonexistent")

        assert result is None


# ============================================================================
# ContactCRUD.get_multi_by_type 测试
# ============================================================================
class TestGetMultiByType:
    """测试批量获取联系人"""

    def test_get_multi_by_type_success(self, crud, mock_db, mock_contact):
        """测试成功批量获取联系人"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [mock_contact]

        with patch.object(crud.sensitive_data_handler, "decrypt_data"):
            results = crud.get_multi_by_type(
                mock_db, "asset", ["asset_123", "asset_456"]
            )

        assert len(results) == 1

    def test_get_multi_by_type_with_contact_type(self, crud, mock_db, mock_contact):
        """测试按联系人类型筛选"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [mock_contact]

        with patch.object(crud.sensitive_data_handler, "decrypt_data"):
            results = crud.get_multi_by_type(
                mock_db,
                "asset",
                ["asset_123"],
                contact_type=ContactType.PRIMARY,  # Use valid ContactType
            )

        assert len(results) == 1


# ============================================================================
# 全局实例测试
# ============================================================================
class TestGlobalInstance:
    """测试全局实例"""

    def test_contact_crud_instance_exists(self):
        """测试全局实例存在"""
        assert contact_crud is not None
        assert isinstance(contact_crud, ContactCRUD)
