from typing import Any

"""
路由注册器
统一管理API路由注册，支持版本控制和中间件配置
"""

import logging
from collections.abc import Callable

from fastapi import APIRouter, FastAPI

logger = logging.getLogger(__name__)


class RouteRegistry:
    """路由注册器"""

    def __init__(self) -> None:
        self.routers: list[dict[str, Any]] = []
        self.versioned_routers: dict[str | None, list[dict[str, Any]]] = {}
        self.global_middlewares: list[Callable[..., Any]] = []
        self.global_dependencies: list[Any] = []

    def register_router(
        self,
        router: APIRouter,
        prefix: str,
        tags: list[str],
        version: str | None = "v1",
        middleware: list[Callable[..., Any]] | None = None,
        dependencies: list[Any] | None = None,
        should_include_in_schema: bool = True,
        is_deprecated: bool = False,
    ) -> None:
        """
        注册路由器

        Args:
            router: APIRouter实例
            prefix: 路由前缀
            tags: 路由标签
            version: API版本
            middleware: 中间件列表
            dependencies: 依赖注入列表
            should_include_in_schema: 是否包含在API文档中
            is_deprecated: 是否已废弃
        """
        router_config = {
            "router": router,
            "prefix": prefix,
            "tags": tags,
            "middleware": middleware or [],
            "dependencies": dependencies or [],
            "include_in_schema": should_include_in_schema,
            "deprecated": is_deprecated,
            "version": version,
        }

        # 添加到versioned_routers（支持None版本用于非版本化路由）
        if version not in self.versioned_routers:
            self.versioned_routers[version] = []

        self.versioned_routers[version].append(router_config)
        logger.info(f"注册路由: {prefix} (版本: {version}, 标签: {tags})")

    def register_global_middleware(self, middleware: Callable[..., Any]) -> None:
        """注册全局中间件"""
        self.global_middlewares.append(middleware)
        logger.info(f"注册全局中间件: {middleware.__name__}")

    def register_global_dependency(self, dependency: Any) -> None:
        """注册全局依赖"""
        self.global_dependencies.append(dependency)
        logger.info(f"注册全局依赖: {dependency}")

    def include_all_routers(self, app: FastAPI, version: str | None = None) -> None:
        """
        包含所有指定版本的路由

        Args:
            app: FastAPI应用实例
            version: API版本，None表示包含所有非版本化路由
        """
        # 处理None版本 - 用于非版本化路由（如PDF导入）
        if version is None:
            version = "v1"  # 默认使用v1版本
            # 先检查是否有None版本的路由（非版本化路由）
            if None in self.versioned_routers:
                logger.info(f"包含 {len(self.versioned_routers[None])} 个非版本化路由")
                for router_config in self.versioned_routers[None]:
                    self._include_single_router(app, router_config)
            # 再处理v1版本
            if version not in self.versioned_routers:
                logger.warning(f"版本 {version} 没有注册的路由")
                return
        else:
            if version not in self.versioned_routers:
                logger.warning(f"版本 {version} 没有注册的路由")
                return

        for router_config in self.versioned_routers[version]:
            self._include_single_router(app, router_config)

        logger.info(
            f"完成版本 {version} 的路由注册，共 {len(self.versioned_routers[version])} 个路由"
        )

    def _include_single_router(
        self, app: FastAPI, router_config: dict[str, Any]
    ) -> None:
        """包含单个路由器"""
        router = router_config["router"]
        prefix = router_config["prefix"]
        tags = router_config["tags"]
        middleware = router_config["middleware"]
        dependencies = router_config["dependencies"]
        include_in_schema = router_config["include_in_schema"]
        deprecated = router_config["deprecated"]

        # 应用全局依赖
        all_dependencies = list(self.global_dependencies) + list(dependencies)

        # 注册路由
        app.include_router(
            router,
            prefix=prefix,
            tags=tags,
            dependencies=all_dependencies,
            include_in_schema=include_in_schema,
        )

        # 应用路由级中间件
        for mw in middleware:
            router.middleware("http")(mw)

        if deprecated:
            logger.warning(f"路由 {prefix} 已标记为废弃")

    def include_all(self, app: FastAPI, version: str | None = None) -> None:
        """与 include_all_routers 等价的便捷别名，便于主入口统一调用"""
        self.include_all_routers(app, version)

    def get_router_info(self, version: str = "v1") -> list[dict[str, Any]]:
        """获取路由信息"""
        if version not in self.versioned_routers:
            return []

        router_info = []
        for config in self.versioned_routers[version]:
            router_info.append(
                {
                    "prefix": config["prefix"],
                    "tags": config["tags"],
                    "deprecated": config["deprecated"],
                    "route_count": len(config["router"].routes),
                }
            )

        return router_info

    def validate_routes(self) -> list[str]:
        """验证路由配置，返回警告信息"""
        warnings = []

        for version, routers in self.versioned_routers.items():
            prefixes = []
            for config in routers:
                prefix = config["prefix"]
                if prefix in prefixes:
                    warnings.append(f"版本 {version} 存在重复的前缀: {prefix}")
                prefixes.append(prefix)

        return warnings


