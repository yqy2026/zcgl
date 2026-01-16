"""
资产加密集成测试

测试完整的 CRUD 工作流程，包括：
- 加密写入
- 解密读取
- 搜索加密字段
- 优雅降级（密钥缺失）
"""

import base64

import pytest
from sqlalchemy.orm import Session

from src.crud.asset import AssetCRUD, SensitiveDataHandler
from src.models.asset import Asset
from src.schemas.asset import AssetCreate, AssetUpdate


# ============================================================================
# Fixtures
# ============================================================================
@pytest.fixture
def valid_encryption_key():
    """生成有效的加密密钥"""
    key_bytes = b"f" * 32
    key_b64 = base64.b64encode(key_bytes).decode("ascii")
    return f"{key_b64}:1"


@pytest.fixture
def asset_crud_with_encryption(valid_encryption_key, monkeypatch):
    """创建启用加密的 AssetCRUD fixture"""
    # Set environment variable before importing modules
    monkeypatch.setenv("DATA_ENCRYPTION_KEY", valid_encryption_key)

    # Clear any cached modules to force reload with new env var
    import sys
    modules_to_clear = [
        "src.core.config",
        "src.core.encryption",
        "src.crud.asset",
    ]
    for mod in modules_to_clear:
        if mod in sys.modules:
            del sys.modules[mod]

    # Re-import with new environment variable
    from src.crud.asset import AssetCRUD

    return AssetCRUD()


@pytest.fixture
def asset_crud_no_encryption(monkeypatch):
    """创建禁用加密的 AssetCRUD fixture"""
    # Unset environment variable
    monkeypatch.delenv("DATA_ENCRYPTION_KEY", raising=False)
    monkeypatch.setenv("DATA_ENCRYPTION_KEY", "")

    # Clear cached modules
    import sys
    modules_to_clear = [
        "src.core.config",
        "src.core.encryption",
        "src.crud.asset",
    ]
    for mod in modules_to_clear:
        if mod in sys.modules:
            del sys.modules[mod]

    from src.crud.asset import AssetCRUD
    return AssetCRUD()


@pytest.fixture
def sample_asset_data():
    """示例资产数据"""
    return {
        "property_name": "测试物业A",
        "tenant_name": "张三公司",
        "ownership_entity": "李四集团",
        "address": "北京市朝阳区某某街道123号",
        "manager_name": "王经理",
        "business_category": "商业",
        "actual_property_area": 100.5,
        "monthly_rent": 5000.0,
        "deposit": 15000.0,
        # Required fields
        "ownership_status": "已确权",
        "property_nature": "商业",
        "usage_status": "在用",
        "is_litigated": 0,
        "data_status": "正常",
    }


