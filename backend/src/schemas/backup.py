"""
备份和恢复相关的数据模型
"""


from pydantic import BaseModel, Field


class BackupRequest(BaseModel):
    """备份请求模型"""

    description: str | None = Field(None, description="备份描述")
    async_backup: bool = Field(False, description="是否异步备份")


class BackupInfo(BaseModel):
    """备份信息模型"""

    filename: str = Field(..., description="备份文件名")
    file_path: str = Field(..., description="备份文件路径")
    file_size: int = Field(..., description="文件大小（字节）")
    timestamp: str = Field(..., description="备份时间戳")
    created_at: str = Field(..., description="创建时间")
    description: str = Field(..., description="备份描述")
    is_compressed: bool = Field(..., description="是否压缩")
    backup_type: str = Field(..., description="备份类型")
    original_size: int | None = Field(None, description="原始大小（压缩文件）")


class BackupResponse(BaseModel):
    """备份响应模型"""

    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="响应消息")
    backup_info: BackupInfo | None = Field(None, description="备份信息")
    async_backup: bool = Field(False, description="是否异步备份")


class BackupListResponse(BaseModel):
    """备份列表响应模型"""

    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="响应消息")
    backups: list[BackupInfo] = Field(..., description="备份文件列表")
    total_count: int = Field(..., description="备份文件总数")


class BackupInfoResponse(BaseModel):
    """备份信息响应模型"""

    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="响应消息")
    info: BackupInfo | None = Field(None, description="备份详细信息")


class RestoreRequest(BaseModel):
    """恢复请求模型"""

    backup_filename: str = Field(..., description="要恢复的备份文件名")
    confirm: bool = Field(False, description="确认恢复操作")


class RestoreResponse(BaseModel):
    """恢复响应模型"""

    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="响应消息")
    restored: bool = Field(..., description="是否已恢复")
    safety_backup: str | None = Field(None, description="安全备份文件路径")


class BackupConfig(BaseModel):
    """备份配置模型"""

    backup_dir: str = Field(..., description="备份目录")
    max_backups: int = Field(..., description="最大备份数量")
    compress: bool = Field(..., description="是否压缩")
    auto_backup_enabled: bool = Field(..., description="是否启用自动备份")
    backup_interval_hours: int = Field(..., description="自动备份间隔（小时）")
    backup_retention_days: int = Field(..., description="备份保留天数")


class SchedulerStatus(BaseModel):
    """调度器状态模型"""

    is_running: bool = Field(..., description="是否运行中")
    last_backup_time: str | None = Field(None, description="上次备份时间")
    auto_backup_enabled: bool = Field(..., description="是否启用自动备份")
    backup_interval_hours: int = Field(..., description="备份间隔（小时）")
    backup_retention_days: int = Field(..., description="备份保留天数")
    max_backups: int = Field(..., description="最大备份数量")


class SchedulerStatusResponse(BaseModel):
    """调度器状态响应模型"""

    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="响应消息")
    status: SchedulerStatus = Field(..., description="调度器状态")
