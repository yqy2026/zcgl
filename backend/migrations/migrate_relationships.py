"""
数据库关系迁移脚本
为权属方、项目和资产建立正确的关联关系
"""

import sqlite3
import uuid
from datetime import datetime

def migrate_relationships():
    """执行关系迁移"""

    conn = sqlite3.connect('land_property.db')
    cursor = conn.cursor()

    print("开始执行关系迁移...")

    try:
        # 1. 检查是否已存在ownership_id列
        cursor.execute("PRAGMA table_info(assets)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'ownership_id' not in columns:
            print("添加ownership_id列到assets表...")
            cursor.execute("ALTER TABLE assets ADD COLUMN ownership_id VARCHAR(36)")

        # 2. 创建项目-权属方关系表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS project_ownership_relations (
                id VARCHAR(36) PRIMARY KEY,
                project_id VARCHAR(36) NOT NULL,
                ownership_id VARCHAR(36) NOT NULL,
                relation_type VARCHAR(50) DEFAULT '合作',
                start_date DATE,
                end_date DATE,
                description TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_by VARCHAR(100),
                updated_by VARCHAR(100),
                FOREIGN KEY (project_id) REFERENCES projects(id),
                FOREIGN KEY (ownership_id) REFERENCES ownerships(id)
            )
        ''')

        # 3. 为ownership_id列创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_assets_ownership_id ON assets(ownership_id)")

        # 4. 为项目-权属方关系表创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_project_ownership_project_id ON project_ownership_relations(project_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_project_ownership_ownership_id ON project_ownership_relations(ownership_id)")

        # 5. 迁移现有数据：根据ownership_entity匹配ownerships表
        print("迁移现有权属方数据...")
        cursor.execute('''
            UPDATE assets
            SET ownership_id = (
                SELECT id FROM ownerships
                WHERE ownerships.name = assets.ownership_entity
                LIMIT 1
            )
            WHERE ownership_entity IS NOT NULL
            AND ownership_entity != ''
        ''')

        # 6. 创建项目-权属方关系数据
        print("创建项目-权属方关系数据...")
        cursor.execute('''
            INSERT OR IGNORE INTO project_ownership_relations (id, project_id, ownership_id, relation_type, created_at)
            SELECT
                lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-' || lower(hex(randomblob(2))) || '-' || lower(hex(randomblob(2))) || '-' || lower(hex(randomblob(6))),
                p.id,
                o.id,
                '管理',
                CURRENT_TIMESTAMP
            FROM projects p
            JOIN ownerships o ON p.ownership_entity = o.name
            WHERE p.ownership_entity IS NOT NULL
            AND p.ownership_entity != ''
        ''')

        conn.commit()
        print("关系迁移完成！")

        # 7. 显示迁移结果统计
        print("\n迁移结果统计:")

        # 资产表迁移统计
        cursor.execute("SELECT COUNT(*) FROM assets WHERE ownership_id IS NOT NULL")
        migrated_assets = cursor.fetchone()[0]
        print(f"- 已关联权属方的资产数量: {migrated_assets}")

        # 项目-权属方关系统计
        cursor.execute("SELECT COUNT(*) FROM project_ownership_relations")
        project_relations = cursor.fetchone()[0]
        print(f"- 项目-权属方关系数量: {project_relations}")

        # 显示还未关联的资产
        cursor.execute("SELECT COUNT(*) FROM assets WHERE ownership_id IS NULL AND ownership_entity IS NOT NULL")
        unmigrated_assets = cursor.fetchone()[0]
        if unmigrated_assets > 0:
            print(f"- 未匹配到权属方的资产数量: {unmigrated_assets} (需要手动处理)")

    except Exception as e:
        conn.rollback()
        print(f"迁移失败: {str(e)}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_relationships()