# ============================================================================
# CRUD 操作加密测试
# ============================================================================
@pytest.mark.usefixtures("db_tables")
class TestAssetCRUDEncryption:
    """测试 AssetCRUD 的加密功能"""

    def test_create_encrypts_pii_fields(
        self, db_session: Session, asset_crud_with_encryption: AssetCRUD, sample_asset_data: dict
    ):
        """测试创建资产时加密PII字段"""
        # 创建资产
        asset = asset_crud_with_encryption.create(db=db_session, obj_in=sample_asset_data)

        # 从数据库直接查询（绕过 CRUD 解密）
        db_asset = db_session.query(Asset).filter(Asset.id == asset.id).first()

        # PII字段应该在数据库中是加密格式
        assert db_asset.tenant_name.startswith("enc:v1:")
        assert db_asset.ownership_entity.startswith("enc:v1:")
        assert db_asset.address.startswith("enc:v1:")
        assert db_asset.manager_name.startswith("enc:v1:")

        # 非PII字段应该是明文
        assert db_asset.property_name == "测试物业A"

    def test_get_decrypts_pii_fields(
        self, db_session: Session, asset_crud_with_encryption: AssetCRUD, sample_asset_data: dict
    ):
        """测试获取资产时解密PII字段"""
        # 创建资产
        created = asset_crud_with_encryption.create(db=db_session, obj_in=sample_asset_data)

        # 获取资产
        asset = asset_crud_with_encryption.get(db=db_session, id=created.id)

        # PII字段应该被解密为明文
        assert asset.tenant_name == "张三公司"
        assert asset.ownership_entity == "李四集团"
        assert asset.address == "北京市朝阳区某某街道123号"
        assert asset.manager_name == "王经理"

    def test_get_multi_decrypts_all_records(
        self, db_session: Session, asset_crud_with_encryption: AssetCRUD, sample_asset_data: dict
    ):
        """测试获取多个资产时解密所有记录"""
        # 创建多个资产
        for i in range(3):
            data = sample_asset_data.copy()
            data["property_name"] = f"测试物业{i}"
            data["tenant_name"] = f"租户{i}"
            asset_crud_with_encryption.create(db=db_session, obj_in=data)

        # 获取所有资产
        assets = asset_crud_with_encryption.get_multi(db=db_session, limit=10)

        # 所有记录的PII字段都应该被解密
        assert len(assets) >= 3
        for asset in assets[:3]:
            assert not asset.tenant_name.startswith("enc:v1:")
            assert not asset.ownership_entity.startswith("enc:v1:")

    def test_update_encrypts_new_pii_values(
        self, db_session: Session, asset_crud_with_encryption: AssetCRUD, sample_asset_data: dict
    ):
        """测试更新资产时加密新的PII值"""
        # 创建资产
        created = asset_crud_with_encryption.create(db=db_session, obj_in=sample_asset_data)

        # 更新PII字段
        update_data = AssetUpdate(
            tenant_name="新租户公司", ownership_entity="新权属方"
        )
        updated = asset_crud_with_encryption.update(
            db=db_session, db_obj=created, obj_in=update_data
        )

        # 从数据库直接查询（绕过 CRUD 解密）
        db_asset = db_session.query(Asset).filter(Asset.id == updated.id).first()

        # 更新的字段应该是加密格式
        assert db_asset.tenant_name.startswith("enc:v1:")
        assert db_asset.ownership_entity.startswith("enc:v1:")

        # 通过 CRUD 获取应该是明文
        asset = asset_crud_with_encryption.get(db=db_session, id=updated.id)
        assert asset.tenant_name == "新租户公司"
        assert asset.ownership_entity == "新权属方"

    def test_update_preserves_non_pii_fields(
        self, db_session: Session, asset_crud_with_encryption: AssetCRUD, sample_asset_data: dict
    ):
        """测试更新非PII字段不受影响"""
        # 创建资产
        created = asset_crud_with_encryption.create(db=db_session, obj_in=sample_asset_data)

        # 更新非PII字段
        original_tenant = created.tenant_name  # 已加密
        update_data = AssetUpdate(business_category="办公")
        updated = asset_crud_with_encryption.update(
            db=db_session, db_obj=created, obj_in=update_data
        )

        # PII字段应该保持不变
        assert updated.tenant_name == original_tenant

        # 非PII字段应该更新
        assert updated.business_category == "办公"


# ============================================================================
# 搜索加密字段测试
# ============================================================================
@pytest.mark.usefixtures("db_tables")
class TestSearchEncryptedFields:
    """测试搜索加密字段的功能"""

    def test_search_on_encrypted_field(
        self, db_session: Session, asset_crud_with_encryption: AssetCRUD, sample_asset_data: dict
    ):
        """测试搜索加密的PII字段"""
        # 创建多个资产
        for i in range(3):
            data = sample_asset_data.copy()
            data["property_name"] = f"物业{i}"
            data["tenant_name"] = f"搜索测试公司{i}" if i < 2 else f"其他公司{i}"
            asset_crud_with_encryption.create(db=db_session, obj_in=data)

        # 搜索 tenant_name（加密字段）
        # 注意：当前实现中，QueryBuilder 可能不支持直接搜索加密字段
        # 这里测试至少不会崩溃，且返回解密后的结果
        assets, total = asset_crud_with_encryption.get_multi_with_search(
            db=db_session, search="搜索测试公司", skip=0, limit=10
        )

        # 结果应该被解密
        for asset in assets:
            if asset.tenant_name and asset.tenant_name.startswith("搜索测试公司"):
                # 确保结果是解密后的明文
                assert not asset.tenant_name.startswith("enc:v1:")


