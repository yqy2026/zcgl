"""
简化版配置 - 移除Redis依赖
"""

import os
from typing import Optional

class Settings:
    """应用配置类 - 简化版"""
    
    # 数据库配置
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "sqlite:///./asset_management.db"  # 默认使用SQLite
    )
    
    # 应用配置
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    
    # CORS配置
    CORS_ORIGINS: list = os.getenv(
        "CORS_ORIGINS", 
        "http://localhost:3000,http://localhost"
    ).split(",")
    
    # 文件上传配置
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "10485760"))  # 10MB
    
    # 日志配置
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # 分页配置
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    # Excel处理配置
    EXCEL_MAX_ROWS: int = 10000
    EXCEL_BATCH_SIZE: int = 100

# 创建全局设置实例
settings = Settings()

# 任务状态存储（内存版本，替代Redis）
class InMemoryTaskStore:
    """内存任务状态存储"""
    
    def __init__(self):
        self._tasks = {}
    
    def set_task_status(self, task_id: str, status: dict, expire_seconds: int = 3600):
        """设置任务状态"""
        self._tasks[task_id] = {
            "data": status,
            "created_at": os.time.time(),
            "expire_at": os.time.time() + expire_seconds
        }
    
    def get_task_status(self, task_id: str) -> Optional[dict]:
        """获取任务状态"""
        if task_id not in self._tasks:
            return None
        
        task = self._tasks[task_id]
        
        # 检查是否过期
        if os.time.time() > task["expire_at"]:
            del self._tasks[task_id]
            return None
        
        return task["data"]
    
    def delete_task(self, task_id: str):
        """删除任务"""
        if task_id in self._tasks:
            del self._tasks[task_id]
    
    def cleanup_expired(self):
        """清理过期任务"""
        current_time = os.time.time()
        expired_keys = [
            key for key, task in self._tasks.items()
            if current_time > task["expire_at"]
        ]
        for key in expired_keys:
            del self._tasks[key]

# 创建全局任务存储实例
task_store = InMemoryTaskStore()

# 定期清理过期任务的后台任务
import asyncio
from contextlib import asynccontextmanager

async def cleanup_expired_tasks():
    """定期清理过期任务"""
    while True:
        try:
            task_store.cleanup_expired()
            await asyncio.sleep(300)  # 每5分钟清理一次
        except Exception as e:
            print(f"清理过期任务时出错: {e}")
            await asyncio.sleep(60)  # 出错时等待1分钟再重试

@asynccontextmanager
async def lifespan(app):
    """应用生命周期管理"""
    # 启动时
    print("🚀 启动土地物业资产管理系统（简化版）")
    print(f"📊 数据库: {settings.DATABASE_URL}")
    print(f"🔧 调试模式: {settings.DEBUG}")
    
    # 启动后台清理任务
    cleanup_task = asyncio.create_task(cleanup_expired_tasks())
    
    yield
    
    # 关闭时
    cleanup_task.cancel()
    print("🛑 系统已关闭")

# 导出配置
__all__ = ["settings", "task_store", "lifespan"]