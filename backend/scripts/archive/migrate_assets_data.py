#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据迁移脚本 - 从旧数据库迁移到新数据库
解决Analytics模块数据缺失问题
"""

import sqlite3
import os
import sys
from datetime import datetime
from pathlib import Path

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

def migrate_assets_data():
    """将旧数据库的资产数据迁移到新数据库"""

    # 数据库路径 - 使用绝对路径
    old_db_path = os.path.abspath("./database/assets.db")
    new_db_path = os.path.abspath("./data/land_property.db")

    print("开始数据迁移...")
    print(f"源数据库: {old_db_path}")
    print(f"目标数据库: {new_db_path}")

    # 检查源数据库是否存在
    if not os.path.exists(old_db_path):
        print(f"错误: 源数据库不存在: {old_db_path}")
        return False

    # 检查目标数据库是否存在
    if not os.path.exists(new_db_path):
        print(f"错误: 目标数据库不存在: {new_db_path}")
        return False

    try:
        # 连接两个数据库
        old_conn = sqlite3.connect(old_db_path)
        new_conn = sqlite3.connect(new_db_path)

        old_cursor = old_conn.cursor()
        new_cursor = new_conn.cursor()

        # 读取旧数据
        print("读取旧数据库中的资产数据...")
        old_cursor.execute("SELECT * FROM assets")
        old_assets = old_cursor.fetchall()

        if not old_assets:
            print("警告: 旧数据库中没有资产数据")
            return False

        print(f"找到 {len(old_assets)} 条资产记录")

        # 获取旧数据库的列名
        old_cursor.execute("PRAGMA table_info(assets)")
        old_columns = [row[1] for row in old_cursor.fetchall()]

        # 字段映射：旧字段 -> 新字段
        field_mapping = {
            'id': 'id',
            'property_name': 'property_name',
            'ownership_entity': 'ownership_entity',
            'management_entity': 'notes',  # 管理实体存储到备注中
            'address': 'address',
            'land_area': 'land_area',
            'actual_property_area': 'actual_property_area',
            'rentable_area': 'rentable_area',
            'rented_area': 'rented_area',
            'unrented_area': 'unrented_area',
            'non_commercial_area': 'non_commercial_area',
            'ownership_status': 'ownership_status',
            'certificated_usage': 'certificated_usage',
            'actual_usage': 'actual_usage',
            'business_category': 'business_category',
            'usage_status': 'usage_status',
            'is_litigated': 'is_litigated',
            'property_nature': 'property_nature',
            'business_model': 'business_model',
            'include_in_occupancy_rate': 'include_in_occupancy_rate',
            'lease_contract': 'lease_contract_number',
            'current_contract_start_date': 'contract_start_date',
            'current_contract_end_date': 'contract_end_date',
            'tenant_name': 'tenant_name',
            'ownership_category': 'ownership_category',
            'wuyang_project_name': 'project_name',
            'created_at': 'created_at',
            'updated_at': 'updated_at'
        }

        # 迁移数据
        migrated_count = 0
        for asset in old_assets:
            # 创建字段映射
            old_data_dict = dict(zip(old_columns, asset))

            # 构建新数据
            new_data = {}
            for old_field, new_field in field_mapping.items():
                if old_field in old_data_dict and old_data_dict[old_field] is not None:
                    value = old_data_dict[old_field]

                    # 数据转换
                    if old_field == 'is_litigated' and isinstance(value, str):
                        new_data[new_field] = value == '是'
                    elif old_field == 'include_in_occupancy_rate' and isinstance(value, str):
                        new_data[new_field] = value == '是'
                    elif old_field == 'usage_status' and value == '出租':
                        new_data[new_field] = '已出租'
                    elif old_field == 'ownership_status' and value == '已确权':
                        new_data[new_field] = '正常'
                    else:
                        new_data[new_field] = value

            # 添加必需的字段
            if 'data_status' not in new_data:
                new_data['data_status'] = '正常'
            if 'version' not in new_data:
                new_data['version'] = 1
            if 'created_by' not in new_data:
                new_data['created_by'] = 'system_migration'
            if 'updated_by' not in new_data:
                new_data['updated_by'] = 'system_migration'

            # 设置默认值
            default_fields = {
                'is_litigated': False,
                'is_sublease': False,
                'operation_status': '正常',
                'tags': None,
                'audit_notes': None,
                'tenant_id': None,
                'project_id': None,
                'ownership_id': None
            }

            for field, default_value in default_fields.items():
                if field not in new_data:
                    new_data[field] = default_value

            # 构建插入SQL
            columns = list(new_data.keys())
            placeholders = ['?' for _ in columns]
            values = list(new_data.values())

            insert_sql = f"""
            INSERT OR REPLACE INTO assets ({', '.join(columns)})
            VALUES ({', '.join(placeholders)})
            """

            new_cursor.execute(insert_sql, values)
            migrated_count += 1

            print(f"成功迁移资产: {new_data.get('property_name', 'Unknown')}")

        # 提交事务
        new_conn.commit()

        # 关闭连接
        old_conn.close()
        new_conn.close()

        print(f"数据迁移完成！成功迁移 {migrated_count} 条资产记录")
        return True

    except Exception as e:
        print(f"数据迁移失败: {str(e)}")
        return False

def verify_migration():
    """验证迁移结果"""
    print("验证迁移结果...")

    new_db_path = os.path.abspath("./data/land_property.db")
    conn = sqlite3.connect(new_db_path)
    cursor = conn.cursor()

    # 检查资产数量
    cursor.execute("SELECT COUNT(*) FROM assets")
    asset_count = cursor.fetchone()[0]

    # 检查几条记录
    cursor.execute("SELECT id, property_name, data_status FROM assets LIMIT 5")
    sample_assets = cursor.fetchall()

    print(f"新数据库中共有 {asset_count} 条资产记录")

    for asset in sample_assets:
        print(f"  - {asset[1]} (状态: {asset[2]})")

    conn.close()
    return asset_count > 0

if __name__ == "__main__":
    print("=" * 60)
    print("资产数据迁移工具")
    print("=" * 60)

    # 切换到backend目录
    backend_dir = Path(__file__).parent.parent
    os.chdir(backend_dir)

    # 执行迁移
    if migrate_assets_data():
        if verify_migration():
            print("迁移成功！现在可以测试Analytics API了")
        else:
            print("警告: 迁移完成但验证失败")
    else:
        print("迁移失败")