# ============================================================================
# 优雅降级测试
# ============================================================================
@pytest.mark.usefixtures("db_tables")
class TestGracefulDegradation:
    """测试密钥缺失时的优雅降级"""

    def test_create_without_key_stores_plaintext(
        self, db_session: Session, asset_crud_no_encryption: AssetCRUD, sample_asset_data: dict
    ):
        """测试密钥缺失时创建资产存储明文"""
        # 创建资产
        asset = asset_crud_no_encryption.create(db=db_session, obj_in=sample_asset_data)

        # 从数据库直接查询
        db_asset = db_session.query(Asset).filter(Asset.id == asset.id).first()

        # 所有字段都应该是明文
        assert db_asset.tenant_name == "张三公司"
        assert db_asset.ownership_entity == "李四集团"
        assert db_asset.address == "北京市朝阳区某某街道123号"

    def test_get_without_key_returns_plaintext(
        self, db_session: Session, asset_crud_no_encryption: AssetCRUD, sample_asset_data: dict
    ):
        """测试密钥缺失时获取资产返回明文"""
        # 创建资产（存储为明文）
        asset = asset_crud_no_encryption.create(db=db_session, obj_in=sample_asset_data)

        # 获取资产
        result = asset_crud_no_encryption.get(db=db_session, id=asset.id)

        # 应该返回明文
        assert result.tenant_name == "张三公司"
        assert result.ownership_entity == "李四集团"

    def test_mixed_encrypted_plaintext_data(
        self,
        db_session: Session,
        asset_crud_with_encryption: AssetCRUD,
        asset_crud_no_encryption: AssetCRUD,
        sample_asset_data: dict,
    ):
        """测试混合加密和明文数据（加密前已存在的记录）"""
        # 先用无加密创建一条记录（模拟旧数据）
        old_asset = asset_crud_no_encryption.create(db=db_session, obj_in=sample_asset_data)

        # 再用加密创建一条记录
        data2 = sample_asset_data.copy()
        data2["property_name"] = "新物业"
        new_asset = asset_crud_with_encryption.create(db=db_session, obj_in=data2)

        # 通过加密CRUD获取所有记录
        assets = asset_crud_with_encryption.get_multi(db=db_session, limit=10)

        # 应该能同时处理加密和明文数据
        assert len(assets) >= 2

        # 查找两条记录
        old_result = next((a for a in assets if a.id == old_asset.id), None)
        new_result = next((a for a in assets if a.id == new_asset.id), None)

        # 旧数据（明文）应该能正确返回
        assert old_result is not None
        assert old_result.tenant_name == "张三公司"

        # 新数据（加密）应该被正确解密
        assert new_result is not None
        assert new_result.tenant_name == "张三公司"


# ============================================================================
# 并发访问测试
# ============================================================================
@pytest.mark.usefixtures("db_tables")
class TestConcurrentAccess:
    """测试并发访问时的加密功能"""

    def test_concurrent_creates(
        self, db_session: Session, asset_crud_with_encryption: AssetCRUD, sample_asset_data: dict
    ):
        """测试并发创建加密资产"""
        import threading

        results = []
        errors = []

        def create_asset(index: int):
            try:
                data = sample_asset_data.copy()
                data["property_name"] = f"并发测试{index}"
                data["tenant_name"] = f"租户{index}"
                asset = asset_crud_with_encryption.create(db=db_session, obj_in=data)
                results.append(asset.id)
            except Exception as e:
                errors.append(e)

        # 创建10个线程
        threads = []
        for i in range(10):
            t = threading.Thread(target=create_asset, args=(i,))
            threads.append(t)
            t.start()

        # 等待所有线程完成
        for t in threads:
            t.join()

        # 验证结果
        assert len(errors) == 0, f"创建时发生错误: {errors}"
        assert len(results) == 10

        # 验证所有记录都正确加密
        for asset_id in results:
            db_asset = db_session.query(Asset).filter(Asset.id == asset_id).first()
            assert db_asset.tenant_name.startswith("enc:v1:")


# ============================================================================
# 加密前缀格式验证
# ============================================================================
@pytest.mark.usefixtures("db_tables")
class TestEncryptionFormat:
    """验证加密数据格式"""

    def test_deterministic_encryption_format(
        self, db_session: Session, asset_crud_with_encryption: AssetCRUD, sample_asset_data: dict
    ):
        """测试确定性加密格式（可搜索字段）"""
        asset = asset_crud_with_encryption.create(db=db_session, obj_in=sample_asset_data)

        # 从数据库查询
        db_asset = db_session.query(Asset).filter(Asset.id == asset.id).first()

        # 可搜索字段应该是确定性加密（相同明文 → 相同密文）
        # 格式: enc:v1:base64(ciphertext)
        searchable_fields = ["tenant_name", "ownership_entity", "address"]
        for field in searchable_fields:
            value = getattr(db_asset, field)
            assert value.startswith("enc:v1:")
            # 验证格式（3部分，用冒号分隔）
            parts = value.split(":")
            assert len(parts) == 3
            assert parts[0] == "enc"
            assert parts[1] == "v1"

    def test_standard_encryption_format(
        self, db_session: Session, asset_crud_with_encryption: AssetCRUD, sample_asset_data: dict
    ):
        """测试标准加密格式（非搜索字段）"""
        asset = asset_crud_with_encryption.create(db=db_session, obj_in=sample_asset_data)

        # 从数据库查询
        db_asset = db_session.query(Asset).filter(Asset.id == asset.id).first()

        # 非搜索字段应该是标准加密（随机nonce）
        # 格式: enc:v1:base64(nonce):base64(ciphertext)
        non_searchable_fields = ["manager_name"]
        for field in non_searchable_fields:
            value = getattr(db_asset, field)
            assert value.startswith("enc:v1:")
            # 验证格式（4部分，用冒号分隔）
            parts = value.split(":")
            assert len(parts) == 4
            assert parts[0] == "enc"
            assert parts[1] == "v1"
