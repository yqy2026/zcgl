"""数据备份和恢复服�?
使用SQLite数据库的备份和恢复功�?
"""

import os
import shutil
import sqlite3
import gzip
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import asyncio
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from ..database import get_db, DATABASE_URL
from models.asset import Asset
from crud.asset import CRUDAsset

logger = logging.getLogger(__name__)


class BackupError(Exception):
    """备份操作异常"""
    pass


class RestoreError(Exception):
    """恢复操作异常"""
    pass


class BackupConfig:
    """备份配置"""
    
    def __init__(self):
        self.backup_dir = Path("backups")
        self.max_backups = 30  # 保留最�?0个备�?
        self.compress = True  # 是否压缩备份文件
        self.auto_backup_enabled = True  # 是否启用自动备份
        self.backup_interval_hours = 24  # 自动备份间隔（小时）
        self.backup_retention_days = 30  # 备份保留天数
        
        # 确保备份目录存在
        self.backup_dir.mkdir(exist_ok=True)
    
    def get_backup_filename(self, timestamp: Optional[datetime] = None) -> str:
        """生成备份文件�?""
        if timestamp is None:
            timestamp = datetime.now()
        
        filename = f"backup_{timestamp.strftime('%Y%m%d_%H%M%S')}.db"
        if self.compress:
            filename += ".gz"
        
        return filename
    
    def get_backup_path(self, filename: str) -> Path:
        """获取备份文件完整路径"""
        return self.backup_dir / filename


class DatabaseBackupService:
    """数据库备份服�?""
    
    def __init__(self, config: Optional[BackupConfig] = None):
        self.config = config or BackupConfig()
        self.asset_crud = CRUDAsset(Asset)
        self.executor = ThreadPoolExecutor(max_workers=2)
    
    def create_backup(self, description: Optional[str] = None) -> Dict[str, Any]:
        """创建数据库备�?""
        try:
            timestamp = datetime.now()
            filename = self.config.get_backup_filename(timestamp)
            backup_path = self.config.get_backup_path(filename)
            
            logger.info(f"开始创建数据库备份: {filename}")
            
            # 获取数据库文件路�?
            db_path = self._get_database_path()
            
            if not os.path.exists(db_path):
                raise BackupError(f"数据库文件不存在: {db_path}")
            
            # 创建备份
            if self.config.compress:
                self._create_compressed_backup(db_path, backup_path)
            else:
                self._create_simple_backup(db_path, backup_path)
            
            # 获取备份文件信息
            backup_info = self._get_backup_info(backup_path, timestamp, description)
            
            # 清理旧备�?
            self._cleanup_old_backups()
            
            logger.info(f"数据库备份创建完�? {filename}, 大小: {backup_info['file_size']} 字节")
            
            return {
                "success": True,
                "message": "备份创建成功",
                "backup_info": backup_info
            }
            
        except Exception as e:
            logger.error(f"创建数据库备份失�? {str(e)}")
            return {
                "success": False,
                "message": f"备份创建失败: {str(e)}",
                "backup_info": None
            }
    
    async def create_backup_async(self, description: Optional[str] = None) -> Dict[str, Any]:
        """异步创建数据库备�?""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self.create_backup, description)
    
    def restore_backup(self, backup_filename: str, confirm: bool = False) -> Dict[str, Any]:
        """恢复数据库备�?""
        try:
            if not confirm:
                return {
                    "success": False,
                    "message": "恢复操作需要确认参�?,
                    "restored": False
                }
            
            backup_path = self.config.get_backup_path(backup_filename)
            
            if not backup_path.exists():
                raise RestoreError(f"备份文件不存�? {backup_filename}")
            
            logger.info(f"开始恢复数据库备份: {backup_filename}")
            
            # 获取当前数据库路�?
            db_path = self._get_database_path()
            
            # 创建当前数据库的备份（作为恢复前的安全备份）
            safety_backup = self._create_safety_backup(db_path)
            
            try:
                # 恢复备份
                if backup_filename.endswith('.gz'):
                    self._restore_compressed_backup(backup_path, db_path)
                else:
                    self._restore_simple_backup(backup_path, db_path)
                
                # 验证恢复的数据库
                if not self._validate_restored_database(db_path):
                    raise RestoreError("恢复的数据库验证失败")
                
                logger.info(f"数据库备份恢复完�? {backup_filename}")
                
                return {
                    "success": True,
                    "message": "数据库恢复成�?,
                    "restored": True,
                    "safety_backup": safety_backup
                }
                
            except Exception as e:
                # 恢复失败，回滚到安全备份
                logger.error(f"数据库恢复失败，回滚到安全备�? {str(e)}")
                if safety_backup and os.path.exists(safety_backup):
                    shutil.copy2(safety_backup, db_path)
                raise
                
        except Exception as e:
            logger.error(f"恢复数据库备份失�? {str(e)}")
            return {
                "success": False,
                "message": f"恢复失败: {str(e)}",
                "restored": False
            }
    
    def list_backups(self) -> Dict[str, Any]:
        """列出所有备份文�?""
        try:
            backups = []
            
            if not self.config.backup_dir.exists():
                return {
                    "success": True,
                    "message": "备份目录不存�?,
                    "backups": [],
                    "total_count": 0
                }
            
            # 遍历备份目录
            for backup_file in self.config.backup_dir.glob("backup_*.db*"):
                try:
                    backup_info = self._parse_backup_filename(backup_file.name)
                    if backup_info:
                        backup_info.update({
                            "file_path": str(backup_file),
                            "file_size": backup_file.stat().st_size,
                            "created_at": datetime.fromtimestamp(backup_file.stat().st_ctime).isoformat(),
                            "modified_at": datetime.fromtimestamp(backup_file.stat().st_mtime).isoformat()
                        })
                        backups.append(backup_info)
                except Exception as e:
                    logger.warning(f"解析备份文件信息失败: {backup_file.name}, {str(e)}")
                    continue
            
            # 按创建时间倒序排列
            backups.sort(key=lambda x: x['timestamp'], reverse=True)
            
            return {
                "success": True,
                "message": f"找到 {len(backups)} 个备份文�?,
                "backups": backups,
                "total_count": len(backups)
            }
            
        except Exception as e:
            logger.error(f"列出备份文件失败: {str(e)}")
            return {
                "success": False,
                "message": f"列出备份失败: {str(e)}",
                "backups": [],
                "total_count": 0
            }
    
    def delete_backup(self, backup_filename: str) -> Dict[str, Any]:
        """删除备份文件"""
        try:
            backup_path = self.config.get_backup_path(backup_filename)
            
            if not backup_path.exists():
                return {
                    "success": False,
                    "message": "备份文件不存�?,
                    "deleted": False
                }
            
            # 删除文件
            backup_path.unlink()
            
            logger.info(f"删除备份文件: {backup_filename}")
            
            return {
                "success": True,
                "message": "备份文件删除成功",
                "deleted": True
            }
            
        except Exception as e:
            logger.error(f"删除备份文件失败: {str(e)}")
            return {
                "success": False,
                "message": f"删除失败: {str(e)}",
                "deleted": False
            }
    
    def get_backup_info(self, backup_filename: str) -> Dict[str, Any]:
        """获取备份文件详细信息"""
        try:
            backup_path = self.config.get_backup_path(backup_filename)
            
            if not backup_path.exists():
                return {
                    "success": False,
                    "message": "备份文件不存�?,
                    "info": None
                }
            
            # 解析文件名信�?
            info = self._parse_backup_filename(backup_filename)
            if not info:
                return {
                    "success": False,
                    "message": "无法解析备份文件�?,
                    "info": None
                }
            
            # 获取文件统计信息
            stat = backup_path.stat()
            info.update({
                "file_path": str(backup_path),
                "file_size": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "is_compressed": backup_filename.endswith('.gz')
            })
            
            # 如果是压缩文件，尝试获取原始大小
            if info["is_compressed"]:
                try:
                    with gzip.open(backup_path, 'rb') as f:
                        # 读取文件头来估算原始大小
                        f.seek(-4, 2)
                        info["original_size"] = int.from_bytes(f.read(4), 'little')
                except:
                    info["original_size"] = None
            
            return {
                "success": True,
                "message": "获取备份信息成功",
                "info": info
            }
            
        except Exception as e:
            logger.error(f"获取备份信息失败: {str(e)}")
            return {
                "success": False,
                "message": f"获取信息失败: {str(e)}",
                "info": None
            }
    
    def cleanup_old_backups(self) -> Dict[str, Any]:
        """清理过期的备份文�?""
        try:
            deleted_count = self._cleanup_old_backups()
            
            return {
                "success": True,
                "message": f"清理完成，删除了 {deleted_count} 个过期备�?,
                "deleted_count": deleted_count
            }
            
        except Exception as e:
            logger.error(f"清理备份文件失败: {str(e)}")
            return {
                "success": False,
                "message": f"清理失败: {str(e)}",
                "deleted_count": 0
            }
    
    def _get_database_path(self) -> str:
        """获取数据库文件路�?""
        # 从DATABASE_URL中提取文件路�?
        if DATABASE_URL.startswith('sqlite:///'):
            return DATABASE_URL[10:]  # 移除 'sqlite:///' 前缀
        else:
            raise BackupError(f"不支持的数据库类�? {DATABASE_URL}")
    
    def _create_simple_backup(self, source_path: str, backup_path: Path):
        """创建简单备份（直接复制�?""
        shutil.copy2(source_path, backup_path)
    
    def _create_compressed_backup(self, source_path: str, backup_path: Path):
        """创建压缩备份"""
        with open(source_path, 'rb') as f_in:
            with gzip.open(backup_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
    
    def _restore_simple_backup(self, backup_path: Path, target_path: str):
        """恢复简单备�?""
        shutil.copy2(backup_path, target_path)
    
    def _restore_compressed_backup(self, backup_path: Path, target_path: str):
        """恢复压缩备份"""
        with gzip.open(backup_path, 'rb') as f_in:
            with open(target_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
    
    def _create_safety_backup(self, db_path: str) -> Optional[str]:
        """创建安全备份（恢复前的当前数据库备份�?""
        try:
            safety_path = f"{db_path}.safety_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(db_path, safety_path)
            return safety_path
        except Exception as e:
            logger.warning(f"创建安全备份失败: {str(e)}")
            return None
    
    def _validate_restored_database(self, db_path: str) -> bool:
        """验证恢复的数据库"""
        try:
            # 尝试连接数据库并执行简单查�?
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            conn.close()
            
            # 检查是否有必要的表
            table_names = [table[0] for table in tables]
            required_tables = ['assets', 'asset_history']  # 必要的表
            
            for table in required_tables:
                if table not in table_names:
                    logger.error(f"恢复的数据库缺少必要的表: {table}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"验证恢复的数据库失败: {str(e)}")
            return False
    
    def _get_backup_info(self, backup_path: Path, timestamp: datetime, description: Optional[str]) -> Dict[str, Any]:
        """获取备份文件信息"""
        stat = backup_path.stat()
        
        return {
            "filename": backup_path.name,
            "file_path": str(backup_path),
            "file_size": stat.st_size,
            "timestamp": timestamp.isoformat(),
            "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "description": description or "自动备份",
            "is_compressed": backup_path.name.endswith('.gz'),
            "backup_type": "full"
        }
    
    def _parse_backup_filename(self, filename: str) -> Optional[Dict[str, Any]]:
        """解析备份文件�?""
        try:
            # 移除扩展�?
            name = filename
            if name.endswith('.gz'):
                name = name[:-3]
            if name.endswith('.db'):
                name = name[:-3]
            
            # 解析格式: backup_YYYYMMDD_HHMMSS
            if not name.startswith('backup_'):
                return None
            
            timestamp_str = name[7:]  # 移除 'backup_' 前缀
            timestamp = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
            
            return {
                "filename": filename,
                "timestamp": timestamp.isoformat(),
                "backup_type": "full",
                "is_compressed": filename.endswith('.gz')
            }
            
        except Exception as e:
            logger.warning(f"解析备份文件名失�? {filename}, {str(e)}")
            return None
    
    def _cleanup_old_backups(self) -> int:
        """清理过期的备份文�?""
        try:
            deleted_count = 0
            cutoff_date = datetime.now() - timedelta(days=self.config.backup_retention_days)
            
            # 获取所有备份文�?
            backup_files = list(self.config.backup_dir.glob("backup_*.db*"))
            
            # 按修改时间排序，保留最新的文件
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # 删除超过保留数量的文�?
            if len(backup_files) > self.config.max_backups:
                for backup_file in backup_files[self.config.max_backups:]:
                    try:
                        backup_file.unlink()
                        deleted_count += 1
                        logger.info(f"删除超量备份文件: {backup_file.name}")
                    except Exception as e:
                        logger.warning(f"删除备份文件失败: {backup_file.name}, {str(e)}")
            
            # 删除过期的文�?
            for backup_file in backup_files:
                try:
                    file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                    if file_time < cutoff_date:
                        backup_file.unlink()
                        deleted_count += 1
                        logger.info(f"删除过期备份文件: {backup_file.name}")
                except Exception as e:
                    logger.warning(f"删除过期备份文件失败: {backup_file.name}, {str(e)}")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"清理备份文件失败: {str(e)}")
            return 0


class AutoBackupScheduler:
    """自动备份调度�?""
    
    def __init__(self, backup_service: DatabaseBackupService):
        self.backup_service = backup_service
        self.config = backup_service.config
        self.is_running = False
        self.last_backup_time = None
    
    async def start_scheduler(self):
        """启动自动备份调度�?""
        if not self.config.auto_backup_enabled:
            logger.info("自动备份已禁�?)
            return
        
        self.is_running = True
        logger.info(f"启动自动备份调度器，间隔: {self.config.backup_interval_hours} 小时")
        
        while self.is_running:
            try:
                # 检查是否需要备�?
                if self._should_create_backup():
                    logger.info("开始执行自动备�?)
                    result = await self.backup_service.create_backup_async("自动备份")
                    
                    if result["success"]:
                        self.last_backup_time = datetime.now()
                        logger.info("自动备份完成")
                    else:
                        logger.error(f"自动备份失败: {result['message']}")
                
                # 等待一小时后再次检�?
                await asyncio.sleep(3600)  # 1小时
                
            except Exception as e:
                logger.error(f"自动备份调度器异�? {str(e)}")
                await asyncio.sleep(3600)  # 出错后等�?小时再重�?
    
    def stop_scheduler(self):
        """停止自动备份调度�?""
        self.is_running = False
        logger.info("自动备份调度器已停止")
    
    def _should_create_backup(self) -> bool:
        """检查是否应该创建备�?""
        if self.last_backup_time is None:
            return True
        
        time_since_last_backup = datetime.now() - self.last_backup_time
        return time_since_last_backup.total_seconds() >= (self.config.backup_interval_hours * 3600)


# 全局备份服务实例
backup_service = DatabaseBackupService()
auto_backup_scheduler = AutoBackupScheduler(backup_service)
