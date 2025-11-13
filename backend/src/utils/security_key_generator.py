"""
安全密钥生成和管理工具
用于生成和验证JWT密钥、数据库密码等安全配置
"""

import secrets
import string
from datetime import datetime, UTC
from pathlib import Path
from typing import Dict, Any

import hashlib
import logging

logger = logging.getLogger(__name__)


class SecurityKeyGenerator:
    """安全密钥生成器"""

    @staticmethod
    def generate_jwt_secret_key(length: int = 64) -> str:
        """
        生成JWT密钥

        Args:
            length: 密钥长度，默认64字符

        Returns:
            str: 生成的安全密钥
        """
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    @staticmethod
    def generate_database_password(length: int = 32) -> str:
        """
        生成数据库密码

        Args:
            length: 密码长度，默认32字符

        Returns:
            str: 生成的安全密码
        """
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*()_+-=[]{}|;:,.<>?"
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    @staticmethod
    def generate_api_key(length: int = 32) -> str:
        """
        生成API密钥

        Args:
            length: 密钥长度，默认32字符

        Returns:
            str: 生成的API密钥
        """
        return secrets.token_urlsafe(length)

    @staticmethod
    def generate_session_id() -> str:
        """
        生成会话ID

        Returns:
            str: 生成的会话ID
        """
        return secrets.token_urlsafe(32)

    @staticmethod
    def hash_password(password: str, salt: str | None = None) -> Dict[str, str]:
        """
        哈希密码

        Args:
            password: 原始密码
            salt: 盐值，如果不提供则自动生成

        Returns:
            Dict: 包含哈希密码和盐值的字典
        """
        if salt is None:
            salt = secrets.token_hex(16)

        # 使用PBKDF2进行密码哈希
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # 迭代次数
        )

        return {
            'hash': password_hash.hex(),
            'salt': salt
        }

    @staticmethod
    def verify_password(password: str, stored_hash: str, salt: str) -> bool:
        """
        验证密码

        Args:
            password: 输入的密码
            stored_hash: 存储的哈希值
            salt: 盐值

        Returns:
            bool: 密码是否正确
        """
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        )

        return password_hash.hex() == stored_hash


