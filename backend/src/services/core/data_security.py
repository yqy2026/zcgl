from typing import Any

"""
数据加密服务
"""

import base64
import os

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class DataEncryptionService:
    """数据加密服务"""

    def __init__(self):
        # 从环境变量获取加密密钥，如果不存在则生成一�?
        self.encryption_key = self._get_or_create_encryption_key()
        self.cipher_suite = Fernet(self.encryption_key)

    def _get_or_create_encryption_key(self) -> bytes:
        """获取或创建加密密�?""
        # 优先从环境变量获取密�?
        key_env = os.getenv("DATA_ENCRYPTION_KEY")
        if key_env:
            # 如果是base64编码的字符串，需要解�?
            try:
                return base64.urlsafe_b64decode(key_env)
            except Exception:
                # 如果解码失败，可能是直接的密钥字符串
                return self._derive_key_from_password(key_env.encode(), b"salt")

        # 如果没有环境变量，生成一个新的密�?
        return Fernet.generate_key()

    def _derive_key_from_password(self, password: bytes, salt: bytes) -> bytes:
        """从密码派生密�?""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        return key

    def encrypt_data(self, data: str | bytes) -> str:
        """加密数据"""
        if isinstance(data, str):
            data = data.encode("utf-8")

        encrypted_data = self.cipher_suite.encrypt(data)
        return base64.urlsafe_b64encode(encrypted_data).decode("utf-8")

    def decrypt_data(self, encrypted_data: str) -> str:
        """解密数据"""
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode("utf-8"))
            decrypted_data = self.cipher_suite.decrypt(encrypted_bytes)
            return decrypted_data.decode("utf-8")
        except Exception as e:
            raise ValueError(f"数据解密失败: {e}")

    def encrypt_sensitive_fields(self, data: dict[str, Any]) -> dict[str, Any]:
        """加密敏感字段"""
        encrypted_data = data.copy()
        for field in ["owner_name", "contact_info"]:
            if field in encrypted_data and encrypted_data[field]:
                try:
                    encrypted_data[field] = self.encrypt_data(
                        str(encrypted_data[field])
                    )
                except Exception as e:
                    print(f"加密字段 {field} 失败: {e}")
        return encrypted_data

    def decrypt_sensitive_fields(self, data: dict[str, Any]) -> dict[str, Any]:
        """解密敏感字段"""
        decrypted_data = data.copy()
        for field in ["owner_name", "contact_info"]:
            if field in decrypted_data and decrypted_data[field]:
                try:
                    decrypted_data[field] = self.decrypt_data(
                        str(decrypted_data[field])
                    )
                except Exception as e:
                    print(f"解密字段 {field} 失败: {e}")
        return decrypted_data


class DataMaskingService:
    """数据脱敏服务"""

    @staticmethod
    def mask_email(email: str) -> str:
        """邮箱脱敏"""
        if not email or "@" not in email:
            return email

        parts = email.split("@")
        username = parts[0]
        domain = parts[1]

        if len(username) <= 2:
            masked_username = "*" * len(username)
        else:
            masked_username = username[0] + "*" * (len(username) - 2) + username[-1]

        return f"{masked_username}@{domain}"

    @staticmethod
    def mask_phone(phone: str) -> str:
        """手机号脱�?""
        if not phone or len(phone) < 11:
            return phone

        # 保留�?位和�?�?
        return phone[:3] + "****" + phone[-4:]

    @staticmethod
    def mask_id_card(id_card: str) -> str:
        """身份证号脱敏"""
        if not id_card or len(id_card) < 18:
            return id_card

        # 保留�?位和�?�?
        return id_card[:6] + "**********" + id_card[-4:]

    @staticmethod
    def mask_bank_card(card_number: str) -> str:
        """银行卡号脱敏"""
        if not card_number:
            return card_number

        # 保留�?位和�?�?
        if len(card_number) > 10:
            return card_number[:6] + "*" * (len(card_number) - 10) + card_number[-4:]
        else:
            return "*" * len(card_number)

    @staticmethod
    def mask_name(name: str) -> str:
        """姓名脱敏"""
        if not name:
            return name

        if len(name) == 1:
            return "*"
        elif len(name) == 2:
            return name[0] + "*"
        else:
            return name[0] + "*" * (len(name) - 2) + name[-1]


# 创建全局实例
encryption_service = DataEncryptionService()
masking_service = DataMaskingService()


def get_encryption_service() -> DataEncryptionService:
    """获取加密服务实例"""
    return encryption_service


def get_masking_service() -> DataMaskingService:
    """获取数据脱敏服务实例"""
    return masking_service
