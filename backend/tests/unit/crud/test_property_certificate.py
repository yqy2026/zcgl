"""
产权证 CRUD 单元测试

测试 CRUDPropertyCertificate 和 CRUDPropertyOwner 的所有主要方法
"""

from unittest.mock import MagicMock, patch

import pytest

from src.crud.property_certificate import (
    CRUDPropertyCertificate,
    CRUDPropertyOwner,
    property_certificate_crud,
    property_owner_crud,
)
from src.models.property_certificate import PropertyCertificate, PropertyOwner


class TestCRUDPropertyOwnerCreate:
    """测试 PropertyOwner create 方法 - 敏感数据加密"""

    @pytest.fixture
    def crud(self):
        return CRUDPropertyOwner(PropertyOwner)

    @pytest.fixture
    def mock_db(self, db_session):
        db_session.add = MagicMock(wraps=db_session.add)
        db_session.commit = MagicMock(wraps=db_session.commit)
        db_session.refresh = MagicMock(wraps=db_session.refresh)
        return db_session

    def test_create_owner_encrypts_sensitive_fields(self, crud, mock_db):
        """测试创建权利人时加密敏感字段"""
        create_data = {
            "name": "张三",
            "id_number": "110101199001011234",
            "phone": "13800138000",
        }

        with patch.object(crud.sensitive_data_handler, "encrypt_data") as mock_encrypt:
            mock_encrypt.return_value = {
                "name": "张三",
                "id_number": "encrypted_id",
                "phone": "encrypted_phone",
            }
            with patch.object(
                CRUDPropertyOwner.__bases__[0], "create"
            ) as mock_base_create:
                mock_owner = MagicMock(spec=PropertyOwner)
                mock_base_create.return_value = mock_owner

                result = crud.create(mock_db, obj_in=create_data)

            mock_encrypt.assert_called_once_with(create_data)
            assert result is not None

    def test_create_owner_with_schema(self, crud, mock_db):
        """测试使用 Schema 创建权利人"""
        create_schema = MagicMock()
        create_schema.model_dump.return_value = {
            "name": "李四",
            "id_number": "110101199002021234",
            "phone": "13900139000",
        }

        with patch.object(crud.sensitive_data_handler, "encrypt_data") as mock_encrypt:
            mock_encrypt.return_value = create_schema.model_dump.return_value
            with patch.object(
                CRUDPropertyOwner.__bases__[0], "create"
            ) as mock_base_create:
                mock_owner = MagicMock(spec=PropertyOwner)
                mock_base_create.return_value = mock_owner

                result = crud.create(mock_db, obj_in=create_schema)

            assert result is not None


class TestCRUDPropertyOwnerGet:
    """测试 PropertyOwner get 方法 - 敏感数据解密"""

    @pytest.fixture
    def crud(self):
        return CRUDPropertyOwner(PropertyOwner)

    @pytest.fixture
    def mock_db(self, db_session):
        return db_session

    def test_get_owner_decrypts_sensitive_fields(self, crud, mock_db):
        """测试获取权利人时解密敏感字段"""
        mock_owner = MagicMock(spec=PropertyOwner)
        mock_owner.__dict__ = {
            "id": "owner-1",
            "name": "张三",
            "id_number": "encrypted_id",
            "phone": "encrypted_phone",
        }

        with patch.object(
            CRUDPropertyOwner.__bases__[0], "get", return_value=mock_owner
        ):
            with patch.object(
                crud.sensitive_data_handler, "decrypt_data"
            ) as mock_decrypt:
                result = crud.get(mock_db, id="owner-1")

            mock_decrypt.assert_called_once()
            assert result is not None

    def test_get_owner_not_found(self, crud, mock_db):
        """测试获取不存在的权利人"""
        with patch.object(CRUDPropertyOwner.__bases__[0], "get", return_value=None):
            result = crud.get(mock_db, id="not-exist")

        assert result is None


