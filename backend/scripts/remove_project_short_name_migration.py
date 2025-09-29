#!/usr/bin/env python3
"""
数据库迁移脚本：删除项目简称字段
- 删除 project_short_name 字段
- 删除重复的 project_name 字段
"""

import sqlite3
import os
import sys
from datetime import datetime

# 添加项目根目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))


def get_db_path():
    """获取数据库文件路径"""
    # 从环境变量获取数据库URL，默认为sqlite:///./land_property.db
    database_url = os.getenv("DATABASE_URL", "sqlite:///./land_property.db")
    
    if database_url.startswith("sqlite:///"):
        # 提取文件路径
        db_path = database_url.replace("sqlite:///", "")
        # 如果是相对路径，转换为绝对路径
        if not os.path.isabs(db_path):
            # 相对于backend/src目录
            backend_src_dir = os.path.join(os.path.dirname(__file__), '..', 'src')
            db_path = os.path.join(backend_src_dir, db_path)
        return os.path.abspath(db_path)
    else:
        raise ValueError(f"不支持的数据库类型: {database_url}")


def backup_database():
    """备份数据库"""
    db_path = get_db_path()
    if not os.path.exists(db_path):
        print(f"数据库文件不存在: {db_path}")
        return None
    
    backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    try:
        # 使用SQLite的备份API
        source = sqlite3.connect(db_path)
        backup = sqlite3.connect(backup_path)
        source.backup(backup)
        source.close()
        backup.close()
        
        print(f"数据库已备份到: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"备份数据库失败: {e}")
        return None


def check_table_structure():
    """检查当前表结构"""
    db_path = get_db_path()
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取表结构
        cursor.execute("PRAGMA table_info(assets)")
        columns = cursor.fetchall()
        
        print("当前 assets 表结构:")
        for col in columns:
            print(f"  {col[1]} {col[2]} {'NOT NULL' if col[3] else 'NULL'} {'PRIMARY KEY' if col[5] else ''}")
        
        # 检查是否存在重复的 project_name 字段
        project_name_count = sum(1 for col in columns if col[1] == 'project_name')
        project_short_name_exists = any(col[1] == 'project_short_name' for col in columns)
        
        conn.close()
        
        return {
            'columns': columns,
            'project_name_count': project_name_count,
            'project_short_name_exists': project_short_name_exists
        }
        
    except Exception as e:
        print(f"检查表结构失败: {e}")
        return None


def migrate_database():
    """执行数据库迁移"""
    db_path = get_db_path()
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 开始事务
        cursor.execute("BEGIN TRANSACTION")
        
        # 获取当前表结构
        cursor.execute("PRAGMA table_info(assets)")
        columns = cursor.fetchall()
        
        # 创建新表结构（排除 project_short_name 和重复的 project_name）
        new_columns = []
        project_name_added = False
        
        for col in columns:
            col_name = col[1]
            col_type = col[2]
            not_null = col[3]
            default_val = col[4]
            pk = col[5]
            
            # 跳过 project_short_name 字段
            if col_name == 'project_short_name':
                continue
            
            # 只保留第一个 project_name 字段
            if col_name == 'project_name':
                if project_name_added:
                    continue
                project_name_added = True
            
            # 构建列定义
            col_def = f"{col_name} {col_type}"
            if pk:
                col_def += " PRIMARY KEY"
            elif not_null:
                col_def += " NOT NULL"
            if default_val is not None:
                col_def += f" DEFAULT {default_val}"
            
            new_columns.append(col_def)
        
        # 创建新表
        create_table_sql = f"""
        CREATE TABLE assets_new (
            {', '.join(new_columns)}
        )
        """
        
        print("创建新表结构...")
        cursor.execute(create_table_sql)
        
        # 获取要复制的列名（排除 project_short_name）
        copy_columns = []
        project_name_copied = False
        
        for col in columns:
            col_name = col[1]
            if col_name == 'project_short_name':
                continue
            if col_name == 'project_name':
                if project_name_copied:
                    continue
                project_name_copied = True
            copy_columns.append(col_name)
        
        # 复制数据
        copy_sql = f"""
        INSERT INTO assets_new ({', '.join(copy_columns)})
        SELECT {', '.join(copy_columns)}
        FROM assets
        """
        
        print("复制数据到新表...")
        cursor.execute(copy_sql)
        
        # 删除旧表
        print("删除旧表...")
        cursor.execute("DROP TABLE assets")
        
        # 重命名新表
        print("重命名新表...")
        cursor.execute("ALTER TABLE assets_new RENAME TO assets")
        
        # 提交事务
        cursor.execute("COMMIT")
        
        print("数据库迁移完成!")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"数据库迁移失败: {e}")
        try:
            cursor.execute("ROLLBACK")
            conn.close()
        except:
            pass
        return False


def verify_migration():
    """验证迁移结果"""
    print("\n验证迁移结果...")
    
    structure = check_table_structure()
    if not structure:
        return False
    
    # 检查是否还存在 project_short_name 字段
    if structure['project_short_name_exists']:
        print("迁移失败: project_short_name 字段仍然存在")
        return False
    
    # 检查 project_name 字段数量
    if structure['project_name_count'] > 1:
        print(f"迁移失败: 仍然存在 {structure['project_name_count']} 个 project_name 字段")
        return False
    
    print("迁移验证成功!")
    print(f"   - project_name 字段数量: {structure['project_name_count']}")
    print(f"   - project_short_name 字段已删除")
    
    return True


def main():
    """主函数"""
    print("开始数据库迁移: 删除项目简称字段")
    print("=" * 50)
    
    # 1. 检查当前表结构
    print("1. 检查当前表结构...")
    structure = check_table_structure()
    if not structure:
        print("❌ 无法检查表结构，退出迁移")
        return False
    
    print(f"   - project_name 字段数量: {structure['project_name_count']}")
    print(f"   - project_short_name 字段存在: {structure['project_short_name_exists']}")
    
    # 如果不需要迁移，直接退出
    if structure['project_name_count'] <= 1 and not structure['project_short_name_exists']:
        print("数据库结构已经是最新的，无需迁移")
        return True
    
    # 2. 备份数据库
    print("\n2. 备份数据库...")
    backup_path = backup_database()
    if not backup_path:
        print("❌ 备份失败，退出迁移")
        return False
    
    # 3. 执行迁移
    print("\n3. 执行数据库迁移...")
    if not migrate_database():
        print("❌ 迁移失败")
        return False
    
    # 4. 验证迁移结果
    print("\n4. 验证迁移结果...")
    if not verify_migration():
        print("❌ 迁移验证失败")
        return False
    
    print("\n" + "=" * 50)
    print("数据库迁移成功完成!")
    print(f"备份文件: {backup_path}")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)