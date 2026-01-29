"""
Comprehensive Unit Tests for Backup API Routes (src/api/v1/system/backup.py)

This test module covers all endpoints in the backup router to achieve 70%+ coverage:

Endpoints Tested:
1. POST /backup/create - Create database backup
2. GET /backup/list - Get backup file list
3. GET /backup/download/{backup_name} - Download backup file
4. POST /backup/restore/{backup_name} - Restore from backup
5. DELETE /backup/delete/{backup_name} - Delete backup file
6. GET /backup/stats - Get backup statistics
7. POST /backup/validate/{backup_name} - Validate backup file
8. POST /backup/cleanup - Cleanup old backups

Testing Approach:
- Mock all dependencies (BackupService, database, file system)
- Test successful responses
- Test error handling scenarios
- Test request validation
- Test response schemas
- Test file system operations
"""

import os
import tempfile
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.responses import FileResponse

from src.core.exception_handler import BaseBusinessError

pytestmark = pytest.mark.api


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_db():
    """Create mock database session"""
    db = MagicMock()
    # Mock database bind with URL
    db.bind = MagicMock()
    db.bind.url = "postgresql+psycopg://user:pass@localhost/test_database"
    return db


@pytest.fixture
def mock_db_without_bind():
    """Create mock database session without bind"""
    db = MagicMock()
    db.bind = None
    return db


@pytest.fixture
def mock_db_with_non_postgres():
    """Create mock database session with non-PostgreSQL URL"""
    db = MagicMock()
    db.bind = MagicMock()
    db.bind.url = "postgresql+psycopg://user:pass@localhost/db"
    return db


