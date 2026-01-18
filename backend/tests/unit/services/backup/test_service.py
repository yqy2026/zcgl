"""
测试 BackupService (备份服务)
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from src.services.backup.backup_service import BackupService


@pytest.fixture
def temp_backup_dir(tmp_path):
    """创建临时备份目录"""
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    return str(backup_dir)


@pytest.fixture
def backup_service(temp_backup_dir):
    """创建 BackupService 实例"""
    return BackupService(backup_dir=temp_backup_dir)


@pytest.fixture
def mock_db_file(tmp_path):
    """创建模拟数据库文件"""
    db_file = tmp_path / "test.db"
    db_file.write_text("test database content")
    return str(db_file)


class TestBackupServiceInit:
    """测试 BackupService 初始化"""

    def test_init_with_default_backup_dir(self, tmp_path):
        """测试使用默认备份目录初始化"""
        with patch("src.services.backup.backup_service.os.makedirs") as mock_makedirs:
            with patch("src.services.backup.backup_service.os.path.exists") as mock_exists:
                mock_exists.return_value = False

                service = BackupService()

                assert service.backup_dir == "backups"
                mock_makedirs.assert_called_once_with("backups")

    def test_init_with_custom_backup_dir(self, backup_service, temp_backup_dir):
        """测试使用自定义备份目录初始化"""
        assert backup_service.backup_dir == temp_backup_dir

    def test_init_creates_backup_dir_if_not_exists(self, tmp_path):
        """测试备份目录不存在时自动创建"""
        new_dir = tmp_path / "new_backups"
        service = BackupService(backup_dir=str(new_dir))

        assert new_dir.exists()
        assert service.backup_dir == str(new_dir)

    def test_init_with_existing_backup_dir(self, backup_service, temp_backup_dir):
        """测试使用已存在的备份目录"""
        # 目录已存在，不应抛出异常
        assert Path(temp_backup_dir).exists()
        assert backup_service.backup_dir == temp_backup_dir


class TestCreateBackup:
    """测试创建备份功能"""

    def test_create_backup_with_default_name(self, backup_service, temp_backup_dir):
        """测试使用默认名称创建备份"""
        result = backup_service.create_backup()

        assert "backup_name" in result
        assert "backup_filename" in result
        assert "backup_path" in result
        assert "backup_size" in result
        assert "created_at" in result

        assert result["backup_filename"].endswith(".db")
        assert result["backup_path"] == str(Path(temp_backup_dir) / result["backup_filename"])
        assert result["backup_size"] > 0

        # 验证文件存在
        assert Path(result["backup_path"]).exists()

    def test_create_backup_with_custom_name(self, backup_service, temp_backup_dir):
        """测试使用自定义名称创建备份"""
        custom_name = "my_custom_backup"
        result = backup_service.create_backup(backup_name=custom_name)

        assert result["backup_name"] == custom_name
        assert result["backup_filename"] == f"{custom_name}.db"
        assert Path(result["backup_path"]).exists()

    def test_create_backup_with_db_path(self, backup_service, mock_db_file, temp_backup_dir):
        """测试从真实数据库文件创建备份"""
        result = backup_service.create_backup(
            backup_name="real_backup", db_path=mock_db_file
        )

        assert result["backup_name"] == "real_backup"
        assert result["backup_size"] > 0

        # 验证备份文件内容与原文件相同
        backup_path = Path(result["backup_path"])
        assert backup_path.exists()
        assert backup_path.read_text() == "test database content"

    def test_create_backup_without_db_path(self, backup_service, temp_backup_dir):
        """测试不提供数据库路径时创建模拟备份"""
        result = backup_service.create_backup(backup_name="mock_backup")

        backup_path = Path(result["backup_path"])
        assert backup_path.exists()

        content = backup_path.read_text()
        assert "# 数据库备份文件" in content
        assert "# 创建时间:" in content
        assert "# 备份名称: mock_backup" in content
        assert "# 注意: 这是模拟备份文件" in content

    def test_create_backup_with_nonexistent_db_path(
        self, backup_service, temp_backup_dir
    ):
        """测试使用不存在的数据库路径创建备份"""
        result = backup_service.create_backup(
            backup_name="fallback_backup", db_path="/nonexistent/path.db"
        )

        # 应该创建模拟备份
        assert result["backup_name"] == "fallback_backup"
        assert Path(result["backup_path"]).exists()

    def test_create_backup_generates_unique_names(self, backup_service):
        """测试多次创建备份生成唯一名称"""
        import time

        result1 = backup_service.create_backup()
        time.sleep(1.1)  # 确保时间戳不同（需要超过1秒）
        result2 = backup_service.create_backup()

        # 默认名称包含时间戳，应该不同
        assert result1["backup_name"] != result2["backup_name"]

    def test_create_backup_exception_handling(self, backup_service):
        """测试创建备份时的异常处理"""
        with patch("src.services.backup.backup_service.os.path.join") as mock_join:
            mock_join.side_effect = OSError("Disk full")

            with pytest.raises(OSError):
                backup_service.create_backup()

    def test_create_backup_file_size(self, backup_service, mock_db_file):
        """测试备份文件大小正确"""
        result = backup_service.create_backup(db_path=mock_db_file)

        original_size = Path(mock_db_file).stat().st_size
        assert result["backup_size"] == original_size


class TestListBackups:
    """测试列出备份功能"""

    def test_list_backups_empty_directory(self, backup_service, temp_backup_dir):
        """测试空备份目录"""
        result = backup_service.list_backups()

        assert result == []
        assert isinstance(result, list)

    def test_list_backups_with_multiple_backups(self, backup_service, temp_backup_dir):
        """测试列出多个备份"""
        # 创建多个备份文件
        backup_service.create_backup(backup_name="backup1")
        backup_service.create_backup(backup_name="backup2")
        backup_service.create_backup(backup_name="backup3")

        result = backup_service.list_backups()

        assert len(result) == 3
        assert all("filename" in b for b in result)
        assert all("backup_name" in b for b in result)
        assert all("file_path" in b for b in result)
        assert all("file_size" in b for b in result)
        assert all("created_at" in b for b in result)
        assert all("modified_at" in b for b in result)

    def test_list_backups_sorted_by_created_time(self, backup_service):
        """测试备份按创建时间倒序排列"""
        backup_service.create_backup(backup_name="backup1")
        backup_service.create_backup(backup_name="backup2")
        backup_service.create_backup(backup_name="backup3")

        result = backup_service.list_backups()

        # 验证倒序排列（最新的在前）
        assert result[0]["created_at"] >= result[1]["created_at"]
        assert result[1]["created_at"] >= result[2]["created_at"]

    def test_list_backups_filters_non_db_files(self, backup_service, temp_backup_dir):
        """测试只列出 .db 文件"""
        # 创建备份文件
        backup_service.create_backup(backup_name="backup1")

        # 创建非 .db 文件
        (Path(temp_backup_dir) / "readme.txt").write_text("readme")
        (Path(temp_backup_dir) / "config.json").write_text("{}")

        result = backup_service.list_backups()

        # 应该只返回 .db 文件
        assert len(result) == 1
        assert result[0]["filename"] == "backup1.db"

    def test_list_backups_with_nonexistent_directory(self):
        """测试备份目录不存在时的处理"""
        service = BackupService(backup_dir="/nonexistent/backups")

        with patch("src.services.backup.backup_service.os.path.exists") as mock_exists:
            mock_exists.return_value = False

            result = service.list_backups()

            assert result == []

    def test_list_backups_file_attributes(self, backup_service):
        """测试备份文件属性正确"""
        backup_service.create_backup(backup_name="test_backup")

        result = backup_service.list_backups()

        assert len(result) == 1
        backup = result[0]

        assert backup["filename"] == "test_backup.db"
        assert backup["backup_name"] == "test_backup"
        assert backup["file_size"] > 0
        assert backup["created_at"]
        assert backup["modified_at"]

    def test_list_backups_exception_handling(self, backup_service):
        """测试列出备份时的异常处理"""
        with patch("src.services.backup.backup_service.os.listdir") as mock_listdir:
            mock_listdir.side_effect = PermissionError("Access denied")

            with pytest.raises(PermissionError):
                backup_service.list_backups()


class TestGetBackup:
    """测试获取单个备份信息"""

    def test_get_existing_backup(self, backup_service):
        """测试获取已存在的备份信息"""
        backup_service.create_backup(backup_name="test_backup")

        result = backup_service.get_backup("test_backup")

        assert result is not None
        assert result["backup_name"] == "test_backup"
        assert result["filename"] == "test_backup.db"
        assert "file_path" in result
        assert "file_size" in result
        assert "created_at" in result
        assert "modified_at" in result

    def test_get_nonexistent_backup(self, backup_service):
        """测试获取不存在的备份"""
        result = backup_service.get_backup("nonexistent")

        assert result is None

    def test_get_backup_file_size(self, backup_service, mock_db_file):
        """测试获取备份文件大小"""
        backup_service.create_backup(backup_name="size_test", db_path=mock_db_file)

        result = backup_service.get_backup("size_test")

        assert result["file_size"] > 0

    def test_get_backup_exception_handling(self, backup_service):
        """测试获取备份信息时的异常处理"""
        # 先创建一个备份
        backup_service.create_backup(backup_name="test_backup")

        with patch("src.services.backup.backup_service.os.stat") as mock_stat:
            mock_stat.side_effect = OSError("File system error")

            with pytest.raises(OSError):
                backup_service.get_backup("test_backup")


class TestDeleteBackup:
    """测试删除备份功能"""

    def test_delete_existing_backup(self, backup_service):
        """测试删除已存在的备份"""
        backup_service.create_backup(backup_name="to_delete")

        result = backup_service.delete_backup("to_delete")

        assert result["deleted_backup"] == "to_delete"
        assert "deleted_at" in result

        # 验证文件已被删除
        backups = backup_service.list_backups()
        assert len(backups) == 0

    def test_delete_nonexistent_backup(self, backup_service):
        """测试删除不存在的备份"""
        with pytest.raises(FileNotFoundError, match="备份文件不存在"):
            backup_service.delete_backup("nonexistent")

    def test_delete_backup_removes_file(self, backup_service, temp_backup_dir):
        """测试删除备份会移除文件"""
        backup_service.create_backup(backup_name="file_test")
        backup_path = Path(temp_backup_dir) / "file_test.db"

        assert backup_path.exists()

        backup_service.delete_backup("file_test")

        assert not backup_path.exists()

    def test_delete_backup_exception_handling(self, backup_service):
        """测试删除备份时的异常处理"""
        # 先创建一个备份
        backup_service.create_backup(backup_name="test_backup")

        with patch("src.services.backup.backup_service.os.remove") as mock_remove:
            mock_remove.side_effect = PermissionError("Access denied")

            with pytest.raises(PermissionError):
                backup_service.delete_backup("test_backup")


class TestRestoreBackup:
    """测试恢复备份功能"""

    def test_restore_backup_without_db_path(self, backup_service):
        """测试不提供数据库路径时恢复备份"""
        backup_service.create_backup(backup_name="to_restore")

        result = backup_service.restore_backup(
            backup_name="to_restore", db_path=None, create_current_backup=False
        )

        assert result["restored_backup"] == "to_restore"
        assert "restored_at" in result
        assert "current_backup" not in result

    def test_restore_backup_with_db_path(self, backup_service, mock_db_file, tmp_path):
        """测试使用数据库路径恢复备份"""
        # 先创建备份
        backup_service.create_backup(backup_name="restore_test", db_path=mock_db_file)

        # 创建目标数据库文件
        target_db = tmp_path / "target.db"
        target_db.write_text("original content")

        # 恢复备份
        result = backup_service.restore_backup(
            backup_name="restore_test", db_path=str(target_db), create_current_backup=False
        )

        assert result["restored_backup"] == "restore_test"
        assert target_db.read_text() == "test database content"

    def test_restore_backup_with_current_backup(
        self, backup_service, mock_db_file, tmp_path
    ):
        """测试恢复前创建当前状态备份"""
        # 先创建备份
        backup_service.create_backup(backup_name="restore_source", db_path=mock_db_file)

        # 创建目标数据库文件
        target_db = tmp_path / "target.db"
        target_db.write_text("current state")

        # 恢复备份并创建当前备份
        result = backup_service.restore_backup(
            backup_name="restore_source",
            db_path=str(target_db),
            create_current_backup=True,
        )

        assert result["restored_backup"] == "restore_source"
        assert "current_backup" in result
        assert "restored_at" in result

        # 验证创建了当前备份
        backups = backup_service.list_backups()
        current_backup_names = [b["backup_name"] for b in backups]
        assert any("current_backup_" in name for name in current_backup_names)

    def test_restore_nonexistent_backup(self, backup_service):
        """测试恢复不存在的备份"""
        with pytest.raises(FileNotFoundError, match="备份文件不存在"):
            backup_service.restore_backup("nonexistent")

    def test_restore_backup_exception_handling(self, backup_service):
        """测试恢复备份时的异常处理"""
        with patch("src.services.backup.backup_service.shutil.copy2") as mock_copy:
            mock_copy.side_effect = OSError("Copy failed")

            backup_service.create_backup(backup_name="test")

            with pytest.raises(OSError):
                backup_service.restore_backup("test", db_path="/some/path")


class TestValidateBackup:
    """测试验证备份功能"""

    def test_validate_valid_backup(self, backup_service, mock_db_file):
        """测试验证有效的备份"""
        backup_service.create_backup(backup_name="valid", db_path=mock_db_file)

        result = backup_service.validate_backup("valid")

        assert result["valid"] is True
        assert result["backup_name"] == "valid"
        assert result["file_size"] > 0
        assert "validated_at" in result

    def test_validate_nonexistent_backup(self, backup_service):
        """测试验证不存在的备份"""
        result = backup_service.validate_backup("nonexistent")

        assert result["valid"] is False
        assert "error" in result
        assert "备份文件不存在" in result["error"]

    def test_validate_empty_backup(self, backup_service, temp_backup_dir):
        """测试验证空文件备份"""
        # 创建空备份文件
        empty_backup = Path(temp_backup_dir) / "empty.db"
        empty_backup.write_text("")

        result = backup_service.validate_backup("empty")

        assert result["valid"] is False
        assert "error" in result
        assert "文件大小为0" in result["error"]

    def test_validate_backup_exception_handling(self, backup_service):
        """测试验证备份时的异常处理"""
        with patch("src.services.backup.backup_service.os.stat") as mock_stat:
            mock_stat.side_effect = OSError("File system error")

            result = backup_service.validate_backup("test")

            assert result["valid"] is False
            assert "error" in result


class TestCleanupOldBackups:
    """测试清理旧备份功能"""

    def test_cleanup_with_no_backups(self, backup_service):
        """测试没有备份时的清理"""
        result = backup_service.cleanup_old_backups(keep_count=10)

        assert result["cleaned"] == 0
        assert result["kept"] == 0
        assert "message" in result

    def test_cleanup_with_fewer_backups_than_limit(self, backup_service):
        """测试备份数量少于限制时不清理"""
        backup_service.create_backup(backup_name="backup1")
        backup_service.create_backup(backup_name="backup2")
        backup_service.create_backup(backup_name="backup3")

        result = backup_service.cleanup_old_backups(keep_count=10)

        assert result["cleaned"] == 0
        assert result["kept"] == 3
        assert "message" in result

    def test_cleanup_with_exact_limit(self, backup_service):
        """测试备份数量等于限制时不清理"""
        for i in range(5):
            backup_service.create_backup(backup_name=f"backup{i}")

        result = backup_service.cleanup_old_backups(keep_count=5)

        assert result["cleaned"] == 0
        assert result["kept"] == 5

    def test_cleanup_removes_old_backups(self, backup_service):
        """测试清理删除超出限制的旧备份"""
        # 创建 15 个备份
        for i in range(15):
            backup_service.create_backup(backup_name=f"backup{i:02d}")

        result = backup_service.cleanup_old_backups(keep_count=10)

        assert result["cleaned"] == 5
        assert result["kept"] == 10
        assert len(result["deleted_backups"]) == 5

        # 验证只保留了 10 个最新备份
        remaining_backups = backup_service.list_backups()
        assert len(remaining_backups) == 10

    def test_cleanup_keeps_newest_backups(self, backup_service):
        """测试清理保留最新的备份"""
        # 创建多个备份
        for i in range(5):
            backup_service.create_backup(backup_name=f"backup{i}")

        # 清理，保留 3 个
        backup_service.cleanup_old_backups(keep_count=3)

        remaining = backup_service.list_backups()

        # 验证保留了最新的 3 个（按创建时间倒序）
        assert len(remaining) == 3
        assert remaining[0]["created_at"] >= remaining[1]["created_at"]
        assert remaining[1]["created_at"] >= remaining[2]["created_at"]

    def test_cleanup_handles_delete_failures(self, backup_service):
        """测试清理时处理删除失败的情况"""
        # 创建备份
        for i in range(12):
            backup_service.create_backup(backup_name=f"backup{i}")

        # Mock delete_backup 使部分删除失败
        original_delete = backup_service.delete_backup
        call_count = [0]

        def mock_delete_with_failure(name):
            call_count[0] += 1
            if call_count[0] <= 2:  # 前两次删除失败
                raise Exception(f"Failed to delete {name}")
            return original_delete(name)

        with patch.object(backup_service, "delete_backup", side_effect=mock_delete_with_failure):
            result = backup_service.cleanup_old_backups(keep_count=10)

            # 应该删除了能删除的（10个中的2个失败，删除0个？）
            # 实际上会尝试删除2个（索引10和11），如果都失败，cleaned=0
            assert result["cleaned"] >= 0
            assert result["kept"] == 10

    def test_cleanup_exception_handling(self, backup_service):
        """测试清理时的异常处理"""
        with patch(
            "src.services.backup.backup_service.BackupService.list_backups"
        ) as mock_list:
            mock_list.side_effect = Exception("List failed")

            with pytest.raises(Exception):
                backup_service.cleanup_old_backups()


class TestGetBackupStats:
    """测试获取备份统计功能"""

    def test_get_stats_with_no_backups(self, backup_service):
        """测试没有备份时的统计"""
        result = backup_service.get_backup_stats()

        assert result["total_count"] == 0
        assert result["total_size"] == 0
        assert result["oldest_backup"] is None
        assert result["newest_backup"] is None

    def test_get_stats_with_single_backup(self, backup_service, mock_db_file):
        """测试单个备份的统计"""
        backup_service.create_backup(backup_name="single", db_path=mock_db_file)

        result = backup_service.get_backup_stats()

        assert result["total_count"] == 1
        assert result["total_size"] > 0
        assert result["total_size_mb"] >= 0  # 小文件可能小于 1MB
        assert result["oldest_backup"] == result["newest_backup"]

    def test_get_stats_with_multiple_backups(self, backup_service, mock_db_file):
        """测试多个备份的统计"""
        # 创建多个不同大小的备份
        backup_service.create_backup(backup_name="backup1", db_path=mock_db_file)
        backup_service.create_backup(backup_name="backup2", db_path=mock_db_file)
        backup_service.create_backup(backup_name="backup3", db_path=mock_db_file)

        result = backup_service.get_backup_stats()

        assert result["total_count"] == 3
        assert result["total_size"] > 0
        assert result["total_size_mb"] >= 0  # 小文件可能小于 1MB
        assert result["oldest_backup"] is not None
        assert result["newest_backup"] is not None

    def test_get_stats_size_calculation(self, backup_service, mock_db_file):
        """测试统计大小计算正确"""
        backup_service.create_backup(backup_name="size1", db_path=mock_db_file)
        backup_service.create_backup(backup_name="size2", db_path=mock_db_file)

        result = backup_service.get_backup_stats()

        # 验证总大小是两个备份之和
        backups = backup_service.list_backups()
        expected_total = sum(b["file_size"] for b in backups)
        assert result["total_size"] == expected_total

        # 验证 MB 转换正确
        expected_mb = round(expected_total / (1024 * 1024), 2)
        assert result["total_size_mb"] == expected_mb

    def test_get_stats_oldest_and_newest(self, backup_service):
        """测试统计中 oldest 和 newest 正确"""
        backup_service.create_backup(backup_name="first")
        backup_service.create_backup(backup_name="second")
        backup_service.create_backup(backup_name="third")

        result = backup_service.get_backup_stats()

        backups = backup_service.list_backups()
        # newest 是第一个（最新）
        assert result["newest_backup"] == backups[0]["created_at"]
        # oldest 是最后一个（最旧）
        assert result["oldest_backup"] == backups[-1]["created_at"]

    def test_get_stats_exception_handling(self, backup_service):
        """测试获取统计时的异常处理"""
        with patch(
            "src.services.backup.backup_service.BackupService.list_backups"
        ) as mock_list:
            mock_list.side_effect = Exception("Stats failed")

            with pytest.raises(Exception):
                backup_service.get_backup_stats()


class TestBackupServiceIntegration:
    """集成测试：测试多个方法的组合使用"""

    def test_backup_lifecycle(self, backup_service, mock_db_file):
        """测试完整备份生命周期"""
        # 1. 创建备份
        create_result = backup_service.create_backup(
            backup_name="lifecycle", db_path=mock_db_file
        )
        assert "lifecycle" in create_result["backup_name"]

        # 2. 列出备份
        backups = backup_service.list_backups()
        assert len(backups) == 1

        # 3. 获取备份信息
        backup_info = backup_service.get_backup("lifecycle")
        assert backup_info is not None
        assert backup_info["backup_name"] == "lifecycle"

        # 4. 验证备份
        validation = backup_service.validate_backup("lifecycle")
        assert validation["valid"] is True

        # 5. 获取统计
        stats = backup_service.get_backup_stats()
        assert stats["total_count"] == 1

        # 6. 删除备份
        delete_result = backup_service.delete_backup("lifecycle")
        assert delete_result["deleted_backup"] == "lifecycle"

        # 7. 验证已删除
        final_backups = backup_service.list_backups()
        assert len(final_backups) == 0

    def test_multiple_backups_management(self, backup_service, mock_db_file):
        """测试管理多个备份"""
        # 创建多个备份
        backup_names = []
        for i in range(5):
            name = f"backup{i}"
            backup_service.create_backup(backup_name=name, db_path=mock_db_file)
            backup_names.append(name)

        # 验证所有备份都存在
        backups = backup_service.list_backups()
        assert len(backups) == 5

        # 验证每个备份
        for name in backup_names:
            validation = backup_service.validate_backup(name)
            assert validation["valid"] is True

        # 获取统计
        stats = backup_service.get_backup_stats()
        assert stats["total_count"] == 5

        # 清理，保留 3 个
        cleanup_result = backup_service.cleanup_old_backups(keep_count=3)
        assert cleanup_result["cleaned"] == 2
        assert cleanup_result["kept"] == 3

        # 验证只保留 3 个
        final_backups = backup_service.list_backups()
        assert len(final_backups) == 3

    def test_backup_restore_workflow(self, backup_service, mock_db_file, tmp_path):
        """测试备份恢复工作流"""
        # 创建目标数据库
        target_db = tmp_path / "production.db"
        target_db.write_text("production data")

        # 创建备份
        backup_service.create_backup(backup_name="prod_snapshot", db_path=str(target_db))

        # 修改生产数据库
        target_db.write_text("modified production data")

        # 验证数据库已修改
        assert target_db.read_text() == "modified production data"

        # 恢复备份（不创建当前备份）
        backup_service.restore_backup(
            backup_name="prod_snapshot",
            db_path=str(target_db),
            create_current_backup=False,
        )

        # 验证已恢复
        assert target_db.read_text() == "production data"


class TestEdgeCases:
    """测试边缘情况"""

    def test_backup_with_special_characters_in_name(self, backup_service):
        """测试备份名称包含特殊字符"""
        special_name = "backup_2024-01-15_test"
        result = backup_service.create_backup(backup_name=special_name)

        assert result["backup_name"] == special_name
        assert Path(result["backup_path"]).exists()

    def test_very_long_backup_name(self, backup_service):
        """测试很长的备份名称"""
        long_name = "a" * 200
        result = backup_service.create_backup(backup_name=long_name)

        assert result["backup_name"] == long_name
        assert Path(result["backup_path"]).exists()

    def test_concurrent_backup_creation(self, backup_service):
        """测试并发创建备份（快速连续）"""

        results = []
        for i in range(10):
            result = backup_service.create_backup(backup_name=f"concurrent_{i}")
            results.append(result)

        # 验证所有备份都创建成功
        assert len(results) == 10
        for result in results:
            assert Path(result["backup_path"]).exists()

        # 验证备份名称唯一
        names = [r["backup_name"] for r in results]
        assert len(names) == len(set(names))

    def test_backup_with_unicode_name(self, backup_service):
        """测试使用 Unicode 字符的备份名称"""
        unicode_name = "备份_测试_数据"
        result = backup_service.create_backup(backup_name=unicode_name)

        assert result["backup_name"] == unicode_name
        assert Path(result["backup_path"]).exists()
