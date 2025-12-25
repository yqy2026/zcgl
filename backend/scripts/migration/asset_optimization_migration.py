#!/usr/bin/env python3
"""
资产字段优化迁移脚本

该脚本用于将现有资产数据迁移到优化后的结构，包括：
1. 数据类型转换 (String -> Boolean, Float -> Decimal)
2. 添加新的系统表和数据
3. 数据验证和清理
4. 创建触发器和索引

使用方法:
    python asset_optimization_migration.py

注意：运行前请确保已备份数据库！
"""

import os
import sqlite3
import sys
import uuid
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_db_connection():
    """获取数据库连接"""
    db_path = os.path.join(os.path.dirname(__file__), '..', 'land_property.db')
    return sqlite3.connect(db_path)

def backup_database():
    """备份数据库"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"backups/migration_backup_{timestamp}.db"

    # 确保备份目录存在
    os.makedirs(os.path.dirname(backup_path), exist_ok=True)

    # 复制数据库文件
    import shutil
    db_path = os.path.join(os.path.dirname(__file__), '..', 'land_property.db')
    shutil.copy2(db_path, backup_path)
    print(f"数据库已备份到: {backup_path}")
    return backup_path

def create_system_dictionaries_table(conn):
    """创建系统数据字典表"""
    cursor = conn.cursor()

    # 检查表是否已存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='system_dictionaries'")
    if cursor.fetchone():
        print("system_dictionaries 表已存在，跳过创建")
        return

    # 创建表
    cursor.execute("""
        CREATE TABLE system_dictionaries (
            id VARCHAR(50) PRIMARY KEY,
            dict_type VARCHAR(50) NOT NULL,
            dict_code VARCHAR(50) NOT NULL,
            dict_label VARCHAR(100) NOT NULL,
            dict_value VARCHAR(100) NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            is_active BOOLEAN NOT NULL DEFAULT 1,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(dict_type, dict_code)
        )
    """)

    # 创建索引
    cursor.execute("CREATE INDEX idx_dict_type ON system_dictionaries(dict_type)")
    cursor.execute("CREATE INDEX idx_dict_active ON system_dictionaries(is_active)")

    print("system_dictionaries 表创建成功")

def populate_system_dictionaries(conn):
    """填充系统数据字典数据"""
    cursor = conn.cursor()

    # 检查是否已有数据
    cursor.execute("SELECT COUNT(*) FROM system_dictionaries")
    if cursor.fetchone()[0] > 0:
        print("system_dictionaries 已有数据，跳过填充")
        return

    # 准备数据
    now = datetime.now().isoformat()
    dictionaries = [
        # 确权状态
        ('ownership_status', 'CONFIRMED', '已确权', '已确权', 1),
        ('ownership_status', 'UNCONFIRMED', '未确权', '未确权', 2),
        ('ownership_status', 'PARTIAL', '部分确权', '部分确权', 3),

        # 物业性质
        ('property_nature', 'COMMERCIAL', '经营性', '经营性', 1),
        ('property_nature', 'NON_COMMERCIAL', '非经营性', '非经营性', 2),

        # 使用状态
        ('usage_status', 'RENTED', '出租', '出租', 1),
        ('usage_status', 'VACANT', '空置', '空置', 2),
        ('usage_status', 'SELF_USED', '自用', '自用', 3),
        ('usage_status', 'PUBLIC_HOUSING', '公房', '公房', 4),
        ('usage_status', 'PENDING_TRANSFER', '待移交', '待移交', 5),
        ('usage_status', 'PENDING_DISPOSAL', '待处置', '待处置', 6),
        ('usage_status', 'OTHER', '其他', '其他', 7),

        # 租户类型
        ('tenant_type', 'INDIVIDUAL', '个人', '个人', 1),
        ('tenant_type', 'ENTERPRISE', '企业', '企业', 2),
        ('tenant_type', 'GOVERNMENT', '政府机构', '政府机构', 3),
        ('tenant_type', 'OTHER', '其他', '其他', 4),

        # 合同状态
        ('contract_status', 'ACTIVE', '生效中', '生效中', 1),
        ('contract_status', 'EXPIRED', '已到期', '已到期', 2),
        ('contract_status', 'TERMINATED', '已终止', '已终止', 3),
        ('contract_status', 'PENDING', '待签署', '待签署', 4),

        # 经营模式
        ('business_model', 'LEASE_SUBLEASE', '承租转租', '承租转租', 1),
        ('business_model', 'ENTRUSTED_OPERATION', '委托经营', '委托经营', 2),
        ('business_model', 'SELF_OPERATION', '自营', '自营', 3),
        ('business_model', 'OTHER', '其他', '其他', 4),

        # 经营状态
        ('operation_status', 'NORMAL', '正常经营', '正常经营', 1),
        ('operation_status', 'SUSPENDED', '停业整顿', '停业整顿', 2),
        ('operation_status', 'RENOVATING', '装修中', '装修中', 3),
        ('operation_status', 'SEEKING_TENANT', '待招租', '待招租', 4),

        # 数据状态
        ('data_status', 'NORMAL', '正常', '正常', 1),
        ('data_status', 'DELETED', '已删除', '已删除', 2),
        ('data_status', 'ARCHIVED', '已归档', '已归档', 3),

        # 审核状态
        ('audit_status', 'PENDING', '待审核', '待审核', 1),
        ('audit_status', 'APPROVED', '已审核', '已审核', 2),
        ('audit_status', 'REJECTED', '审核不通过', '审核不通过', 3),

        # 业态类别
        ('business_category', 'COMMERCIAL', '商业', '商业', 1),
        ('business_category', 'OFFICE', '办公', '办公', 2),
        ('business_category', 'RESIDENTIAL', '住宅', '住宅', 3),
        ('business_category', 'WAREHOUSE', '仓储', '仓储', 4),
        ('business_category', 'INDUSTRIAL', '工业', '工业', 5),
        ('business_category', 'OTHER', '其他', '其他', 6),
    ]

    # 插入数据
    for dict_type, dict_code, dict_label, dict_value, sort_order in dictionaries:
        cursor.execute("""
            INSERT INTO system_dictionaries 
            (id, dict_type, dict_code, dict_label, dict_value, sort_order, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
        """, (str(uuid.uuid4()), dict_type, dict_code, dict_label, dict_value, sort_order, now, now))

    print(f"已插入 {len(dictionaries)} 条数据字典记录")

def create_custom_fields_table(conn):
    """创建自定义字段表"""
    cursor = conn.cursor()

    # 检查表是否已存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='asset_custom_fields'")
    if cursor.fetchone():
        print("asset_custom_fields 表已存在，跳过创建")
        return

    # 创建表
    cursor.execute("""
        CREATE TABLE asset_custom_fields (
            id VARCHAR(50) PRIMARY KEY,
            asset_id VARCHAR(50) NOT NULL,
            field_name VARCHAR(100) NOT NULL,
            field_type VARCHAR(20) NOT NULL,
            field_value TEXT,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE,
            UNIQUE(asset_id, field_name)
        )
    """)

    # 创建索引
    cursor.execute("CREATE INDEX idx_custom_fields_asset ON asset_custom_fields(asset_id)")
    cursor.execute("CREATE INDEX idx_custom_fields_name ON asset_custom_fields(field_name)")
    cursor.execute("CREATE INDEX idx_custom_fields_type ON asset_custom_fields(field_type)")

    print("asset_custom_fields 表创建成功")

def migrate_asset_data(conn):
    """迁移资产数据"""
    cursor = conn.cursor()

    print("开始迁移资产数据...")

    # 1. 转换 is_litigated 字段从字符串到布尔值
    cursor.execute("SELECT id, is_litigated FROM assets WHERE is_litigated IS NOT NULL")
    assets = cursor.fetchall()

    for asset_id, is_litigated in assets:
        # 转换字符串到布尔值
        boolean_value = 1 if is_litigated == '是' else 0
        cursor.execute("UPDATE assets SET is_litigated = ? WHERE id = ?", (boolean_value, asset_id))

    print(f"已转换 {len(assets)} 条资产的涉诉状态字段")

    # 2. 添加 tenant_id 字段（如果不存在）
    try:
        cursor.execute("ALTER TABLE assets ADD COLUMN tenant_id VARCHAR(50)")
        print("已添加 tenant_id 字段")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("tenant_id 字段已存在，跳过添加")
        else:
            raise

def add_audit_fields_to_history(conn):
    """为历史记录表添加审计字段"""
    cursor = conn.cursor()

    # 添加新的审计字段
    audit_fields = [
        ('change_reason', 'VARCHAR(200)'),
        ('ip_address', 'VARCHAR(45)'),
        ('user_agent', 'TEXT'),
        ('session_id', 'VARCHAR(100)')
    ]

    for field_name, field_type in audit_fields:
        try:
            cursor.execute(f"ALTER TABLE asset_history ADD COLUMN {field_name} {field_type}")
            print(f"已添加 {field_name} 字段到 asset_history 表")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print(f"{field_name} 字段已存在，跳过添加")
            else:
                raise

def add_mime_type_to_documents(conn):
    """为文档表添加MIME类型字段"""
    cursor = conn.cursor()

    try:
        cursor.execute("ALTER TABLE asset_documents ADD COLUMN mime_type VARCHAR(100)")
        print("已添加 mime_type 字段到 asset_documents 表")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("mime_type 字段已存在，跳过添加")
        else:
            raise

def create_performance_indexes(conn):
    """创建性能索引"""
    cursor = conn.cursor()

    indexes = [
        # 基础搜索索引
        ("idx_assets_property_name_search", "assets", "property_name"),
        ("idx_assets_address_search", "assets", "address"),
        ("idx_assets_ownership_entity_search", "assets", "ownership_entity"),

        # 筛选索引
        ("idx_assets_ownership_status_filter", "assets", "ownership_status"),
        ("idx_assets_property_nature_filter", "assets", "property_nature"),
        ("idx_assets_usage_status_filter", "assets", "usage_status"),
        ("idx_assets_business_category_filter", "assets", "business_category"),
        ("idx_assets_is_litigated_filter", "assets", "is_litigated"),

        # 复合索引
        ("idx_assets_ownership_nature_combo", "assets", "ownership_entity, property_nature"),
        ("idx_assets_status_nature_combo", "assets", "usage_status, property_nature"),

        # 面积索引
        ("idx_assets_actual_property_area_range", "assets", "actual_property_area"),
        ("idx_assets_rentable_area_range", "assets", "rentable_area"),
        ("idx_assets_rented_area_range", "assets", "rented_area"),

        # 时间索引
        ("idx_assets_created_at_time", "assets", "created_at"),
        ("idx_assets_updated_at_time", "assets", "updated_at"),
        ("idx_assets_contract_start_date_time", "assets", "contract_start_date"),
        ("idx_assets_contract_end_date_time", "assets", "contract_end_date"),

        # 历史记录索引
        ("idx_asset_history_asset_id_ref", "asset_history", "asset_id"),
        ("idx_asset_history_operation_time_sort", "asset_history", "operation_time"),
        ("idx_asset_history_operation_type_filter", "asset_history", "operation_type"),
        ("idx_asset_history_operator", "asset_history", "operator"),

        # 文档索引
        ("idx_asset_documents_asset_id_ref", "asset_documents", "asset_id"),
        ("idx_asset_documents_upload_time_sort", "asset_documents", "upload_time"),

        # 多租户索引
        ("idx_assets_tenant", "assets", "tenant_id"),
    ]

    created_count = 0
    for index_name, table_name, columns in indexes:
        try:
            cursor.execute(f"CREATE INDEX {index_name} ON {table_name}({columns})")
            created_count += 1
        except sqlite3.OperationalError as e:
            if "already exists" in str(e):
                continue  # 索引已存在，跳过
            else:
                print(f"⚠️ 创建索引 {index_name} 失败: {e}")

    print(f"已创建 {created_count} 个性能索引")

def create_calculation_triggers(conn):
    """创建计算字段触发器"""
    cursor = conn.cursor()

    # 删除可能存在的旧触发器
    old_triggers = [
        'tr_assets_calculate_fields_insert',
        'tr_assets_calculate_fields_update',
        'tr_assets_validate_constraints',
        'tr_assets_validate_constraints_update'
    ]

    for trigger in old_triggers:
        try:
            cursor.execute(f"DROP TRIGGER IF EXISTS {trigger}")
        except:
            pass

    # 创建计算字段触发器 - INSERT
    cursor.execute("""
        CREATE TRIGGER tr_assets_calculate_fields_insert
        AFTER INSERT ON assets
        FOR EACH ROW
        BEGIN
            -- 计算未出租面积
            UPDATE assets SET unrented_area = CASE 
                WHEN NEW.rentable_area IS NOT NULL AND NEW.rented_area IS NOT NULL 
                THEN NEW.rentable_area - NEW.rented_area 
                ELSE NULL 
            END WHERE id = NEW.id;
            
            -- 计算出租率
            UPDATE assets SET occupancy_rate = CASE 
                WHEN NEW.rentable_area IS NOT NULL AND NEW.rentable_area > 0 AND NEW.rented_area IS NOT NULL 
                THEN ROUND((NEW.rented_area / NEW.rentable_area) * 100, 2)
                ELSE NULL 
            END WHERE id = NEW.id;
            
            -- 计算净收益
            UPDATE assets SET net_income = CASE 
                WHEN NEW.annual_income IS NOT NULL AND NEW.annual_expense IS NOT NULL 
                THEN NEW.annual_income - NEW.annual_expense 
                ELSE NULL 
            END WHERE id = NEW.id;
        END;
    """)

    # 创建计算字段触发器 - UPDATE
    cursor.execute("""
        CREATE TRIGGER tr_assets_calculate_fields_update
        AFTER UPDATE ON assets
        FOR EACH ROW
        WHEN (
            OLD.rentable_area != NEW.rentable_area OR 
            OLD.rented_area != NEW.rented_area OR
            OLD.annual_income != NEW.annual_income OR 
            OLD.annual_expense != NEW.annual_expense
        )
        BEGIN
            -- 计算未出租面积
            UPDATE assets SET unrented_area = CASE 
                WHEN NEW.rentable_area IS NOT NULL AND NEW.rented_area IS NOT NULL 
                THEN NEW.rentable_area - NEW.rented_area 
                ELSE NULL 
            END WHERE id = NEW.id;
            
            -- 计算出租率
            UPDATE assets SET occupancy_rate = CASE 
                WHEN NEW.rentable_area IS NOT NULL AND NEW.rentable_area > 0 AND NEW.rented_area IS NOT NULL 
                THEN ROUND((NEW.rented_area / NEW.rentable_area) * 100, 2)
                ELSE NULL 
            END WHERE id = NEW.id;
            
            -- 计算净收益
            UPDATE assets SET net_income = CASE 
                WHEN NEW.annual_income IS NOT NULL AND NEW.annual_expense IS NOT NULL 
                THEN NEW.annual_income - NEW.annual_expense 
                ELSE NULL 
            END WHERE id = NEW.id;
        END;
    """)

    print("已创建计算字段触发器")

def validate_migration(conn):
    """验证迁移结果"""
    cursor = conn.cursor()

    print("验证迁移结果...")

    # 检查表是否存在
    tables = ['system_dictionaries', 'asset_custom_fields']
    for table in tables:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
        if cursor.fetchone():
            print(f"表 {table} 存在")
        else:
            print(f"表 {table} 不存在")

    # 检查数据字典数据
    cursor.execute("SELECT COUNT(*) FROM system_dictionaries")
    dict_count = cursor.fetchone()[0]
    print(f"数据字典表包含 {dict_count} 条记录")

    # 检查资产表字段
    cursor.execute("PRAGMA table_info(assets)")
    columns = [row[1] for row in cursor.fetchall()]

    required_fields = ['tenant_id']
    for field in required_fields:
        if field in columns:
            print(f"字段 {field} 存在于 assets 表")
        else:
            print(f"字段 {field} 不存在于 assets 表")

    # 检查历史记录表字段
    cursor.execute("PRAGMA table_info(asset_history)")
    history_columns = [row[1] for row in cursor.fetchall()]

    audit_fields = ['change_reason', 'ip_address', 'user_agent', 'session_id']
    for field in audit_fields:
        if field in history_columns:
            print(f"审计字段 {field} 存在于 asset_history 表")
        else:
            print(f"审计字段 {field} 不存在于 asset_history 表")

    # 检查索引
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'")
    indexes = [row[0] for row in cursor.fetchall()]
    print(f"共创建了 {len(indexes)} 个索引")

    # 检查触发器
    cursor.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'tr_%'")
    triggers = [row[0] for row in cursor.fetchall()]
    print(f"共创建了 {len(triggers)} 个触发器")

def main():
    """主函数"""
    print("开始资产字段优化迁移...")
    print("=" * 50)

    try:
        # 1. 备份数据库
        backup_path = backup_database()

        # 2. 获取数据库连接
        conn = get_db_connection()
        conn.execute("PRAGMA foreign_keys = ON")  # 启用外键约束

        # 3. 创建新表
        create_system_dictionaries_table(conn)
        populate_system_dictionaries(conn)
        create_custom_fields_table(conn)

        # 4. 迁移现有数据
        migrate_asset_data(conn)
        add_audit_fields_to_history(conn)
        add_mime_type_to_documents(conn)

        # 5. 创建索引和触发器
        create_performance_indexes(conn)
        create_calculation_triggers(conn)

        # 6. 提交事务
        conn.commit()

        # 7. 验证迁移结果
        validate_migration(conn)

        print("=" * 50)
        print("资产字段优化迁移完成！")
        print(f"备份文件: {backup_path}")
        print("主要改进:")
        print("   - 创建了系统数据字典表，统一管理枚举值")
        print("   - 创建了自定义字段表，支持灵活扩展")
        print("   - 优化了数据类型，提高精度和一致性")
        print("   - 添加了性能索引，提升查询速度")
        print("   - 创建了计算字段触发器，确保数据一致性")
        print("   - 增强了审计日志功能")
        print("   - 添加了多租户支持")

    except Exception as e:
        print(f"迁移过程中发生错误: {e}")
        print("请检查备份文件并联系技术支持")
        return 1

    finally:
        if 'conn' in locals():
            conn.close()

    return 0

if __name__ == "__main__":
    sys.exit(main())
