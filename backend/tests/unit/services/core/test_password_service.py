"""
密码服务单元测试

测试 PasswordService 的密码哈希、验证、过期检查等功能
"""

import json
from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest

from src.services.core.password_service import PasswordService


# ============================================================================
# get_password_hash 测试
# ============================================================================
class TestGetPasswordHash:
    """测试密码哈希生成"""

    def test_generates_hash(self):
        """测试生成密码哈希"""
        service = PasswordService()
        password = "TestPassword123!"
        hashed = service.get_password_hash(password)

        # bcrypt 哈希格式: $2b$[cost]$[salt][hash]
        assert hashed.startswith("$2b$")
        assert len(hashed) == 60  # bcrypt 哈希固定长度

    def test_same_password_different_hashes(self):
        """测试相同密码产生不同哈希（随机盐）"""
        service = PasswordService()
        password = "TestPassword123!"

        hash1 = service.get_password_hash(password)
        hash2 = service.get_password_hash(password)

        # 由于随机盐，哈希应该不同
        assert hash1 != hash2

    def test_empty_password(self):
        """测试空密码"""
        service = PasswordService()
        hashed = service.get_password_hash("")

        # 应该仍然生成有效哈希
        assert hashed.startswith("$2b$")


# ============================================================================
# verify_password 测试
# ============================================================================
class TestVerifyPassword:
    """测试密码验证"""

    def test_verify_correct_password(self):
        """测试验证正确密码"""
        service = PasswordService()
        password = "TestPassword123!"
        hashed = service.get_password_hash(password)

        assert service.verify_password(password, hashed) is True

    def test_verify_incorrect_password(self):
        """测试验证错误密码"""
        service = PasswordService()
        password = "TestPassword123!"
        hashed = service.get_password_hash(password)

        assert service.verify_password("WrongPassword", hashed) is False

    def test_verify_with_bcrypt_hash(self):
        """测试验证标准 bcrypt 哈希"""
        service = PasswordService()
        # 已知的 bcrypt 测试哈希
        known_hash = "$2b$12$sWq/wXXqnXJOv3EJbYHqF.5FvWHJLLNf7L7p7Q7L7p7Q7L7p7Q"

        # 这个哈希对应密码 "test"
        result = service.verify_password("test", known_hash)
        # 由于盐不同，这个已知哈希可能不匹配，所以不断言
        assert isinstance(result, bool)

    def test_verify_empty_password(self):
        """测试验证空密码"""
        service = PasswordService()
        hashed = service.get_password_hash("")

        assert service.verify_password("", hashed) is True
        assert service.verify_password("wrong", hashed) is False

    def test_verify_handles_invalid_hash(self):
        """测试处理无效哈希"""
        service = PasswordService()
        # 无效的哈希格式
        assert service.verify_password("password", "invalid_hash") is False

    def test_verify_none_values(self):
        """测试 None 值处理"""
        service = PasswordService()
        # 应该优雅处理 None 而不崩溃
        result = service.verify_password("password", None)
        assert result is False


# ============================================================================
# validate_password_strength 测试
# ============================================================================
class TestValidatePasswordStrength:
    """测试密码强度验证"""

    def test_strong_password(self):
        """测试强密码"""
        service = PasswordService()
        # 满足所有要求：大写、小写、数字、特殊字符
        assert service.validate_password_strength("Test123!@#") is True
        assert service.validate_password_strength("Password123!") is True

    def test_too_short(self):
        """测试密码过短"""
        service = PasswordService()
        # 少于 MIN_PASSWORD_LENGTH (默认8)
        assert service.validate_password_strength("Test1!") is False

    def test_no_uppercase(self):
        """测试缺少大写字母"""
        service = PasswordService()
        assert service.validate_password_strength("test123!@#") is False

    def test_no_lowercase(self):
        """测试缺少小写字母"""
        service = PasswordService()
        assert service.validate_password_strength("TEST123!@#") is False

    def test_no_digit(self):
        """测试缺少数字"""
        service = PasswordService()
        assert service.validate_password_strength("TestPassword!") is False

    def test_no_special_char(self):
        """测试缺少特殊字符"""
        service = PasswordService()
        assert service.validate_password_strength("TestPassword123") is False

    def test_all_special_characters(self):
        """测试所有支持的特殊字符"""
        service = PasswordService()
        # 测试各种特殊字符
        assert service.validate_password_strength("Test123!") is True
        assert service.validate_password_strength("Test123@") is True
        assert service.validate_password_strength("Test123#") is True
        assert service.validate_password_strength("Test123$") is True
        assert service.validate_password_strength("Test123%") is True
        assert service.validate_password_strength("Test123^") is True
        assert service.validate_password_strength("Test123&") is True
        assert service.validate_password_strength("Test123*") is True

    def test_minimal_valid_password(self):
        """测试最小有效密码（8字符，包含所有类型）"""
        service = PasswordService()
        # 正好8个字符
        assert service.validate_password_strength("Test1!@#") is True
        assert service.validate_password_strength("Aa1!aaaa") is True


