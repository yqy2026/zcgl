"""
临时脚本: 创建测试用户
"""

import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))


import bcrypt
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# 数据库连接
# 先加载同目录下的 .env
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=str(env_path))
else:
    # 尝试加载项目根目录的 .env
    root_env = Path(__file__).parent.parent / ".env"
    if root_env.exists():
        load_dotenv(dotenv_path=str(root_env))

from src.core.config import settings

DATABASE_URL = settings.DATABASE_URL
engine = create_engine(DATABASE_URL)

# 生成密码哈希 (密码: admin123)
password = "admin123"
salt = bcrypt.gensalt()
password_hash = bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

# 创建用户
user_id = str(uuid.uuid4())
now = datetime.now(UTC)

with engine.connect() as conn:
    try:
        role_result = conn.execute(
            text(
                """
            SELECT id
            FROM roles
            WHERE name IN ('super_admin', 'admin')
            ORDER BY CASE WHEN name = 'super_admin' THEN 0 ELSE 1 END
            LIMIT 1
            """
            )
        )
        role_row = role_result.fetchone()
        if role_row is None:
            raise RuntimeError("No admin role found in roles table.")
        role_id = role_row[0]

        conn.execute(
            text(
                """
            INSERT INTO users (
                id, username, email, full_name, password_hash,
                is_active, is_locked, failed_login_attempts,
                password_last_changed, created_at, updated_at, created_by, updated_by
            ) VALUES (
                :id, :username, :email, :full_name, :password_hash,
                :is_active, :is_locked, :failed_login_attempts,
                :password_last_changed, :created_at, :updated_at, :created_by, :updated_by
            )
        """
            ),
            {
                "id": user_id,
                "username": "admin",
                "email": "admin@example.com",
                "full_name": "系统管理员",
                "password_hash": password_hash,
                "is_active": True,
                "is_locked": False,
                "failed_login_attempts": 0,
                "password_last_changed": now,
                "created_at": now,
                "updated_at": now,
                "created_by": "system",
                "updated_by": "system",
            },
        )
        conn.execute(
            text(
                """
            INSERT INTO user_role_assignments (
                id, user_id, role_id, assigned_by, assigned_at, is_active, created_at, updated_at
            ) VALUES (
                :id, :user_id, :role_id, :assigned_by, :assigned_at, :is_active, :created_at, :updated_at
            )
        """
            ),
            {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "role_id": role_id,
                "assigned_by": "system",
                "assigned_at": now,
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            },
        )
        conn.commit()
        print("SUCCESS: Created user admin (password: admin123)")
        print(f"   User ID: {user_id}")
    except Exception as e:
        print(f"ERROR: Failed to create user: {e}")
        result = conn.execute(
            text(
                "SELECT username, email, is_active FROM users WHERE username = 'admin'"
            )
        )
        user = result.fetchone()
        if user:
            print(
                f"INFO: User already exists: username={user[0]}, email={user[1]}, active={user[2]}"
            )