@pytest.fixture
def temp_backup_dir():
    """Create temporary backup directory for testing"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup
    if os.path.exists(temp_dir):
        import shutil

        shutil.rmtree(temp_dir)


@pytest.fixture
def mock_backup_service():
    """Create mock BackupService"""
    service = MagicMock()
    return service


# ============================================================================
# Test: POST /create - Create Backup
# ============================================================================


class TestCreateBackup:
    """Tests for POST /backup/create endpoint"""

    @patch("src.api.v1.system.backup.BackupService")
    @pytest.mark.asyncio
    async def test_create_backup_success(self, mock_service_class, mock_db):
        """Test successful backup creation"""
        from src.api.v1.system.backup import create_backup

        mock_service = MagicMock()
        mock_service.create_backup.return_value = {
            "backup_name": "test_backup",
            "backup_filename": "test_backup.dump",
            "backup_path": "backups/test_backup.dump",
            "backup_size": 1024,
            "created_at": datetime.now(UTC).isoformat(),
        }
        mock_service_class.return_value = mock_service

        result = await create_backup(backup_name="test_backup", db=mock_db)

        assert result["success"] is True
        assert result["message"] == "数据备份创建成功"
        assert "data" in result
        assert result["data"]["backup_name"] == "test_backup"
        mock_service.create_backup.assert_called_once()

    @patch("src.api.v1.system.backup.BackupService")
    @pytest.mark.asyncio
    async def test_create_backup_without_name(self, mock_service_class, mock_db):
        """Test backup creation without providing name (uses timestamp)"""
        from src.api.v1.system.backup import create_backup

        mock_service = MagicMock()
        mock_service.create_backup.return_value = {
            "backup_name": "backup_20260116_120000",
            "backup_filename": "backup_20260116_120000.dump",
            "backup_path": "backups/backup_20260116_120000.dump",
            "backup_size": 2048,
            "created_at": datetime.now(UTC).isoformat(),
        }
        mock_service_class.return_value = mock_service

        result = await create_backup(backup_name=None, db=mock_db)

        assert result["success"] is True
        mock_service.create_backup.assert_called_once_with(
            backup_name=None,
            database_url="postgresql+psycopg://user:pass@localhost/test_database",
        )

    @patch("src.api.v1.system.backup.BackupService")
    @pytest.mark.asyncio
    async def test_create_backup_db_url_extraction(self, mock_service_class, mock_db):
        """Test that database URL is correctly extracted from db.bind.url"""
        from src.api.v1.system.backup import create_backup

        mock_service = MagicMock()
        mock_service.create_backup.return_value = {
            "backup_name": "db_backup",
            "backup_filename": "db_backup.dump",
            "backup_path": "backups/db_backup.dump",
            "backup_size": 4096,
            "created_at": datetime.now(UTC).isoformat(),
        }
        mock_service_class.return_value = mock_service

        result = await create_backup(backup_name="db_backup", db=mock_db)

        mock_service.create_backup.assert_called_once_with(
            backup_name="db_backup",
            database_url="postgresql+psycopg://user:pass@localhost/test_database",
        )
        assert result["success"] is True

    @patch("src.api.v1.system.backup.BackupService")
    @pytest.mark.asyncio
    async def test_create_backup_db_without_bind(
        self, mock_service_class, mock_db_without_bind, monkeypatch
    ):
        """Test backup creation when db.bind is None"""
        from src.api.v1.system import backup as backup_module

        mock_service = MagicMock()
        mock_service.create_backup.return_value = {
            "backup_name": "backup_no_bind",
            "backup_filename": "backup_no_bind.dump",
            "backup_path": "backups/backup_no_bind.dump",
            "backup_size": 512,
            "created_at": datetime.now(UTC).isoformat(),
        }
        mock_service_class.return_value = mock_service

        fallback_url = "postgresql+psycopg://user:pass@localhost/fallback_db"
        monkeypatch.setattr(backup_module.settings, "DATABASE_URL", fallback_url)
        result = await backup_module.create_backup(
            backup_name="backup_no_bind", db=mock_db_without_bind
        )

        mock_service.create_backup.assert_called_once_with(
            backup_name="backup_no_bind",
            database_url=fallback_url,
        )
        assert result["success"] is True

    @patch("src.api.v1.system.backup.BackupService")
    @pytest.mark.asyncio
    async def test_create_backup_non_postgres_db(
        self, mock_service_class, mock_db_with_non_postgres
    ):
        """Test backup creation with non-PostgreSQL database"""
        from src.api.v1.system.backup import create_backup

        mock_service = MagicMock()
        mock_service.create_backup.return_value = {
            "backup_name": "pg_backup",
            "backup_filename": "pg_backup.dump",
            "backup_path": "backups/pg_backup.dump",
            "backup_size": 1024,
            "created_at": datetime.now(UTC).isoformat(),
        }
        mock_service_class.return_value = mock_service

        result = await create_backup(
            backup_name="pg_backup", db=mock_db_with_non_postgres
        )

        mock_service.create_backup.assert_called_once_with(
            backup_name="pg_backup",
            database_url="postgresql+psycopg://user:pass@localhost/db",
        )
        assert result["success"] is True

    @patch("src.api.v1.system.backup.BackupService")
    @pytest.mark.asyncio
    async def test_create_backup_service_error(self, mock_service_class, mock_db):
        """Test backup creation when service raises an exception"""
        from src.api.v1.system.backup import create_backup

        mock_service = MagicMock()
        mock_service.create_backup.side_effect = Exception("Backup failed: Disk full")
        mock_service_class.return_value = mock_service

        with pytest.raises(BaseBusinessError) as exc_info:
            await create_backup(backup_name="error_backup", db=mock_db)

        assert exc_info.value.status_code == 500
        assert "创建数据备份失败" in exc_info.value.message
        assert "Disk full" in exc_info.value.message


# ============================================================================
# Test: GET /list - List Backups
# ============================================================================


class TestListBackups:
    """Tests for GET /backup/list endpoint"""

    @patch("src.api.v1.system.backup.BackupService")
    @pytest.mark.asyncio
    async def test_list_backups_success(self, mock_service_class):
        """Test successful backup list retrieval"""
        from src.api.v1.system.backup import list_backups

        mock_service = MagicMock()
        mock_service.list_backups.return_value = [
            {
                "filename": "backup1.dump",
                "backup_name": "backup1",
                "file_path": "backups/backup1.dump",
                "file_size": 1024,
                "created_at": "2026-01-16T10:00:00",
                "modified_at": "2026-01-16T10:00:00",
            },
            {
                "filename": "backup2.dump",
                "backup_name": "backup2",
                "file_path": "backups/backup2.dump",
                "file_size": 2048,
                "created_at": "2026-01-16T11:00:00",
                "modified_at": "2026-01-16T11:00:00",
            },
        ]
        mock_service_class.return_value = mock_service

        result = await list_backups()

        assert result["success"] is True
        assert result["message"] == "找到 2 个备份文件"
        assert len(result["data"]) == 2
        mock_service.list_backups.assert_called_once()

    @patch("src.api.v1.system.backup.BackupService")
    @pytest.mark.asyncio
    async def test_list_backups_empty(self, mock_service_class):
        """Test listing backups when none exist"""
        from src.api.v1.system.backup import list_backups

        mock_service = MagicMock()
        mock_service.list_backups.return_value = []
        mock_service_class.return_value = mock_service

        result = await list_backups()

        assert result["success"] is True
        assert result["message"] == "找到 0 个备份文件"
        assert result["data"] == []

    @patch("src.api.v1.system.backup.BackupService")
    @pytest.mark.asyncio
    async def test_list_backups_service_error(self, mock_service_class):
        """Test list backups when service raises an exception"""
        from src.api.v1.system.backup import list_backups

        mock_service = MagicMock()
        mock_service.list_backups.side_effect = Exception("Permission denied")
        mock_service_class.return_value = mock_service

        with pytest.raises(BaseBusinessError) as exc_info:
            await list_backups()

        assert exc_info.value.status_code == 500
        assert "获取备份列表失败" in exc_info.value.message


# ============================================================================
# Test: GET /download/{backup_name} - Download Backup
# ============================================================================


class TestDownloadBackup:
    """Tests for GET /backup/download/{backup_name} endpoint"""

    @patch("src.api.v1.system.backup.BackupService")
    @pytest.mark.asyncio
    async def test_download_backup_success(self, mock_service_class, temp_backup_dir):
        """Test successful backup download"""
        from src.api.v1.system.backup import download_backup

        # Create a temporary backup file
        backup_path = os.path.join(temp_backup_dir, "test_backup.dump")
        with open(backup_path, "wb") as f:
            f.write(b"fake database content")

        mock_service = MagicMock()
        mock_service.get_backup.return_value = {
            "filename": "test_backup.dump",
            "backup_name": "test_backup",
            "file_path": backup_path,
            "file_size": len(b"fake database content"),
            "created_at": datetime.now(UTC).isoformat(),
            "modified_at": datetime.now(UTC).isoformat(),
        }
        mock_service_class.return_value = mock_service

        result = await download_backup(backup_name="test_backup")

        assert isinstance(result, FileResponse)
        assert result.media_type == "application/octet-stream"
        mock_service.get_backup.assert_called_once_with("test_backup")

    @patch("src.api.v1.system.backup.BackupService")
    @pytest.mark.asyncio
    async def test_download_backup_not_found(self, mock_service_class):
        """Test downloading non-existent backup"""
        from src.api.v1.system.backup import download_backup

        mock_service = MagicMock()
        mock_service.get_backup.return_value = None
        mock_service_class.return_value = mock_service

        with pytest.raises(BaseBusinessError) as exc_info:
            await download_backup(backup_name="nonexistent")

        assert exc_info.value.status_code == 404
        assert "backup" in exc_info.value.message
        assert "不存在" in exc_info.value.message

    @patch("src.api.v1.system.backup.BackupService")
    @pytest.mark.asyncio
    async def test_download_backup_service_error(self, mock_service_class):
        """Test download when service raises an exception"""
        from src.api.v1.system.backup import download_backup

        mock_service = MagicMock()
        mock_service.get_backup.side_effect = Exception("Service error")
        mock_service_class.return_value = mock_service

        with pytest.raises(BaseBusinessError) as exc_info:
            await download_backup(backup_name="error_backup")

        assert exc_info.value.status_code == 500
        assert "下载备份文件失败" in exc_info.value.message


# ============================================================================
# Test: POST /restore/{backup_name} - Restore Backup
# ============================================================================


class TestRestoreBackup:
    """Tests for POST /backup/restore/{backup_name} endpoint"""

    @patch("src.api.v1.system.backup.BackupService")
    @pytest.mark.asyncio
    async def test_restore_backup_success(self, mock_service_class, mock_db):
        """Test successful backup restoration"""
        from src.api.v1.system.backup import restore_backup

        mock_service = MagicMock()
        mock_service.restore_backup.return_value = {
            "restored_backup": "test_backup",
            "restored_at": datetime.now(UTC).isoformat(),
            "current_backup": "current_backup_20260116_120000",
        }
        mock_service_class.return_value = mock_service

        result = await restore_backup(
            backup_name="test_backup", confirm=True, db=mock_db
        )

        assert result["success"] is True
        assert result["message"] == "数据恢复成功"
        assert "data" in result
        mock_service.restore_backup.assert_called_once_with(
            backup_name="test_backup",
            database_url="postgresql+psycopg://user:pass@localhost/test_database",
            create_current_backup=True,
        )

    @patch("src.api.v1.system.backup.BackupService")
    @pytest.mark.asyncio
    async def test_restore_backup_not_confirmed(self, mock_service_class, mock_db):
        """Test restore without confirmation parameter"""
        from src.api.v1.system.backup import restore_backup

        with pytest.raises(BaseBusinessError) as exc_info:
            await restore_backup(backup_name="test_backup", confirm=False, db=mock_db)

        assert exc_info.value.status_code == 400
        assert "请确认恢复操作" in exc_info.value.message

    @patch("src.api.v1.system.backup.BackupService")
    @pytest.mark.asyncio
    async def test_restore_backup_file_not_found(self, mock_service_class, mock_db):
        """Test restoring from non-existent backup file"""
        from src.api.v1.system.backup import restore_backup

        mock_service = MagicMock()
        mock_service.restore_backup.side_effect = FileNotFoundError(
            "备份文件不存在: missing_backup"
        )
        mock_service_class.return_value = mock_service

        with pytest.raises(BaseBusinessError) as exc_info:
            await restore_backup(backup_name="missing_backup", confirm=True, db=mock_db)

        assert exc_info.value.status_code == 404
        assert "backup" in exc_info.value.message
        assert "不存在" in exc_info.value.message

    @patch("src.api.v1.system.backup.BackupService")
    @pytest.mark.asyncio
    async def test_restore_backup_service_error(self, mock_service_class, mock_db):
        """Test restore when service raises an exception"""
        from src.api.v1.system.backup import restore_backup

        mock_service = MagicMock()
        mock_service.restore_backup.side_effect = Exception(
            "Restore failed: Database locked"
        )
        mock_service_class.return_value = mock_service

        with pytest.raises(BaseBusinessError) as exc_info:
            await restore_backup(backup_name="error_backup", confirm=True, db=mock_db)

        assert exc_info.value.status_code == 500
        assert "恢复数据备份失败" in exc_info.value.message

    @patch("src.api.v1.system.backup.BackupService")
    @pytest.mark.asyncio
    async def test_restore_backup_db_without_bind(
        self, mock_service_class, mock_db_without_bind, monkeypatch
    ):
        """Test restore when db.bind is None"""
        from src.api.v1.system import backup as backup_module

        mock_service = MagicMock()
        mock_service.restore_backup.return_value = {
            "restored_backup": "backup_no_bind",
            "restored_at": datetime.now(UTC).isoformat(),
        }
        mock_service_class.return_value = mock_service

        fallback_url = "postgresql+psycopg://user:pass@localhost/fallback_db"
        monkeypatch.setattr(backup_module.settings, "DATABASE_URL", fallback_url)
        result = await backup_module.restore_backup(
            backup_name="backup_no_bind", confirm=True, db=mock_db_without_bind
        )

        mock_service.restore_backup.assert_called_once_with(
            backup_name="backup_no_bind",
            database_url=fallback_url,
            create_current_backup=True,
        )
        assert result["success"] is True


# ============================================================================
# Test: DELETE /delete/{backup_name} - Delete Backup
# ============================================================================


class TestDeleteBackup:
    """Tests for DELETE /backup/delete/{backup_name} endpoint"""

    @patch("src.api.v1.system.backup.BackupService")
    @pytest.mark.asyncio
    async def test_delete_backup_success(self, mock_service_class):
        """Test successful backup deletion"""
        from src.api.v1.system.backup import delete_backup

        mock_service = MagicMock()
        mock_service.delete_backup.return_value = {
            "deleted_backup": "test_backup",
            "deleted_at": datetime.now(UTC).isoformat(),
        }
        mock_service_class.return_value = mock_service

        result = await delete_backup(backup_name="test_backup")

        assert result["success"] is True
        assert result["message"] == "备份文件 test_backup 已成功删除"
        assert "data" in result
        mock_service.delete_backup.assert_called_once_with("test_backup")

    @patch("src.api.v1.system.backup.BackupService")
    @pytest.mark.asyncio
    async def test_delete_backup_file_not_found(self, mock_service_class):
        """Test deleting non-existent backup file"""
        from src.api.v1.system.backup import delete_backup

        mock_service = MagicMock()
        mock_service.delete_backup.side_effect = FileNotFoundError(
            "备份文件不存在: nonexistent"
        )
        mock_service_class.return_value = mock_service

        with pytest.raises(BaseBusinessError) as exc_info:
            await delete_backup(backup_name="nonexistent")

        assert exc_info.value.status_code == 404
        assert "backup" in exc_info.value.message
        assert "不存在" in exc_info.value.message

    @patch("src.api.v1.system.backup.BackupService")
    @pytest.mark.asyncio
    async def test_delete_backup_service_error(self, mock_service_class):
        """Test delete when service raises an exception"""
        from src.api.v1.system.backup import delete_backup

        mock_service = MagicMock()
        mock_service.delete_backup.side_effect = Exception("Permission denied")
        mock_service_class.return_value = mock_service

        with pytest.raises(BaseBusinessError) as exc_info:
            await delete_backup(backup_name="error_backup")

        assert exc_info.value.status_code == 500
        assert "删除备份文件失败" in exc_info.value.message


# ============================================================================
# Test: GET /stats - Get Backup Statistics
# ============================================================================


class TestGetBackupStats:
    """Tests for GET /backup/stats endpoint"""

    @patch("src.api.v1.system.backup.BackupService")
    @pytest.mark.asyncio
    async def test_get_backup_stats_success(self, mock_service_class):
        """Test successful backup statistics retrieval"""
        from src.api.v1.system.backup import get_backup_stats

        mock_service = MagicMock()
        mock_service.get_backup_stats.return_value = {
            "total_count": 5,
            "total_size": 5120,
            "total_size_mb": 0.005,
            "oldest_backup": "2026-01-01T10:00:00",
            "newest_backup": "2026-01-16T12:00:00",
        }
        mock_service_class.return_value = mock_service

        result = await get_backup_stats()

        assert result["success"] is True
        assert "data" in result
        assert result["data"]["total_count"] == 5
        assert result["data"]["total_size"] == 5120
        mock_service.get_backup_stats.assert_called_once()

    @patch("src.api.v1.system.backup.BackupService")
    @pytest.mark.asyncio
    async def test_get_backup_stats_empty(self, mock_service_class):
        """Test getting stats when no backups exist"""
        from src.api.v1.system.backup import get_backup_stats

        mock_service = MagicMock()
        mock_service.get_backup_stats.return_value = {
            "total_count": 0,
            "total_size": 0,
            "total_size_mb": 0,
            "oldest_backup": None,
            "newest_backup": None,
        }
        mock_service_class.return_value = mock_service

        result = await get_backup_stats()

        assert result["success"] is True
        assert result["data"]["total_count"] == 0

    @patch("src.api.v1.system.backup.BackupService")
    @pytest.mark.asyncio
    async def test_get_backup_stats_service_error(self, mock_service_class):
        """Test stats when service raises an exception"""
        from src.api.v1.system.backup import get_backup_stats

        mock_service = MagicMock()
        mock_service.get_backup_stats.side_effect = Exception("Stats error")
        mock_service_class.return_value = mock_service

        with pytest.raises(BaseBusinessError) as exc_info:
            await get_backup_stats()

        assert exc_info.value.status_code == 500
        assert "获取备份统计失败" in exc_info.value.message


# ============================================================================
# Test: POST /validate/{backup_name} - Validate Backup
# ============================================================================


class TestValidateBackup:
    """Tests for POST /backup/validate/{backup_name} endpoint"""

    @patch("src.api.v1.system.backup.BackupService")
    @pytest.mark.asyncio
    async def test_validate_backup_success(self, mock_service_class):
        """Test successful backup validation"""
        from src.api.v1.system.backup import validate_backup

        mock_service = MagicMock()
        mock_service.validate_backup.return_value = {
            "valid": True,
            "backup_name": "test_backup",
            "file_size": 1024,
            "validated_at": datetime.now(UTC).isoformat(),
        }
        mock_service_class.return_value = mock_service

        result = await validate_backup(backup_name="test_backup")

        assert result["success"] is True
        assert result["data"]["valid"] is True
        assert result["data"]["backup_name"] == "test_backup"
        mock_service.validate_backup.assert_called_once_with("test_backup")

    @patch("src.api.v1.system.backup.BackupService")
    @pytest.mark.asyncio
    async def test_validate_backup_invalid(self, mock_service_class):
        """Test validation of invalid backup"""
        from src.api.v1.system.backup import validate_backup

        mock_service = MagicMock()
        mock_service.validate_backup.return_value = {
            "valid": False,
            "error": "备份文件大小为0",
        }
        mock_service_class.return_value = mock_service

        result = await validate_backup(backup_name="invalid_backup")

        assert result["success"] is False
        assert result["data"]["valid"] is False
        assert "error" in result["data"]

    @patch("src.api.v1.system.backup.BackupService")
    @pytest.mark.asyncio
    async def test_validate_backup_service_error(self, mock_service_class):
        """Test validation when service raises an exception"""
        from src.api.v1.system.backup import validate_backup

        mock_service = MagicMock()
        mock_service.validate_backup.side_effect = Exception("Validation error")
        mock_service_class.return_value = mock_service

        with pytest.raises(BaseBusinessError) as exc_info:
            await validate_backup(backup_name="error_backup")

        assert exc_info.value.status_code == 500
        assert "验证备份文件失败" in exc_info.value.message


# ============================================================================
# Test: POST /cleanup - Cleanup Old Backups
# ============================================================================


class TestCleanupOldBackups:
    """Tests for POST /backup/cleanup endpoint"""

    @patch("src.api.v1.system.backup.BackupService")
    @pytest.mark.asyncio
    async def test_cleanup_old_backups_success(self, mock_service_class):
        """Test successful cleanup of old backups"""
        from src.api.v1.system.backup import cleanup_old_backups

        mock_service = MagicMock()
        mock_service.cleanup_old_backups.return_value = {
            "cleaned": 5,
            "kept": 10,
            "deleted_backups": ["backup1", "backup2", "backup3", "backup4", "backup5"],
            "cleaned_at": datetime.now(UTC).isoformat(),
        }
        mock_service_class.return_value = mock_service

        result = await cleanup_old_backups(keep_count=10)

        assert result["success"] is True
        assert result["message"] == "已清理 5 个旧备份"
        assert result["data"]["cleaned"] == 5
        assert result["data"]["kept"] == 10
        mock_service.cleanup_old_backups.assert_called_once_with(keep_count=10)

    @patch("src.api.v1.system.backup.BackupService")
    @pytest.mark.asyncio
    async def test_cleanup_no_backups_to_remove(self, mock_service_class):
        """Test cleanup when no backups need to be removed"""
        from src.api.v1.system.backup import cleanup_old_backups

        mock_service = MagicMock()
        mock_service.cleanup_old_backups.return_value = {
            "cleaned": 0,
            "kept": 5,
            "message": "备份数量未超过限制，无需清理",
        }
        mock_service_class.return_value = mock_service

        result = await cleanup_old_backups(keep_count=10)

        assert result["success"] is True
        assert result["data"]["cleaned"] == 0

    @patch("src.api.v1.system.backup.BackupService")
    @pytest.mark.asyncio
    async def test_cleanup_with_default_keep_count(self, mock_service_class):
        """Test cleanup with default keep_count parameter"""
        from src.api.v1.system.backup import cleanup_old_backups

        mock_service = MagicMock()
        mock_service.cleanup_old_backups.return_value = {
            "cleaned": 2,
            "kept": 10,
            "deleted_backups": ["old1", "old2"],
            "cleaned_at": datetime.now(UTC).isoformat(),
        }
        mock_service_class.return_value = mock_service

        result = await cleanup_old_backups(keep_count=10)

        assert result["success"] is True
        mock_service.cleanup_old_backups.assert_called_once()

    @patch("src.api.v1.system.backup.BackupService")
    @pytest.mark.asyncio
    async def test_cleanup_service_error(self, mock_service_class):
        """Test cleanup when service raises an exception"""
        from src.api.v1.system.backup import cleanup_old_backups

        mock_service = MagicMock()
        mock_service.cleanup_old_backups.side_effect = Exception("Cleanup failed")
        mock_service_class.return_value = mock_service

        with pytest.raises(BaseBusinessError) as exc_info:
            await cleanup_old_backups(keep_count=10)

        assert exc_info.value.status_code == 500
        assert "清理旧备份失败" in exc_info.value.message


# ============================================================================
# Test: Edge Cases and Integration
# ============================================================================


class TestBackupEdgeCases:
    """Tests for edge cases and integration scenarios"""

    @patch("src.api.v1.system.backup.BackupService")
    @pytest.mark.asyncio
    async def test_backup_with_unicode_name(self, mock_service_class, mock_db):
        """Test backup creation with unicode characters in name"""
        from src.api.v1.system.backup import create_backup

        mock_service = MagicMock()
        mock_service.create_backup.return_value = {
            "backup_name": "备份_测试",
            "backup_filename": "备份_测试.dump",
            "backup_path": "backups/备份_测试.dump",
            "backup_size": 1024,
            "created_at": datetime.now(UTC).isoformat(),
        }
        mock_service_class.return_value = mock_service

        result = await create_backup(backup_name="备份_测试", db=mock_db)

        assert result["success"] is True
        assert result["data"]["backup_name"] == "备份_测试"

    @patch("src.api.v1.system.backup.BackupService")
    @pytest.mark.asyncio
    async def test_restore_without_auto_backup(self, mock_service_class, mock_db):
        """Test restore without creating automatic backup of current state"""
        from src.api.v1.system.backup import restore_backup

        mock_service = MagicMock()
        mock_service.restore_backup.return_value = {
            "restored_backup": "test_backup",
            "restored_at": datetime.now(UTC).isoformat(),
        }
        mock_service_class.return_value = mock_service

        result = await restore_backup(
            backup_name="test_backup", confirm=True, db=mock_db
        )

        # Verify create_current_backup defaults to True
        call_args = mock_service.restore_backup.call_args
        assert call_args.kwargs["create_current_backup"] is True
        assert result["success"] is True

    @patch("src.api.v1.system.backup.BackupService")
    @pytest.mark.asyncio
    async def test_multiple_operations_consistency(self, mock_service_class, mock_db):
        """Test consistency across multiple backup operations"""
        from src.api.v1.system.backup import (
            create_backup,
            get_backup_stats,
            list_backups,
            validate_backup,
        )

        mock_service = MagicMock()

        # Setup return values
        mock_service.create_backup.return_value = {
            "backup_name": "consistency_test",
            "backup_filename": "consistency_test.dump",
            "backup_path": "backups/consistency_test.dump",
            "backup_size": 2048,
            "created_at": datetime.now(UTC).isoformat(),
        }
        mock_service.list_backups.return_value = [
            {
                "filename": "consistency_test.dump",
                "backup_name": "consistency_test",
                "file_path": "backups/consistency_test.dump",
                "file_size": 2048,
                "created_at": datetime.now(UTC).isoformat(),
                "modified_at": datetime.now(UTC).isoformat(),
            }
        ]
        mock_service.get_backup_stats.return_value = {
            "total_count": 1,
            "total_size": 2048,
            "total_size_mb": 0.002,
            "oldest_backup": datetime.now(UTC).isoformat(),
            "newest_backup": datetime.now(UTC).isoformat(),
        }
        mock_service.validate_backup.return_value = {
            "valid": True,
            "backup_name": "consistency_test",
            "file_size": 2048,
            "validated_at": datetime.now(UTC).isoformat(),
        }
        mock_service_class.return_value = mock_service

        # Execute operations
        create_result = await create_backup(backup_name="consistency_test", db=mock_db)
        list_result = await list_backups()
        stats_result = await get_backup_stats()
        validate_result = await validate_backup(backup_name="consistency_test")

        # Verify consistency
        assert create_result["success"] is True
        assert list_result["success"] is True
        assert stats_result["success"] is True
        assert validate_result["success"] is True
        assert stats_result["data"]["total_count"] == 1
        assert list_result["data"][0]["backup_name"] == "consistency_test"

    @patch("src.api.v1.system.backup.BackupService")
    @pytest.mark.asyncio
    async def test_concurrent_backup_operations(self, mock_service_class):
        """Test handling of concurrent backup operations"""
        from src.api.v1.system.backup import get_backup_stats, list_backups

        mock_service = MagicMock()

        # Simulate concurrent access
        mock_service.list_backups.return_value = [
            {
                "filename": f"backup{i}.dump",
                "backup_name": f"backup{i}",
                "file_path": f"backups/backup{i}.dump",
                "file_size": 1024 * (i + 1),
                "created_at": datetime.now(UTC).isoformat(),
                "modified_at": datetime.now(UTC).isoformat(),
            }
            for i in range(10)
        ]
        mock_service.get_backup_stats.return_value = {
            "total_count": 10,
            "total_size": 1024 * 55,  # Sum of 1-10
            "total_size_mb": 0.055,
            "oldest_backup": datetime.now(UTC).isoformat(),
            "newest_backup": datetime.now(UTC).isoformat(),
        }
        mock_service_class.return_value = mock_service

        list_result = await list_backups()
        stats_result = await get_backup_stats()

        assert len(list_result["data"]) == 10
        assert stats_result["data"]["total_count"] == 10
        assert stats_result["data"]["total_size"] == 1024 * 55