class TestCRUDPropertyOwnerGetMulti:
    """测试 PropertyOwner get_multi 方法"""

    @pytest.fixture
    def crud(self):
        return CRUDPropertyOwner(PropertyOwner)

    @pytest.fixture
    def mock_db(self, db_session):
        return db_session

    def test_get_multi_decrypts_all(self, crud, mock_db):
        """测试批量获取时解密所有记录"""
        mock_owners = [
            MagicMock(spec=PropertyOwner, __dict__={"id": "1", "id_number": "enc1"}),
            MagicMock(spec=PropertyOwner, __dict__={"id": "2", "id_number": "enc2"}),
        ]

        with patch.object(
            CRUDPropertyOwner.__bases__[0], "get_multi", return_value=mock_owners
        ):
            with patch.object(
                crud.sensitive_data_handler, "decrypt_data"
            ) as mock_decrypt:
                result = crud.get_multi(mock_db, skip=0, limit=10)

            assert mock_decrypt.call_count == 2
            assert len(result) == 2

    def test_get_multi_empty_list(self, crud, mock_db):
        """测试批量获取空列表"""
        with patch.object(
            CRUDPropertyOwner.__bases__[0], "get_multi", return_value=[]
        ):
            result = crud.get_multi(mock_db)

        assert result == []


class TestCRUDPropertyOwnerUpdate:
    """测试 PropertyOwner update 方法"""

    @pytest.fixture
    def crud(self):
        return CRUDPropertyOwner(PropertyOwner)

    @pytest.fixture
    def mock_db(self, db_session):
        return db_session

    def test_update_owner_encrypts_sensitive_fields(self, crud, mock_db):
        """测试更新时加密敏感字段"""
        mock_owner = MagicMock(spec=PropertyOwner)
        update_data = {"phone": "13700137000"}

        with patch.object(crud.sensitive_data_handler, "encrypt_data") as mock_encrypt:
            mock_encrypt.return_value = {"phone": "encrypted_new_phone"}
            with patch.object(
                CRUDPropertyOwner.__bases__[0], "update"
            ) as mock_base_update:
                mock_base_update.return_value = mock_owner

                result = crud.update(mock_db, db_obj=mock_owner, obj_in=update_data)

            mock_encrypt.assert_called_once_with(update_data)
            assert result is not None

    def test_update_owner_with_schema(self, crud, mock_db):
        """测试使用 Schema 更新权利人"""
        mock_owner = MagicMock(spec=PropertyOwner)
        update_schema = MagicMock()
        update_schema.model_dump.return_value = {"name": "新名字"}

        with patch.object(crud.sensitive_data_handler, "encrypt_data") as mock_encrypt:
            mock_encrypt.return_value = {"name": "新名字"}
            with patch.object(
                CRUDPropertyOwner.__bases__[0], "update"
            ) as mock_base_update:
                mock_base_update.return_value = mock_owner

                result = crud.update(mock_db, db_obj=mock_owner, obj_in=update_schema)

            assert result is not None


class TestCRUDPropertyOwnerSearchByIdNumber:
    """测试 PropertyOwner search_by_id_number 方法"""

    @pytest.fixture
    def crud(self):
        return CRUDPropertyOwner(PropertyOwner)

    @pytest.fixture
    def mock_db(self, db_session):
        db_session.query = MagicMock()
        return db_session

    def test_search_by_id_number_encrypts_query(self, crud, mock_db):
        """测试使用加密值搜索"""
        mock_owners = [MagicMock(spec=PropertyOwner, __dict__={"id": "1"})]
        mock_db.query.return_value.filter.return_value.offset.return_value.limit.return_value.all.return_value = (
            mock_owners
        )

        with patch.object(
            crud.sensitive_data_handler, "encrypt_field"
        ) as mock_encrypt_field:
            mock_encrypt_field.return_value = "encrypted_search_id"
            with patch.object(
                crud.sensitive_data_handler, "decrypt_data"
            ):
                result = crud.search_by_id_number(
                    mock_db, id_number="110101199001011234"
                )

            mock_encrypt_field.assert_called_once_with(
                "id_number", "110101199001011234"
            )
            assert len(result) == 1

    def test_search_by_id_number_not_found(self, crud, mock_db):
        """测试搜索不存在的证件号码"""
        mock_db.query.return_value.filter.return_value.offset.return_value.limit.return_value.all.return_value = (
            []
        )

        with patch.object(
            crud.sensitive_data_handler, "encrypt_field"
        ) as mock_encrypt_field:
            mock_encrypt_field.return_value = "encrypted_search_id"
            result = crud.search_by_id_number(mock_db, id_number="not-exist")

        assert result == []


