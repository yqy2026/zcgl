#!/usr/bin/env python3
"""
生产环境配置验证脚本

在部署到生产环境之前运行此脚本，确保所有安全配置项已正确设置。

用法:
    python scripts/validate_production_config.py

退出码:
    0 - 所有检查通过
    1 - 发现安全问题，无法部署
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.config import settings
from src.core.jwt_security import validate_current_jwt_config, jwt_security
from src.core.encryption import EncryptionKeyManager


class ProductionConfigValidator:
    """生产环境配置验证器"""

    def __init__(self):
        self.issues = []
        self.warnings = []
        self.passed_checks = []

    def validate_all(self) -> bool:
        """
        运行所有验证检查

        Returns:
            bool: True 如果所有检查通过，False 如果有阻塞性问题
        """
        print("=" * 70)
        print("生产环境配置验证")
        print("=" * 70)
        print()

        # 检查环境变量
        self._check_environment()

        # 检查 SECRET_KEY
        self._check_secret_key()

        # 检查 JWT 配置
        self._check_jwt_config()

        # 检查数据库配置
        self._check_database_config()

        # 检查加密配置
        self._check_encryption_config()

        # 检查调试模式
        self._check_debug_mode()

        # 检查 CORS 配置
        self._check_cors_config()

        # 输出结果
        self._print_results()

        return len(self.issues) == 0

    def _check_environment(self):
        """检查环境变量设置"""
        env = os.getenv("ENVIRONMENT", "production")

        if env != "production":
            self.warnings.append(
                f"ENVIRONMENT 设置为 '{env}'，但您正在运行生产配置验证。"
                "确保生产环境设置 ENVIRONMENT=production"
            )
        else:
            self.passed_checks.append("✓ ENVIRONMENT 正确设置为 'production'")

    def _check_secret_key(self):
        """检查 SECRET_KEY 安全性"""
        try:
            secret_key = settings.SECRET_KEY

            # 检查长度
            if len(secret_key) < 32:
                self.issues.append(
                    f"SECRET_KEY 长度不足: {len(secret_key)} 字符 (最少需要 32 字符)"
                )
            else:
                self.passed_checks.append(f"✓ SECRET_KEY 长度符合要求 ({len(secret_key)} 字符)")

            # 检查弱密钥模式
            weak_patterns = [
                "EMERGENCY", "REPLACE-WITH", "dev-secret-key",
                "your-secret-key", "secret-key", "test-key",
                "example", "default", "changeme", "change-this"
            ]

            found_patterns = [p for p in weak_patterns if p.lower() in secret_key.lower()]
            if found_patterns:
                self.issues.append(
                    f"SECRET_KEY 包含弱密钥模式: {', '.join(found_patterns)}"
                )
            else:
                self.passed_checks.append("✓ SECRET_KEY 不包含已知弱密钥模式")

            # 使用 JWT 安全验证
            validation_result = jwt_security.validate_secret_key(secret_key)
            if not validation_result["is_valid"]:
                for issue in validation_result["issues"]:
                    self.issues.append(f"SECRET_KEY 安全问题: {issue}")

            if validation_result["suggestions"]:
                for suggestion in validation_result["suggestions"]:
                    self.warnings.append(f"SECRET_KEY 建议: {suggestion}")

        except Exception as e:
            self.issues.append(f"无法验证 SECRET_KEY: {e}")

    def _check_jwt_config(self):
        """检查 JWT 配置"""
        try:
            jwt_result = validate_current_jwt_config()

            if not jwt_result["config_valid"]:
                for issue in jwt_result["issues"]:
                    self.issues.append(f"JWT 配置问题: {issue}")
            else:
                self.passed_checks.append("✓ JWT 配置验证通过")

            for recommendation in jwt_result.get("recommendations", []):
                self.warnings.append(f"JWT 建议: {recommendation}")

            # 检查令牌有效期
            access_token_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
            if access_token_minutes > 120:
                self.warnings.append(
                    f"访问令牌有效期过长: {access_token_minutes} 分钟 (建议不超过 120 分钟)"
                )
            else:
                self.passed_checks.append(f"✓ 访问令牌有效期合理 ({access_token_minutes} 分钟)")

        except Exception as e:
            self.issues.append(f"JWT 配置验证失败: {e}")

    def _check_database_config(self):
        """检查数据库配置"""
        db_url = settings.DATABASE_URL

        if db_url.startswith("sqlite"):
            self.warnings.append(
                "使用 SQLite 数据库。生产环境强烈建议使用 PostgreSQL 或 MySQL。"
            )
        elif db_url.startswith("postgresql") or db_url.startswith("mysql"):
            self.passed_checks.append(f"✓ 使用生产级数据库 ({db_url.split(':')[0]})")
        else:
            self.warnings.append(f"检测到非标准数据库配置: {db_url.split(':')[0]}")

        # 检查数据库 URL 是否包含密码
        if "@" in db_url and ":" in db_url.split("@")[0]:
            # 数据库 URL 包含认证信息，这是正常的
            self.passed_checks.append("✓ 数据库配置包含认证信息")
        elif not db_url.startswith("sqlite"):
            self.warnings.append("数据库配置可能缺少认证信息")

    def _check_encryption_config(self):
        """检查数据加密配置"""
        key_manager = EncryptionKeyManager()

        if not key_manager.is_available():
            self.warnings.append(
                "DATA_ENCRYPTION_KEY 未设置。敏感数据（PII）将以明文存储。"
                "强烈建议设置加密密钥以保护手机号、身份证号等敏感信息。"
            )
        else:
            key = key_manager.get_key()
            if key and len(key) >= 32:
                self.passed_checks.append(
                    f"✓ 数据加密已启用 (密钥版本: {key_manager.get_version()})"
                )
            else:
                self.issues.append(
                    f"DATA_ENCRYPTION_KEY 长度不足 ({len(key) if key else 0} 字节，需要至少 32 字节)"
                )

    def _check_debug_mode(self):
        """检查调试模式"""
        if settings.DEBUG:
            self.issues.append(
                "DEBUG 模式已启用！生产环境必须设置 DEBUG=false"
            )
        else:
            self.passed_checks.append("✓ DEBUG 模式已禁用")

    def _check_cors_config(self):
        """检查 CORS 配置"""
        cors_origins = settings.CORS_ORIGINS

        # 检查是否包含通配符
        if "*" in cors_origins:
            self.issues.append(
                "CORS_ORIGINS 包含通配符 '*'，这会允许任何域访问 API。"
                "生产环境必须指定具体的域名。"
            )
        # 检查是否包含 localhost
        elif any("localhost" in origin for origin in cors_origins):
            self.warnings.append(
                "CORS_ORIGINS 包含 localhost 域名。确保这是预期的配置。"
            )
        else:
            self.passed_checks.append(f"✓ CORS 配置了 {len(cors_origins)} 个具体域名")

    def _print_results(self):
        """打印验证结果"""
        print()
        print("=" * 70)
        print("验证结果")
        print("=" * 70)
        print()

        # 打印通过的检查
        if self.passed_checks:
            print("✅ 通过的检查:")
            for check in self.passed_checks:
                print(f"  {check}")
            print()

        # 打印警告
        if self.warnings:
            print("⚠️  警告 (建议修复但不阻塞部署):")
            for warning in self.warnings:
                print(f"  - {warning}")
            print()

        # 打印阻塞性问题
        if self.issues:
            print("❌ 严重问题 (必须修复才能部署):")
            for issue in self.issues:
                print(f"  - {issue}")
            print()

        # 总结
        print("=" * 70)
        if self.issues:
            print("❌ 验证失败！发现 {} 个严重问题。".format(len(self.issues)))
            print("   请修复上述问题后再部署到生产环境。")
        else:
            print("✅ 验证通过！配置符合生产环境要求。")
            if self.warnings:
                print(f"   建议处理 {len(self.warnings)} 个警告以提高安全性。")
        print("=" * 70)
        print()


def main():
    """主函数"""
    try:
        validator = ProductionConfigValidator()
        success = validator.validate_all()

        # 根据验证结果设置退出码
        sys.exit(0 if success else 1)

    except Exception as e:
        print(f"验证过程中发生错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
