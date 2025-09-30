"""
组织架构表结构更新迁移脚本
为现有的organizations表添加缺失的列
"""

import sqlite3
import os
from datetime import datetime

def add_missing_organization_columns():
    """为organizations表添加缺失的列"""
    db_path = os.path.join(os.path.dirname(__file__), '..', 'land_property.db')

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 获取当前表结构
        cursor.execute("PRAGMA table_info(organizations)")
        existing_columns = [col[1] for col in cursor.fetchall()]

        # 需要添加的列
        missing_columns = [
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

        print(f"当前表列数: {len(existing_columns)}")
        print(f"需要添加的列数: {len(missing_columns)}")

        # 添加缺失的列
        added_columns = []
        for col_name, col_def, comment in missing_columns:
            if col_name not in existing_columns:
                print(f"添加列: {col_name}")
                try:
                    cursor.execute(f"ALTER TABLE organizations ADD COLUMN {col_name} {col_def}")
                    added_columns.append(col_name)
                except sqlite3.OperationalError as e:
                    print(f"添加列 {col_name} 失败: {e}")
            else:
                print(f"列 {col_name} 已存在")

        # 提交事务
        conn.commit()
        print(f"成功添加 {len(added_columns)} 个列: {added_columns}")

        # 显示更新后的表结构
        print("\n更新后的表结构:")
        cursor.execute("PRAGMA table_info(organizations)")
        for row in cursor.fetchall():
            nullable = "NOT NULL" if row[3] == 0 else "NULL"
            default_val = f"DEFAULT {row[4]}" if row[4] is not None else ""
            print(f"  {row[1]} ({row[2]}) {nullable} {default_val} -- {row[5] or ''}")

    except Exception as e:
        print(f"迁移失败: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

def create_sample_organizations():
    """创建示例组织数据"""
    db_path = os.path.join(os.path.dirname(__file__), '..', 'land_property.db')

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
                    id, name, code, level, sort_order, parent_id, path, description, functions,
                    is_deleted, created_at, updated_at, created_by, updated_by,
                    type, status, phone, email, address, leader_name, leader_phone, leader_email
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                'root', root_org[0], root_org[1], 1, 0, None, '/root', '公司总部', '公司总体管理',
                False, datetime.now().isoformat(), datetime.now().isoformat(), 'system', 'system',
                root_org[2], root_org[3], root_org[4], root_org[5], root_org[6], root_org[7], root_org[8], root_org[9]
            ))

            # 插入子组织
            for i, org in enumerate(sample_orgs[1:], 1):
                cursor.execute("""
                    INSERT INTO organizations (
                        id, name, code, level, sort_order, parent_id, path, description, functions,
                        is_deleted, created_at, updated_at, created_by, updated_by,
                        type, status, phone, email, address, leader_name, leader_phone, leader_email
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    f'org_{i}', org[0], org[1], 2, i, 'root', f'/root/org_{i}', org[0], org[0],
                    False, datetime.now().isoformat(), datetime.now().isoformat(), 'system', 'system',
                    org[2], org[3], org[4], org[5], org[6], org[7], org[8], org[9]
                ))

            conn.commit()
            print("示例组织数据创建完成")
        else:
            print(f"\n已存在 {count} 条组织记录")

    except Exception as e:
        print(f"创建示例数据失败: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("开始组织架构表结构迁移...")
    add_missing_organization_columns()
    create_sample_organizations()
    print("迁移完成！")