"""
请求日志中间件
记录所有API请求的详细信息，用于安全和审计
"""

import json
import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from http import HTTPStatus
from typing import Any

import jwt
from fastapi import Request, Response
from jwt import PyJWTError as JWTError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ..core.config import settings
from ..crud.auth import UserCRUD
from ..crud.operation_log import OperationLogCRUD
from ..database import async_session_scope
from ..security.cookie_manager import cookie_manager
from ..security.logging_security import SensitiveDataFilter, log_request_info

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self.sensitive_filter = SensitiveDataFilter()
        self.max_body_size = 10 * 1024

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # 生成请求ID
        request_id = str(uuid.uuid4())

        # 记录请求开始时间
        start_time = time.time()

        # 获取客户端信息
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")

        # 对用户代理进行脱敏处理
        user_agent = self.sensitive_filter._filter_sensitive_data(user_agent)

        user_id = getattr(request.state, "user_id", None)
        username = getattr(request.state, "username", None)
        if not user_id:
            user_id, username = self._extract_user_info(request)
            if user_id:
                request.state.user_id = user_id
                request.state.username = username

        request, request_body = await self._extract_request_body(request)

        # 执行请求
        response = await call_next(request)

        # 计算请求持续时间
        duration_ms = (time.time() - start_time) * 1000

        user_id = getattr(request.state, "user_id", None) or user_id
        username = getattr(request.state, "username", None) or username

        # 对查询参数进行脱敏处理
        query_params = dict(request.query_params)
        filtered_query_params: dict[str, str] = {}
        for key, value in query_params.items():
            # 检查键是否敏感
            if self.sensitive_filter._is_sensitive_key(key):
                filtered_query_params[key] = "***"
            else:
                # 对值进行脱敏处理
                filtered_query_params[key] = (
                    self.sensitive_filter._filter_sensitive_data(str(value))
                )

        # 记录请求日志
        log_request_info(
            method=request.method,
            path=str(request.url.path),
            query_string=str(filtered_query_params) if filtered_query_params else None,
            status_code=response.status_code,
            duration_ms=duration_ms,
            request_id=request_id,
            client_ip=client_ip,
            user_agent=user_agent,
            user_id=user_id,
        )

        await self._log_operation(
            request=request,
            response=response,
            duration_ms=duration_ms,
            user_id=user_id,
            username=username,
            client_ip=client_ip,
            user_agent=user_agent,
            filtered_query_params=filtered_query_params,
            request_body=request_body,
        )

        # 添加请求ID到响应头
        response.headers["X-Request-ID"] = request_id

        return response

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端IP地址"""
        # 检查代理头
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:  # pragma: no cover
            return forwarded_for.split(",")[0].strip()  # pragma: no cover

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:  # pragma: no cover
            return real_ip  # pragma: no cover

        # 回退到客户端地址
        if request.client:  # pragma: no cover
            return request.client.host  # pragma: no cover

        return "unknown"  # pragma: no cover

    async def _log_operation(
        self,
        request: Request,
        response: Response,
        duration_ms: float,
        user_id: str | None,
        username: str | None,
        client_ip: str,
        user_agent: str,
        filtered_query_params: dict[str, str],
        request_body: str | None,
    ) -> None:
        if not user_id:
            return

        path = request.url.path or ""
        if not path.startswith("/api/"):
            return

        path_parts = [part for part in path.split("/") if part]
        if len(path_parts) >= 2 and path_parts[0] == "api":
            if path_parts[1] == "v1":
                path_parts = path_parts[2:]
            else:
                path_parts = path_parts[1:]

        if not path_parts:
            return

        module = path_parts[0]
        request_method = request.method.upper()
        action = self._map_action(request_method, path_parts)
        action_name = self._map_action_name(action)
        module_name = self._map_module_name(module)

        request_params = None
        if filtered_query_params:
            request_params = json.dumps(filtered_query_params, ensure_ascii=False)

        try:
            async with async_session_scope() as db:
                error_message = None
                if response.status_code >= 400:
                    try:
                        error_message = (
                            f"{response.status_code} "
                            f"{HTTPStatus(response.status_code).phrase}"
                        )
                    except ValueError:
                        error_message = str(response.status_code)

                resolved_username = username
                if not resolved_username and user_id:
                    user_crud = UserCRUD()
                    user_obj = await user_crud.get_async(db, user_id)
                    if user_obj:
                        resolved_username = user_obj.username

                log_crud = OperationLogCRUD()
                await log_crud.create_async(
                    db=db,
                    user_id=user_id,
                    username=resolved_username,
                    action=action,
                    action_name=action_name,
                    module=module,
                    module_name=module_name,
                    request_method=request_method,
                    request_url=path,
                    response_status=response.status_code,
                    response_time=int(duration_ms),
                    ip_address=client_ip,
                    user_agent=user_agent,
                    request_params=request_params,
                    request_body=request_body,
                    error_message=error_message,
                )
        except Exception:
            logger.exception("Operation log creation failed")
            return

    def _extract_user_info(self, request: Request) -> tuple[str | None, str | None]:
        token = None
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()

        if not token:
            cookie_header = request.headers.get("cookie", "")
            token = cookie_manager.get_token_from_cookie(cookie_header)

        if not token:
            return None, None

        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[getattr(settings, "ALGORITHM", "HS256")],
                audience=settings.JWT_AUDIENCE,
                issuer=settings.JWT_ISSUER,
            )
        except JWTError:
            return None, None

        user_id = payload.get("sub")
        username = payload.get("username")
        if not user_id:
            return None, None

        return str(user_id), str(username) if username else None

    async def _extract_request_body(
        self, request: Request
    ) -> tuple[Request, str | None]:
        if request.method in {"GET", "HEAD", "OPTIONS"}:
            return request, None

        content_type = request.headers.get("content-type", "").lower()
        body = await request.body()

        if not body:
            return request, None

        async def receive() -> dict[str, object]:
            return {"type": "http.request", "body": body, "more_body": False}

        request = Request(request.scope, receive)

        if "application/json" not in content_type:
            return request, None

        if len(body) > self.max_body_size:
            return request, None

        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return request, None

        filtered_payload: Any
        if isinstance(payload, dict):
            filtered_payload = self.sensitive_filter.filter_dict(payload)
        elif isinstance(payload, list):
            filtered_payload = self.sensitive_filter.filter_list(payload)
        else:
            filtered_payload = self.sensitive_filter._filter_sensitive_data(
                str(payload)
            )

        return request, json.dumps(filtered_payload, ensure_ascii=False)

    def _map_action(self, method: str, path_parts: list[str]) -> str:
        if path_parts and path_parts[-1] in {"login", "logout"}:
            return path_parts[-1]
        if "export" in path_parts:
            return "export"
        if "import" in path_parts:
            return "import"
        if method == "POST":
            return "create"
        if method in {"PUT", "PATCH"}:
            return "update"
        if method == "DELETE":
            return "delete"
        return "read"

    def _map_action_name(self, action: str) -> str:
        mapping = {
            "create": "创建",
            "update": "更新",
            "delete": "删除",
            "read": "查看",
            "login": "登录",
            "logout": "登出",
            "export": "导出",
            "import": "导入",
            "security": "安全操作",
        }
        return mapping.get(action, action)

    def _map_module_name(self, module: str) -> str:
        mapping = {
            "dashboard": "数据看板",
            "assets": "资产管理",
            "rental": "租赁管理",
            "contract-groups": "租赁管理",
            "contracts": "租赁管理",
            "ownership": "权属方管理",
            "ownerships": "权属方管理",
            "project": "项目管理",
            "projects": "项目管理",
            "system": "系统管理",
            "auth": "认证授权",
            "logs": "操作日志",
            "organizations": "组织架构管理",
            "roles": "角色管理",
            "permissions": "权限管理",
        }
        return mapping.get(module, module)


# 便捷函数创建中间件
def create_request_logging_middleware(
    app: ASGIApp | None = None,
) -> RequestLoggingMiddleware | type[RequestLoggingMiddleware]:
    """创建请求日志中间件"""
    if app is None:  # pragma: no cover
        return RequestLoggingMiddleware  # pragma: no cover
    return RequestLoggingMiddleware(app)  # pragma: no cover
