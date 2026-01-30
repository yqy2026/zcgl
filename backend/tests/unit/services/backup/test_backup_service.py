"""
备份服务单元测试

测试 BackupService 的所有主要方法
"""

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from src.services.backup.backup_service import BackupService


class TestBackupServiceInit:
    """测试 BackupService 初始化"""

    def test_init_with_default_dir(self):
        """测试使用默认备份目录初始化"""
        with patch.object(BackupService, '_ensure_backup_dir'):
            service = BackupService()
            assert service.backup_dir == "backups"

    def test_init_with_custom_dir(self):
        """测试使用自定义备份目录初始化"""
        with patch.object(BackupService, '_ensure_backup_dir'):
            service = BackupService(backup_dir="/custom/backup/path")
            assert service.backup_dir == "/custom/backup/path"

    def test_ensure_backup_dir_creates_directory(self):
        """测试确保备份目录存在"""
        with tempfile.TemporaryDirectory() as tmpdir:
            backup_dir = os.path.join(tmpdir, "test_backups")
            BackupService(backup_dir=backup_dir)
            assert os.path.exists(backup_dir)


class TestCreateBackup:
    """测试 create_backup 方法"""

    @pytest.fixture
    def service(self):
        """创建测试服务实例"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield BackupService(backup_dir=tmpdir)

    def test_create_backup_requires_database_url(self, service):
        """测试创建备份需要数据库URL"""
        with pytest.raises(ValueError, match="需要提供"):
            service.create_backup()

    def test_create_backup_requires_postgresql(self, service):
        """测试仅支持 PostgreSQL 备份"""
        with pytest.raises(ValueError, match="仅支持 PostgreSQL"):
            service.create_backup(database_url="mysql://localhost/test")

    @patch('subprocess.run')
    def test_create_backup_success(self, mock_run, service):
        """测试成功创建备份"""
        mock_run.return_value = MagicMock(returncode=0)

        backup_name = "test_backup"

        with patch('os.path.getsize', return_value=1024):
            result = service.create_backup(
                backup_name=backup_name,
                database_url="postgresql://localhost/testdb"
            )

        assert result["backup_name"] == backup_name
        assert "created_at" in result
        mock_run.assert_called_once()


class TestListBackups:
    """测试 list_backups 方法"""

    def test_list_backups_empty_dir(self):
        """测试空目录返回空列表"""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = BackupService(backup_dir=tmpdir)
            result = service.list_backups()
            assert result == []

    def test_list_backups_with_files(self):
        """测试列出备份文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = BackupService(backup_dir=tmpdir)

            for i in range(3):
                backup_file = os.path.join(tmpdir, f"backup_{i}.dump")
                with open(backup_file, 'w') as f:
                    f.write(f"test content {i}")

            result = service.list_backups()

            assert len(result) == 3
            assert all("filename" in b for b in result)


class TestGetBackup:
    """测试 get_backup 方法"""

    def test_get_backup_exists(self):
        """测试获取存在的备份"""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = BackupService(backup_dir=tmpdir)

            backup_file = os.path.join(tmpdir, "test_backup.dump")
            with open(backup_file, 'w') as f:
                f.write("test content")

            result = service.get_backup("test_backup")

            assert result is not None
            assert result["backup_name"] == "test_backup"

    def test_get_backup_not_exists(self):
        """测试获取不存在的备份"""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = BackupService(backup_dir=tmpdir)
            result = service.get_backup("nonexistent")
            assert result is None


class TestDeleteBackup:
    """测试 delete_backup 方法"""

    def test_delete_backup_success(self):
        """测试成功删除备份"""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = BackupService(backup_dir=tmpdir)

            backup_file = os.path.join(tmpdir, "test_backup.dump")
            with open(backup_file, 'w') as f:
                f.write("test content")

            result = service.delete_backup("test_backup")

            assert result["deleted_backup"] == "test_backup"
            assert not os.path.exists(backup_file)

    def test_delete_backup_not_exists(self):
        """测试删除不存在的备份"""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = BackupService(backup_dir=tmpdir)

            with pytest.raises(FileNotFoundError):
                service.delete_backup("nonexistent")


class TestValidateBackup:
    """测试 validate_backup 方法"""

    def test_validate_backup_valid(self):
        """测试验证有效备份"""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = BackupService(backup_dir=tmpdir)

            backup_file = os.path.join(tmpdir, "test_backup.dump")
            with open(backup_file, 'w') as f:
                f.write("valid content")

            result = service.validate_backup("test_backup")

            assert result["valid"] is True

    def test_validate_backup_empty_file(self):
        """测试验证空文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = BackupService(backup_dir=tmpdir)

            backup_file = os.path.join(tmpdir, "empty_backup.dump")
            with open(backup_file, "w"):
                pass

            result = service.validate_backup("empty_backup")

            assert result["valid"] is False


class TestCleanupOldBackups:
    """测试 cleanup_old_backups 方法"""

    def test_cleanup_no_action_needed(self):
        """测试备份数量未超限时不清理"""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = BackupService(backup_dir=tmpdir)

            for i in range(3):
                backup_file = os.path.join(tmpdir, f"backup_{i}.dump")
                with open(backup_file, 'w') as f:
                    f.write(f"content {i}")

            result = service.cleanup_old_backups(keep_count=10)

            assert result["cleaned"] == 0


class TestGetBackupStats:
    """测试 get_backup_stats 方法"""

    def test_get_stats_empty(self):
        """测试空备份目录的统计"""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = BackupService(backup_dir=tmpdir)
            result = service.get_backup_stats()

            assert result["total_count"] == 0

    def test_get_stats_with_backups(self):
        """测试有备份时的统计"""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = BackupService(backup_dir=tmpdir)

            for i in range(3):
                backup_file = os.path.join(tmpdir, f"backup_{i}.dump")
                with open(backup_file, 'w') as f:
                    f.write("x" * 1000)

            result = service.get_backup_stats()

            assert result["total_count"] == 3


class TestNormalizePostgresUrl:
    """测试 _normalize_postgres_url 静态方法"""

    def test_normalize_standard_url(self):
        """测试标准 PostgreSQL URL"""
        url = "postgresql://localhost/testdb"
        result = BackupService._normalize_postgres_url(url)
        assert result == url

    def test_normalize_psycopg_url(self):
        """测试 psycopg 驱动 URL"""
        url = "postgresql+psycopg://localhost/testdb"
        result = BackupService._normalize_postgres_url(url)
        assert result == "postgresql://localhost/testdb"
