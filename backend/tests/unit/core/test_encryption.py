"""
加密模块单元测试

测试 EncryptionKeyManager, FieldEncryptor, 和 SensitiveDataHandler 的功能
"""

import base64
from unittest.mock import patch

import pytest

from src.core.encryption import (
    EncryptionKeyManager,
    FieldEncryptor,
    generate_encryption_key,
)


# ============================================================================
# EncryptionKeyManager 测试
# ============================================================================

@pytest.fixture(autouse=True)
def reset_encryption_modules(monkeypatch):
    """
    Auto-used fixture to reset encryption-related modules before each test.
    This prevents test isolation issues when other tests set DATA_ENCRYPTION_KEY.
    """
    # Remove DATA_ENCRYPTION_KEY from environment
    monkeypatch.delenv("DATA_ENCRYPTION_KEY", raising=False)

    # Clear cached modules to force reload
    import sys
    modules_to_clear = [
        "src.core.config",
        "src.core.encryption",
    ]
    for mod in modules_to_clear:
        if mod in sys.modules:
            del sys.modules[mod]

    yield

    # Cleanup after test
    for mod in modules_to_clear:
        if mod in sys.modules:
            del sys.modules[mod]


class TestEncryptionKeyManager:
    """测试密钥管理器的加载、验证和版本管理功能"""

    def test_load_valid_key_with_version(self, monkeypatch):
        """测试加载带版本号的有效密钥"""
        # Clear any cached modules first
        import sys
        for mod in list(sys.modules.keys()):
            if "src.core.config" in mod or "src.core.encryption" in mod:
                del sys.modules[mod]

        # 生成一个有效的密钥
        key_bytes = b"a" * 32  # 32字节密钥
        key_b64 = base64.b64encode(key_bytes).decode("ascii")
        test_key = f"{key_b64}:1"

        # Set environment variable
        monkeypatch.setenv("DATA_ENCRYPTION_KEY", test_key)

        # Import fresh and patch settings directly
        from src.core import config
        from src.core.encryption import EncryptionKeyManager

        # Use monkeypatch to persist the value for the entire test
        monkeypatch.setattr(config.settings, 'DATA_ENCRYPTION_KEY', test_key)

        manager = EncryptionKeyManager()

        assert manager.is_available() is True
        assert manager.get_version() == 1
        assert manager.get_key() == key_bytes

    def test_load_valid_key_without_version(self, monkeypatch):
        """测试加载不带版本号的有效密钥（默认版本1）"""
        # Clear any cached modules first
        import sys
        for mod in list(sys.modules.keys()):
            if "src.core.config" in mod or "src.core.encryption" in mod:
                del sys.modules[mod]

        key_bytes = b"b" * 32
        key_b64 = base64.b64encode(key_bytes).decode("ascii")

        # Set environment variable
        monkeypatch.setenv("DATA_ENCRYPTION_KEY", key_b64)

        # Import fresh and patch settings directly
        from src.core import config
        from src.core.encryption import EncryptionKeyManager

        # Use monkeypatch to persist the value for the entire test
        monkeypatch.setattr(config.settings, 'DATA_ENCRYPTION_KEY', key_b64)

        manager = EncryptionKeyManager()

        assert manager.is_available() is True
        assert manager.get_version() == 1
        assert manager.get_key() == key_bytes

    def test_load_invalid_base64_key(self, monkeypatch):
        """测试加载无效的base64密钥"""
        # Clear any cached modules first
        import sys
        for mod in list(sys.modules.keys()):
            if "src.core.config" in mod or "src.core.encryption" in mod:
                del sys.modules[mod]

        # Set environment variable
        monkeypatch.setenv("DATA_ENCRYPTION_KEY", "not-valid-base64:1")

        # Import fresh and patch settings directly
        from src.core import config
        from src.core.encryption import EncryptionKeyManager

        # Use monkeypatch to persist the value for the entire test
        monkeypatch.setattr(config.settings, 'DATA_ENCRYPTION_KEY', "not-valid-base64:1")

        manager = EncryptionKeyManager()

        assert manager.is_available() is False
        assert manager.get_key() is None

    def test_load_short_key(self, monkeypatch):
        """测试加载过短的密钥（< 32字节）"""
        # Clear any cached modules first
        import sys
        for mod in list(sys.modules.keys()):
            if "src.core.config" in mod or "src.core.encryption" in mod:
                del sys.modules[mod]

        key_bytes = b"short"  # 5字节，不足32字节
        key_b64 = base64.b64encode(key_bytes).decode("ascii")

        # Set environment variable
        monkeypatch.setenv("DATA_ENCRYPTION_KEY", key_b64)

        # Import fresh and patch settings directly
        from src.core import config
        from src.core.encryption import EncryptionKeyManager

        # Use monkeypatch to persist the value for the entire test
        monkeypatch.setattr(config.settings, 'DATA_ENCRYPTION_KEY', key_b64)

        manager = EncryptionKeyManager()

        assert manager.is_available() is False
        assert manager.get_key() is None

    def test_load_missing_key(self, monkeypatch):
        """测试密钥缺失的情况"""
        # Remove environment variable completely
        monkeypatch.delenv("DATA_ENCRYPTION_KEY", raising=False)

        # Clear all cached modules to force reload
        import sys
        for mod in list(sys.modules.keys()):
            if "src.core.config" in mod or "src.core.encryption" in mod:
                del sys.modules[mod]

        # Import modules fresh - settings will read from environment (which is now deleted)
        from src.core import config
        from src.core.encryption import EncryptionKeyManager

        # Use monkeypatch to persist the empty value for the entire test
        monkeypatch.setattr(config.settings, 'DATA_ENCRYPTION_KEY', "")

        manager = EncryptionKeyManager()

        assert manager.is_available() is False
        assert manager.get_key() is None

    def test_extract_version_v2(self, monkeypatch):
        """测试提取版本号2"""
        # Clear modules first
        import sys
        for mod in list(sys.modules.keys()):
            if "src.core.config" in mod or "src.core.encryption" in mod:
                del sys.modules[mod]

        key_bytes = b"c" * 32
        key_b64 = base64.b64encode(key_bytes).decode("ascii")
        test_key = f"{key_b64}:2"

        # Set environment variable
        monkeypatch.setenv("DATA_ENCRYPTION_KEY", test_key)

        # Import fresh and patch settings directly
        from src.core import config
        from src.core.encryption import EncryptionKeyManager

        # Use monkeypatch to persist the value for the entire test
        monkeypatch.setattr(config.settings, 'DATA_ENCRYPTION_KEY', test_key)

        manager = EncryptionKeyManager()

        assert manager.get_version() == 2


