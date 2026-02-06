"""
加密服务核心模块

提供字段级别的加密/解密功能，支持：
- AES-256-CBC 确定性加密（可搜索字段）- 从密钥派生固定IV实现确定性
- AES-256-GCM 标准加密（非搜索字段）
- 密钥版本管理（支持未来密钥轮换）
- 环境感知降级（生产环境可强制要求密钥）

安全设计：
- 密钥通过环境变量 DATA_ENCRYPTION_KEY 提供
- 密钥格式: {base64_key}:{version}（支持多版本: key1:1,key2:2）
- 密文格式:
  - 确定性: enc:v{version}:base64(ciphertext)
  - 标准: enc:v{version}:base64(nonce):base64(ciphertext)
- 生产环境强制要求密钥（REQUIRE_ENCRYPTION=true 时）
"""

import base64
import logging
import secrets
from typing import Any

from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from ..core.config import settings
from ..core.environment import get_environment, is_production
from ..core.exception_handler import ConfigurationError

logger = logging.getLogger(__name__)


# ============================================================================
# 加密前缀常量
# ============================================================================
ENCRYPTION_PREFIX = "enc:v"
DETERMINISTIC_SUFFIX = ":"  # 确定性加密: enc:v1:base64(ciphertext)
# 标准加密: enc:v1:base64(nonce):base64(ciphertext)


# ============================================================================
# 密钥管理器
# ============================================================================
class EncryptionKeyManager:
    """
    加密密钥管理器

    功能：
    - 从环境变量加载 DATA_ENCRYPTION_KEY
    - 验证密钥长度（必须 >= 32 字节）
    - 提取密钥版本号
    - 环境感知降级（生产环境可强制要求密钥）
    """

    def __init__(self) -> None:
        """初始化密钥管理器，从环境加载密钥"""
        self._keys: dict[int, bytes] = {}
        self.version: int = 1
        self._environment: str = get_environment().value
        self._load_key_from_env()

    def _load_key_from_env(self) -> None:
        """
        从环境变量加载并解析密钥

        密钥格式: {base64_key}:{version}
        多版本格式: key1:1,key2:2
        示例: MTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIz:1

        生产环境行为：
        - 若 REQUIRE_ENCRYPTION=true（默认）且无密钥，抛出 ConfigurationError
        - 若 REQUIRE_ENCRYPTION=false，仅记录警告
        """
        env_key = settings.DATA_ENCRYPTION_KEY
        require_encryption = getattr(settings, "REQUIRE_ENCRYPTION", None)

        # 默认：生产环境强制要求，非生产环境不强制
        if require_encryption is None:
            require_encryption = is_production()

        if not env_key:
            if require_encryption:
                raise ConfigurationError(
                    "CRITICAL: DATA_ENCRYPTION_KEY is required but not set. "
                    "PII data cannot be stored securely without encryption. "
                    "Generate a key with: python -m backend.src.core.encryption "
                    "Or set REQUIRE_ENCRYPTION=false to disable this check (NOT recommended for production).",
                    config_key="DATA_ENCRYPTION_KEY",
                )
            logger.warning(
                "DATA_ENCRYPTION_KEY not set - PII encryption disabled. "
                "Data will be stored in plaintext. "
                "This is acceptable for development but NOT for production."
            )
            return

        try:
            # 支持多密钥格式：key1:1,key2:2
            key_parts = [part.strip() for part in env_key.split(",") if part.strip()]
            if not key_parts:
                return

            for part in key_parts:
                key_b64 = part
                version = 1
                if ":" in part:
                    key_b64, version_str = part.rsplit(":", 1)
                    try:
                        version = int(version_str)
                    except ValueError:
                        logger.warning(
                            f"Invalid key version: {version_str}, using version 1"
                        )
                        key_b64 = part
                        version = 1

                try:
                    key_bytes = base64.b64decode(key_b64)
                except Exception as e:
                    logger.error(f"Failed to decode encryption key: {e}")
                    continue

                if len(key_bytes) < 32:
                    logger.error(
                        f"DATA_ENCRYPTION_KEY too short: {len(key_bytes)} bytes "
                        f"(minimum 32 bytes required). Skipping version {version}."
                    )
                    continue

                self._keys[version] = key_bytes

            if not self._keys:
                logger.error(
                    "No valid DATA_ENCRYPTION_KEY entries loaded. Encryption disabled."
                )
                return

            self.version = max(self._keys.keys())
            logger.info(
                "Encryption keys loaded (versions: %s), current=%s",
                sorted(self._keys.keys()),
                self.version,
            )

        except Exception as e:
            logger.error(
                f"Failed to load DATA_ENCRYPTION_KEY: {e}. Encryption disabled."
            )
            self._keys = {}

    def is_available(self) -> bool:
        """检查加密密钥是否可用"""
        return bool(self._keys)

    def get_key(self, version: int | None = None) -> bytes | None:
        """获取加密密钥（返回 None 表示密钥不可用）"""
        if not self._keys:
            return None
        if version is None:
            return self._keys.get(self.version)
        return self._keys.get(version)

    def get_version(self) -> int:
        """获取当前密钥版本"""
        return self.version

    def get_versions(self) -> list[int]:
        """获取所有可用密钥版本（升序）"""
        return sorted(self._keys.keys())


