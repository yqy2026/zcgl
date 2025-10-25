"""å¤ä»½åæ¢å¤ç¸å³çæ°æ®æ¨¡å
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class BackupRequest(BaseModel):
    """å¤ä»½è¯·æ±æ¨¡å"""
    description: Optional[str] = Field(None, description="å¤ä»½æè¿°")
    async_backup: bool = Field(False, description="æ¯å¦å¼æ­¥å¤ä»½")


class BackupInfo(BaseModel):
    """å¤ä»½ä¿¡æ¯æ¨¡å"""
    filename: str = Field(..., description="å¤ä»½æä»¶å?)
    file_path: str = Field(..., description="å¤ä»½æä»¶è·¯å¾")
    file_size: int = Field(..., description="æä»¶å¤§å°ï¼å­èï¼")
    timestamp: str = Field(..., description="å¤ä»½æ¶é´æ?)
    created_at: str = Field(..., description="åå»ºæ¶é´")
    description: str = Field(..., description="å¤ä»½æè¿°")
    is_compressed: bool = Field(..., description="æ¯å¦åç¼©")
    backup_type: str = Field(..., description="å¤ä»½ç±»å")
    original_size: Optional[int] = Field(None, description="åå§å¤§å°ï¼åç¼©æä»¶ï¼")


class BackupResponse(BaseModel):
    """å¤ä»½ååºæ¨¡å"""
    success: bool = Field(..., description="æä½æ¯å¦æå")
    message: str = Field(..., description="ååºæ¶æ¯")
    backup_info: Optional[BackupInfo] = Field(None, description="å¤ä»½ä¿¡æ¯")
    async_backup: bool = Field(False, description="æ¯å¦å¼æ­¥å¤ä»½")


class BackupListResponse(BaseModel):
    """å¤ä»½åè¡¨ååºæ¨¡å"""
    success: bool = Field(..., description="æä½æ¯å¦æå")
    message: str = Field(..., description="ååºæ¶æ¯")
    backups: List[BackupInfo] = Field(..., description="å¤ä»½æä»¶åè¡¨")
    total_count: int = Field(..., description="å¤ä»½æä»¶æ»æ°")


class BackupInfoResponse(BaseModel):
    """å¤ä»½ä¿¡æ¯ååºæ¨¡å"""
    success: bool = Field(..., description="æä½æ¯å¦æå")
    message: str = Field(..., description="ååºæ¶æ¯")
    info: Optional[BackupInfo] = Field(None, description="å¤ä»½è¯¦ç»ä¿¡æ¯")


class RestoreRequest(BaseModel):
    """æ¢å¤è¯·æ±æ¨¡å"""
    backup_filename: str = Field(..., description="è¦æ¢å¤çå¤ä»½æä»¶å?)
    confirm: bool = Field(False, description="ç¡®è®¤æ¢å¤æä½")


class RestoreResponse(BaseModel):
    """æ¢å¤ååºæ¨¡å"""
    success: bool = Field(..., description="æä½æ¯å¦æå")
    message: str = Field(..., description="ååºæ¶æ¯")
    restored: bool = Field(..., description="æ¯å¦å·²æ¢å¤?)
    safety_backup: Optional[str] = Field(None, description="å®å¨å¤ä»½æä»¶è·¯å¾")


class BackupConfig(BaseModel):
    """å¤ä»½éç½®æ¨¡å"""
    backup_dir: str = Field(..., description="å¤ä»½ç®å½")
    max_backups: int = Field(..., description="æå¤§å¤ä»½æ°é?)
    compress: bool = Field(..., description="æ¯å¦åç¼©")
    auto_backup_enabled: bool = Field(..., description="æ¯å¦å¯ç¨èªå¨å¤ä»½")
    backup_interval_hours: int = Field(..., description="èªå¨å¤ä»½é´éï¼å°æ¶ï¼")
    backup_retention_days: int = Field(..., description="å¤ä»½ä¿çå¤©æ°")


class SchedulerStatus(BaseModel):
    """è°åº¦å¨ç¶ææ¨¡å?""
    is_running: bool = Field(..., description="æ¯å¦è¿è¡ä¸?)
    last_backup_time: Optional[str] = Field(None, description="ä¸æ¬¡å¤ä»½æ¶é´")
    auto_backup_enabled: bool = Field(..., description="æ¯å¦å¯ç¨èªå¨å¤ä»½")
    backup_interval_hours: int = Field(..., description="å¤ä»½é´éï¼å°æ¶ï¼")
    backup_retention_days: int = Field(..., description="å¤ä»½ä¿çå¤©æ°")
    max_backups: int = Field(..., description="æå¤§å¤ä»½æ°é?)


class SchedulerStatusResponse(BaseModel):
    """è°åº¦å¨ç¶æååºæ¨¡å?""
    success: bool = Field(..., description="æä½æ¯å¦æå")
    message: str = Field(..., description="ååºæ¶æ¯")
    status: SchedulerStatus = Field(..., description="è°åº¦å¨ç¶æ?)
