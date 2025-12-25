"""
组织架构数据库迁移脚本
添加新的组织字段以支持完整的组织管理功能
"""

import os
import sqlite3
from datetime import datetime


def add_organization_columns():
    """为organizations表添加新列"""
    db_path = os.path.join(os.path.dirname(__file__), '..', '..', 'land_property.db')

    try:
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 检查是否已存在code列
        cursor.execute("PRAGMA table_info(organizations)")
        columns = [row[1] for row in cursor.fetchall()]

        # 需要添加的列
        new_columns = [
            ('code', 'VARCHAR(50) NOT NULL DEFAULT ""', '组织编码'),
            ('type', 'VARCHAR(20) NOT NULL DEFAULT "company"', '组织类型'),
            ('status', 'VARCHAR(20) NOT NULL DEFAULT "active"', '状态'),
            ('phone', 'VARCHAR(20)', '联系电话'),
            ('email', 'VARCHAR(100)', '邮箱'),
            ('address', 'VARCHAR(200)', '地址'),
            ('leader_name', 'VARCHAR(50)', '负责人姓名'),
            ('leader_phone', 'VARCHAR(20)', '负责人电话'),
            ('leader_email', 'VARCHAR(100)', '负责人邮箱')
        ]

        # 添加不存在的列
        for column_name, column_def, comment in new_columns:
            if column_name not in columns:
                print(f"添加列: {column_name}")
                cursor.execute(f"ALTER TABLE organizations ADD COLUMN {column_name} {column_def}")

                # 为SQLite添加列注释（通过表注释）
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS organization_columns (
                        column_name TEXT PRIMARY KEY,
                        comment TEXT,
                        created_at TEXT
                    )
                """)

                cursor.execute("""
                    INSERT OR REPLACE INTO organization_columns (column_name, comment, created_at)
                    VALUES (?, ?, ?)
                """, (column_name, comment, datetime.now().isoformat()))

        # 提交事务
        conn.commit()
        print("组织架构数据库迁移完成")

        # 显示当前表结构
        print("\n当前表结构:")
        cursor.execute("PRAGMA table_info(organizations)")
        for row in cursor.fetchall():
            print(f"  {row[1]:15} {row[2]:20} {row[3]:5} {row[4]:10} {row[5] or ''}")

    except Exception as e:
        print(f"迁移失败: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

def create_sample_organizations():
    """创建示例组织数据"""
    db_path = os.path.join(os.path.dirname(__file__), '..', '..', 'land_property.db')

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 检查是否已有数据
        cursor.execute("SELECT COUNT(*) FROM organizations")
        count = cursor.fetchone()[0]

        if count == 0:
            print("\n创建示例组织数据...")

            # 创建示例组织
            sample_orgs = [
                ('公司总部', 'HQ001', 'company', 'active', '010-12345678', 'head@company.com', '北京市朝阳区', '张总', '13800138000', 'ceo@company.com'),
                ('技术部', 'TECH001', 'department', 'active', '010-12345679', 'tech@company.com', '北京市朝阳区', '李经理', '13800138001', 'tech@company.com'),
                ('市场部', 'MKT001', 'department', 'active', '010-12345680', 'market@company.com', '北京市朝阳区', '王经理', '13800138002', 'market@company.com'),
                ('人力资源部', 'HR001', 'department', 'active', '010-12345681', 'hr@company.com', '北京市朝阳区', '赵经理', '13800138003', 'hr@company.com'),
                ('财务部', 'FIN001', 'department', 'active', '010-12345682', 'finance@company.com', '北京市朝阳区', '刘经理', '13800138004', 'finance@company.com')
            ]

            # 插入根级组织
            root_org = sample_orgs[0]
            cursor.execute("""
                INSERT INTO organizations (
                    id, name, code, level, sort_order, type, status, phone, email, address,
                    leader_name, leader_phone, leader_email, description, functions,
                    is_deleted, created_at, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                'root', root_org[0], root_org[1], 1, 0, root_org[2], root_org[3],
                root_org[4], root_org[5], root_org[6], root_org[7], root_org[8],
                root_org[9], '公司总部', '公司总体管理', False, datetime.now().isoformat(), 'system'
            ))

            # 插入子组织
            for i, org in enumerate(sample_orgs[1:], 1):
                cursor.execute("""
                    INSERT INTO organizations (
                        id, name, code, level, sort_order, type, status, phone, email, address,
                        leader_name, leader_phone, leader_email, parent_id, path, description, functions,
                        is_deleted, created_at, created_by
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    f'org_{i}', org[0], org[1], 2, i, org[2], org[3],
                    org[4], org[5], org[6], org[7], org[8], org[9],
                    'root', f'/root/org_{i}', org[0], org[0], False, datetime.now().isoformat(), 'system'
                ))

            conn.commit()
            print("示例组织数据创建完成")
        else:
            print(f"\n已存在 {count} 条组织记录")

    except Exception as e:
        print(f"创建示例数据失败: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("开始组织架构数据库迁移...")
    add_organization_columns()
    create_sample_organizations()
    print("迁移完成！")