# ============================================================================
# 字段加密器
# ============================================================================
class FieldEncryptor:
    """
    字段级别加密器

    支持两种加密模式：
    1. 确定性加密 (AES-256-CBC with derived IV): 相同明文 → 相同密文（用于搜索）
    2. 标准加密 (AES-256-GCM): 相同明文 → 不同密文（更高安全性）

    设计原则：
    - 所有密文都带有版本前缀，支持未来密钥轮换
    - None 值透传，不加密
    - 解密失败时返回原值（优雅降级）
    - 密钥缺失时返回 None（调用方处理）
    """

    # 加密前缀常量
    ENCRYPTION_PREFIX = "enc:v"

    def __init__(self, key_manager: EncryptionKeyManager) -> None:
        """
        初始化字段加密器

        Args:
            key_manager: 密钥管理器实例
        """
        self.key_manager = key_manager

    def _derive_deterministic_iv(self, key: bytes, version: int) -> bytes:
        """
        从密钥派生确定性的IV

        使用密钥和版本号生成一个固定的16字节IV用于CBC模式
        这样相同的密钥和版本总是产生相同的IV，从而实现确定性加密

        Args:
            key: 加密密钥
            version: 密钥版本

        Returns:
            16字节的IV
        """
        # 使用HKDF从密钥派生IV
        digest = hashes.Hash(hashes.SHA256())
        digest.update(key)
        digest.update(str(version).encode("utf-8"))
        # 使用前16字节作为IV
        return digest.finalize()[:16]

    @staticmethod
    def _parse_version(version_str: str) -> int | None:
        """解析密文中的版本号"""
        if version_str.startswith("v"):
            version_str = version_str[1:]
        try:
            return int(version_str)
        except ValueError:
            return None

    # --------------------------------------------------------------------
    # 确定性加密 (用于可搜索字段)
    # --------------------------------------------------------------------
    def encrypt_deterministic(self, plaintext: str | None) -> str | None:
        """
        确定性加密 - AES-256-CBC with derived IV

        特点：相同明文总是产生相同密文，支持数据库搜索
        为了实现确定性，我们从密钥派生一个固定的IV

        Args:
            plaintext: 要加密的明文（None 则返回 None）

        Returns:
            加密后的字符串，格式: enc:v{version}:base64(ciphertext)
            如果密钥不可用，返回 None
        """
        if plaintext is None:
            return None

        key = self.key_manager.get_key()
        if key is None:
            # 开发环境：返回原值而非 None，防止数据丢失
            logger.warning(
                "DATA_ENCRYPTION_KEY not configured, storing plaintext. "
                "This is acceptable for development only."
            )
            return plaintext

        try:
            # 使用 AES-256-CBC
            # 为了实现确定性加密，我们需要一个固定的IV
            # 从密钥派生IV
            iv = self._derive_deterministic_iv(key, self.key_manager.get_version())

            # 创建加密器
            cipher = Cipher(algorithms.AES(key[:32]), modes.CBC(iv))
            encryptor = cipher.encryptor()

            # 填充明文到块大小的倍数（PKCS7）
            padder = padding.PKCS7(128).padder()
            padded_data = padder.update(plaintext.encode("utf-8")) + padder.finalize()

            # 加密
            ciphertext = encryptor.update(padded_data) + encryptor.finalize()

            # Base64 编码
            ciphertext_b64 = base64.b64encode(ciphertext).decode("ascii")

            # 添加版本前缀: enc:v1:base64(ciphertext)
            version = self.key_manager.get_version()
            return f"{self.ENCRYPTION_PREFIX}{version}{DETERMINISTIC_SUFFIX}{ciphertext_b64}"

        except Exception as e:
            logger.error(f"Failed to encrypt deterministically: {e}")
            return None

    def decrypt_deterministic(self, ciphertext: str | None) -> str | None:
        """
        解密确定性加密的数据

        Args:
            ciphertext: 密文（格式: enc:v{version}:base64(ciphertext)）

        Returns:
            解密后的明文，如果不是加密格式或解密失败则返回原值
        """
        if ciphertext is None:
            return None

        # 检查是否为加密格式
        if not ciphertext.startswith(self.ENCRYPTION_PREFIX):
            return ciphertext  # 不是加密格式，返回原值（可能是旧数据）

        key = self.key_manager.get_key()
        if key is None:
            logger.warning("Cannot decrypt: encryption key not available")
            return ciphertext  # 密钥不可用，返回原值

        try:
            # 解析格式: enc:v1:base64(ciphertext)
            parts = ciphertext.split(":", 2)
            if len(parts) != 3:
                logger.warning(f"Invalid encrypted format: {ciphertext[:20]}...")
                return ciphertext  # 格式错误，返回原值

            _, version_str, ciphertext_b64 = parts

            version = self._parse_version(version_str)
            key = self.key_manager.get_key(version)
            if key is None:
                logger.warning(
                    f"Cannot decrypt: encryption key for version {version_str} not available"
                )
                return ciphertext

            # Base64 解码
            ciphertext_bytes = base64.b64decode(ciphertext_b64)

            # 派生相同的IV
            iv = self._derive_deterministic_iv(
                key,
                version if version is not None else self.key_manager.get_version(),
            )

            # 解密（AES-CBC）
            cipher = Cipher(algorithms.AES(key[:32]), modes.CBC(iv))
            decryptor = cipher.decryptor()

            # 解密并去除填充
            padded_plaintext = decryptor.update(ciphertext_bytes) + decryptor.finalize()
            unpadder = padding.PKCS7(128).unpadder()
            plaintext_bytes = unpadder.update(padded_plaintext) + unpadder.finalize()

            return plaintext_bytes.decode("utf-8")

        except Exception as e:
            # 区分格式错误和真正的解密错误
            if "Invalid base64" in str(e) or "incorrect padding" in str(e):
                logger.warning(f"Invalid encrypted data format: {e}")
                return ciphertext  # 格式错误，返回原值
            else:
                logger.error(f"Failed to decrypt deterministic data: {e}")
                # 真正的解密错误（如密钥错误）返回 None，防止暴露损坏数据
                return None

    # --------------------------------------------------------------------
    # 标准加密 (用于非搜索字段)
    # --------------------------------------------------------------------
    def encrypt_standard(self, plaintext: str | None) -> str | None:
        """
        标准加密 - AES-256-GCM

        特点：每次加密产生不同的密文（随机 nonce），安全性更高

        Args:
            plaintext: 要加密的明文（None 则返回 None）

        Returns:
            加密后的字符串，格式: enc:v{version}:base64(nonce):base64(ciphertext)
            如果密钥不可用，返回 None
        """
        if plaintext is None:
            return None

        key = self.key_manager.get_key()
        if key is None:
            # 开发环境：返回原值而非 None，防止数据丢失
            logger.warning(
                "DATA_ENCRYPTION_KEY not configured, storing plaintext. "
                "This is acceptable for development only."
            )
            return plaintext

        try:
            # 使用 AES-256-GCM（带认证的加密）
            aesgcm = AESGCM(key)

            # 生成随机 nonce（12 字节是 GCM 的推荐长度）
            nonce = secrets.token_bytes(12)

            # 加密
            ciphertext = aesgcm.encrypt(
                nonce, plaintext.encode("utf-8"), associated_data=None
            )

            # Base64 编码
            nonce_b64 = base64.b64encode(nonce).decode("ascii")
            ciphertext_b64 = base64.b64encode(ciphertext).decode("ascii")

            # 添加版本前缀: enc:v1:base64(nonce):base64(ciphertext)
            version = self.key_manager.get_version()
            return f"{self.ENCRYPTION_PREFIX}{version}:{nonce_b64}:{ciphertext_b64}"

        except Exception as e:
            logger.error(f"Failed to encrypt with standard method: {e}")
            return None

    def decrypt_standard(self, ciphertext: str | None) -> str | None:
        """
        解密标准加密的数据

        Args:
            ciphertext: 密文（格式: enc:v{version}:base64(nonce):base64(ciphertext)）

        Returns:
            解密后的明文，如果不是加密格式或解密失败则返回原值
        """
        if ciphertext is None:
            return None

        # 检查是否为加密格式
        if not ciphertext.startswith(self.ENCRYPTION_PREFIX):
            return ciphertext  # 不是加密格式，返回原值（可能是旧数据）

        key = self.key_manager.get_key()
        if key is None:
            logger.warning("Cannot decrypt: encryption key not available")
            return ciphertext  # 密钥不可用，返回原值

        try:
            # 解析格式: enc:v1:base64(nonce):base64(ciphertext)
            parts = ciphertext.split(":", 3)
            if len(parts) != 4:
                # 可能是确定性加密格式（只有 3 部分）
                if len(parts) == 3:
                    return self.decrypt_deterministic(ciphertext)
                logger.warning(f"Invalid encrypted format: {ciphertext[:20]}...")
                return ciphertext  # 格式错误，返回原值

            _, version_str, nonce_b64, ciphertext_b64 = parts

            version = self._parse_version(version_str)
            key = self.key_manager.get_key(version)
            if key is None:
                logger.warning(
                    f"Cannot decrypt: encryption key for version {version_str} not available"
                )
                return ciphertext

            # Base64 解码
            nonce = base64.b64decode(nonce_b64)
            ciphertext_bytes = base64.b64decode(ciphertext_b64)

            # 解密（AES-GCM）
            aesgcm = AESGCM(key)
            plaintext_bytes = aesgcm.decrypt(
                nonce, ciphertext_bytes, associated_data=None
            )

            return plaintext_bytes.decode("utf-8")

        except Exception as e:
            # 区分格式错误和真正的解密错误
            if "Invalid base64" in str(e) or "incorrect padding" in str(e):
                logger.warning(f"Invalid encrypted data format: {e}")
                return ciphertext  # 格式错误，返回原值
            else:
                logger.error(f"Failed to decrypt standard data: {e}")
                # 真正的解密错误（如密钥错误）返回 None，防止暴露损坏数据
                return None

    # --------------------------------------------------------------------
    # 工具方法
    # --------------------------------------------------------------------
    @staticmethod
    def is_encrypted(value: str | None) -> bool:
        """
        检查值是否为加密格式

        Args:
            value: 要检查的值

        Returns:
            True 如果是加密格式，False 否则
        """
        if value is None:
            return False
        return value.startswith(FieldEncryptor.ENCRYPTION_PREFIX)


