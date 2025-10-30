#!/usr/bin/env python3
import sqlite3

# 直接设置一个有效的admin密码哈希 ("secret")
password_hash = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj6hsZYmQmMa"

conn = sqlite3.connect('data/land_property.db')
cursor = conn.cursor()

# 更新admin密码为"secret"
cursor.execute("UPDATE users SET password_hash = ? WHERE username = 'admin'", (password_hash,))
conn.commit()

# 验证更新
cursor.execute("SELECT username, password_hash FROM users WHERE username = 'admin'")
result = cursor.fetchone()
print(f"用户名: {result[0]}")
print(f"密码哈希: {result[1]}")
print("现在可以使用 admin/secret 登录")

conn.close()