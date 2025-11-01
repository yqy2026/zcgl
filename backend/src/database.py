"""
数据库配置和连接管理
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .database_security import enhance_database_security

# 数据库URL配置
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/land_property.db")

# 创建数据库引擎
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL.lower() else {}
)

# 增强数据库安全
enhance_database_security(engine)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基础模型类
Base = declarative_base()

def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    """创建所有数据库表"""
    Base.metadata.create_all(bind=engine)

def drop_tables():
    """删除所有数据库表"""
    Base.metadata.drop_all(bind=engine)

def init_db():
    """初始化数据库"""
    create_tables()
    print("数据库初始化完成")

if __name__ == "__main__":
    init_db()
