#!/usr/bin/env python3
"""
更新admin用户密码的脚本
"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

import bcrypt
from sqlalchemy import text

from database import get_db


def update_admin_password():
    """更新admin用户的密码"""

    # 新密码
    password = "Admin123!@#"

    # 生成bcrypt哈希
    salt = bcrypt.gensalt(rounds=12)
    password_hash = bcrypt.hashpw(password.encode('utf-8'), salt)
    password_hash_str = password_hash.decode('utf-8')

    print("Password: Admin123!@#")
    print(f"Generated hash: {password_hash_str}")

    # 更新数据库
    db = next(get_db())
    try:
        # 使用text()包装SQL语句
        update_sql = text("UPDATE users SET password_hash = :password_hash, updated_at = :updated_at WHERE username = :username")
        db.execute(update_sql, {
            'password_hash': password_hash_str,
            'updated_at': '2025-11-09T22:00:00',
            'username': 'admin'
        })
        db.commit()
        print("Admin user password updated successfully")

        # 验证更新
        select_sql = text("SELECT username, password_hash FROM users WHERE username = :username")
        result = db.execute(select_sql, {'username': 'admin'}).fetchone()
        if result:
            print(f"Verification - Username: {result[0]}")
            print(f"Verification - Hash: {result[1][:50]}...")
            print("Update verification successful")
        else:
            print("Verification failed: admin user not found")

    except Exception as e:
        print(f"Update failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    update_admin_password()
