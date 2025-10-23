"""
API版本控制中间件
提供灵活的API版本管理功能
"""

import os
import time
import logging
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta

from fastapi import Request, Response, HTTPException
from fastapi.routing import APIRoute
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class APIVersionMiddleware(BaseHTTPMiddleware):
    """API版本控制中间件"""

    def __init__(
        self,
        app,
        default_version: str = "v1",
        supported_versions: List[str] = None,
        version_header: str = "X-API-Version",
        deprecated_versions: Dict[str, datetime] = None,
        sunset_period_days: int = 90
    ):
        super().__init__(app)
        self.default_version = default_version
        self.supported_versions = supported_versions or ["v1", "v2"]
        self.version_header = version_header
        self.deprecated_versions = deprecated_versions or {}
        self.sunset_period_days = sunset_period_days

        # 版本使用统计
        self.version_stats: Dict[str, Dict] = {
            version: {
                "count": 0,
                "last_used": None,
                "errors": 0
            }
            for version in self.supported_versions
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求，添加版本控制逻辑"""
        start_time = time.time()

        # 确定API版本
        version = self._determine_version(request)

        # 检查版本支持
        if version not in self.supported_versions:
            return self._create_version_error_response(
                detail=f"不支持的API版本: {version}",
                supported_versions=self.supported_versions,
                default_version=self.default_version
            )

        # 检查版本是否已弃用
        if version in self.deprecated_versions:
            sunset_date = self.deprecated_versions[version] + timedelta(days=self.sunset_period_days)
            if datetime.now() > sunset_date:
                return self._create_version_error_response(
                    detail=f"API版本 {version} 已停止支持",
                    supported_versions=self.supported_versions,
                    default_version=self.default_version,
                    status_code=410  # Gone
                )

        # 添加版本信息到请求状态
        request.state.api_version = version
        request.state.version_deprecated = version in self.deprecated_versions
        request.state.version_sunset_date = (
            self.deprecated_versions[version] + timedelta(days=self.sunset_period_days)
            if version in self.deprecated_versions else None
        )

        # 处理请求
        try:
            response = await call_next(request)

            # 更新版本统计
            self._update_version_stats(version, True)

            # 添加版本响应头
            response.headers[self.version_header] = version
            response.headers["X-API-Supported-Versions"] = ",".join(self.supported_versions)

            # 如果版本已弃用，添加警告头
            if version in self.deprecated_versions:
                response.headers["Deprecation"] = "true"
                response.headers["Sunset"] = request.state.version_sunset_date.isoformat()
                response.headers[
                    "Link"
                ] = f'</api/{self.default_version}{str(request.url.path)}>; rel="successor-version"'

            # 添加性能信息
            process_time = time.time() - start_time
            response.headers["X-Process-Time"] = str(process_time)

            return response

        except Exception as e:
            # 更新错误统计
            self._update_version_stats(version, False)
            logger.error(f"API版本 {version} 处理错误: {e}")
            raise

    def _determine_version(self, request: Request) -> str:
        """确定API版本"""
        # 1. 检查URL路径中的版本
        path_parts = str(request.url.path).strip("/").split("/")
        if len(path_parts) >= 2 and path_parts[0] == "api":
            potential_version = path_parts[1]
            if potential_version.startswith("v") and potential_version[1:].isdigit():
                return potential_version

        # 2. 检查查询参数
        version_param = request.query_params.get("version")
        if version_param and version_param.startswith("v"):
            return version_param

        # 3. 检查请求头
        version_header = request.headers.get(self.version_header)
        if version_header and version_header.startswith("v"):
            return version_header

        # 4. 使用默认版本
        return self.default_version

    def _create_version_error_response(
        self,
        detail: str,
        supported_versions: List[str],
        default_version: str,
        status_code: int = 400
    ) -> JSONResponse:
        """创建版本错误响应"""
        return JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "code": "API_VERSION_ERROR",
                    "message": detail,
                    "supported_versions": supported_versions,
                    "default_version": default_version,
                    "documentation": "/docs"
                }
            }
        )

    def _update_version_stats(self, version: str, success: bool):
        """更新版本使用统计"""
        if version in self.version_stats:
            self.version_stats[version]["count"] += 1
            self.version_stats[version]["last_used"] = datetime.now()
            if not success:
                self.version_stats[version]["errors"] += 1

    def get_version_stats(self) -> Dict[str, Any]:
        """获取版本使用统计"""
        return {
            "stats": self.version_stats,
            "supported_versions": self.supported_versions,
            "deprecated_versions": {
                version: sunset_date.isoformat()
                for version, sunset_date in self.deprecated_versions.items()
            },
            "total_requests": sum(
                stats["count"] for stats in self.version_stats.values()
            )
        }


class APIVersionRoute(APIRoute):
    """支持版本控制的API路由"""

    def __init__(
        self,
        path: str,
        endpoint: Callable,
        *,
        version: str = None,
        deprecated_versions: List[str] = None,
        successor_version: str = None,
        **kwargs
    ):
        super().__init__(path, endpoint, **kwargs)
        self.version = version
        self.deprecated_versions = deprecated_versions or []
        self.successor_version = successor_version

    def get_route_handler(self) -> Callable:
        """获取路由处理器，添加版本检查"""
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            # 获取请求版本
            requested_version = getattr(request.state, 'api_version', 'v1')

            # 检查版本兼容性
            if self.version and self.version != requested_version:
                # 如果是弃用的版本，检查是否允许访问
                if self.version in self.deprecated_versions:
                    # 允许访问，但添加警告
                    response = await original_route_handler(request)
                    response.headers["X-API-Version-Deprecated"] = "true"
                    return response
                else:
                    # 版本不匹配
                    raise HTTPException(
                        status_code=404,
                        detail=f"端点 {self.path} 在版本 {requested_version} 中不可用"
                    )

            return await original_route_handler(request)

        return custom_route_handler


def versioned_route(
    path: str,
    version: str,
    deprecated_versions: List[str] = None,
    successor_version: str = None
):
    """装饰器：创建版本化路由"""
    def decorator(func: Callable):
        func.__version__ = version
        func.__deprecated_versions__ = deprecated_versions or []
        func.__successor_version__ = successor_version
        return func
    return decorator


class APIVersionManager:
    """API版本管理器"""

    def __init__(self):
        self.versions: Dict[str, Dict] = {}
        self.migration_plans: Dict[str, List[str]] = {}

    def register_version(
        self,
        version: str,
        description: str,
        release_date: datetime,
        deprecation_date: Optional[datetime] = None,
        sunset_date: Optional[datetime] = None
    ):
        """注册API版本"""
        self.versions[version] = {
            "description": description,
            "release_date": release_date,
            "deprecation_date": deprecation_date,
            "sunset_date": sunset_date,
            "status": self._get_version_status(deprecation_date, sunset_date)
        }

    def create_migration_plan(
        self,
        from_version: str,
        to_version: str,
        steps: List[str]
    ):
        """创建版本迁移计划"""
        migration_key = f"{from_version}->{to_version}"
        self.migration_plans[migration_key] = steps

    def _get_version_status(
        self,
        deprecation_date: Optional[datetime],
        sunset_date: Optional[datetime]
    ) -> str:
        """获取版本状态"""
        now = datetime.now()

        if sunset_date and now > sunset_date:
            return "sunset"
        elif deprecation_date and now > deprecation_date:
            return "deprecated"
        else:
            return "active"

    def get_version_info(self) -> Dict[str, Any]:
        """获取版本信息"""
        return {
            "versions": self.versions,
            "migration_plans": self.migration_plans,
            "current_default": self._get_current_default_version()
        }

    def _get_current_default_version(self) -> str:
        """获取当前默认版本"""
        active_versions = [
            version for version, info in self.versions.items()
            if info["status"] == "active"
        ]
        # 返回最新的活跃版本
        return max(active_versions, key=lambda v: self.versions[v]["release_date"]) if active_versions else "v1"

    def generate_migration_guide(self, from_version: str, to_version: str) -> Dict[str, Any]:
        """生成迁移指南"""
        migration_key = f"{from_version}->{to_version}"
        steps = self.migration_plans.get(migration_key, [])

        from_info = self.versions.get(from_version, {})
        to_info = self.versions.get(to_version, {})

        return {
            "from_version": from_version,
            "to_version": to_version,
            "from_info": from_info,
            "to_info": to_info,
            "migration_steps": steps,
            "breaking_changes": self._get_breaking_changes(from_version, to_version),
            "recommended_actions": self._get_recommended_actions(from_version, to_version)
        }

    def _get_breaking_changes(self, from_version: str, to_version: str) -> List[str]:
        """获取破坏性变更（简化版本）"""
        # 这里应该基于实际的API变更来计算
        return [
            "端点路径变更",
            "请求参数格式变更",
            "响应结构变更"
        ]

    def _get_recommended_actions(self, from_version: str, to_version: str) -> List[str]:
        """获取推荐操作"""
        return [
            f"更新API调用从 {from_version} 到 {to_version}",
            "测试新的API端点",
            "更新错误处理逻辑",
            "检查响应格式变更"
        ]


# 创建全局版本管理器实例
version_manager = APIVersionManager()

# 初始化默认版本
version_manager.register_version(
    version="v1",
    description="初始API版本",
    release_date=datetime(2024, 1, 1)
)

version_manager.register_version(
    version="v2",
    description="增强版API，支持任务管理和高级功能",
    release_date=datetime(2024, 10, 1)
)