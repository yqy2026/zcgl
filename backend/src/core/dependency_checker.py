"""
启动时依赖检查
在生产环境验证所有关键依赖是否存在
"""

import logging
from collections.abc import Callable

from .environment import is_production
from .exception_handler import ConfigurationError

logger = logging.getLogger(__name__)


class DependencyChecker:
    """依赖检查器"""

    def __init__(self) -> None:
        self.critical_deps: dict[str, Callable[[], bool]] = {}
        self.optional_deps: dict[str, Callable[[], bool]] = {}

    def register_critical(self, name: str, check_fn: Callable[[], bool]) -> None:
        """
        注册关键依赖检查函数

        Args:
            name: 依赖名称
            check_fn: 检查函数，返回 True 表示依赖可用
        """
        self.critical_deps[name] = check_fn

    def register_optional(self, name: str, check_fn: Callable[[], bool]) -> None:
        """
        注册可选依赖检查函数

        Args:
            name: 依赖名称
            check_fn: 检查函数，返回 True 表示依赖可用
        """
        self.optional_deps[name] = check_fn

    def check_all(self) -> bool:
        """
        检查所有依赖

        Returns:
            bool: 所有关键依赖是否都可用

        Raises:
            ConfigurationError: 生产环境关键依赖缺失时
        """
        logger.info("开始依赖检查...")

        all_ok = True

        # 检查关键依赖
        logger.info("\n关键依赖检查:")
        for name, check_fn in self.critical_deps.items():
            try:
                if check_fn():
                    logger.info(f"  ✓ {name}")
                else:
                    logger.error(f"  ✗ {name} - 检查失败")
                    all_ok = False
            except Exception as e:
                logger.error(f"  ✗ {name} - 检查异常: {e}")
                all_ok = False

        # 检查可选依赖
        logger.info("\n可选依赖检查:")
        for name, check_fn in self.optional_deps.items():
            try:
                if check_fn():
                    logger.info(f"  ○ {name} - 已加载")
                else:
                    logger.info(f"  ○ {name} - 未加载（可选）")
            except Exception as e:
                logger.warning(f"  ○ {name} - 检查异常: {e}")

        # 生产环境关键依赖必须全部存在
        if is_production() and not all_ok:
            logger.error("生产环境关键依赖检查失败，拒绝启动")
            raise ConfigurationError(
                "生产环境关键依赖缺失",
                config_key="CRITICAL_DEPENDENCIES",
            )

        logger.info(f"\n依赖检查完成: {'✓ 通过' if all_ok else '⚠️ 有警告'}")
        return all_ok


# 全局依赖检查器实例
dependency_checker = DependencyChecker()
