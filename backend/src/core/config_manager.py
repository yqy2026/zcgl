"""
统一配置管理器
提供集中的配置管理、环境变量处理和配置验证功能
"""

import json
import logging
import os
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class ConfigSource(str, Enum):
    """配置来源枚举"""

    ENVIRONMENT = "environment"
    FILE = "file"
    DEFAULTS = "defaults"


@dataclass
class ConfigField:
    """配置字段定义"""

    name: str
    field_type: type
    default_value: Any = None
    required: bool = True
    description: str = ""
    env_var: str | None = None
    validator: Callable | None = None
    sensitive: bool = False  # 是否为敏感信息


class ConfigManager:
    """统一配置管理器"""

    def __init__(self, config_file: str | None = None):
        self.config_file = config_file or os.getenv("CONFIG_FILE", "config.yaml")
        self._config: dict[str, Any] = {}
        self._fields: dict[str, ConfigField] = {}
        self._initialized = False

    def register_field(self, field: ConfigField):
        """注册配置字段"""
        self._fields[field.name] = field
        logger.debug(f"Registered config field: {field.name}")

    def register_fields(self, fields: list[ConfigField]):
        """批量注册配置字段"""
        for field in fields:
            self.register_field(field)

    def initialize(self) -> None:
        """初始化配置管理器"""
        if self._initialized:
            return

        logger.info("Initializing configuration manager")

        # 1. 设置默认值
        self._load_defaults()

        # 2. 从文件加载配置
        if os.path.exists(self.config_file):
            self._load_from_file()
        else:
            logger.warning(f"Config file not found: {self.config_file}")

        # 3. 从环境变量加载配置
        self._load_from_environment()

        # 4. 验证配置
        self._validate_config()

        self._initialized = True
        logger.info("Configuration manager initialized successfully")

    def _load_defaults(self):
        """加载默认配置值"""
        for field_name, field in self._fields.items():
            if field.default_value is not None:
                self._config[field_name] = field.default_value

    def _load_from_file(self):
        """从文件加载配置"""
        try:
            file_ext = Path(self.config_file).suffix.lower()

            with open(self.config_file, encoding="utf-8") as f:
                if file_ext in [".yaml", ".yml"]:
                    file_config = yaml.safe_load(f)
                elif file_ext == ".json":
                    file_config = json.load(f)
                else:
                    logger.warning(f"Unsupported config file format: {file_ext}")
                    return

            if file_config:
                self._deep_update(self._config, file_config)
                logger.info(f"Loaded configuration from {self.config_file}")

        except Exception as e:
            logger.error(f"Failed to load config file {self.config_file}: {e}")

    def _load_from_environment(self):
        """从环境变量加载配置"""
        for field_name, field in self._fields.items():
            env_var = field.env_var or f"ZCGL_{field_name.upper()}"
            env_value = os.getenv(env_var)

            if env_value is not None:
                # 类型转换
                try:
                    converted_value = self._convert_type(env_value, field.field_type)
                    self._config[field_name] = converted_value
                    logger.debug(
                        f"Loaded {field_name} from environment variable {env_var}"
                    )
                except (ValueError, TypeError) as e:
                    logger.error(
                        f"Failed to convert environment variable {env_var}: {e}"
                    )

    def _convert_type(self, value: str, target_type: type) -> Any:
        """类型转换"""
        if target_type == bool:
            return value.lower() in ("true", "1", "yes", "on")
        elif target_type == int:
            return int(value)
        elif target_type == float:
            return float(value)
        elif target_type == list:
            # 支持逗号分隔的列表
            return [item.strip() for item in value.split(",") if item.strip()]
        else:
            return value

    def _validate_config(self):
        """验证配置"""
        errors = []

        for field_name, field in self._fields.items():
            value = self._config.get(field_name)

            # 检查必填字段
            if field.required and value is None:
                errors.append(f"Required field '{field_name}' is missing")
                continue

            # 跳过None值的验证
            if value is None:
                continue

            # 类型检查
            if not isinstance(value, field.field_type):
                try:
                    # 尝试类型转换
                    self._config[field_name] = self._convert_type(
                        str(value), field.field_type
                    )
                except (ValueError, TypeError):
                    errors.append(
                        f"Field '{field_name}' should be of type {field.field_type.__name__}, "
                        f"got {type(value).__name__}"
                    )

            # 自定义验证
            if field.validator:
                try:
                    if not field.validator(value):
                        errors.append(f"Field '{field_name}' failed custom validation")
                except Exception as e:
                    errors.append(f"Field '{field_name}' validation error: {e}")

        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(
                f"  - {error}" for error in errors
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

    def _deep_update(self, base_dict: dict, update_dict: dict):
        """深度更新字典"""
        for key, value in update_dict.items():
            if (
                key in base_dict
                and isinstance(base_dict[key], dict)
                and isinstance(value, dict)
            ):
                self._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        if not self._initialized:
            self.initialize()

        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """设置配置值"""
        self._config[key] = value

    def get_all(self) -> dict[str, Any]:
        """获取所有配置（过滤敏感信息）"""
        if not self._initialized:
            self.initialize()

        config = self._config.copy()
        # 过滤敏感信息
        for field_name, field in self._fields.items():
            if field.sensitive and field_name in config:
                config[field_name] = "***HIDDEN***"

        return config

    def reload(self) -> None:
        """重新加载配置"""
        logger.info("Reloading configuration")
        self._config.clear()
        self._initialized = False
        self.initialize()

    def save_to_file(self, file_path: str | None = None) -> None:
        """保存配置到文件"""
        if not file_path:
            file_path = self.config_file

        # 过滤敏感信息
        config_to_save = {}
        for field_name, field in self._fields.items():
            if field_name in self._config:
                if field.sensitive:
                    config_to_save[field_name] = self._config[field_name]
                else:
                    config_to_save[field_name] = self._config[field_name]

        try:
            file_ext = Path(file_path).suffix.lower()

            with open(file_path, "w", encoding="utf-8") as f:
                if file_ext in [".yaml", ".yml"]:
                    yaml.dump(
                        config_to_save, f, default_flow_style=False, allow_unicode=True
                    )
                elif file_ext == ".json":
                    json.dump(config_to_save, f, indent=2, ensure_ascii=False)

            logger.info(f"Configuration saved to {file_path}")

        except Exception as e:
            logger.error(f"Failed to save config file {file_path}: {e}")
            raise


# 全局配置管理器实例
config_manager = ConfigManager()


# 定义系统配置字段
def setup_default_config():
    """设置默认配置字段"""

    fields = [
        # 数据库配置
        ConfigField(
            name="database_url",
            field_type=str,
            default_value="sqlite:///./data/land_property.db",
            env_var="DATABASE_URL",
            description="数据库连接URL",
        ),
        ConfigField(
            name="database_echo",
            field_type=bool,
            default_value=False,
            env_var="DATABASE_ECHO",
            description="是否打印SQL语句",
        ),
        # API配置
        ConfigField(
            name="api_host",
            field_type=str,
            default_value="0.0.0.0",
            env_var="API_HOST",
            description="API服务器主机",
        ),
        ConfigField(
            name="api_port",
            field_type=int,
            default_value=8002,
            env_var="API_PORT",
            description="API服务器端口",
        ),
        ConfigField(
            name="api_title",
            field_type=str,
            default_value="Land Property Asset Management API",
            env_var="API_TITLE",
            description="API标题",
        ),
        # 安全配置
        ConfigField(
            name="secret_key",
            field_type=str,
            default_value="your-secret-key-change-in-production",
            env_var="SECRET_KEY",
            description="JWT密钥",
            sensitive=True,
            required=True,
        ),
        ConfigField(
            name="access_token_expire_minutes",
            field_type=int,
            default_value=30,
            env_var="ACCESS_TOKEN_EXPIRE_MINUTES",
            description="访问令牌过期时间（分钟）",
        ),
        # 文件上传配置
        ConfigField(
            name="upload_max_size_mb",
            field_type=int,
            default_value=50,
            env_var="UPLOAD_MAX_SIZE_MB",
            description="文件上传最大大小（MB）",
        ),
        ConfigField(
            name="upload_allowed_extensions",
            field_type=list,
            default_value=["xlsx", "xls", "pdf", "doc", "docx"],
            env_var="UPLOAD_ALLOWED_EXTENSIONS",
            description="允许上传的文件扩展名",
        ),
        # Excel处理配置
        ConfigField(
            name="excel_batch_size",
            field_type=int,
            default_value=1000,
            env_var="EXCEL_BATCH_SIZE",
            description="Excel处理批次大小",
        ),
        ConfigField(
            name="excel_timeout_seconds",
            field_type=int,
            default_value=300,
            env_var="EXCEL_TIMEOUT_SECONDS",
            description="Excel处理超时时间（秒）",
        ),
        # 任务处理配置
        ConfigField(
            name="task_max_retries",
            field_type=int,
            default_value=3,
            env_var="TASK_MAX_RETRIES",
            description="任务最大重试次数",
        ),
        ConfigField(
            name="task_retention_days",
            field_type=int,
            default_value=30,
            env_var="TASK_RETENTION_DAYS",
            description="任务记录保留天数",
        ),
        # 日志配置
        ConfigField(
            name="log_level",
            field_type=str,
            default_value="INFO",
            env_var="LOG_LEVEL",
            description="日志级别",
            validator=lambda x: x.upper()
            in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        ),
        ConfigField(
            name="log_file",
            field_type=str,
            default_value="logs/app.log",
            env_var="LOG_FILE",
            description="日志文件路径",
        ),
        # 缓存配置
        ConfigField(
            name="cache_enabled",
            field_type=bool,
            default_value=False,
            env_var="CACHE_ENABLED",
            description="是否启用缓存",
        ),
        ConfigField(
            name="cache_ttl_seconds",
            field_type=int,
            default_value=3600,
            env_var="CACHE_TTL_SECONDS",
            description="缓存过期时间（秒）",
        ),
        # 开发模式配置
        ConfigField(
            name="dev_mode",
            field_type=bool,
            default_value=False,
            env_var="DEV_MODE",
            description="开发模式",
        ),
        ConfigField(
            name="debug",
            field_type=bool,
            default_value=False,
            env_var="DEBUG",
            description="调试模式",
        ),
        # CORS配置
        ConfigField(
            name="cors_origins",
            field_type=list,
            default_value=["http://localhost:5173"],
            env_var="CORS_ORIGINS",
            description="CORS允许的源",
        ),
    ]

    config_manager.register_fields(fields)


# 便捷函数
def get_config(key: str, default: Any = None) -> Any:
    """获取配置值的便捷函数"""
    return config_manager.get(key, default)


def get_all_config() -> dict[str, Any]:
    """获取所有配置的便捷函数"""
    return config_manager.get_all()


def initialize_config():
    """初始化配置的便捷函数"""
    setup_default_config()
    config_manager.initialize()


if __name__ == "__main__":
    # 测试配置管理器
    initialize_config()

    print("=== Configuration ===")
    all_config = get_all_config()
    for key, value in sorted(all_config.items()):
        print(f"{key}: {value}")

    print(f"\nTotal configuration items: {len(all_config)}")
