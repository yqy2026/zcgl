"""
V1 API兼容性中间件
提供V1端点到非版本化端点的自动重定向
"""

from fastapi import Request, Response
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import logging
import re
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)


class V1CompatibilityMiddleware(BaseHTTPMiddleware):
    """
    V1 API兼容性中间件
    自动将V1端点请求重定向到非版本化端点
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

        # 统一非版本化架构 - 保留关键V1端点兼容性
        self.path_mappings = {
            # 健康检查和应用信息 - 直接在main.py中定义了双重路径
            # 这里主要用于动态路由的重定向

            # 动态路由映射（如果有动态生成的端点）
            r'^/api/v1/analytics/comprehensive$': '/api/analytics/comprehensive',
            r'^/api/v1/organizations/tree$': '/api/organizations/tree',
            r'^/api/v1/rental-contracts$': '/api/rental-contracts',
        }

        # 需要保留的V1端点（不重定向）
        self.preserved_v1_endpoints = [
            '/api/v1/health',
            '/api/v1/info',
        ]

    async def dispatch(self, request: Request, call_next):
        """处理请求，检查是否需要V1兼容性重定向"""

        # 获取请求路径
        path = request.url.path

        # 只处理V1端点请求
        if not path.startswith('/api/v1/'):
            return await call_next(request)

        # 检查是否为保留的V1端点
        if path in self.preserved_v1_endpoints:
            return await call_next(request)

        # 尝试匹配重定向规则
        new_path = self._get_redirected_path(path)

        if new_path and new_path != path:
            # 记录重定向
            logger.info(f"V1兼容性重定向: {path} -> {new_path}")

            # 构建新的URL
            url = str(request.url)
            new_url = url.replace(path, new_path, 1)

            # 对于GET请求使用重定向，其他请求使用内部转发
            if request.method == "GET":
                return RedirectResponse(
                    url=new_url,
                    status_code=302,
                    headers={"X-V1-Redirect": "true"}
                )
            else:
                # 对于非GET请求，修改请求路径并继续处理
                request.scope["path"] = new_path
                request.scope["raw_path"] = new_path.encode()
                return await call_next(request)

        # 如果没有匹配的重定向规则，继续处理原请求
        return await call_next(request)

    def _get_redirected_path(self, original_path: str) -> str:
        """根据映射规则获取重定向路径"""

        for pattern, replacement in self.path_mappings.items():
            match = re.match(pattern, original_path)
            if match:
                # 使用替换规则，支持捕获组
                new_path = re.sub(pattern, replacement, original_path)
                return new_path

        # 如果没有匹配的规则，尝试通用规则
        # 将 /api/v1/{module}/{action} 映射为 /api/{module}/{action}
        generic_match = re.match(r'^/api/v1/([^/]+)(.*)$', original_path)
        if generic_match:
            module = generic_match.group(1)
            rest = generic_match.group(2)
            return f'/api/{module}{rest}'

        return original_path

    def add_custom_mapping(self, v1_pattern: str, target_path: str):
        """添加自定义V1端点映射"""
        self.path_mappings[v1_pattern] = target_path
        logger.info(f"添加V1兼容性映射: {v1_pattern} -> {target_path}")

    def preserve_endpoint(self, endpoint: str):
        """保留指定的V1端点（不进行重定向）"""
        if endpoint not in self.preserved_v1_endpoints:
            self.preserved_v1_endpoints.append(endpoint)
            logger.info(f"保留V1端点: {endpoint}")


# 便捷函数
def add_v1_compatibility(app, preserve_endpoints: list = None):
    """为FastAPI应用添加V1兼容性中间件"""

    if preserve_endpoints:
        middleware = V1CompatibilityMiddleware(app)
        for endpoint in preserve_endpoints:
            middleware.preserve_endpoint(endpoint)
        app.add_middleware(V1CompatibilityMiddleware)
    else:
        app.add_middleware(V1CompatibilityMiddleware)

    logger.info("V1兼容性中间件已启用")


# 重定向日志装饰器
def log_v1_redirect(func):
    """装饰器：记录V1重定向日志"""
    async def wrapper(*args, **kwargs):
        logger.info(f"V1端点访问: {func.__name__}")
        return await func(*args, **kwargs)
    return wrapper


class V1CompatibilityConfig:
    """V1兼容性配置类"""

    def __init__(self):
        self.enabled = True
        self.log_redirects = True
        self.preserved_endpoints = [
            '/api/v1/health',
            '/api/v1/info',
        ]
        self.custom_mappings = {}

    def add_mapping(self, v1_path: str, target_path: str):
        """添加自定义映射"""
        self.custom_mappings[v1_path] = target_path

    def preserve_endpoint(self, endpoint: str):
        """保留端点"""
        if endpoint not in self.preserved_endpoints:
            self.preserved_endpoints.append(endpoint)


# 全局配置实例
v1_config = V1CompatibilityConfig()