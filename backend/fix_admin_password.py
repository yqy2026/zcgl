#!/usr/bin/env python3
"""
修复管理员密码脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core.database import get_db
from src.models.user import User
from passlib.context import CryptContext
import uuid
from datetime import datetime

# 密码哈希上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """生成密码哈希"""
    return pwd_context.hash(password)

def fix_admin_password():
    """修复管理员密码"""
    db = next(get_db())

    try:
        # 查找admin用户
        admin_user = db.query(User).filter(User.username == "admin").first()

        if not admin_user:
            print("❌ 未找到admin用户")
            return False

        # 生成新的密码哈希 (admin/admin)
        new_password_hash = hash_password("admin")

        # 更新密码
        admin_user.password_hash = new_password_hash
        admin_user.updated_at = datetime.utcnow()

        db.commit()

        print(f"✅ 已更新admin用户密码")
        print(f"   用户名: admin")
        print(f"   密码: admin")
        print(f"   新的密码哈希: {new_password_hash}")

        return True

    except Exception as e:
        print(f"❌ 更新密码失败: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def test_login():
    """测试登录功能"""
    from src.services.auth_service import AuthService

    try:
        result = AuthService.login("admin", "admin")
        if result:
            print("✅ 登录测试成功")
            return True
        else:
            print("❌ 登录测试失败")
            return False
    except Exception as e:
        print(f"❌ 登录测试失败: {e}")
        return False

if __name__ == "__main__":
    print("开始修复admin用户密码...")

    if fix_admin_password():
        print("\n密码修复完成！")
        print("现在可以使用 admin/admin 登录系统")
    else:
        print("\n密码修复失败！")
        sys.exit(1)