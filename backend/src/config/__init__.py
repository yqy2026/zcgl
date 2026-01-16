from typing import TYPE_CHECKING, Any  # noqa: F401

"""
应用配置设置
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager  # noqa: F401

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from redis.asyncio import ConnectionPool, Redis  # noqa: F401

# typing imports removed - not used in this file
try:
    import redis.asyncio as redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None  # type: ignore

if TYPE_CHECKING and REDIS_AVAILABLE:
    pass  # pragma: no cover


class Settings:
    """应用配置"""

    # 数据库配置
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./land_property.db",  # 默认使用SQLite
    )

    # Redis配置
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # 应用配置
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY",
        "emergency-test-secret-key-for-development-only-change-in-production",
    )
    if not SECRET_KEY or SECRET_KEY in [
        "EMERGENCY-ONLY-REPLACE-WITH-ENV-SECRET-KEY-NOW"
    ]:
        logger.warning(
            "Using default or missing SECRET_KEY. Please set a proper environment variable in production."
        )
    DATA_ENCRYPTION_KEY: str = os.getenv("DATA_ENCRYPTION_KEY", "")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # 验证数据加密密钥配置
    # 注意: 空字符串是可接受的（优雅降级），但在生产环境中应该配置
    if not DATA_ENCRYPTION_KEY and not DEBUG:
        logger.warning(
            "DATA_ENCRYPTION_KEY not set - PII encryption disabled. "
            "Sensitive data will be stored in plaintext. "
            "Set DATA_ENCRYPTION_KEY for production use. "
            "Generate one with: python -m src.core.encryption"
        )

    # CORS配置
    CORS_ORIGINS: list[str] = os.getenv(
        "CORS_ORIGINS", "http://localhost:3000,http://localhost:5173,http://localhost"
    ).split(",")

    # 文件上传配置
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "52428800"))  # 50MB

    # 日志配置
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # 分页配置
    DEFAULT_PAGE_SIZE: int = int(os.getenv("DEFAULT_PAGE_SIZE", "20"))
    MAX_PAGE_SIZE: int = int(os.getenv("MAX_PAGE_SIZE", "100"))

    # Excel处理配置
    EXCEL_MAX_ROWS: int = int(os.getenv("EXCEL_MAX_ROWS", "10000"))
    EXCEL_BATCH_SIZE: int = int(os.getenv("EXCEL_BATCH_SIZE", "100"))

    # JWT配置
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120")
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    # 密码策略
    MIN_PASSWORD_LENGTH: int = int(os.getenv("MIN_PASSWORD_LENGTH", "8"))
    MAX_FAILED_ATTEMPTS: int = int(os.getenv("MAX_FAILED_ATTEMPTS", "5"))
    LOCKOUT_DURATION_MINUTES: int = int(os.getenv("LOCKOUT_DURATION_MINUTES", "30"))
    PASSWORD_EXPIRE_DAYS: int = int(os.getenv("PASSWORD_EXPIRE_DAYS", "90"))

    # 会话配置
    MAX_CONCURRENT_SESSIONS: int = int(os.getenv("MAX_CONCURRENT_SESSIONS", "5"))
    SESSION_EXPIRE_DAYS: int = int(os.getenv("SESSION_EXPIRE_DAYS", "7"))

    # 审计配置
    AUDIT_LOG_RETENTION_DAYS: int = int(os.getenv("AUDIT_LOG_RETENTION_DAYS", "90"))

    # PDF处理配置
    PDF_MAX_FILE_SIZE_MB: int = int(os.getenv("PDF_MAX_FILE_SIZE_MB", "50"))
    PDF_PROCESSING_TIMEOUT: int = int(os.getenv("PDF_PROCESSING_TIMEOUT", "300"))

    # OCR配置
    OCR_DEFAULT_ENGINE: str = os.getenv("OCR_DEFAULT_ENGINE", "paddleocr")
    OCR_HIGH_ACCURACY_THRESHOLD: float = float(
        os.getenv("OCR_HIGH_ACCURACY_THRESHOLD", "0.8")
    )


# 创建全局设置实例
settings = Settings()

# Redis连接池
redis_pool: "ConnectionPool | None" = None
redis_client: "Redis | None" = None


async def init_redis() -> None:
    """初始化Redis连接"""
    global redis_pool, redis_client

    if not REDIS_AVAILABLE:
        logger.warning("Redis库未安装，跳过Redis初始化")
        return

    try:
        redis_pool = redis.ConnectionPool.from_url(settings.REDIS_URL)
        redis_client = redis.Redis(connection_pool=redis_pool)
        # 测试连接
        if redis_client is not None:
            redis_client.ping()
        logger.info(f"Redis连接成功: {settings.REDIS_URL}")
    except Exception as e:
        logger.error(f"Redis连接失败: {e}")
        redis_client = None


async def close_redis() -> None:
    """关闭Redis连接"""
    global redis_pool, redis_client
    if redis_client:
        await redis_client.close()
    if redis_pool:
        await redis_pool.disconnect()


# 任务状态存储（Redis版本）
class RedisTaskStore:
    """Redis任务状态存储"""

    async def set_task_status(
        self, task_id: str, status: dict[str, Any], expire_seconds: int = 3600
    ) -> None:
        """设置任务状态"""
        if redis_client:
            try:
                await redis_client.setex(f"task:{task_id}", expire_seconds, str(status))
            except Exception as e:
                logger.error(f"设置任务状态失败: {e}")

    async def get_task_status(self, task_id: str) -> dict[str, Any] | None:
        """获取任务状态"""
        if redis_client:
            try:
                data = await redis_client.get(f"task:{task_id}")
                if data:
                    import json

                    # Using json.loads() for safe deserialization
                    parsed = json.loads(data.decode("utf-8"))
                    return parsed  # type: ignore[no-any-return]
            except Exception as e:
                logger.error(f"获取任务状态失败: {e}")
        return None

    async def delete_task(self, task_id: str) -> None:
        """删除任务"""
        if redis_client:
            try:
                await redis_client.delete(f"task:{task_id}")
            except Exception as e:
                logger.error(f"删除任务失败: {e}")


# 创建全局任务存储实例
task_store = RedisTaskStore()


# 定期清理过期任务的后台任务
async def cleanup_expired_tasks() -> None:
    """定期清理过期任务"""
    # Redis会自动清理过期键，这里可以用于其他清理工作
    while True:
        try:
            await asyncio.sleep(3600)  # 1小时检查一次
        except Exception as e:
            logger.error(f"清理过期任务时出错: {e}")
            await asyncio.sleep(60)  # 出错时等1分钟再重试


@asynccontextmanager
async def lifespan(app: Any) -> Any:
    """应用生命周期管理"""
    # 启动时
    logger.info("启动土地物业资产管理系统")
    logger.info(f"数据库: {settings.DATABASE_URL}")
    logger.info(f"Redis: {settings.REDIS_URL}")
    logger.info(f"调试模式: {settings.DEBUG}")

    # 初始化Redis
    await init_redis()

    # 启动后台清理任务
    cleanup_task = asyncio.create_task(cleanup_expired_tasks())

    yield

    # 关闭时
    cleanup_task.cancel()
    await close_redis()
    logger.info("系统已关闭")


# 导出配置
__all__ = ["settings", "task_store", "lifespan"]
