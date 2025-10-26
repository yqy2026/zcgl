#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
错误恢复中间件
在API层面集成错误恢复机制，提供透明的错误处理和恢复
"""

import time
import traceback
import uuid
from typing import Callable, Dict, Any, Optional
from datetime import datetime
import logging
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..services.error_recovery_service import (
    ErrorRecoveryEngine,
    ErrorCategory,
    ErrorSeverity,
    ErrorContext,
    with_error_recovery
)

logger = logging.getLogger(__name__)

class ErrorRecoveryMiddleware(BaseHTTPMiddleware):
    """错误恢复中间件"""

    def __init__(self, app, recovery_engine: Optional[ErrorRecoveryEngine] = None):
        super().__init__(app)
        self.recovery_engine = recovery_engine or ErrorRecoveryEngine()
        self.request_contexts = {}  # 存储请求上下文

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求并执行错误恢复"""

        request_id = str(uuid.uuid4())
        start_time = time.time()

        # 添加请求ID到请求状态
        request.state.request_id = request_id
        request.state.start_time = start_time

        try:
            # 调用下一个中间件或路由处理器
            response = await call_next(request)

            # 记录成功请求
            self._record_success_request(request, response, start_time)

            return response

        except HTTPException as http_exc:
            # HTTP异常通常不需要恢复，直接返回
            logger.warning(f"HTTP异常: {http_exc.status_code} - {http_exc.detail}")
            return self._create_http_error_response(http_exc, request_id)

        except Exception as exc:
            # 其他异常，尝试恢复
            return await self._handle_exception_with_recovery(
                exc, request, call_next, request_id, start_time
            )

    async def _handle_exception_with_recovery(
        self,
        exc: Exception,
        request: Request,
        call_next: Callable,
        request_id: str,
        start_time: float
    ) -> Response:
        """处理异常并尝试恢复"""

        # 确定错误类别
        error_category = self._classify_error(exc, request)
        error_severity = self._determine_error_severity(exc, error_category)

        # 创建错误上下文
        error_context = ErrorContext(
            error_id=request_id,
            error_type=type(exc).__name__,
            error_message=str(exc),
            stack_trace=traceback.format_exc(),
            severity=error_severity,
            category=error_category,
            timestamp=datetime.now(),
            user_id=getattr(request.state, 'user_id', None),
            request_id=request_id,
            component=request.url.path,
            operation=f"{request.method} {request.url.path}",
            additional_data={
                'url': str(request.url),
                'method': request.method,
                'headers': dict(request.headers),
                'query_params': dict(request.query_params)
            }
        )

        logger.error(f"请求异常 [ID: {request_id}]: {error_category.value} - {str(exc)}")

        # 尝试恢复
        recovery_func = self._create_recovery_function(request, call_next)
        recovery_result = await self.recovery_engine.recover_from_error(
            error_context, recovery_func
        )

        if recovery_result.success:
            # 恢复成功
            logger.info(f"错误恢复成功 [ID: {request_id}]: {recovery_result.strategy_used}")

            # 创建成功响应，包含恢复信息
            recovery_time = time.time() - start_time
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "data": recovery_result.metrics.get('result'),
                    "recovery_info": {
                        "was_recovered": True,
                        "strategy_used": recovery_result.strategy_used,
                        "attempts_made": recovery_result.attempts_made,
                        "recovery_time": recovery_result.total_time,
                        "recovery_actions": recovery_result.recovery_actions
                    },
                    "request_id": request_id,
                    "processing_time": recovery_time
                }
            )
        else:
            # 恢复失败
            logger.error(f"错误恢复失败 [ID: {request_id}]: {recovery_result.final_error}")

            # 记录恢复失败
            self._record_recovery_failure(error_context, recovery_result)

            # 创建错误响应
            return JSONResponse(
                status_code=self._get_error_status_code(error_category, error_severity),
                content={
                    "success": False,
                    "error": {
                        "code": f"{error_category.value.upper()}_ERROR",
                        "message": str(recovery_result.final_error or exc),
                        "type": error_category.value,
                        "severity": error_severity.value
                    },
                    "recovery_info": {
                        "was_recovered": False,
                        "strategy_used": recovery_result.strategy_used,
                        "attempts_made": recovery_result.attempts_made,
                        "recovery_actions": recovery_result.recovery_actions,
                        "suggestions": self._get_error_suggestions(error_category)
                    },
                    "request_id": request_id
                }
            )

    def _classify_error(self, exc: Exception, request: Request) -> ErrorCategory:
        """分类错误类型"""

        error_message = str(exc).lower()
        error_type = type(exc).__name__.lower()

        # 网络相关错误
        if any(keyword in error_message for keyword in ['timeout', 'connection', 'network', 'dns']) or \
           any(keyword in error_type for keyword in ['timeout', 'connection']):
            return ErrorCategory.NETWORK

        # 数据库相关错误
        if any(keyword in error_message for keyword in ['database', 'sql', 'connection', 'deadlock']) or \
           any(keyword in error_type for keyword in ['database', 'sql']):
            return ErrorCategory.DATABASE

        # 验证相关错误
        if any(keyword in error_message for keyword in ['validation', 'invalid', 'required', 'format']) or \
           any(keyword in error_type for keyword in ['validation', 'value']):
            return ErrorCategory.VALIDATION

        # 认证相关错误
        if any(keyword in error_message for keyword in ['auth', 'token', 'unauthorized', 'permission']) or \
           any(keyword in error_type for keyword in ['auth', 'permission']):
            return ErrorCategory.AUTHENTICATION

        # 文件系统相关错误
        if any(keyword in error_message for keyword in ['file', 'path', 'directory', 'disk']) or \
           any(keyword in error_type for keyword in ['file', 'path', 'io']):
            return ErrorCategory.FILE_SYSTEM

        # 外部API相关错误
        if any(keyword in error_message for keyword in ['api', 'service', 'external']) or \
           any(keyword in error_type for keyword in ['api']):
            return ErrorCategory.EXTERNAL_API

        # 处理相关错误
        if any(keyword in error_message for keyword in ['processing', 'parse', 'transform']) or \
           any(keyword in error_type for keyword in ['processing', 'parse']):
            return ErrorCategory.PROCESSING

        # 默认为系统错误
        return ErrorCategory.SYSTEM

    def _determine_error_severity(self, exc: Exception, error_category: ErrorCategory) -> ErrorSeverity:
        """确定错误严重程度"""

        # 关键类别通常为高严重性
        if error_category in [ErrorCategory.DATABASE, ErrorCategory.SYSTEM]:
            return ErrorSeverity.HIGH

        # 认证和权限为中等严重性
        if error_category in [ErrorCategory.AUTHENTICATION, ErrorCategory.AUTHORIZATION]:
            return ErrorSeverity.MEDIUM

        # 验证和文件系统错误通常为低严重性
        if error_category in [ErrorCategory.VALIDATION, ErrorCategory.FILE_SYSTEM]:
            return ErrorSeverity.LOW

        # 默认为中等严重性
        return ErrorSeverity.MEDIUM

    def _create_recovery_function(self, request: Request, call_next: Callable) -> Callable:
        """创建恢复函数"""

        async def recovery_function():
            # 在恢复时重新创建请求上下文
            response = await call_next(request)
            return response

        return recovery_function

    def _get_error_status_code(self, error_category: ErrorCategory, severity: ErrorSeverity) -> int:
        """获取错误状态码"""

        status_map = {
            ErrorCategory.VALIDATION: 400,
            ErrorCategory.AUTHENTICATION: 401,
            ErrorCategory.AUTHORIZATION: 403,
            ErrorCategory.FILE_SYSTEM: 404,
            ErrorCategory.NETWORK: 503,
            ErrorCategory.DATABASE: 503,
            ErrorCategory.EXTERNAL_API: 502,
            ErrorCategory.PROCESSING: 422,
            ErrorCategory.BUSINESS_LOGIC: 422,
            ErrorCategory.SYSTEM: 500
        }

        # 如果是关键错误，返回服务器错误
        if severity == ErrorSeverity.CRITICAL:
            return 500

        return status_map.get(error_category, 500)

    def _get_error_suggestions(self, error_category: ErrorCategory) -> list:
        """获取错误处理建议"""

        suggestions_map = {
            ErrorCategory.NETWORK: [
                "检查网络连接",
                "稍后重试",
                "联系系统管理员"
            ],
            ErrorCategory.DATABASE: [
                "检查数据库连接",
                "验证数据完整性",
                "联系技术支持"
            ],
            ErrorCategory.VALIDATION: [
                "检查输入数据格式",
                "验证必填字段",
                "参考API文档"
            ],
            ErrorCategory.AUTHENTICATION: [
                "重新登录",
                "检查token有效性",
                "联系管理员重置密码"
            ],
            ErrorCategory.FILE_SYSTEM: [
                "检查文件路径",
                "验证文件权限",
                "检查磁盘空间"
            ],
            ErrorCategory.EXTERNAL_API: [
                "检查外部服务状态",
                "稍后重试",
                "联系API提供商"
            ]
        }

        return suggestions_map.get(error_category, ["联系技术支持"])

    def _record_success_request(self, request: Request, response: Response, start_time: float):
        """记录成功请求"""
        processing_time = time.time() - start_time

        # 这里可以记录到监控系统
        logger.info(f"请求成功: {request.method} {request.url.path} - {processing_time:.3f}s")

    def _record_recovery_failure(self, error_context: ErrorContext, recovery_result):
        """记录恢复失败"""
        # 这里可以发送告警或记录到监控系统
        logger.critical(f"错误恢复失败严重事件: {error_context.error_id}")

    def _create_http_error_response(self, http_exc: HTTPException, request_id: str) -> JSONResponse:
        """创建HTTP错误响应"""
        return JSONResponse(
            status_code=http_exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": f"HTTP_{http_exc.status_code}",
                    "message": http_exc.detail,
                    "type": "http_error",
                    "severity": "medium"
                },
                "request_id": request_id
            }
        )

# 错误恢复中间件工厂函数
def create_error_recovery_middleware(app, **options):
    """创建错误恢复中间件"""
    recovery_engine = options.get('recovery_engine')
    return ErrorRecoveryMiddleware(app, recovery_engine)

# API路由错误恢复装饰器
def api_error_recovery(error_category: ErrorCategory, fallback_response: Optional[Dict[str, Any]] = None):
    """API错误恢复装饰器"""

    def decorator(func):
        @with_error_recovery(error_category)
        async def wrapper(*args, **kwargs):
            try:
                result = await func(*args, **kwargs)
                return {
                    "success": True,
                    "data": result
                }
            except Exception as e:
                if fallback_response:
                    logger.warning(f"API函数 {func.__name__} 执行fallback响应")
                    return fallback_response
                raise e

        return wrapper
    return decorator