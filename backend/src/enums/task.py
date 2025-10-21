"""
任务管理相关枚举定义
统一管理所有任务相关的枚举类型，避免重复定义
"""

from enum import Enum


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @classmethod
    def get_active_statuses(cls):
        """获取活跃状态（未完成）"""
        return [cls.PENDING, cls.RUNNING]

    @classmethod
    def get_finished_statuses(cls):
        """获取完成状态"""
        return [cls.COMPLETED, cls.FAILED, cls.CANCELLED]

    @classmethod
    def get_all_values(cls):
        """获取所有状态值"""
        return [status.value for status in cls]


class TaskType(str, Enum):
    """任务类型枚举"""
    EXCEL_EXPORT = "excel_export"
    EXCEL_IMPORT = "excel_import"
    DATA_VALIDATION = "data_validation"
    BATCH_UPDATE = "batch_update"
    PDF_PROCESSING = "pdf_processing"

    @classmethod
    def get_file_related_types(cls):
        """获取文件处理相关类型"""
        return [cls.EXCEL_EXPORT, cls.EXCEL_IMPORT, cls.PDF_PROCESSING]

    @classmethod
    def get_data_processing_types(cls):
        """获取数据处理相关类型"""
        return [cls.DATA_VALIDATION, cls.BATCH_UPDATE]


class ExcelConfigType(str, Enum):
    """Excel配置类型枚举"""
    IMPORT = "import"
    EXPORT = "export"
    VALIDATION = "validation"
    FIELD_MAPPING = "field_mapping"

    @classmethod
    def get_all_types(cls):
        """获取所有配置类型"""
        return [config_type.value for config_type in cls]


class TaskPriority(str, Enum):
    """任务优先级枚举"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

    @classmethod
    def get_priority_order(cls):
        """获取优先级顺序（从高到低）"""
        return [cls.URGENT, cls.HIGH, cls.NORMAL, cls.LOW]