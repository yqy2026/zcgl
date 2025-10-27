"""
任务管理相关数据库模型
用于跟踪Excel导入导出等异步任务的状态
"""

from sqlalchemy import Column, String, DateTime, Integer, Text, JSON, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid

from ..database import Base
from ..enums.task import TaskStatus, TaskType


class AsyncTask(Base):
    """异步任务模型"""
    __tablename__ = "async_tasks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # 基本信息
    task_type = Column(String(50), nullable=False, comment="任务类型")
    status = Column(String(20), nullable=False, default=TaskStatus.PENDING, comment="任务状态")
    title = Column(String(200), nullable=False, comment="任务标题")
    description = Column(Text, comment="任务描述")

    # 时间信息
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment="创建时间")
    started_at = Column(DateTime, comment="开始时间")
    completed_at = Column(DateTime, comment="完成时间")

    # 进度信息
    progress = Column(Integer, default=0, comment="进度百分比 (0-100)")
    total_items = Column(Integer, comment="总项目数")
    processed_items = Column(Integer, default=0, comment="已处理项目数")
    failed_items = Column(Integer, default=0, comment="失败项目数")

    # 结果信息
    result_data = Column(JSON, comment="结果数据")
    error_message = Column(Text, comment="错误信息")

    # 用户和会话信息
    user_id = Column(String(100), comment="创建用户ID")
    session_id = Column(String(100), comment="会话ID")

    # 配置和参数
    parameters = Column(JSON, comment="任务参数")
    config = Column(JSON, comment="任务配置")

    # 系统字段
    is_active = Column(Boolean, default=True, comment="是否活跃")
    retry_count = Column(Integer, default=0, comment="重试次数")
    max_retries = Column(Integer, default=3, comment="最大重试次数")

    def __repr__(self):
        return f"<AsyncTask(id={self.id}, type={self.task_type}, status={self.status})>"

    @property
    def is_completed(self) -> bool:
        """任务是否已完成"""
        return self.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]

    @property
    def is_running(self) -> bool:
        """任务是否正在运行"""
        return self.status == TaskStatus.RUNNING

    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_items == 0:
            return 0.0
        return (self.processed_items - self.failed_items) / self.total_items * 100

    @property
    def duration_seconds(self) -> float:
        """任务持续时间（秒）"""
        if not self.started_at:
            return 0.0

        end_time = self.completed_at or datetime.now(timezone.utc)
        return (end_time - self.started_at).total_seconds()


class TaskHistory(Base):
    """任务历史记录模型"""
    __tablename__ = "task_history"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String, nullable=False, comment="关联任务ID")

    # 历史记录信息
    action = Column(String(100), nullable=False, comment="操作类型")
    message = Column(Text, comment="消息内容")
    details = Column(JSON, comment="详细信息")

    # 时间信息
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment="创建时间")

    # 用户信息
    user_id = Column(String(100), comment="用户ID")

    def __repr__(self):
        return f"<TaskHistory(id={self.id}, task_id={self.task_id}, action={self.action})>"


class ExcelTaskConfig(Base):
    """Excel任务配置模型"""
    __tablename__ = "excel_task_configs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # 配置信息
    config_name = Column(String(200), nullable=False, comment="配置名称")
    config_type = Column(String(50), nullable=False, comment="配置类型")
    task_type = Column(String(50), nullable=False, comment="任务类型")

    # 映射配置
    field_mapping = Column(JSON, comment="字段映射配置")
    validation_rules = Column(JSON, comment="验证规则配置")
    format_config = Column(JSON, comment="格式配置")

    # 默认设置
    is_default = Column(Boolean, default=False, comment="是否默认配置")
    is_active = Column(Boolean, default=True, comment="是否启用")

    # 用户和创建信息
    created_by = Column(String(100), comment="创建者")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    def __repr__(self):
        return f"<ExcelTaskConfig(id={self.id}, name={self.config_name}, type={self.config_type})>"