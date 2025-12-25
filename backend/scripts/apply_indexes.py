"""
应用数据库索引脚本
用于添加性能优化索引
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging

from sqlalchemy import create_engine, text

from src.core.config import settings

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def apply_indexes():
    """应用性能优化索引"""
    try:
        # 创建数据库连接
        engine = create_engine(settings.DATABASE_URL)

        # 读取索引SQL文件
        index_file = os.path.join(os.path.dirname(__file__), "..", "migrations", "add_performance_indexes.sql")

        with open(index_file, encoding='utf-8') as f:
            index_sql = f.read()

        # 执行索引创建
        with engine.connect() as conn:
            # 分割SQL语句并执行
            statements = [stmt.strip() for stmt in index_sql.split(';') if stmt.strip()]

            for statement in statements:
                try:
                    result = conn.execute(text(statement))
                    logger.info(f"执行索引创建: {statement[:50]}...")
                except Exception as e:
                    if "already exists" in str(e) or "duplicate" in str(e).lower():
                        logger.info(f"索引已存在，跳过: {statement[:50]}...")
                    else:
                        logger.warning(f"执行索引失败: {e}")

            conn.commit()

        logger.info("数据库索引应用完成")
        return True

    except Exception as e:
        logger.error(f"应用数据库索引失败: {e}")
        return False
    finally:
        if 'engine' in locals():
            engine.dispose()

if __name__ == "__main__":
    success = apply_indexes()
    if success:
        print("✅ 数据库索引应用成功")
        sys.exit(0)
    else:
        print("❌ 数据库索引应用失败")
        sys.exit(1)
