"""
统一配置管理系统
整合所有配置文件，提供统一的配置管理体验
"""

import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml
from pydantic import Field, validator

try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings


class Environment(str, Enum):
    """环境枚举"""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    """日志级别枚举"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class DatabaseConfig(BaseSettings):
    """数据库配置"""

    # 数据库连接
    url: str = Field("sqlite:///./app.db", env="DATABASE_URL")
    echo: bool = Field(False, env="DATABASE_ECHO")
    pool_size: int = Field(10, env="DATABASE_POOL_SIZE")
    max_overflow: int = Field(20, env="DATABASE_MAX_OVERFLOW")
    pool_timeout: int = Field(30, env="DATABASE_POOL_TIMEOUT")
    pool_recycle: int = Field(3600, env="DATABASE_POOL_RECYCLE")

    # 数据库配置
    connect_args: Dict[str, Any] = Field(
        default={"charset": "utf8mb4"}, env="DATABASE_CONNECT_ARGS"
    )

    class Config:
        env_prefix = "DB_"


class SecurityConfig(BaseSettings):
    """安全配置"""

    # JWT配置
    secret_key: str = Field("your-secret-key-change-in-production", env="SECRET_KEY")
    algorithm: str = Field("HS256", env="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(7, env="REFRESH_TOKEN_EXPIRE_DAYS")

    # 密码配置
    bcrypt_rounds: int = Field(12, env="BCRYPT_ROUNDS")

    # CORS配置
    allowed_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        env="ALLOWED_ORIGINS",
    )
    allowed_methods: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"], env="ALLOWED_METHODS"
    )
    allowed_headers: List[str] = Field(default=["*"], env="ALLOWED_HEADERS")
    allow_credentials: bool = Field(True, env="ALLOW_CREDENTIALS")

    # 安全头配置
    enable_security_headers: bool = Field(True, env="ENABLE_SECURITY_HEADERS")

    @validator("secret_key")
    def validate_secret_key(cls, v):
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        if v == "dev-secret-key-DO-NOT-USE-IN-PRODUCTION-REPLACE-WITH-ENV-VAR":
            raise ValueError(
                "Please replace the default SECRET_KEY with a secure value"
            )
        return v


class LoggingConfig(BaseSettings):
    """日志配置"""

    level: LogLevel = Field(LogLevel.INFO, env="LOG_LEVEL")
    format: str = Field(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s", env="LOG_FORMAT"
    )
    date_format: str = Field("%Y-%m-%d %H:%M:%S", env="LOG_DATE_FORMAT")

    # 文件日志配置
    file_enabled: bool = Field(True, env="LOG_FILE_ENABLED")
    file_path: str = Field("logs/app.log", env="LOG_FILE_PATH")
    max_bytes: int = Field(10485760, env="LOG_MAX_BYTES")  # 10MB
    backup_count: int = Field(5, env="LOG_BACKUP_COUNT")

    # 控制台日志配置
    console_enabled: bool = Field(True, env="LOG_CONSOLE_ENABLED")


class APIConfig(BaseSettings):
    """API配置"""

    # API基础配置
    title: str = Field("地产资产管理系统API", env="API_TITLE")
    description: str = Field("地产资产管理系统后端API", env="API_DESCRIPTION")
    version: str = Field("1.0.0", env="API_VERSION")
    prefix: str = Field("/api/v1", env="API_PREFIX")

    # 服务器配置
    host: str = Field("0.0.0.0", env="HOST")
    port: int = Field(8002, env="PORT")
    reload: bool = Field(False, env="RELOAD")
    debug: bool = Field(False, env="DEBUG")

    # 请求限制
    max_request_size: int = Field(10485760, env="MAX_REQUEST_SIZE")  # 10MB
    request_timeout: int = Field(30, env="REQUEST_TIMEOUT")


class FileUploadConfig(BaseSettings):
    """文件上传配置"""

    # 基础配置
    upload_dir: str = Field("uploads", env="UPLOAD_DIR")
    max_file_size: int = Field(104857600, env="MAX_FILE_SIZE")  # 100MB
    allowed_extensions: List[str] = Field(
        default=[".pdf", ".xlsx", ".xls", ".csv", ".jpg", ".jpeg", ".png"],
        env="ALLOWED_EXTENSIONS",
    )

    # PDF处理配置
    pdf_processing_enabled: bool = Field(True, env="PDF_PROCESSING_ENABLED")
    ocr_enabled: bool = Field(True, env="OCR_ENABLED")
    max_pdf_pages: int = Field(100, env="MAX_pdf_PAGES")

    # 文件清理配置
    cleanup_enabled: bool = Field(True, env="FILE_CLEANUP_ENABLED")
    cleanup_interval_hours: int = Field(24, env="CLEANUP_INTERVAL_HOURS")
    file_retention_days: int = Field(30, env="FILE_RETENTION_DAYS")


class CacheConfig(BaseSettings):
    """缓存配置"""

    # Redis配置
    redis_url: str = Field("redis://localhost:6379/0", env="REDIS_URL")
    redis_enabled: bool = Field(True, env="REDIS_ENABLED")

    # 缓存配置
    default_ttl: int = Field(3600, env="CACHE_DEFAULT_TTL")  # 1小时
    session_ttl: int = Field(86400, env="CACHE_SESSION_TTL")  # 24小时

    # 缓存键前缀
    key_prefix: str = Field("zcgl:", env="CACHE_KEY_PREFIX")


class MonitoringConfig(BaseSettings):
    """监控配置"""

    # 健康检查
    health_check_enabled: bool = Field(True, env="HEALTH_CHECK_ENABLED")

    # 性能监控
    performance_monitoring_enabled: bool = Field(
        True, env="PERFORMANCE_MONITORING_ENABLED"
    )

    # 错误监控
    error_monitoring_enabled: bool = Field(True, env="ERROR_MONITORING_ENABLED")

    # 指标收集
    metrics_enabled: bool = Field(False, env="METRICS_ENABLED")
    metrics_port: int = Field(9090, env="METRICS_PORT")


class UnifiedConfig(BaseSettings):
    """统一配置类"""

    # 环境配置
    environment: Environment = Field(Environment.DEVELOPMENT, env="ENVIRONMENT")
    debug: bool = Field(False, env="DEBUG")

    # 子配置
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    file_upload: FileUploadConfig = Field(default_factory=FileUploadConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)

    # 应用配置
    app_name: str = Field("地产资产管理系统", env="APP_NAME")
    app_version: str = Field("1.0.0", env="APP_VERSION")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @validator("environment", pre=True)
    def set_debug_for_development(cls, v):
        """开发环境自动启用debug模式"""
        if v == Environment.DEVELOPMENT:
            return v
        return v

    @validator("debug", pre=True, always=True)
    def set_debug_based_on_environment(cls, v, values):
        """根据环境设置debug模式"""
        if "environment" in values:
            return values["environment"] == Environment.DEVELOPMENT
        return v

    def is_development(self) -> bool:
        """判断是否为开发环境"""
        return self.environment == Environment.DEVELOPMENT

    def is_production(self) -> bool:
        """判断是否为生产环境"""
        return self.environment == Environment.PRODUCTION

    def is_testing(self) -> bool:
        """判断是否为测试环境"""
        return self.environment == Environment.TESTING

    def get_database_url(self) -> str:
        """获取数据库连接URL"""
        return self.database.url

    def get_cors_origins(self) -> List[str]:
        """获取CORS允许的源"""
        return self.security.allowed_origins

    def upload_path(self) -> Path:
        """获取上传目录路径"""
        return Path(self.file_upload.upload_dir)

    def log_path(self) -> Path:
        """获取日志文件路径"""
        return Path(self.logging.file_path)


class ConfigManager:
    """配置管理器"""

    def __init__(self):
        self._config: Optional[UnifiedConfig] = None
        self._config_file: Optional[Path] = None
        # 自动加载配置
        self.load_config()

    def load_config(
        self,
        config_file: Optional[Union[str, Path]] = None,
        env_file: Optional[Union[str, Path]] = None,
    ) -> UnifiedConfig:
        """加载配置"""

        # 处理配置文件
        if config_file:
            self._config_file = Path(config_file)
            if self._config_file.exists():
                config_data = self._load_yaml_config(self._config_file)
                # 设置环境变量
                self._set_env_from_config(config_data)

        # 处理环境文件
        env_file_path = None
        if env_file:
            env_file_path = Path(env_file)
        elif Path(".env").exists():
            env_file_path = Path(".env")

        # 创建配置实例
        config_kwargs = {}
        if env_file_path:
            config_kwargs["env_file"] = str(env_file_path)

        self._config = UnifiedConfig(**config_kwargs)

        # 验证配置
        self._validate_config()

        # 创建必要的目录
        self._create_directories()

        return self._config

    def get_config(self) -> UnifiedConfig:
        """获取配置"""
        if self._config is None:
            raise RuntimeError("Configuration not loaded. Call load_config() first.")
        return self._config

    def _load_yaml_config(self, config_file: Path) -> Dict[str, Any]:
        """加载YAML配置文件"""
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            raise RuntimeError(f"Failed to load config file {config_file}: {e}")

    def _set_env_from_config(self, config_data: Dict[str, Any]) -> None:
        """从配置数据设置环境变量"""
        for key, value in config_data.items():
            if isinstance(value, (str, int, float, bool)):
                os.environ[key.upper()] = str(value)

    def _validate_config(self) -> None:
        """验证配置"""
        if not self._config:
            return

        # 验证关键配置
        if self._config.is_production():
            if (
                self._config.security.secret_key
                == "dev-secret-key-DO-NOT-USE-IN-PRODUCTION-REPLACE-WITH-ENV-VAR"
            ):
                raise ValueError("Production environment requires a secure SECRET_KEY")

            if self._config.debug:
                raise ValueError("Debug mode should not be enabled in production")

        # 验证数据库连接
        if not self._config.database.url:
            raise ValueError("DATABASE_URL is required")

        # 验证上传目录
        upload_path = self._config.upload_path()
        if not upload_path.exists():
            try:
                upload_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                raise RuntimeError(
                    f"Failed to create upload directory {upload_path}: {e}"
                )

    def _create_directories(self) -> None:
        """创建必要的目录"""
        if not self._config:
            return

        directories = [
            self._config.upload_path(),
            Path(self._config.logging.file_path).parent,
            Path("logs"),
            Path("temp"),
        ]

        for directory in directories:
            try:
                directory.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                print(f"Warning: Failed to create directory {directory}: {e}")


# 创建全局配置管理器实例
config_manager = ConfigManager()


# 便捷函数
def load_config(
    config_file: Optional[Union[str, Path]] = None,
    env_file: Optional[Union[str, Path]] = None,
) -> UnifiedConfig:
    """加载配置的便捷函数"""
    return config_manager.load_config(config_file, env_file)


def get_config() -> UnifiedConfig:
    """获取配置的便捷函数"""
    return config_manager.get_config()


# 全局配置实例（延迟加载）
_config_instance: Optional[UnifiedConfig] = None


def get_global_config() -> UnifiedConfig:
    """获取全局配置实例"""
    global _config_instance
    if _config_instance is None:
        _config_instance = load_config()
    return _config_instance
