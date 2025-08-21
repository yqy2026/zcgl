"""测试数据备份和恢复功能
"""

import pytest
import os
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from src.services.backup_service import (
    DatabaseBackupService,
    BackupConfig,
    AutoBackupScheduler,
    BackupError,
    RestoreError
)


class TestBackupConfig:
    """测试备份配置"""
    
    def test_backup_config_initialization(self):
        """测试备份配置初始化"""
        config = BackupConfig()
        
        assert config.backup_dir == Path("backups")
        assert config.max_backups == 30
        assert config.compress is True
        assert config.auto_backup_enabled is True
        assert config.backup_interval_hours == 24
        assert config.backup_retention_days == 30
    
    def test_get_backup_filename(self):
        """测试生成备份文件名"""
        config = BackupConfig()
        timestamp = datetime(2024, 1, 15, 10, 30, 45)
        
        # 测试压缩文件名
        filename = config.get_backup_filename(timestamp)
        assert filename == "backup_20240115_103045.db.gz"
        
        # 测试非压缩文件名
        config.compress = False
        filename = config.get_backup_filename(timestamp)
        assert filename == "backup_20240115_103045.db"
    
    def test_get_backup_path(self):
        """测试获取备份文件路径"""
        config = BackupConfig()
        filename = "backup_20240115_103045.db.gz"
        
        path = config.get_backup_path(filename)
        assert path == config.backup_dir / filename


