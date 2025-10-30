"""
增强配置管理器
提供统一的配置加载、验证和管理功能
"""

import secrets
from enum import Enum
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings

from .logging_security import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class Environment(Enum):
    """环境枚举"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    """日志级别枚举"""
    CRITICAL = "CRITICAL"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    DEBUG = "DEBUG"
    NOTSET = "NOTSET"


class DatabaseConfig(BaseModel):
    """数据库配置"""
    url: str = Field(..., description="数据库连接URL")
    echo: bool = Field(False, description="是否打印SQL语句")
    pool_size: int = Field(5, description="连接池大小")
    max_overflow: int = Field(10, description="连接池最大溢出")
    pool_timeout: int = Field(30, description="连接池超时时间")
    pool_recycle: int = Field(3600, description="连接池回收时间")
    isolation_level: str = Field("READ COMMITTED", description="事务隔离级别")

    @validator('url')
    def validate_url(self, v):
        if not v:
            raise ValueError('数据库URL不能为空')
        return v


class RedisConfig(BaseModel):
    """Redis配置"""
    host: str = Field("localhost", description="Redis主机")
    port: int = Field(6379, description="Redis端口")
    db: int = Field(0, description="Redis数据库")
    password: str | None = Field(None, description="Redis密码")
    max_connections: int = Field(10, description="最大连接数")
    socket_timeout: int = Field(5, description="套接字超时")
    socket_connect_timeout: int = Field(5, description="连接超时")


class SecurityConfig(BaseModel):
    """安全配置"""
    secret_key: str = Field(..., description="JWT密钥")
    algorithm: str = Field("HS256", description="JWT算法")
    access_token_expire_minutes: int = Field(30, description="访问令牌过期时间（分钟）")
    refresh_token_expire_days: int = Field(7, description="刷新令牌过期时间（天）")
    password_min_length: int = Field(8, description="密码最小长度")
    password_max_failed_attempts: int = Field(5, description="密码最大失败次数")
    password_lockout_duration: int = Field(900, description="密码锁定持续时间（秒）")
    max_concurrent_sessions: int = Field(5, description="最大并发会话数")
    enable_two_factor_auth: bool = Field(False, description="是否启用双因素认证")
    enable_rate_limiting: bool = Field(True, description="是否启用速率限制")
    rate_limit_requests: int = Field(100, description="速率限制请求数")
    rate_limit_window: int = Field(60, description="速率限制时间窗口（秒）")

    @validator('secret_key')
    def validate_secret_key(self, v):
        if len(v) < 32:
            raise ValueError('密钥长度至少为32个字符')
        return v


class CacheConfig(BaseModel):
    """缓存配置"""
    backend: str = Field("memory", description="缓存后端")
    ttl: int = Field(300, description="默认缓存时间（秒）")
    key_prefix: str = Field("zcgl", description="缓存键前缀")
    max_size: int = Field(1000, description="内存缓存最大条目数")
    redis_db: int = Field(1, description="Redis缓存数据库")

    @validator('backend')
    def validate_backend(self, v):
        valid_backends = ["memory", "redis", "memcached"]
        if v not in valid_backends:
            raise ValueError(f'缓存后端必须是以下之一: {", ".join(valid_backends)}')
        return v


class LoggingConfig(BaseModel):
    """日志配置"""
    level: LogLevel = Field(LogLevel.INFO, description="日志级别")
    format: str = Field(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="日志格式"
    )
    file_path: str | None = Field(None, description="日志文件路径")
    max_bytes: int = Field(10485760, description="日志文件最大字节数")
    backup_count: int = Field(5, description="日志文件备份数量")
    enable_console: bool = Field(True, description="是否启用控制台输出")
    enable_file: bool = Field(True, description="是否启用文件输出")
    enable_rotation: bool = Field(True, description="是否启用日志轮转")


class CORSConfig(BaseModel):
    """CORS配置"""
    allow_origins: list[str] = Field(["*"], description="允许的源")
    allow_credentials: bool = Field(True, description="是否允许凭据")
    allow_methods: list[str] = Field(["*"], description="允许的方法")
    allow_headers: list[str] = Field(["*"], description="允许的头部")
    max_age: int = Field(600, description="预检请求缓存时间")


class FileUploadConfig(BaseModel):
    """文件上传配置"""
    max_file_size: int = Field(10 * 1024 * 1024, description="最大文件大小（字节）")
    allowed_extensions: list[str] = Field(
        [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".jpg", ".jpeg", ".png"],
        description="允许的文件扩展名"
    )
    upload_path: str = Field("uploads", description="上传路径")
    chunk_size: int = Field(8192, description="分块大小")
    enable_virus_scan: bool = Field(False, description="是否启用病毒扫描")


class EnhancedSettings(BaseSettings):
    """增强的设置类"""

    # 基础配置
    app_name: str = Field("土地物业资产管理系统", description="应用名称")
    app_version: str = Field("2.0.0", description="应用版本")
    environment: Environment = Field(Environment.DEVELOPMENT, description="运行环境")
    debug: bool = Field(False, description="调试模式")
    host: str = Field("0.0.0.0", description="服务器主机")
    port: int = Field(8002, description="服务器端口")
    reload: bool = Field(False, description="是否自动重载")

    # 子配置
    database: DatabaseConfig = Field(..., description="数据库配置")
    redis: RedisConfig = Field(RedisConfig(), description="Redis配置")
    security: SecurityConfig = Field(..., description="安全配置")
    cache: CacheConfig = Field(CacheConfig(), description="缓存配置")
    logging: LoggingConfig = Field(LoggingConfig(), description="日志配置")
    cors: CORSConfig = Field(CORSConfig(), description="CORS配置")
    file_upload: FileUploadConfig = Field(FileUploadConfig(), description="文件上传配置")

    # 业务配置
    timezone: str = Field("Asia/Shanghai", description="时区")
    date_format: str = Field("%Y-%m-%d", description="日期格式")
    datetime_format: str = Field("%Y-%m-%d %H:%M:%S", description="日期时间格式")
    default_language: str = Field("zh-CN", description="默认语言")
    items_per_page: int = Field(20, description="每页默认条目数")
    max_items_per_page: int = Field(100, description="每页最大条目数")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        env_prefix = "APP"

    @validator('environment', pre=True)
    def parse_environment(self, v):
        if isinstance(v, str):
            return Environment(v.lower())
        return v

    @validator('debug', pre=True)
    def parse_debug(self, v, values):
        if v is None:
            return values.get('environment') == Environment.DEVELOPMENT
        return v

    @validator('reload', pre=True)
    def parse_reload(self, v, values):
        if v is None:
            return values.get('environment') == Environment.DEVELOPMENT
        return v

    @classmethod
    def load_from_file(cls, config_path: str | Path) -> "EnhancedSettings":
        """
        从文件加载配置

        Args:
            config_path: 配置文件路径

        Returns:
            设置实例
        """
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")

        # 这里可以支持多种配置文件格式
        if config_path.suffix.lower() in ['.yml', '.yaml']:
            return cls._load_from_yaml(config_path)
        elif config_path.suffix.lower() == '.json':
            return cls._load_from_json(config_path)
        else:
            raise ValueError(f"不支持的配置文件格式: {config_path.suffix}")

    @classmethod
    def _load_from_yaml(cls, config_path: Path) -> "EnhancedSettings":
        """从YAML文件加载配置"""
        try:
            import yaml
            with open(config_path, encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            return cls(**config_data)
        except ImportError:
            raise ImportError("需要安装PyYAML来支持YAML配置文件")

    @classmethod
    def _load_from_json(cls, config_path: Path) -> "EnhancedSettings":
        """从JSON文件加载配置"""
        import json
        with open(config_path, encoding='utf-8') as f:
            config_data = json.load(f)
        return cls(**config_data)

    def save_to_file(self, config_path: str | Path) -> None:
        """
        保存配置到文件

        Args:
            config_path: 配置文件路径
        """
        config_path = Path(config_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)

        config_data = self.dict()

        if config_path.suffix.lower() in ['.yml', '.yaml']:
            self._save_to_yaml(config_path, config_data)
        elif config_path.suffix.lower() == '.json':
            self._save_to_json(config_path, config_data)
        else:
            raise ValueError(f"不支持的配置文件格式: {config_path.suffix}")

    def _save_to_yaml(self, config_path: Path, config_data: dict) -> None:
        """保存到YAML文件"""
        try:
            import yaml
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)
        except ImportError:
            raise ImportError("需要安装PyYAML来支持YAML配置文件")

    def _save_to_json(self, config_path: Path, config_data: dict) -> None:
        """保存到JSON文件"""
        import json
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)

    def get_database_url(self) -> str:
        """获取数据库连接URL"""
        return self.database.url

    def get_redis_url(self) -> str:
        """获取Redis连接URL"""
        if self.redis.password:
            return f"redis://:{self.redis.password}@{self.redis.host}:{self.redis.port}/{self.redis.db}"
        return f"redis://{self.redis.host}:{self.redis.port}/{self.redis.db}"

    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.environment == Environment.DEVELOPMENT

    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.environment == Environment.PRODUCTION

    def is_testing(self) -> bool:
        """是否为测试环境"""
        return self.environment == Environment.TESTING

    def get_log_level(self) -> str:
        """获取日志级别"""
        return self.logging.level.value

    def get_secret_key(self) -> str:
        """获取密钥"""
        return self.security.secret_key

    def validate_config(self) -> list[str]:
        """
        验证配置

        Returns:
            错误消息列表
        """
        errors = []

        # 验证必需配置
        if not self.security.secret_key:
            errors.append("安全密钥不能为空")

        if len(self.security.secret_key) < 32:
            errors.append("安全密钥长度至少为32个字符")

        # 验证文件路径
        if self.file_upload.upload_path:
            upload_path = Path(self.file_upload.upload_path)
            if not upload_path.exists():
                try:
                    upload_path.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    errors.append(f"无法创建上传目录 {upload_path}: {e}")

        # 验证数据库配置
        try:
            from sqlalchemy import create_engine
            engine = create_engine(self.database.url)
            engine.dispose()
        except Exception as e:
            errors.append(f"数据库连接失败: {e}")

        return errors

    def generate_secret_key(self) -> str:
        """生成新的密钥"""
        return secrets.token_urlsafe(32)


class ConfigManager:
    """配置管理器"""

    def __init__(self):
        self._settings: EnhancedSettings | None = None
        self._config_cache: dict[str, Any] = {}

    def load_settings(
        self,
        config_file: str | Path | None = None,
        environment: str | None = None
    ) -> EnhancedSettings:
        """
        加载设置

        Args:
            config_file: 配置文件路径
            environment: 环境变量

        Returns:
            设置实例
        """
        if config_file:
            # 从文件加载
            self._settings = EnhancedSettings.load_from_file(config_file)
        else:
            # 从环境变量加载
            self._settings = EnhancedSettings()

        # 环境变量覆盖
        if environment:
            self._settings.environment = Environment(environment)

        # 验证配置
        errors = self._settings.validate_config()
        if errors:
            error_msg = "配置验证失败: " + "; ".join(errors)
            logger.error(error_msg)
            if self._settings.is_production():
                raise ValueError(error_msg)
            else:
                logger.warning(error_msg)

        return self._settings

    def get_settings(self) -> EnhancedSettings:
        """获取设置"""
        if self._settings is None:
            self._settings = self.load_settings()
        return self._settings

    def get_config(self, key: str, default: Any = None) -> Any:
        """
        获取配置值

        Args:
            key: 配置键
            default: 默认值

        Returns:
            配置值
        """
        settings = self.get_settings()
        return getattr(settings, key, default)

    def set_config(self, key: str, value: Any) -> None:
        """
        设置配置值

        Args:
            key: 配置键
            value: 配置值
        """
        settings = self.get_settings()
        setattr(settings, key, value)

    def reload_config(self) -> EnhancedSettings:
        """重新加载配置"""
        self._settings = None
        return self.get_settings()

    def export_config(self, config_path: str | Path) -> None:
        """
        导出配置到文件

        Args:
            config_path: 配置文件路径
        """
        settings = self.get_settings()
        settings.save_to_file(config_path)

    def import_config(self, config_path: str | Path) -> EnhancedSettings:
        """
        从文件导入配置

        Args:
            config_path: 配置文件路径

        Returns:
            设置实例
        """
        self._settings = EnhancedSettings.load_from_file(config_path)
        return self._settings


# 全局配置管理器实例
config_manager = ConfigManager()
settings = config_manager.get_settings()


# 便捷函数
def get_config(key: str, default: Any = None) -> Any:
    """获取配置便捷函数"""
    return config_manager.get_config(key, default)


def get_settings() -> EnhancedSettings:
    """获取设置便捷函数"""
    return config_manager.get_settings()


def reload_settings() -> EnhancedSettings:
    """重新加载设置便捷函数"""
    return config_manager.reload_settings()
