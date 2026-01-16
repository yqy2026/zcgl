"""
异常处理辅助函数
简化 Service 层异常转换模式
"""

import logging
from sqlalchemy.exc import IntegrityError
from src.core.exception_handler import (
    BusinessValidationError,
    DuplicateResourceError,
    ResourceNotFoundError,
)

logger = logging.getLogger(__name__)


def handle_service_exception(
    e: Exception,
    service_name: str,
    operation: str,
) -> None:
    """
    Service层统一异常处理

    将技术异常转换为业务异常，或重新抛出让全局处理器处理

    Args:
        e: 捕获的异常
        service_name: 服务名称（用于日志）
        operation: 操作名称（用于日志）

    Raises:
        DuplicateResourceError: 数据库唯一约束冲突
        BusinessValidationError: 数据验证或完整性错误
        Exception: 其他异常重新抛出，让全局处理器处理
    """
    logger.error(
        f"{service_name} - {operation} failed",
        exc_info=True,
        extra={"service": service_name, "operation": operation}
    )

    # 数据库唯一约束冲突
    if isinstance(e, IntegrityError):
        if "unique" in str(e).lower():
            raise DuplicateResourceError("资源", "field", "value")
        raise BusinessValidationError("数据完整性错误")

    # 数据验证错误
    if isinstance(e, (ValueError, TypeError)):
        raise BusinessValidationError("数据验证失败")

    # 其他异常重新抛出，让全局处理器处理
    raise
