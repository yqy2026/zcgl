"""
简化的数据库配置（无SQLite依赖）
"""

from typing import Generator

# 模拟数据库会话
class MockSession:
    def __init__(self):
        pass
    
    def query(self, *args, **kwargs):
        return MockQuery()
    
    def add(self, obj):
        pass
    
    def commit(self):
        pass
    
    def refresh(self, obj):
        pass
    
    def close(self):
        pass

class MockQuery:
    def filter(self, *args, **kwargs):
        return self
    
    def first(self):
        return None
    
    def all(self):
        return []
    
    def count(self):
        return 0
    
    def offset(self, n):
        return self
    
    def limit(self, n):
        return self
    
    def order_by(self, *args):
        return self

# 模拟Base类
class MockBase:
    pass

Base = MockBase

def get_db() -> Generator[MockSession, None, None]:
    """获取数据库会话"""
    db = MockSession()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    """创建所有数据库表（模拟）"""
    print("模拟创建数据库表")
    pass