# ============================================================================
# FieldEncryptor 测试
# ============================================================================

@pytest.fixture(autouse=True)
def reset_encryption_modules_for_field(monkeypatch):
    """
    Auto-used fixture to reset encryption-related modules before each test.
    This prevents test isolation issues when other tests set DATA_ENCRYPTION_KEY.
    """
    # Remove DATA_ENCRYPTION_KEY from environment
    monkeypatch.delenv("DATA_ENCRYPTION_KEY", raising=False)

    # Clear cached modules to force reload
    import sys
    modules_to_clear = [
        "src.core.config",
        "src.core.encryption",
    ]
    for mod in modules_to_clear:
        if mod in sys.modules:
            del sys.modules[mod]

    yield

    # Cleanup after test
    for mod in modules_to_clear:
        if mod in sys.modules:
            del sys.modules[mod]


class TestFieldEncryptor:
    """测试字段加密器的加密和解密功能"""

    @pytest.fixture
    def valid_key_manager(self, monkeypatch):
        """创建有效的密钥管理器fixture"""
        # Clear cached modules first
        import sys
        for mod in list(sys.modules.keys()):
            if "src.core.config" in mod or "src.core.encryption" in mod:
                del sys.modules[mod]

        key_bytes = b"d" * 32
        key_b64 = base64.b64encode(key_bytes).decode("ascii")
        test_key = f"{key_b64}:1"

        # Set environment variable
        monkeypatch.setenv("DATA_ENCRYPTION_KEY", test_key)

        # Import fresh and patch settings directly
        from src.core import config
        from src.core.encryption import EncryptionKeyManager

        # Use monkeypatch to persist the value for the entire test
        monkeypatch.setattr(config.settings, 'DATA_ENCRYPTION_KEY', test_key)

        manager = EncryptionKeyManager()
        return manager

    @pytest.fixture
    def missing_key_manager(self, monkeypatch):
        """创建缺失密钥的管理器fixture"""
        # Remove environment variable completely
        monkeypatch.delenv("DATA_ENCRYPTION_KEY", raising=False)

        # Clear cached modules to force reload
        import sys
        modules_to_clear = [
            "src.core.config",
            "src.core.encryption",
        ]
        for mod in modules_to_clear:
            if mod in sys.modules:
                del sys.modules[mod]

        # Import modules fresh - settings will read from environment (which is now deleted)
        from src.core import config
        from src.core.encryption import EncryptionKeyManager

        # Use monkeypatch to persist the empty value for the entire test
        monkeypatch.setattr(config.settings, 'DATA_ENCRYPTION_KEY', "")

        manager = EncryptionKeyManager()
        return manager

    def test_deterministic_encryption_same_plaintext(self, valid_key_manager):
        """测试确定性加密：相同明文产生相同密文"""
        encryptor = FieldEncryptor(valid_key_manager)
        plaintext = "张三公司"

        ciphertext1 = encryptor.encrypt_deterministic(plaintext)
        ciphertext2 = encryptor.encrypt_deterministic(plaintext)

        assert ciphertext1 is not None
        assert ciphertext2 is not None
        assert ciphertext1 == ciphertext2  # 相同明文产生相同密文
        assert ciphertext1.startswith("enc:v1:")

    def test_deterministic_encryption_different_plaintext(self, valid_key_manager):
        """测试确定性加密：不同明文产生不同密文"""
        encryptor = FieldEncryptor(valid_key_manager)

        ciphertext1 = encryptor.encrypt_deterministic("张三公司")
        ciphertext2 = encryptor.encrypt_deterministic("李四公司")

        assert ciphertext1 != ciphertext2

    def test_standard_encryption_randomness(self, valid_key_manager):
        """测试标准加密：相同明文产生不同密文（随机nonce）"""
        encryptor = FieldEncryptor(valid_key_manager)
        plaintext = "王五"

        ciphertext1 = encryptor.encrypt_standard(plaintext)
        ciphertext2 = encryptor.encrypt_standard(plaintext)

        assert ciphertext1 is not None
        assert ciphertext2 is not None
        assert ciphertext1 != ciphertext2  # 不同nonce产生不同密文
        assert ciphertext1.startswith("enc:v1:")
        assert ciphertext2.startswith("enc:v1:")

    def test_encrypt_decrypt_roundtrip_deterministic(self, valid_key_manager):
        """测试确定性加密的加密解密往返"""
        encryptor = FieldEncryptor(valid_key_manager)
        plaintext = "朝阳区物业"

        ciphertext = encryptor.encrypt_deterministic(plaintext)
        decrypted = encryptor.decrypt_deterministic(ciphertext)

        assert decrypted == plaintext

    def test_encrypt_decrypt_roundtrip_standard(self, valid_key_manager):
        """测试标准加密的加密解密往返"""
        encryptor = FieldEncryptor(valid_key_manager)
        plaintext = "张经理"

        ciphertext = encryptor.encrypt_standard(plaintext)
        decrypted = encryptor.decrypt_standard(ciphertext)

        assert decrypted == plaintext

    def test_encrypt_none_returns_none(self, valid_key_manager):
        """测试加密None值返回None"""
        encryptor = FieldEncryptor(valid_key_manager)

        assert encryptor.encrypt_deterministic(None) is None
        assert encryptor.encrypt_standard(None) is None

    def test_decrypt_none_returns_none(self, valid_key_manager):
        """测试解密None值返回None"""
        encryptor = FieldEncryptor(valid_key_manager)

        assert encryptor.decrypt_deterministic(None) is None
        assert encryptor.decrypt_standard(None) is None

    def test_decrypt_non_encrypted_format(self, valid_key_manager):
        """测试解密非加密格式的值返回原值"""
        encryptor = FieldEncryptor(valid_key_manager)

        plaintext = "not-encrypted-value"
        decrypted = encryptor.decrypt_deterministic(plaintext)

        assert decrypted == plaintext

    def test_decrypt_invalid_format_returns_original(self, valid_key_manager):
        """测试解密无效格式的值返回原值"""
        encryptor = FieldEncryptor(valid_key_manager)

        # 格式错误的"加密"值
        invalid_ciphertext = "enc:v1:invalid-base64!@#"
        decrypted = encryptor.decrypt_deterministic(invalid_ciphertext)

        # 解密失败应返回原值
        assert decrypted == invalid_ciphertext

    def test_missing_key_encrypt_returns_none(self, missing_key_manager):
        """测试密钥缺失时加密返回None"""
        # Double-check that manager truly has no key
        assert missing_key_manager.is_available() is False

        encryptor = FieldEncryptor(missing_key_manager)

        assert encryptor.encrypt_deterministic("test") is None
        assert encryptor.encrypt_standard("test") is None

    def test_missing_key_decrypt_returns_original(self, missing_key_manager):
        """测试密钥缺失时解密返回原值"""
        # Double-check that manager truly has no key
        assert missing_key_manager.is_available() is False

        encryptor = FieldEncryptor(missing_key_manager)
        ciphertext = "enc:v1:some-ciphertext"

        # 密钥缺失时解密返回原值
        decrypted = encryptor.decrypt_deterministic(ciphertext)
        assert decrypted == ciphertext

    def test_is_encrypted_utility(self):
        """测试 is_encrypted 工具方法"""
        assert FieldEncryptor.is_encrypted("enc:v1:abc") is True
        assert FieldEncryptor.is_encrypted("enc:v2:def") is True
        assert FieldEncryptor.is_encrypted("plain-text") is False
        assert FieldEncryptor.is_encrypted("encrypted:v1:abc") is False  # 没有前缀
        assert FieldEncryptor.is_encrypted(None) is False
        assert FieldEncryptor.is_encrypted("") is False