class APIVersionManager:
    """API版本管理器"""

    def __init__(self, registry: RouteRegistry):
        self.registry = registry
        self.supported_versions = ["v1"]
        self.default_version = "v1"

    def add_version_support(self, version: str) -> None:
        """添加版本支持"""
        if version not in self.supported_versions:
            self.supported_versions.append(version)
            logger.info(f"添加API版本支持: {version}")

    def get_latest_version(self) -> str:
        """获取最新版本"""
        return self.supported_versions[-1]

    def is_version_supported(self, version: str) -> bool:
        """检查版本是否支持"""
        return version in self.supported_versions

    def setup_version_routing(self, app: FastAPI) -> None:
        """设置版本路由"""
        for version in self.supported_versions:
            self.registry.include_all_routers(app, version)

        # 添加版本信息端点
        @app.get("/api/versions", tags=["API版本"])
        async def get_supported_versions() -> dict[str, Any]:
            return {
                "supported_versions": self.supported_versions,
                "default_version": self.default_version,
                "latest_version": self.get_latest_version(),
            }

        # 添加版本重定向
        @app.get("/api", tags=["API版本"])
        async def redirect_to_default_version() -> Any:
            from fastapi.responses import RedirectResponse

            return RedirectResponse(url=f"/api/{self.default_version}")


# 创建全局路由注册器实例
route_registry = RouteRegistry()
version_manager = APIVersionManager(route_registry)


def register_api_routes() -> None:
    """注册所有API路由的便捷函数"""
    try:
        from ..api.v1 import api_router as v1_router

        # 注册路由（版本化）
        route_registry.register_router(
            router=v1_router, prefix="/api/v1", tags=["API"], version="v1"
        )
        logger.info("API 主路由注册成功（版本化）")
    except Exception as e:  # pragma: no cover
        logger.error(f"API 主路由注册失败: {e}")  # pragma: no cover
        raise  # pragma: no cover

    logger.info("完成API路由注册")


def setup_app_routing(app: FastAPI) -> None:
    """设置应用路由"""
    # 注册所有API路由
    register_api_routes()

    # 设置版本路由
    version_manager.setup_version_routing(app)

    # 验证路由配置
    warnings = route_registry.validate_routes()
    for warning in warnings:
        logger.warning(warning)

    logger.info("应用路由设置完成")


# 路由信息工具函数
def get_all_routes_info() -> dict[str, list[dict[str, Any]]]:
    """获取所有版本的路由信息"""
    routes_info: dict[str, list[dict[str, Any]]] = {}
    for version in route_registry.versioned_routers:
        if version is not None:
            routes_info[version] = route_registry.get_router_info(version)
    return routes_info


def get_routes_by_tag(tag: str, version: str = "v1") -> list[dict[str, Any]]:
    """根据标签获取路由信息"""
    routes = route_registry.get_router_info(version)
    return [route for route in routes if tag in route["tags"]]


def get_deprecated_routes(version: str = "v1") -> list[dict[str, Any]]:
    """获取已废弃的路由"""
    routes = route_registry.get_router_info(version)
    return [route for route in routes if route["deprecated"]]


# 导出主要组件
__all__ = [
    "RouteRegistry",
    "APIVersionManager",
    "route_registry",
    "version_manager",
    "register_api_routes",
    "setup_app_routing",
    "get_all_routes_info",
    "get_routes_by_tag",
    "get_deprecated_routes",
]