class TestDatabaseBackupService:
    """测试数据库备份服务"""
    
    @pytest.fixture
    def temp_backup_dir(self):
        """创建临时备份目录"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def backup_config(self, temp_backup_dir):
        """创建测试备份配置"""
        config = BackupConfig()
        config.backup_dir = temp_backup_dir
        config.max_backups = 5
        config.backup_retention_days = 7
        return config
    
    @pytest.fixture
    def backup_service(self, backup_config):
        """创建备份服务实例"""
        return DatabaseBackupService(backup_config)
    
    @pytest.fixture
    def mock_database_file(self, temp_backup_dir):
        """创建模拟数据库文件"""
        import sqlite3
        db_file = temp_backup_dir / "test.db"
        
        # 创建一个真实的SQLite数据库文件
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY)")
        conn.commit()
        conn.close()
        
        return str(db_file)
    
    def test_create_backup_success(self, backup_service, mock_database_file):
        """测试成功创建备份"""
        with patch.object(backup_service, '_get_database_path', return_value=mock_database_file):
            result = backup_service.create_backup("测试备份")
            
            assert result["success"] is True
            assert "备份创建成功" in result["message"]
            assert result["backup_info"] is not None
            assert result["backup_info"]["description"] == "测试备份"
    
    def test_create_backup_database_not_exists(self, backup_service):
        """测试数据库文件不存在时创建备份"""
        with patch.object(backup_service, '_get_database_path', return_value="/nonexistent/db.sqlite"):
            result = backup_service.create_backup("测试备份")
            
            assert result["success"] is False
            assert "数据库文件不存在" in result["message"]
    
    def test_create_compressed_backup(self, backup_service, mock_database_file):
        """测试创建压缩备份"""
        backup_service.config.compress = True
        
        with patch.object(backup_service, '_get_database_path', return_value=mock_database_file):
            result = backup_service.create_backup("压缩备份测试")
            
            assert result["success"] is True
            backup_files = list(backup_service.config.backup_dir.glob("*.gz"))
            assert len(backup_files) == 1
            assert backup_files[0].name.endswith(".db.gz")
    
    def test_create_simple_backup(self, backup_service, mock_database_file):
        """测试创建简单备份"""
        backup_service.config.compress = False
        
        with patch.object(backup_service, '_get_database_path', return_value=mock_database_file):
            result = backup_service.create_backup("简单备份测试")
            
            assert result["success"] is True
            backup_files = list(backup_service.config.backup_dir.glob("backup_*.db"))
            assert len(backup_files) == 1
            assert not backup_files[0].name.endswith(".gz")
    
    def test_list_backups_empty(self, backup_service):
        """测试列出空备份列表"""
        result = backup_service.list_backups()
        
        assert result["success"] is True
        assert result["backups"] == []
        assert result["total_count"] == 0
    
    def test_list_backups_with_files(self, backup_service, mock_database_file):
        """测试列出包含文件的备份列表"""
        # 创建几个备份
        with patch.object(backup_service, '_get_database_path', return_value=mock_database_file):
            backup_service.create_backup("备份1")
            backup_service.create_backup("备份2")
        
        result = backup_service.list_backups()
        
        assert result["success"] is True
        assert len(result["backups"]) == 2
        assert result["total_count"] == 2
        
        # 检查备份按时间倒序排列
        timestamps = [backup["timestamp"] for backup in result["backups"]]
        assert timestamps == sorted(timestamps, reverse=True)
    
    def test_get_backup_info_exists(self, backup_service, mock_database_file):
        """测试获取存在的备份文件信息"""
        # 创建备份
        with patch.object(backup_service, '_get_database_path', return_value=mock_database_file):
            create_result = backup_service.create_backup("测试备份")
            backup_filename = create_result["backup_info"]["filename"]
        
        result = backup_service.get_backup_info(backup_filename)
        
        assert result["success"] is True
        assert result["info"] is not None
        assert result["info"]["filename"] == backup_filename
    
    def test_get_backup_info_not_exists(self, backup_service):
        """测试获取不存在的备份文件信息"""
        result = backup_service.get_backup_info("nonexistent_backup.db")
        
        assert result["success"] is False
        assert "备份文件不存在" in result["message"]
    
    def test_delete_backup_success(self, backup_service, mock_database_file):
        """测试成功删除备份"""
        # 创建备份
        with patch.object(backup_service, '_get_database_path', return_value=mock_database_file):
            create_result = backup_service.create_backup("测试备份")
            backup_filename = create_result["backup_info"]["filename"]
        
        # 删除备份
        result = backup_service.delete_backup(backup_filename)
        
        assert result["success"] is True
        assert result["deleted"] is True
        
        # 验证文件已删除
        backup_path = backup_service.config.get_backup_path(backup_filename)
        assert not backup_path.exists()
    
    def test_delete_backup_not_exists(self, backup_service):
        """测试删除不存在的备份"""
        result = backup_service.delete_backup("nonexistent_backup.db")
        
        assert result["success"] is False
        assert result["deleted"] is False
    
    def test_restore_backup_without_confirm(self, backup_service):
        """测试未确认的恢复操作"""
        result = backup_service.restore_backup("test_backup.db", confirm=False)
        
        assert result["success"] is False
        assert "恢复操作需要确认参数" in result["message"]
    
    def test_restore_backup_file_not_exists(self, backup_service):
        """测试恢复不存在的备份文件"""
        result = backup_service.restore_backup("nonexistent_backup.db", confirm=True)
        
        assert result["success"] is False
        assert "备份文件不存在" in result["message"]
    
    def test_cleanup_old_backups_by_count(self, backup_service, mock_database_file):
        """测试按数量清理旧备份"""
        backup_service.config.max_backups = 3
        
        # 创建5个备份
        with patch.object(backup_service, '_get_database_path', return_value=mock_database_file):
            for i in range(5):
                backup_service.create_backup(f"备份{i}")
        
        result = backup_service.cleanup_old_backups()
        
        assert result["success"] is True
        assert result["deleted_count"] == 2  # 删除超出的2个
        
        # 验证只剩3个备份
        remaining_backups = backup_service.list_backups()
        assert remaining_backups["total_count"] == 3
    
    def test_cleanup_old_backups_by_date(self, backup_service, mock_database_file):
        """测试按日期清理旧备份"""
        backup_service.config.backup_retention_days = 1
        
        # 创建备份
        with patch.object(backup_service, '_get_database_path', return_value=mock_database_file):
            backup_service.create_backup("新备份")
        
        # 创建一个旧的备份文件（模拟过期）
        old_backup_path = backup_service.config.backup_dir / "backup_20240101_120000.db.gz"
        old_backup_path.write_text("old backup")
        
        # 修改文件时间为2天前
        old_time = datetime.now() - timedelta(days=2)
        os.utime(old_backup_path, (old_time.timestamp(), old_time.timestamp()))
        
        result = backup_service.cleanup_old_backups()
        
        assert result["success"] is True
        assert result["deleted_count"] >= 1  # 至少删除了过期的备份
    
    def test_parse_backup_filename_valid(self, backup_service):
        """测试解析有效的备份文件名"""
        filename = "backup_20240115_103045.db.gz"
        result = backup_service._parse_backup_filename(filename)
        
        assert result is not None
        assert result["filename"] == filename
        assert result["backup_type"] == "full"
        assert result["is_compressed"] is True
        assert "2024-01-15T10:30:45" in result["timestamp"]
    
    def test_parse_backup_filename_invalid(self, backup_service):
        """测试解析无效的备份文件名"""
        filename = "invalid_backup_name.db"
        result = backup_service._parse_backup_filename(filename)
        
        assert result is None
    
    def test_validate_restored_database_success(self, backup_service, temp_backup_dir):
        """测试验证恢复的数据库成功"""
        # 创建一个包含必要表的SQLite数据库
        import sqlite3
        
        db_file = temp_backup_dir / "valid_test.db"
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE assets (id INTEGER PRIMARY KEY)")
        cursor.execute("CREATE TABLE asset_history (id INTEGER PRIMARY KEY)")
        conn.commit()
        conn.close()
        
        result = backup_service._validate_restored_database(str(db_file))
        assert result is True
    
    def test_validate_restored_database_missing_tables(self, backup_service, temp_backup_dir):
        """测试验证缺少必要表的数据库"""
        # 创建一个只有部分表的SQLite数据库
        import sqlite3
        
        db_file = temp_backup_dir / "invalid_test.db"
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE assets (id INTEGER PRIMARY KEY)")
        # 缺少 asset_history 表
        conn.commit()
        conn.close()
        
        result = backup_service._validate_restored_database(str(db_file))
        assert result is False


class TestAutoBackupScheduler:
    """测试自动备份调度器"""
    
    @pytest.fixture
    def backup_service(self):
        """创建模拟备份服务"""
        service = MagicMock()
        service.config = MagicMock()
        service.config.auto_backup_enabled = True
        service.config.backup_interval_hours = 1  # 1小时间隔用于测试
        return service
    
    @pytest.fixture
    def scheduler(self, backup_service):
        """创建调度器实例"""
        return AutoBackupScheduler(backup_service)
    
    def test_scheduler_initialization(self, scheduler, backup_service):
        """测试调度器初始化"""
        assert scheduler.backup_service == backup_service
        assert scheduler.config == backup_service.config
        assert scheduler.is_running is False
        assert scheduler.last_backup_time is None
    
    def test_should_create_backup_first_time(self, scheduler):
        """测试首次应该创建备份"""
        assert scheduler._should_create_backup() is True
    
    def test_should_create_backup_after_interval(self, scheduler):
        """测试间隔后应该创建备份"""
        # 设置上次备份时间为2小时前
        scheduler.last_backup_time = datetime.now() - timedelta(hours=2)
        scheduler.config.backup_interval_hours = 1
        
        assert scheduler._should_create_backup() is True
    
    def test_should_not_create_backup_within_interval(self, scheduler):
        """测试间隔内不应该创建备份"""
        # 设置上次备份时间为30分钟前
        scheduler.last_backup_time = datetime.now() - timedelta(minutes=30)
        scheduler.config.backup_interval_hours = 1
        
        assert scheduler._should_create_backup() is False
    
    def test_stop_scheduler(self, scheduler):
        """测试停止调度器"""
        scheduler.is_running = True
        scheduler.stop_scheduler()
        
        assert scheduler.is_running is False


@pytest.mark.asyncio
class TestBackupAPI:
    """测试备份API端点"""
    
    @pytest.fixture
    def mock_backup_service(self):
        """模拟备份服务"""
        service = MagicMock()
        service.create_backup.return_value = {
            "success": True,
            "message": "备份创建成功",
            "backup_info": {
                "filename": "backup_20240115_103045.db.gz",
                "file_path": "/path/to/backup_20240115_103045.db.gz",
                "file_size": 1024,
                "timestamp": "2024-01-15T10:30:45",
                "created_at": "2024-01-15T10:30:45",
                "description": "测试备份",
                "is_compressed": True,
                "backup_type": "full"
            }
        }
        service.list_backups.return_value = {
            "success": True,
            "message": "获取备份列表成功",
            "backups": [],
            "total_count": 0
        }
        return service
    
    async def test_create_backup_sync(self, mock_backup_service):
        """测试同步创建备份"""
        from src.api.v1.backup import create_backup
        from src.schemas.backup import BackupRequest
        
        request = BackupRequest(description="测试备份", async_backup=False)
        
        with patch('src.api.v1.backup.backup_service', mock_backup_service):
            response = create_backup(request, MagicMock(), MagicMock())
            
            assert response.success is True
            assert response.message == "备份创建成功"
            assert response.backup_info is not None
            assert response.async_backup is False
    
    async def test_create_backup_async(self, mock_backup_service):
        """测试异步创建备份"""
        from src.api.v1.backup import create_backup
        from src.schemas.backup import BackupRequest
        
        request = BackupRequest(description="测试备份", async_backup=True)
        background_tasks = MagicMock()
        
        with patch('src.api.v1.backup.backup_service', mock_backup_service):
            response = create_backup(request, background_tasks, MagicMock())
            
            assert response.success is True
            assert "后台执行" in response.message
            assert response.backup_info is None
            assert response.async_backup is True
            
            # 验证后台任务被添加
            background_tasks.add_task.assert_called_once()
    
    async def test_list_backups(self, mock_backup_service):
        """测试列出备份"""
        from src.api.v1.backup import list_backups
        
        with patch('src.api.v1.backup.backup_service', mock_backup_service):
            response = list_backups()
            
            assert response.success is True
            assert response.backups == []
            assert response.total_count == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])