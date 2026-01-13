"""
统一错误处理器
功能: 捕获、日志记录、格式化所有异常
时间: 2025-11-03
"""

import logging
import traceback
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .error_codes import APIResponse, BusinessError, ErrorCode

logger = logging.getLogger(__name__)


def get_http_status_code(error_code: ErrorCode) -> int:
    """根据错误码获取HTTP状态码"""
    code = error_code.code

    if 3000 <= code < 4000:
        return status.HTTP_422_UNPROCESSABLE_ENTITY
    elif 4000 <= code < 5000:
        return status.HTTP_404_NOT_FOUND
    elif code in (ErrorCode.UNAUTHORIZED.code, ErrorCode.TOKEN_EXPIRED.code):
        return status.HTTP_401_UNAUTHORIZED
    elif code in (ErrorCode.FORBIDDEN.code, ErrorCode.PERMISSION_DENIED.code):
        return status.HTTP_403_FORBIDDEN
    elif code == ErrorCode.RATE_LIMIT_EXCEEDED.code:
        return status.HTTP_429_TOO_MANY_REQUESTS
    elif code >= 5000:
        return status.HTTP_400_BAD_REQUEST

    return status.HTTP_500_INTERNAL_SERVER_ERROR


def create_error_handlers(app: FastAPI) -> None:
    """为FastAPI应用添加统一的错误处理器"""

    @app.exception_handler(BusinessError)
    async def business_exception_handler(
        request: Request, exc: BusinessError
    ) -> JSONResponse:
        """业务异常处理器"""
        logger.warning(
            f"业务异常 [{exc.error_code.code}]: {exc.message} "
            f"(路径: {request.url.path})"
        )

        response = exc.to_response()
        status_code = get_http_status_code(exc.error_code)

        return JSONResponse(status_code=status_code, content=response.to_dict())

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """FastAPI数据验证异常处理器"""
        errors = {}
        for error in exc.errors():
            field = ".".join(str(x) for x in error["loc"][1:])
            errors[field] = error["msg"]

        logger.warning(f"数据验证失败: {errors}")

        error_info = {
            "code": ErrorCode.VALIDATION_ERROR.code,
            "message": ErrorCode.VALIDATION_ERROR.message,
            "validation_errors": errors,
        }

        response = APIResponse(success=False, error=error_info, message="数据验证失败")

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=response.to_dict()
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """通用异常处理器"""
        logger.error(
            f"未处理的异常 [{type(exc).__name__}]: {str(exc)}\n"
            f"堆栈:\n{traceback.format_exc()}"
        )

        error_info = {
            "code": ErrorCode.INTERNAL_SERVER_ERROR.code,
            "message": ErrorCode.INTERNAL_SERVER_ERROR.message,
            "error_type": type(exc).__name__,
        }

        response = APIResponse(
            success=False, error=error_info, message="服务器内部错误"
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=response.to_dict(),
        )