class SecurityConfigManager:
    """安全配置管理器"""

    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.generator = SecurityKeyGenerator()

    def generate_secure_env_file(self, env_type: str = "production") -> Dict[str, str]:
        """
        生成安全的环境变量配置

        Args:
            env_type: 环境类型 (development/staging/production)

        Returns:
            Dict: 环境变量配置
        """
        timestamp = datetime.now(UTC).isoformat()

        config = {
            # JWT配置
            "SECRET_KEY": self.generator.generate_jwt_secret_key(),
            "ALGORITHM": "HS256",
            "ACCESS_TOKEN_EXPIRE_MINUTES": "15",
            "REFRESH_TOKEN_EXPIRE_DAYS": "7",
            "JWT_ISSUER": "zcgl-system",
            "JWT_AUDIENCE": "zcgl-users",
            "ENABLE_JTI_CLAIM": "true",
            "TOKEN_BLACKLIST_ENABLED": "true",

            # 数据库配置（如果需要）
            # "DATABASE_PASSWORD": self.generator.generate_database_password(),

            # API安全配置
            "API_KEY": self.generator.generate_api_key(),

            # 会话配置
            "SESSION_SECRET": self.generator.generate_jwt_secret_key(32),

            # 环境配置
            "ENVIRONMENT": env_type,
            "DEBUG": "false" if env_type == "production" else "true",

            # 安全配置
            "MIN_PASSWORD_LENGTH": "8",
            "MAX_FAILED_ATTEMPTS": "5",
            "LOCKOUT_DURATION": "900",
            "MAX_CONCURRENT_SESSIONS": "5",
            "AUDIT_LOG_RETENTION_DAYS": "90",

            # 元数据
            "CONFIG_GENERATED_AT": timestamp,
            "CONFIG_VERSION": "1.0.0",
        }

        return config

    def save_env_file(self, config: Dict[str, str], filename: str) -> bool:
        """
        保存环境变量配置到文件

        Args:
            config: 配置字典
            filename: 文件名

        Returns:
            bool: 是否保存成功
        """
        try:
            self.config_dir.mkdir(exist_ok=True)
            env_file = self.config_dir / filename

            with open(env_file, 'w', encoding='utf-8') as f:
                f.write("# 自动生成的安全配置文件\n")
                f.write(f"# 生成时间: {config.get('CONFIG_GENERATED_AT', 'Unknown')}\n")
                f.write("# 请妥善保管此文件，不要提交到版本控制系统\n\n")

                for key, value in config.items():
                    if not key.startswith('CONFIG_'):  # 跳过元数据
                        f.write(f"{key}={value}\n")

            logger.info(f"安全配置已保存到: {env_file}")
            return True

        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
            return False

    def generate_admin_credentials(self) -> Dict[str, Any]:
        """
        生成管理员凭据

        Returns:
            Dict: 管理员凭据信息
        """
        admin_password = self.generator.generate_database_password(16)
        password_info = self.generator.hash_password(admin_password)

        credentials = {
            "username": "admin",
            "password": admin_password,
            "password_hash": password_info['hash'],
            "password_salt": password_info['salt'],
            "email": "admin@zcgl.system",
            "full_name": "系统管理员",
            "role": "admin",
            "is_active": True,
            "created_at": datetime.now(UTC).isoformat()
        }

        return credentials

    def create_secure_admin_user_script(self, credentials: Dict[str, Any]) -> str:
        """
        创建创建管理员用户的SQL脚本

        Args:
            credentials: 管理员凭据

        Returns:
            str: SQL脚本
        """
        script = f"""
-- 创建管理员用户的SQL脚本
-- 生成时间: {credentials['created_at']}

-- 注意: 此脚本包含敏感信息，使用后请立即删除

INSERT OR REPLACE INTO users (
    id,
    username,
    email,
    full_name,
    password_hash,
    password_salt,
    role,
    is_active,
    created_at,
    updated_at
) VALUES (
    'admin-{datetime.now(UTC).strftime("%Y%m%d%H%M%S")}',
    '{credentials['username']}',
    '{credentials['email']}',
    '{credentials['full_name']}',
    '{credentials['password_hash']}',
    '{credentials['password_salt']}',
    '{credentials['role']}',
    {1 if credentials['is_active'] else 0},
    '{credentials['created_at']}',
    '{credentials['created_at']}'
);

-- 管理员登录信息:
-- 用户名: {credentials['username']}
-- 密码: {credentials['password']}
--
-- 请登录后立即修改密码！
"""

        return script

    def validate_jwt_key_strength(self, secret_key: str) -> Dict[str, Any]:
        """
        验证JWT密钥强度

        Args:
            secret_key: JWT密钥

        Returns:
            Dict: 验证结果
        """
        result = {
            "is_strong": False,
            "score": 0,
            "recommendations": []
        }

        # 长度检查
        if len(secret_key) >= 64:
            result["score"] += 25
        else:
            result["recommendations"].append("密钥长度应至少64字符")

        # 字符多样性检查
        has_upper = any(c.isupper() for c in secret_key)
        has_lower = any(c.islower() for c in secret_key)
        has_digit = any(c.isdigit() for c in secret_key)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in secret_key)

        if has_upper:
            result["score"] += 25
        else:
            result["recommendations"].append("密钥应包含大写字母")

        if has_lower:
            result["score"] += 25
        else:
            result["recommendations"].append("密钥应包含小写字母")

        if has_digit:
            result["score"] += 12.5
        else:
            result["recommendations"].append("密钥应包含数字")

        if has_special:
            result["score"] += 12.5
        else:
            result["recommendations"].append("密钥应包含特殊字符")

        # 常见弱密钥检查
        weak_keys = [
            "EMERGENCY-ONLY-REPLACE-WITH-ENV-SECRET-KEY-NOW",
            "dev-secret-key-DO-NOT-USE-IN-PRODUCTION-REPLACE-WITH-ENV-VAR",
            "dev-secret-key-change-in-production",
            "secret",
            "password",
            "123456",
        ]

        if secret_key not in weak_keys:
            result["score"] += 0
        else:
            result["score"] = 0
            result["recommendations"].insert(0, "使用了已知弱密钥，必须立即更换！")

        result["is_strong"] = result["score"] >= 75

        return result


def main():
    """主函数 - 生成安全配置"""
    manager = SecurityConfigManager()

    print("=" * 60)
    print("Security Configuration Generator")
    print("=" * 60)

    # 生成环境配置
    env_config = manager.generate_secure_env_file("production")

    # 保存到文件
    if manager.save_env_file(env_config, "backend.env.secure"):
        print("[OK] Security environment configuration generated")
    else:
        print("[ERROR] Environment configuration generation failed")

    # 生成管理员凭据
    admin_credentials = manager.generate_admin_credentials()

    print("\n" + "=" * 60)
    print("Administrator Credentials")
    print("=" * 60)
    print(f"Username: {admin_credentials['username']}")
    print(f"Password: {admin_credentials['password']}")
    print(f"Email: {admin_credentials['email']}")
    print("\n[WARNING] Please save these credentials immediately and change password after first login!")

    # 创建SQL脚本
    sql_script = manager.create_secure_admin_user_script(admin_credentials)
    sql_file = Path("config/create_admin_user.sql")

    try:
        with open(sql_file, 'w', encoding='utf-8') as f:
            f.write(sql_script)
        print(f"[OK] SQL script generated: {sql_file}")
    except Exception as e:
        print(f"[ERROR] SQL script generation failed: {e}")

    # 验证当前密钥强度
    print("\n" + "=" * 60)
    print("JWT Key Strength Validation")
    print("=" * 60)

    validation = manager.validate_jwt_key_strength(env_config["SECRET_KEY"])
    print(f"Key strength: {'[STRONG]' if validation['is_strong'] else '[WEAK]'}")
    print(f"Strength score: {validation['score']}/100")

    if validation['recommendations']:
        print("Recommendations:")
        for rec in validation['recommendations']:
            print(f"  - {rec}")

    print("\n" + "=" * 60)
    print("Configuration generation completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()