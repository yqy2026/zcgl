#!/usr/bin/env python3
"""
数据库架构迁移脚本 - 添加缺失的认证相关字段
"""

import os
import sys
from datetime import datetime

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from sqlalchemy import create_engine, text

from src.database import DATABASE_URL


def migrate_database():
    """执行数据库架构迁移"""
    print("=" * 80)
    print("开始数据库架构迁移")
    print("=" * 80)

    # 创建数据库引擎
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    )

    with engine.connect() as conn:
        # 检查当前数据库版本和表结构
        print("1. 检查当前表结构...")

        # 检查 users 表是否需要更新
        result = conn.execute(text("PRAGMA table_info(users)"))
        columns = [row[1] for row in result.fetchall()]
        print(f"   users表当前字段: {columns}")

        # 需要添加的字段
        missing_columns = []
        required_columns = ["password_history", "password_last_changed"]

        for col in required_columns:
            if col not in columns:
                missing_columns.append(col)

        if missing_columns:
            print(f"2. 添加缺失字段: {missing_columns}")

            # 添加 password_history 字段
            if "password_history" in missing_columns:
                try:
                    conn.execute(
                        text("ALTER TABLE users ADD COLUMN password_history TEXT")
                    )
                    print("   + 添加 password_history 字段")
                except Exception as e:
                    print(f"   - 添加 password_history 字段失败: {e}")

            # 添加 password_last_changed 字段
            if "password_last_changed" in missing_columns:
                try:
                    # SQLite不支持带动态默认值的ALTER TABLE，分两步操作
                    conn.execute(
                        text(
                            "ALTER TABLE users ADD COLUMN password_last_changed DATETIME"
                        )
                    )
                    print("   + 添加 password_last_changed 字段")

                    # 为现有记录设置默认值
                    conn.execute(
                        text(
                            "UPDATE users SET password_last_changed = CURRENT_TIMESTAMP WHERE password_last_changed IS NULL"
                        )
                    )
                    print("   + 设置现有记录的默认值")
                except Exception as e:
                    print(f"   - 添加 password_last_changed 字段失败: {e}")

            # 提交更改
            conn.commit()
            print("   数据库架构更新完成")
        else:
            print("   数据库架构已是最新版本")

        # 验证更新结果
        print("3. 验证更新结果...")
        result = conn.execute(text("PRAGMA table_info(users)"))
        updated_columns = [row[1] for row in result.fetchall()]
        print(f"   更新后users表字段: {updated_columns}")

        # 检查其他可能需要更新的表
        print("4. 检查其他表结构...")

        # 检查 user_role_assignments 表
        try:
            result = conn.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='user_role_assignments'"
                )
            )
            if result.fetchone():
                result = conn.execute(text("PRAGMA table_info(user_role_assignments)"))
                assignment_columns = [row[1] for row in result.fetchall()]
                print(f"   user_role_assignments表字段: {assignment_columns}")
            else:
                print("   user_role_assignments表不存在，将在启动时创建")
        except Exception as e:
            print(f"   检查user_role_assignments表失败: {e}")

        # 检查 roles 表
        try:
            result = conn.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='roles'"
                )
            )
            if result.fetchone():
                result = conn.execute(text("PRAGMA table_info(roles)"))
                role_columns = [row[1] for row in result.fetchall()]
                print(f"   roles表字段: {role_columns}")
            else:
                print("   roles表不存在，将在启动时创建")
        except Exception as e:
            print(f"   检查roles表失败: {e}")

        # 检查 permissions 表
        try:
            result = conn.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='permissions'"
                )
            )
            if result.fetchone():
                result = conn.execute(text("PRAGMA table_info(permissions)"))
                permission_columns = [row[1] for row in result.fetchall()]
                print(f"   permissions表字段: {permission_columns}")
            else:
                print("   permissions表不存在，将在启动时创建")
        except Exception as e:
            print(f"   检查permissions表失败: {e}")

        # 测试基本查询
        print("5. 测试数据库连接...")
        try:
            result = conn.execute(text("SELECT COUNT(*) FROM users"))
            user_count = result.scalar()
            print(f"   用户表记录数: {user_count}")
        except Exception as e:
            print(f"   测试用户表查询失败: {e}")

        print("\n" + "=" * 80)
        print("数据库架构迁移完成")
        print("=" * 80)


if __name__ == "__main__":
    print("开始数据库迁移...")
    print(f"时间: {datetime.now()}")
    print(f"数据库路径: {DATABASE_URL}")

    try:
        migrate_database()
        print(f"迁移完成。时间: {datetime.now()}")
    except Exception as e:
        print(f"迁移失败: {e}")
        import traceback

        traceback.print_exc()
