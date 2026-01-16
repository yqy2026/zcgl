"""
系统枚举模块
统一管理所有枚举类型定义
"""

from .status import (
    AssetStatus,
    CommonStatus,
    ContractStatus,
    DocumentStatus,
    TaskExecutionStatus,
    UserStatus,
)  # noqa: F401
from .task import ExcelConfigType, TaskPriority, TaskStatus, TaskType  # noqa: F401

__all__ = [
    "TaskStatus",
    "TaskType",
    "ExcelConfigType",
    "TaskPriority",
    "AssetStatus",
    "UserStatus",
    "TaskExecutionStatus",
    "ContractStatus",
    "DocumentStatus",
    "CommonStatus",
]
