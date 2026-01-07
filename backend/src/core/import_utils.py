"""
统一导入工具
提供安全的条件导入功能，支持环境感知的降级策略
"""

import importlib
import logging
from collections.abc import Callable
from typing import Any

from .environment import DependencyPolicy, get_dependency_policy, is_production

logger = logging.getLogger(__name__)


def safe_import(
    module_path: str,
    *,
    critical: bool = False,
    fallback: Any = None,
    mock_factory: Callable[[], Any] | None = None,
    silent: bool = False,
) -> Any:
    """
    安全导入模块，支持环境感知的降级策略

    Args:
        module_path: 模块路径（点分隔）
        critical: 是否为关键依赖（生产环境必须存在）
        fallback: 降级时返回的默认值
        mock_factory: 降级时使用的 mock 工厂函数
        silent: 是否静默处理错误

    Returns:
        导入的模块或降级值

    Raises:
        ImportError: 生产环境导入关键依赖失败时

    Examples:
        >>> # 关键依赖 - 生产环境必须存在
        >>> router_registry = safe_import("core.router_registry", critical=True)

        >>> # 可选依赖 - 允许降级
        >>> ocr_service = safe_import("services.ocr", fallback=None)

        >>> # 使用 mock 工厂
        >>> mock_redis = safe_import("redis", mock_factory=lambda: MockRedis())
    """
    policy = get_dependency_policy()

    try:
        # 动态导入模块
        module = importlib.import_module(module_path)
        return module

    except ImportError as e:
        error_msg = f"导入失败: {module_path} - {str(e)}"

        # 生产环境的关键依赖必须存在
        if critical and is_production():
            logger.error(f"生产环境关键依赖缺失: {error_msg}")
            raise ImportError(f"生产环境缺少关键依赖: {module_path}") from e

        # 严格模式下的关键依赖应该警告
        if critical and policy == DependencyPolicy.STRICT:
            logger.warning(f"关键依赖缺失（严格模式）: {error_msg}")

        # 优雅降级模式
        if not silent:
            logger.info(f"依赖降级: {error_msg}")

        # 返回降级值
        if mock_factory is not None:
            return mock_factory()
        return fallback

    except Exception as e:
        # 非导入错误应该重新抛出
        error_msg = f"导入异常: {module_path} - {str(e)}"
        logger.error(error_msg)
        raise


def safe_import_from(
    module_path: str,
    attribute_name: str,
    *,
    critical: bool = False,
    fallback: Any = None,
    silent: bool = False,
) -> Any:
    """
    从模块安全导入特定属性

    Args:
        module_path: 模块路径
        attribute_name: 属性名称
        critical: 是否为关键依赖
        fallback: 降级时返回的默认值
        silent: 是否静默处理错误

    Returns:
        导入的属性或降级值

    Examples:
        >>> get_ocr_service = safe_import_from(
        ...     "services.providers.ocr_provider", "get_ocr_service", fallback=lambda: None
        ... )
    """
    policy = get_dependency_policy()

    try:
        module = importlib.import_module(module_path)
        return getattr(module, attribute_name)

    except (ImportError, AttributeError) as e:
        error_msg = f"导入失败: {module_path}.{attribute_name} - {str(e)}"

        if critical and is_production():
            logger.error(f"生产环境关键依赖缺失: {error_msg}")
            raise ImportError(f"生产环境缺少关键依赖: {module_path}.{attribute_name}") from e

        if critical and policy == DependencyPolicy.STRICT:
            logger.warning(f"关键依赖缺失（严格模式）: {error_msg}")

        if not silent:
            logger.info(f"依赖降级: {error_msg}")

        return fallback


def create_mock_registry() -> Any:
    """创建 Mock 路由注册器"""

    class MockRegistry:
        def register_global_dependency(self, dep):
            pass

        def include_all(self, app, version):
            pass

    return MockRegistry()


def create_lambda_none(*args, **kwargs) -> None:
    """返回 lambda: None 的工厂函数"""
    return lambda *args, **kwargs: None


# 便捷装饰器
def optional_import(module_path: str):
    """
    装饰器：标记导入失败时应跳过的功能

    Example:
        @optional_import("redis")
        def my_function():
            redis_client.ping()
    """

    def decorator(func):
        try:
            __import__(module_path)
            return func
        except ImportError:
            return lambda *args, **kwargs: None

    return decorator
