"""
数据库关系迁移脚本 - 修复版
为权属方、项目和资产建立正确的关联关系
"""

import sqlite3


def migrate_relationships():
    """执行关系迁移"""

    conn = sqlite3.connect("./land_property.db")
    cursor = conn.cursor()

    print("开始执行关系迁移...")

    try:
        # 1. 检查是否已存在ownership_id列
        cursor.execute("PRAGMA table_info(assets)")
        columns = [column[1] for column in cursor.fetchall()]

        if "ownership_id" not in columns:
            print("添加ownership_id列到assets表...")
            cursor.execute("ALTER TABLE assets ADD COLUMN ownership_id VARCHAR(36)")

        # 2. 为ownership_id列创建索引
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_assets_ownership_id ON assets(ownership_id)"
        )

        # 3. 迁移现有数据：根据ownership_entity匹配ownerships表
        print("迁移现有权属方数据...")
        cursor.execute("""
            UPDATE assets
            SET ownership_id = (
                SELECT id FROM ownerships
                WHERE ownerships.name = assets.ownership_entity
                LIMIT 1
            )
            WHERE ownership_entity IS NOT NULL
            AND ownership_entity != ''
        """)

        # 4. 创建项目-权属方关系数据（使用现有表结构）
        print("创建项目-权属方关系数据...")
        cursor.execute("""
            INSERT OR IGNORE INTO project_ownership_relations (id, project_id, ownership_id, is_active, created_at, updated_at)
            SELECT
                lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-' || lower(hex(randomblob(2))) || '-' || lower(hex(randomblob(2))) || '-' || lower(hex(randomblob(6))),
                p.id,
                o.id,
                1,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            FROM projects p
            JOIN ownerships o ON p.ownership_entity = o.name
            WHERE p.ownership_entity IS NOT NULL
            AND p.ownership_entity != ''
        """)

        conn.commit()
        print("关系迁移完成！")

        # 5. 显示迁移结果统计
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
        cursor.execute(
            "SELECT COUNT(*) FROM assets WHERE ownership_id IS NULL AND ownership_entity IS NOT NULL"
        )
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
