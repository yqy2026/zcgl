#!/usr/bin/env python3
"""
生成admin123密码的bcrypt哈希
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from passlib.context import CryptContext

# 密码哈希上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """生成密码哈希"""
    return pwd_context.hash(password)

if __name__ == "__main__":
    password = "admin123"
    password_hash = hash_password(password)
    print(f"密码: {password}")
    print(f"哈希: {password_hash}")

    # 直接更新数据库
    import sqlite3
    conn = sqlite3.connect('data/land_property.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET password_hash = ? WHERE username = 'admin'", (password_hash,))
    conn.commit()
    conn.close()
    print("数据库已更新")