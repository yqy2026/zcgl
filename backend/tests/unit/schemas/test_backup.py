"""
Unit tests for backup schemas
"""

import pytest
from pydantic import ValidationError

from src.schemas.backup import (
    BackupConfig,
    BackupInfo,
    BackupListResponse,
    BackupRequest,
    BackupResponse,
    RestoreRequest,
    RestoreResponse,
    SchedulerStatus,
    SchedulerStatusResponse,
)


class TestBackupSchemas:
    def test_backup_request_defaults(self):
        req = BackupRequest()
        assert req.async_backup is False
        assert req.description is None

    def test_backup_response_defaults(self):
        info = BackupInfo(
            filename="backup.json",
            file_path="/tmp/backup.json",
            file_size=10,
            timestamp="2024-01-01T00:00:00",
            created_at="2024-01-01T00:00:00",
            description="daily",
            is_compressed=False,
            backup_type="manual",
            original_size=None,
        )
        response = BackupResponse(is_success=True, message="ok", backup_info=info)
        assert response.is_async_backup is False
        assert response.backup_info.filename == "backup.json"

    def test_backup_list_response(self):
        info = BackupInfo(
            filename="backup.json",
            file_path="/tmp/backup.json",
            file_size=10,
            timestamp="2024-01-01T00:00:00",
            created_at="2024-01-01T00:00:00",
            description="daily",
            is_compressed=False,
            backup_type="manual",
            original_size=None,
        )
        response = BackupListResponse(is_success=True, message="ok", backups=[info], total_count=1)
        assert response.total_count == 1

    def test_restore_request_defaults(self):
        req = RestoreRequest(backup_filename="backup.json")
        assert req.should_confirm is False

    def test_restore_response(self):
        resp = RestoreResponse(is_success=True, message="ok", is_restored=True, safety_backup=None)
        assert resp.is_restored is True

    def test_backup_config(self):
        config = BackupConfig(
            backup_dir="/tmp",
            max_backups=3,
            should_compress=True,
            is_auto_backup_enabled=True,
            backup_interval_hours=24,
            backup_retention_days=7,
        )
        assert config.should_compress is True

    def test_scheduler_status_response(self):
        status = SchedulerStatus(
            is_running=True,
            last_backup_time=None,
            is_auto_backup_enabled=True,
            backup_interval_hours=12,
            backup_retention_days=30,
            max_backups=10,
        )
        response = SchedulerStatusResponse(is_success=True, message="ok", status=status)
        assert response.status.is_running is True

    def test_backup_info_requires_fields(self):
        with pytest.raises(ValidationError):
            BackupInfo(filename="only")