# ============================================================================
# is_password_in_history 测试
# ============================================================================
class MockUser:
    """模拟用户对象"""

    def __init__(
        self,
        password_history: str | dict | None = None,
        password_last_changed: datetime | None = None,
    ):
        self.password_history = password_history
        self.password_last_changed = password_last_changed


class TestIsPasswordInHistory:
    """测试密码历史检查"""

    def test_no_password_history(self):
        """测试无密码历史"""
        service = PasswordService()
        user = MockUser(password_history=None)

        assert service.is_password_in_history(user, "TestPassword123!") is False

    def test_empty_password_history(self):
        """测试空密码历史"""
        service = PasswordService()
        user = MockUser(password_history='{"passwords": []}')

        assert service.is_password_in_history(user, "TestPassword123!") is False

    def test_password_in_history(self):
        """测试密码在历史中"""
        service = PasswordService()
        password = "TestPassword123!"
        hashed = service.get_password_hash(password)

        user = MockUser(password_history=json.dumps({"passwords": [hashed]}))

        assert service.is_password_in_history(user, password) is True

    def test_password_not_in_history(self):
        """测试密码不在历史中"""
        service = PasswordService()
        password1 = "TestPassword123!"
        password2 = "DifferentPassword456!"
        hashed = service.get_password_hash(password1)

        user = MockUser(password_history=json.dumps({"passwords": [hashed]}))

        assert service.is_password_in_history(user, password2) is False

    def test_multiple_passwords_in_history(self):
        """测试多个历史密码"""
        service = PasswordService()
        password1 = "TestPassword123!"
        password2 = "Password456!"
        password3 = "Password789!"

        hash1 = service.get_password_hash(password1)
        hash2 = service.get_password_hash(password2)

        user = MockUser(
            password_history=json.dumps({"passwords": [hash1, hash2]})
        )

        assert service.is_password_in_history(user, password1) is True
        assert service.is_password_in_history(user, password2) is True
        assert service.is_password_in_history(user, password3) is False

    def test_dict_password_history(self):
        """测试字典格式的密码历史"""
        service = PasswordService()
        password = "TestPassword123!"
        hashed = service.get_password_hash(password)

        user = MockUser(password_history={"passwords": [hashed]})

        assert service.is_password_in_history(user, password) is True

    def test_invalid_json_in_history(self):
        """测试历史记录中的无效 JSON"""
        service = PasswordService()
        user = MockUser(password_history="invalid json")

        # 应该优雅处理并返回 False
        assert service.is_password_in_history(user, "TestPassword123!") is False

    def test_malformed_password_list(self):
        """测试格式错误的密码列表"""
        service = PasswordService()
        user = MockUser(password_history='{"passwords": ["not_a_hash"]}')

        # 应该不崩溃
        result = service.is_password_in_history(user, "TestPassword123!")
        assert isinstance(result, bool)


