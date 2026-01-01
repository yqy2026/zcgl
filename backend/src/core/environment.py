"""
环境管理模块
提供统一的环境判断和依赖检查功能
"""

import os
from enum import Enum
from typing import Literal


class Environment(str, Enum):
    """环境类型枚举"""

    PRODUCTION = "production"
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"


class DependencyPolicy(str, Enum):
    """依赖策略枚举"""

    STRICT = "strict"  # 严格模式：缺少依赖时报错
    GRACEFUL = "graceful"  # 优雅降级：缺少依赖时警告
    OPTIONAL = "optional"  # 可选：缺少依赖时静默


def get_environment() -> Environment:
    """
    获取当前运行环境

    优先级：ENVIRONMENT > TESTING_MODE > DEBUG > DEV_MODE
    """
    # 检查是否明确指定了环境
    env_str = os.getenv("ENVIRONMENT", "").lower()
    if env_str:
        try:
            return Environment(env_str)
        except ValueError:
            pass

    # 检查测试模式
    if os.getenv("TESTING_MODE", "false").lower() == "true":
        return Environment.TESTING

    # 检查调试/开发模式
    if os.getenv("DEBUG", "false").lower() == "true":
        return Environment.DEVELOPMENT

    if os.getenv("DEV_MODE", "false").lower() == "true":
        return Environment.DEVELOPMENT

    # 默认生产环境
    return Environment.PRODUCTION


def is_production() -> bool:
    """是否为生产环境"""
    return get_environment() == Environment.PRODUCTION


def is_development() -> bool:
    """是否为开发环境"""
    return get_environment() == Environment.DEVELOPMENT


def is_testing() -> bool:
    """是否为测试环境"""
    return get_environment() == Environment.TESTING


def is_staging() -> bool:
    """是否为预发布环境"""
    return get_environment() == Environment.STAGING


def get_dependency_policy() -> DependencyPolicy:
    """
    获取依赖导入策略

    - 生产环境：严格模式
    - 开发环境：严格模式（便于发现问题）
    - 测试环境：优雅降级（mock 依赖）
    """
    env = get_environment()

    # 通过环境变量覆盖策略
    policy_str = os.getenv("DEPENDENCY_POLICY", "").lower()
    if policy_str:
        try:
            return DependencyPolicy(policy_str)
        except ValueError:
            pass

    # 默认策略
    if env == Environment.PRODUCTION:
        return DependencyPolicy.STRICT
    elif env == Environment.TESTING:
        return DependencyPolicy.GRACEFUL
    else:  # DEVELOPMENT or STAGING
        return DependencyPolicy.STRICT


def should_strict_import() -> bool:
    """是否应该严格导入（不允许降级）"""
    return get_dependency_policy() == DependencyPolicy.STRICT


# 关键依赖列表（生产环境必须存在）
CRITICAL_DEPENDENCIES = [
    "core.router_registry",
    "middleware.security_middleware",
    "core.config",
    "database",
]

# 可选依赖列表
OPTIONAL_DEPENDENCIES = [
    "services.providers.ocr_provider",
    "services.adapters.paddle_ocr_engine_adapter",
    "middleware.v1_compatibility",
    "middleware.request_logging",
    "middleware.error_recovery_middleware",
]
