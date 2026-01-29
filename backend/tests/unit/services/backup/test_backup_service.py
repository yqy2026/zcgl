"""
Unit tests for BackupService (PostgreSQL-only).
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.services.backup.backup_service import BackupService


@pytest.fixture
def temp_backup_dir(tmp_path: Path) -> Path:
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    return backup_dir


@pytest.fixture
def backup_service(temp_backup_dir: Path) -> BackupService:
    return BackupService(backup_dir=str(temp_backup_dir))


@pytest.fixture
def postgres_url() -> str:
    return "postgresql+psycopg://user:pass@localhost/test_db"


class TestBackupServiceInit:
    def test_init_with_default_backup_dir(self):
        with patch("src.services.backup.backup_service.os.path.exists") as mock_exists:
            with patch("src.services.backup.backup_service.os.makedirs") as mock_makedirs:
                mock_exists.return_value = False
                service = BackupService()
                assert service.backup_dir == "backups"
                mock_makedirs.assert_called_once_with("backups")

    def test_init_with_custom_backup_dir(self, backup_service, temp_backup_dir):
        assert backup_service.backup_dir == str(temp_backup_dir)

    def test_init_creates_backup_dir_if_not_exists(self, tmp_path: Path):
        new_dir = tmp_path / "new_backups"
        service = BackupService(backup_dir=str(new_dir))
        assert new_dir.exists()
        assert service.backup_dir == str(new_dir)


class TestCreateBackup:
    def test_create_backup_requires_database_url(self, backup_service):
        with pytest.raises(ValueError):
            backup_service.create_backup()
        with pytest.raises(ValueError):
            backup_service.create_backup(database_url="mysql://user:pass@localhost/test")

    def test_create_backup_calls_pg_dump(self, backup_service, postgres_url, temp_backup_dir):
        def _write_dump(cmd, **_kwargs):
            output_path = cmd[cmd.index("-f") + 1]
            Path(output_path).write_bytes(b"dump")
            return MagicMock()

        with patch("subprocess.run", side_effect=_write_dump) as mock_run:
            result = backup_service.create_backup(
                backup_name="custom_backup",
                database_url="postgresql+psycopg://user:pass@localhost/test_db",
            )

        assert result["backup_filename"] == "custom_backup.dump"
        assert Path(result["backup_path"]).exists()
        assert result["backup_size"] > 0

        cmd = mock_run.call_args.args[0]
        assert cmd[0] == "pg_dump"
        # URL should be normalized
        assert cmd[-1].startswith("postgresql://")

    def test_create_backup_with_custom_name(self, backup_service, postgres_url):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock()
            with patch("os.path.getsize", return_value=10):
                result = backup_service.create_backup(
                    backup_name="my_backup", database_url=postgres_url
                )
        assert result["backup_filename"] == "my_backup.dump"


class TestListBackups:
    def test_list_backups_filters_dump(self, backup_service, temp_backup_dir):
        (temp_backup_dir / "a.dump").write_bytes(b"1")
        (temp_backup_dir / "b.txt").write_bytes(b"1")
        (temp_backup_dir / "c.dump").write_bytes(b"1")

        result = backup_service.list_backups()
        assert len(result) == 2
        assert all(item["filename"].endswith(".dump") for item in result)


class TestGetBackup:
    def test_get_backup_returns_none_when_missing(self, backup_service):
        assert backup_service.get_backup("missing") is None

    def test_get_backup_returns_metadata(self, backup_service, temp_backup_dir):
        path = temp_backup_dir / "one.dump"
        path.write_bytes(b"data")
        result = backup_service.get_backup("one")
        assert result is not None
        assert result["filename"] == "one.dump"
        assert result["backup_name"] == "one"


class TestDeleteBackup:
    def test_delete_backup_removes_file(self, backup_service, temp_backup_dir):
        path = temp_backup_dir / "to_delete.dump"
        path.write_bytes(b"data")
        backup_service.delete_backup("to_delete")
        assert not path.exists()


class TestRestoreBackup:
    def test_restore_backup_requires_database_url(self, backup_service, temp_backup_dir):
        # Create a dummy backup file first so the file check passes
        path = temp_backup_dir / "restore_test.dump"
        path.write_bytes(b"data")

        with pytest.raises(ValueError):
            backup_service.restore_backup("restore_test")
        with pytest.raises(ValueError):
            backup_service.restore_backup(
                "restore_test", database_url="mysql://user:pass@localhost/test"
            )

    def test_restore_backup_calls_pg_restore(self, backup_service, postgres_url, temp_backup_dir):
        restore_path = temp_backup_dir / "restore_me.dump"
        restore_path.write_bytes(b"dump")

        with patch("subprocess.run") as mock_run:
            with patch.object(backup_service, "create_backup") as mock_create:
                mock_create.return_value = {
                    "backup_name": "current_backup_20260101_000000",
                    "backup_path": str(temp_backup_dir / "current_backup_20260101_000000.dump"),
                }
                result = backup_service.restore_backup(
                    "restore_me",
                    database_url=postgres_url,
                    create_current_backup=True,
                )

        assert result["restored_backup"] == "restore_me"
        assert result["current_backup"] == "current_backup_20260101_000000"
        cmd = mock_run.call_args.args[0]
        assert cmd[0] == "pg_restore"


class TestValidateBackup:
    def test_validate_backup_invalid(self, backup_service, temp_backup_dir):
        path = temp_backup_dir / "empty.dump"
        path.write_bytes(b"")
        result = backup_service.validate_backup("empty")
        assert result["valid"] is False

    def test_validate_backup_valid(self, backup_service, temp_backup_dir):
        path = temp_backup_dir / "ok.dump"
        path.write_bytes(b"data")
        result = backup_service.validate_backup("ok")
        assert result["valid"] is True


class TestCleanupAndStats:
    def test_cleanup_old_backups(self, backup_service, temp_backup_dir):
        for name in ("a", "b", "c"):
            (temp_backup_dir / f"{name}.dump").write_bytes(b"data")

        result = backup_service.cleanup_old_backups(keep_count=1)
        assert result["cleaned"] == 2
        remaining = list(temp_backup_dir.glob("*.dump"))
        assert len(remaining) == 1

    def test_get_backup_stats(self, backup_service, temp_backup_dir):
        (temp_backup_dir / "one.dump").write_bytes(b"1234")
        (temp_backup_dir / "two.dump").write_bytes(b"12")

        result = backup_service.get_backup_stats()
        assert result["total_count"] == 2
        assert result["total_size"] == 6
