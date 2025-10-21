"""
系统枚举模块
统一管理所有枚举类型定义
"""

from .task import TaskStatus, TaskType, ExcelConfigType, TaskPriority

__all__ = [
    'TaskStatus',
    'TaskType',
    'ExcelConfigType',
    'TaskPriority'
]