# ============================================================================
# 状态查询函数
# ============================================================================
def get_encryption_status() -> dict[str, Any]:
    """
    获取加密服务状态

    Returns:
        包含加密状态信息的字典：
        - enabled: 加密是否可用
        - key_version: 密钥版本号（无密钥时为 None）
        - algorithms: 支持的加密算法列表
        - environment: 当前运行环境
        - warning: 警告信息（如有）
    """
    key_manager = EncryptionKeyManager()
    status: dict[str, Any] = {
        "enabled": key_manager.is_available(),
        "key_version": key_manager.get_version()
        if key_manager.is_available()
        else None,
        "algorithms": ["AES-256-GCM", "AES-256-CBC"],
        "environment": key_manager._environment,
        "warning": None,
    }

    if not key_manager.is_available():
        status["warning"] = (
            "Encryption is disabled. PII data will be stored in plaintext. "
            "Set DATA_ENCRYPTION_KEY to enable encryption."
        )

    return status


# ============================================================================
# CLI 辅助函数
# ============================================================================
def generate_encryption_key() -> str:
    """
    生成新的加密密钥

    Returns:
        格式化的密钥字符串: {base64_key}:1
        可以直接用于 DATA_ENCRYPTION_KEY 环境变量
    """
    # 生成 32 字节（256 位）随机密钥
    key = secrets.token_bytes(32)

    # Base64 编码
    key_b64 = base64.b64encode(key).decode("ascii")

    # 添加版本号
    return f"{key_b64}:1"


def main() -> None:
    """CLI 入口点 - 生成并显示新的加密密钥"""
    print("=" * 70)
    print("Encryption Key Generator")
    print("=" * 70)
    print()
    print("Generating a new 32-byte (256-bit) encryption key...")
    print()

    key = generate_encryption_key()

    print("Key generated successfully!")
    print()
    print("Add this to your .env file:")
    print("-" * 70)
    print(f'DATA_ENCRYPTION_KEY="{key}"')
    print("-" * 70)
    print()
    print("IMPORTANT SECURITY NOTES:")
    print("   - Keep this key secure and never commit it to version control")
    print("   - Store it in a secure secrets manager in production")
    print("   - Use different keys for development, staging, and production")
    print("   - Rotate keys periodically (increment version number)")
    print("   - Test key recovery procedures before production deployment")
    print()


if __name__ == "__main__":
    main()