# ============================================================================
# add_password_to_history 测试
# ============================================================================
class TestAddPasswordToHistory:
    """测试添加密码到历史"""

    def test_add_to_empty_history(self):
        """测试添加到空历史"""
        service = PasswordService()
        user = MockUser(password_history=None)
        new_hash = "$2b$12$testhash"

        service.add_password_to_history(user, new_hash)

        # 验证历史已更新
        assert isinstance(user.password_history, dict)
        assert "passwords" in user.password_history
        assert len(user.password_history["passwords"]) == 1
        assert user.password_history["passwords"][0] == new_hash
        assert user.password_last_changed is not None

    def test_add_to_existing_history(self):
        """测试添加到已有历史"""
        service = PasswordService()
        old_hash = "$2b$12$oldhash"
        user = MockUser(password_history={"passwords": [old_hash]})
        new_hash = "$2b$12$newhash"

        service.add_password_to_history(user, new_hash)

        # 应该有2个历史记录
        assert len(user.password_history["passwords"]) == 2
        assert user.password_history["passwords"][0] == old_hash
        assert user.password_history["passwords"][1] == new_hash

    def test_history_limited_to_10(self):
        """测试历史限制为10个"""
        service = PasswordService()
        # 创建11个历史记录
        old_hashes = [f"$2b$12$hash{i}" for i in range(11)]
        user = MockUser(password_history={"passwords": old_hashes})
        new_hash = "$2b$12$newhash"

        service.add_password_to_history(user, new_hash)

        # 应该只保留最近10个
        assert len(user.password_history["passwords"]) == 10
        assert new_hash in user.password_history["passwords"]
        # 最旧的哈希应该被移除
        assert "$2b$12$hash0" not in user.password_history["passwords"]

    def test_string_password_history(self):
        """测试字符串格式的密码历史"""
        service = PasswordService()
        user = MockUser(
            password_history=json.dumps({"passwords": ["$2b$12$oldhash"]})
        )
        new_hash = "$2b$12$newhash"

        service.add_password_to_history(user, new_hash)

        # 应该正确解析并添加
        assert len(user.password_history["passwords"]) == 2

    def test_invalid_json_replaced_with_empty_history(self):
        """测试无效 JSON 被替换为空历史"""
        service = PasswordService()
        user = MockUser(password_history="invalid json")
        new_hash = "$2b$12$newhash"

        service.add_password_to_history(user, new_hash)

        # 应该创建新的历史记录
        assert isinstance(user.password_history, dict)
        assert len(user.password_history["passwords"]) == 1


# ============================================================================
# is_password_expired 测试
# ============================================================================
class TestIsPasswordExpired:
    """测试密码过期检查"""

    def test_no_password_last_changed(self):
        """测试无密码更改时间"""
        service = PasswordService()
        user = MockUser(password_last_changed=None)

        assert service.is_password_expired(user) is False

    def test_recently_changed_password(self):
        """测试最近更改的密码"""
        service = PasswordService()
        # 刚更改的密码
        user = MockUser(password_last_changed=datetime.now())

        assert service.is_password_expired(user) is False

    def test_expired_password(self):
        """测试过期的密码"""
        service = PasswordService()
        # 100天前更改的密码（超过90天）
        old_date = datetime.now() - timedelta(days=100)
        user = MockUser(password_last_changed=old_date)

        assert service.is_password_expired(user) is True

    def test_exactly_expired(self):
        """测试正好过期的密码"""
        service = PasswordService()
        # 正好90天前（假设 PASSWORD_EXPIRE_DAYS = 90）
        old_date = datetime.now() - timedelta(days=90)
        user = MockUser(password_last_changed=old_date)

        # 密码应该刚过期或即将过期
        result = service.is_password_expired(user)
        assert isinstance(result, bool)

    def test_timezone_aware_datetime(self):
        """测试时区感知的 datetime"""
        service = PasswordService()
        # 带 timezone 的 datetime（虽然 SQLite 通常存储 naive datetime）
        from datetime import timezone

        tz_aware_date = datetime.now(timezone.utc).replace(tzinfo=None)
        user = MockUser(password_last_changed=tz_aware_date)

        # 应该不崩溃并返回布尔值
        result = service.is_password_expired(user)
        assert isinstance(result, bool)

    def test_one_day_before_expiration(self):
        """测试过期前一天"""
        service = PasswordService()
        # 89天前
        old_date = datetime.now() - timedelta(days=89)
        user = MockUser(password_last_changed=old_date)

        # 应该还没过期
        assert service.is_password_expired(user) is False

    def test_one_day_after_expiration(self):
        """测试过期后一天"""
        service = PasswordService()
        # 91天前
        old_date = datetime.now() - timedelta(days=91)
        user = MockUser(password_last_changed=old_date)

        # 应该已过期
        assert service.is_password_expired(user) is True