# ============================================================================
# CLI 辅助函数测试
# ============================================================================
class TestCLIHelpers:
    """测试命令行辅助函数"""

    def test_generate_encryption_key_format(self):
        """测试生成加密密钥的格式"""
        key = generate_encryption_key()

        # 检查格式: base64:version
        assert ":" in key
        parts = key.split(":")
        assert len(parts) == 2

        key_b64, version = parts
        assert version == "1"

        # 验证base64编码
        decoded = base64.b64decode(key_b64)
        assert len(decoded) == 32  # 32字节 = 256位

    def test_generate_encryption_key_uniqueness(self):
        """测试每次生成的密钥都是唯一的"""
        key1 = generate_encryption_key()
        key2 = generate_encryption_key()

        # 密钥应该不同（随机生成）
        assert key1 != key2


# ============================================================================
# SensitiveDataHandler 测试
# ============================================================================
class TestSensitiveDataHandler:
    """测试敏感数据处理器"""

    @pytest.fixture
    def valid_handler(self, monkeypatch):
        """创建有效的敏感数据处理器fixture - 配置测试字段"""
        # Clear cached modules first
        import sys
        for mod in list(sys.modules.keys()):
            if "src.core.config" in mod or "src.core.encryption" in mod or "src.crud.asset" in mod:
                del sys.modules[mod]

        key_bytes = b"e" * 32
        key_b64 = base64.b64encode(key_bytes).decode("ascii")
        test_key = f"{key_b64}:1"

        # Set environment variable
        monkeypatch.setenv("DATA_ENCRYPTION_KEY", test_key)

        # Import fresh and patch settings directly
        from src.core import config
        from src.crud.asset import SensitiveDataHandler

        # Use monkeypatch to persist the value for the entire test
        monkeypatch.setattr(config.settings, 'DATA_ENCRYPTION_KEY', test_key)

        # 创建配置了测试字段的处理器
        return SensitiveDataHandler(
            searchable_fields={"phone", "id_card"},  # 可搜索字段（手机号、身份证）
            non_searchable_fields={"note"}  # 非搜索字段
        )

    @pytest.fixture
    def missing_key_handler(self, monkeypatch):
        """创建缺失密钥的敏感数据处理器fixture"""
        # Remove environment variable completely
        monkeypatch.delenv("DATA_ENCRYPTION_KEY", raising=False)

        # Clear cached modules to force reload
        import sys
        modules_to_clear = [
            "src.core.config",
            "src.core.encryption",
            "src.crud.asset",
        ]
        for mod in modules_to_clear:
            if mod in sys.modules:
                del sys.modules[mod]

        # Import modules fresh - settings will read from environment (which is now deleted)
        from src.core import config
        from src.crud.asset import SensitiveDataHandler

        # Use monkeypatch to persist the empty value for the entire test
        monkeypatch.setattr(config.settings, 'DATA_ENCRYPTION_KEY', "")

        return SensitiveDataHandler()

    def test_pii_field_classification(self):
        """测试PII字段分类 - 验证默认配置为空（子类应覆盖）"""
        from src.crud.asset import SensitiveDataHandler

        # 默认情况下，SensitiveDataHandler 没有配置任何字段
        # 子类（如 OrganizationCRUD, RentContractCRUD）应该通过参数配置
        assert len(SensitiveDataHandler.SEARCHABLE_FIELDS) == 0
        assert len(SensitiveDataHandler.NON_SEARCHABLE_FIELDS) == 0

        # 创建一个配置了字段的实例用于测试
        handler = SensitiveDataHandler(
            searchable_fields={"id_card", "phone"},
            non_searchable_fields={"note"}
        )
        assert "id_card" in handler.SEARCHABLE_FIELDS
        assert "phone" in handler.SEARCHABLE_FIELDS
        assert "note" in handler.NON_SEARCHABLE_FIELDS

    def test_encrypt_pii_field(self, valid_handler):
        """测试加密PII字段 - 使用手机号和身份证作为测试数据"""
        plaintext_phone = "13800138000"
        plaintext_id_card = "110101199001011234"

        # 测试可搜索字段（手机号 - 确定性加密）
        encrypted_phone = valid_handler.encrypt_field("phone", plaintext_phone)
        assert encrypted_phone is not None
        assert encrypted_phone != plaintext_phone
        assert encrypted_phone.startswith("enc:v1:")

        # 测试可搜索字段（身份证号 - 确定性加密）
        encrypted_id = valid_handler.encrypt_field("id_card", plaintext_id_card)
        assert encrypted_id is not None
        assert encrypted_id != plaintext_id_card
        assert encrypted_id.startswith("enc:v1:")

        # 测试非搜索字段（标准加密）
        plaintext_note = "这是备注信息"
        encrypted_note = valid_handler.encrypt_field("note", plaintext_note)
        assert encrypted_note is not None
        assert encrypted_note != plaintext_note
        assert encrypted_note.startswith("enc:v1:")

    def test_non_pii_field_unchanged(self, valid_handler):
        """测试非PII字段不变"""
        value = "property_name_value"

        encrypted = valid_handler.encrypt_field("property_name", value)
        assert encrypted == value  # 非PII字段不应被加密

    def test_decrypt_pii_field(self, valid_handler):
        """测试解密PII字段"""
        plaintext_phone = "13900139000"

        # 先加密
        encrypted = valid_handler.encrypt_field("phone", plaintext_phone)
        assert encrypted != plaintext_phone

        # 再解密
        decrypted = valid_handler.decrypt_field("phone", encrypted)
        assert decrypted == plaintext_phone

    def test_batch_encrypt_dict(self, valid_handler):
        """测试批量加密字典"""
        data = {
            "phone": "13800138000",  # PII字段
            "id_card": "110101199001011234",  # PII字段
            "name": "张三",  # 非PII字段
            "note": "备注信息",  # PII字段
        }

        result = valid_handler.encrypt_data(data.copy())

        # PII字段应该被加密
        assert result["phone"] != "13800138000"
        assert result["phone"].startswith("enc:v1:")
        assert result["id_card"] != "110101199001011234"
        assert result["id_card"].startswith("enc:v1:")
        assert result["note"] != "备注信息"
        assert result["note"].startswith("enc:v1:")

        # 非PII字段应该不变
        assert result["name"] == "张三"

    def test_batch_decrypt_dict(self, valid_handler):
        """测试批量解密字典"""
        # 先加密
        data = {
            "phone": "13900139000",
            "id_card": "110101199001011235",
        }

        encrypted_data = valid_handler.encrypt_data(data.copy())

        # 再解密
        decrypted_data = valid_handler.decrypt_data(encrypted_data)

        # 应该恢复为原始值
        assert decrypted_data["phone"] == "13900139000"
        assert decrypted_data["id_card"] == "110101199001011235"

    def test_batch_encrypt_list(self, valid_handler):
        """测试批量加密列表"""
        data = [
            {"phone": "13800138000", "name": "张三"},
            {"phone": "13900139000", "name": "李四"},
        ]

        result = valid_handler.encrypt_data(data)

        # 所有记录的PII字段都应被加密
        assert result[0]["phone"] != "13800138000"
        assert result[1]["phone"] != "13900139000"

        # 非PII字段不变
        assert result[0]["name"] == "张三"
        assert result[1]["name"] == "李四"

    def test_encryption_disabled_missing_key(self, missing_key_handler):
        """测试密钥缺失时加密被禁用"""
        assert missing_key_handler.encryption_enabled is False

        # 加密操作应该返回原值
        value = "test_value"
        encrypted = missing_key_handler.encrypt_field("phone", value)
        assert encrypted == value

    def test_encrypt_none_value(self, valid_handler):
        """测试加密None值"""
        encrypted = valid_handler.encrypt_field("tenant_name", None)
        assert encrypted is None

    def test_decrypt_none_value(self, valid_handler):
        """测试解密None值"""
        decrypted = valid_handler.decrypt_field("tenant_name", None)
        assert decrypted is None
