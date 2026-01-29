#!/usr/bin/env python3
"""
安全配置验证器
用于检查关键安全配置是否正确设置
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from core.config import settings


def check_secret_key_strength(secret_key: str) -> tuple[bool, str]:
    """检查密钥强度"""
    if not secret_key:
        return False, "密钥为空"

    if secret_key == "dev-secret-key-DO-NOT-USE-IN-PRODUCTION-REPLACE-WITH-ENV-VAR":
        return False, "使用默认开发密钥，生产环境禁止使用"

    if secret_key == "your-secret-key-change-in-production":
        return False, "使用示例密钥，存在安全风险"

    if len(secret_key) < 32:
        return False, "密钥长度不足32字符"

    # 检查密钥复杂度
    has_upper = any(c.isupper() for c in secret_key)
    has_lower = any(c.islower() for c in secret_key)
    has_digit = any(c.isdigit() for c in secret_key)
    has_special = any(c in "-_@" for c in secret_key)

    if not (has_upper and has_lower and has_digit and has_special):
        return False, "密钥复杂度不足，建议包含大小写字母、数字和特殊字符"

    return True, "密钥强度合格"


def check_database_security(database_url: str) -> tuple[bool, str]:
    """检查数据库配置安全性"""
    if not database_url:
        return False, "数据库连接字符串为空"

    if "localhost" in database_url and os.getenv("ENVIRONMENT") == "production":
        return False, "生产环境不应使用localhost数据库"

    return True, "数据库配置合格"


def check_cors_security(cors_origins: list[str]) -> tuple[bool, str]:
    """检查CORS配置安全性"""
    if not cors_origins:
        return False, "CORS配置为空"

    environment = os.getenv("ENVIRONMENT", "development")

    if environment == "production":
        # 检查是否包含不安全的localhost配置
        localhost_origins = [origin for origin in cors_origins if "localhost" in origin]
        if localhost_origins:
            return False, f"生产环境包含不安全的localhost配置: {localhost_origins}"

        # 检查是否使用了通配符
        if "*" in cors_origins:
            return False, "生产环境不应使用通配符CORS配置"

    return True, "CORS配置合格"


def main():
    """主验证函数"""
    print("🔍 开始安全配置验证...")
    print("=" * 60)

    all_passed = True
    warnings = []

    # 1. 检查JWT密钥
    print("🔐 检查JWT密钥配置...")
    secret_key = settings.SECRET_KEY
    is_valid, message = check_secret_key_strength(secret_key)

    if is_valid:
        print(f"   ✅ {message}")
    else:
        print(f"   ❌ {message}")
        all_passed = False

    # 2. 检查数据库配置
    print("\n🗄️  检查数据库配置...")
    database_url = settings.DATABASE_URL
    is_valid, message = check_database_security(database_url)

    if is_valid:
        print(f"   ✅ {message}")
    else:
        print(f"   ❌ {message}")
        all_passed = False

    # 3. 检查CORS配置
    print("\n🌐 检查CORS配置...")
    cors_origins = settings.CORS_ORIGINS
    is_valid, message = check_cors_security(cors_origins)

    if is_valid:
        print(f"   ✅ {message}")
    else:
        print(f"   ❌ {message}")
        all_passed = False

    # 4. 环境特定检查
    print("\n🏭 检查环境配置...")
    environment = os.getenv("ENVIRONMENT", "development")
    debug_mode = settings.DEBUG

    if environment == "production" and debug_mode:
        print("   ❌ 生产环境不应开启DEBUG模式")
        all_passed = False
    elif environment == "production":
        print("   ✅ 生产环境配置正确")
    else:
        print(f"   ℹ️  当前环境: {environment} (开发模式)")

    # 5. 检查文件上传配置
    print("\n📁 检查文件上传配置...")
    max_file_size = settings.MAX_FILE_SIZE
    if max_file_size > 100 * 1024 * 1024:  # 100MB
        warnings.append(f"文件上传大小限制过高: {max_file_size / (1024 * 1024):.1f}MB")
        print(f"   ⚠️  文件上传大小限制过高: {max_file_size / (1024 * 1024):.1f}MB")
    else:
        print(f"   ✅ 文件上传大小限制: {max_file_size / (1024 * 1024):.1f}MB")

    # 输出结果
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 所有关键安全配置检查通过")
    else:
        print("❌ 发现安全配置问题，请立即修复")

    if warnings:
        print("\n⚠️  安全建议:")
        for warning in warnings:
            print(f"   - {warning}")

    # 输出修复建议
    if not all_passed:
        print("\n🛠️  修复建议:")
        print("   1. 设置强安全的SECRET_KEY环境变量")
        print("   2. 配置生产安全的数据库连接")
        print("   3. 限制CORS配置为具体域名")
        print("   4. 生产环境关闭DEBUG模式")

        # 生成安全密钥示例
        import secrets

        new_key = secrets.token_urlsafe(32)
        print(f"\n🔑 建议的新密钥: {new_key}")
        print("   设置方法: export SECRET_KEY='your-new-secret-key'")

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
