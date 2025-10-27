"""
数据库配置和连接管理
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# 数据库URL配置
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/land_property.db")

# 创建数据库引擎
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=True,  # 开发环境显示SQL语句
)

# 增强数据库安全
from .database_security import enhance_database_security

enhance_database_security(engine)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基础模型类
Base = declarative_base()


def get_db():
    """
    获取数据库会话的依赖注入函数
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """
    创建所有数据库表
    """
    # 导入所有模型以确保它们被注册到Base.metadata中

    Base.metadata.create_all(bind=engine)


def drop_tables():
    """
    删除所有数据库表（仅用于测试）
    """
    Base.metadata.drop_all(bind=engine)