class TestCRUDPropertyCertificateGetByCertificateNumber:
    """测试 PropertyCertificate get_by_certificate_number 方法"""

    @pytest.fixture
    def crud(self):
        return CRUDPropertyCertificate(PropertyCertificate)

    @pytest.fixture
    def mock_db(self, db_session):
        db_session.query = MagicMock()
        return db_session

    def test_get_by_certificate_number_exists(self, crud, mock_db):
        """测试根据证书编号获取存在的产权证"""
        mock_cert = MagicMock(spec=PropertyCertificate)
        mock_cert.certificate_number = "CERT-001"

        mock_db.query.return_value.filter.return_value.first.return_value = mock_cert

        result = crud.get_by_certificate_number(mock_db, certificate_number="CERT-001")

        assert result is not None
        assert result.certificate_number == "CERT-001"

    def test_get_by_certificate_number_not_exists(self, crud, mock_db):
        """测试根据证书编号获取不存在的产权证"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = crud.get_by_certificate_number(
            mock_db, certificate_number="NOT-EXIST"
        )

        assert result is None


class TestCRUDPropertyCertificateCreateWithOwners:
    """测试 PropertyCertificate create_with_owners 方法"""

    @pytest.fixture
    def crud(self):
        return CRUDPropertyCertificate(PropertyCertificate)

    @pytest.fixture
    def mock_db(self, db_session):
        db_session.add = MagicMock(wraps=db_session.add)
        db_session.flush = MagicMock(wraps=db_session.flush)
        db_session.commit = MagicMock(wraps=db_session.commit)
        db_session.refresh = MagicMock(wraps=db_session.refresh)
        db_session.query = MagicMock()
        return db_session

    def test_create_with_owners(self, crud, mock_db):
        """测试创建产权证并关联权利人"""
        create_data = MagicMock()
        create_data.model_dump.return_value = {
            "certificate_number": "CERT-002",
            "property_address": "北京市朝阳区",
        }

        mock_owner = MagicMock(spec=PropertyOwner)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_owner

        with patch.object(PropertyCertificate, "__init__", return_value=None):
            with patch.object(PropertyCertificate, "owners", []):
                # 模拟创建行为
                result = MagicMock(spec=PropertyCertificate)
                result.owners = []

                with patch("src.crud.property_certificate.PropertyCertificate") as mock_cert_class:
                    mock_cert_class.return_value = result
                    mock_cert_class.return_value.owners = []

                    crud.create_with_owners(
                        mock_db, obj_in=create_data, owner_ids=["owner-1"]
                    )

        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_create_without_owners(self, crud, mock_db):
        """测试创建产权证不关联权利人"""
        create_data = MagicMock()
        create_data.model_dump.return_value = {
            "certificate_number": "CERT-003",
        }

        with patch("src.crud.property_certificate.PropertyCertificate") as mock_cert_class:
            mock_cert = MagicMock(spec=PropertyCertificate)
            mock_cert.owners = []
            mock_cert_class.return_value = mock_cert

            crud.create_with_owners(mock_db, obj_in=create_data, owner_ids=None)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()


class TestCRUDInstances:
    """测试 CRUD 实例"""

    def test_property_certificate_crud_instance(self):
        """测试产权证 CRUD 实例"""
        assert property_certificate_crud is not None
        assert isinstance(property_certificate_crud, CRUDPropertyCertificate)

    def test_property_owner_crud_instance(self):
        """测试权利人 CRUD 实例"""
        assert property_owner_crud is not None
        assert isinstance(property_owner_crud, CRUDPropertyOwner)
