"""
临时脚本: 创建测试用户
"""
import sys
import uuid
from datetime import datetime, UTC
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

import bcrypt
from sqlalchemy import create_engine, text

# 数据库连接
DATABASE_URL = "sqlite:///D:/work/zcgl/backend/data/land_property.db"
engine = create_engine(DATABASE_URL)

# 生成密码哈希 (密码: admin123)
password = "admin123"
salt = bcrypt.gensalt()
password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

# 创建用户
user_id = str(uuid.uuid4())
now = datetime.now(UTC)

with engine.connect() as conn:
    try:
        # 插入admin用户
        conn.execute(text("""
            INSERT INTO users (
                id, username, email, full_name, password_hash,
                role, is_active, is_locked, failed_login_attempts,
                password_last_changed, created_at, updated_at, created_by, updated_by
            ) VALUES (
                :id, :username, :email, :full_name, :password_hash,
                :role, :is_active, :is_locked, :failed_login_attempts,
                :password_last_changed, :created_at, :updated_at, :created_by, :updated_by
            )
        """), {
            "id": user_id,
            "username": "admin",
            "email": "admin@example.com",
            "full_name": "系统管理员",
            "password_hash": password_hash,
            "role": "admin",
            "is_active": True,
            "is_locked": False,
            "failed_login_attempts": 0,
            "password_last_changed": now,
            "created_at": now,
            "updated_at": now,
            "created_by": "system",
            "updated_by": "system"
        })
        conn.commit()
        print(f"SUCCESS: Created user admin (password: admin123)")
        print(f"   User ID: {user_id}")
    except Exception as e:
        print(f"ERROR: Failed to create user: {e}")
        # 检查用户是否已存在
        result = conn.execute(text("SELECT username, email, is_active FROM users WHERE username = 'admin'"))
        user = result.fetchone()
        if user:
            print(f"INFO: User already exists: username={user[0]}, email={user[1]}, active={user[2]}")
