"""
数据备份和恢复服务

提供数据库备份、恢复和管理功能
"""

import logging
import os
import subprocess  # nosec B404
from datetime import datetime
from typing import Any

from ...core.exception_handler import ConfigurationError

logger = logging.getLogger(__name__)


class BackupService:
    """
    数据备份服务

    提供数据库备份、恢复、列表、删除等功能
    """

    def __init__(self, backup_dir: str | None = None):
        """
        初始化备份服务

        Args:
            backup_dir: 备份目录路径，默认为 "backups"
        """
        self.backup_dir = backup_dir or "backups"
        self._ensure_backup_dir()

    def _ensure_backup_dir(self) -> None:
        """确保备份目录存在"""
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
            logger.info(f"创建备份目录: {self.backup_dir}")

    def create_backup(
        self,
        backup_name: str | None = None,
        database_url: str | None = None,
    ) -> dict[str, Any]:
        """
        创建数据库备份

        Args:
            backup_name: 备份名称，默认使用时间戳
            database_url: PostgreSQL 数据库连接URL

        Returns:
            备份结果信息
        """
        try:
            # 生成备份文件名
            if not backup_name:
                backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            if not database_url:
                raise ConfigurationError(
                    "数据库备份需要提供 PostgreSQL database_url",
                    config_key="DATABASE_URL",
                )
            if not database_url.startswith("postgresql"):
                raise ConfigurationError(
                    "仅支持 PostgreSQL 备份",
                    config_key="DATABASE_URL",
                )
            backup_filename = f"{backup_name}.dump"
            backup_path = os.path.join(self.backup_dir, backup_filename)

            logger.info(f"开始创建数据备份: {backup_path}")

            database_url = self._normalize_postgres_url(database_url)
            cmd = [
                "pg_dump",
                "--format=custom",
                "--no-owner",
                "--no-privileges",
                "-f",
                backup_path,
                database_url,
            ]
            logger.info("执行 PostgreSQL 备份命令: pg_dump (custom format)")
            subprocess.run(cmd, check=True)  # nosec B603

            # 获取备份文件信息
            backup_size = os.path.getsize(backup_path)

            logger.info(f"数据备份创建成功: {backup_path}")

            return {
                "backup_name": backup_name,
                "backup_filename": backup_filename,
                "backup_path": backup_path,
                "backup_size": backup_size,
                "created_at": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"创建数据备份异常: {str(e)}")
            raise

    def list_backups(self) -> list[dict[str, Any]]:
        """
        获取所有备份文件列表

        Returns:
            备份文件列表
        """
        try:
            logger.info("获取备份文件列表")

            if not os.path.exists(self.backup_dir):
                logger.warning(f"备份目录不存在: {self.backup_dir}")
                return []

            backups: list[dict[str, Any]] = []
            for filename in os.listdir(self.backup_dir):
                if filename.endswith(".dump"):
                    file_path = os.path.join(self.backup_dir, filename)
                    file_stat = os.stat(file_path)

                    backups.append(
                        {
                            "filename": filename,
                            "backup_name": os.path.splitext(filename)[0],
                            "file_path": file_path,
                            "file_size": file_stat.st_size,
                            "created_at": datetime.fromtimestamp(
                                file_stat.st_ctime
                            ).isoformat(),
                            "modified_at": datetime.fromtimestamp(
                                file_stat.st_mtime
                            ).isoformat(),
                        }
                    )

            # 按创建时间倒序排列
            backups.sort(key=lambda x: x["created_at"], reverse=True)

            logger.info(f"找到 {len(backups)} 个备份文件")

            return backups

        except Exception as e:
            logger.error(f"获取备份列表异常: {str(e)}")
            raise

    def get_backup(self, backup_name: str) -> dict[str, Any] | None:
        """
        获取指定备份的信息

        Args:
            backup_name: 备份名称

        Returns:
            备份信息，如果不存在则返回 None
        """
        try:
            backup_path = self._find_backup_path(
                backup_name, allowed_extensions=(".dump",)
            )

            if not backup_path or not os.path.exists(backup_path):
                return None

            file_stat = os.stat(backup_path)

            return {
                "filename": os.path.basename(backup_path),
                "backup_name": backup_name,
                "file_path": backup_path,
                "file_size": file_stat.st_size,
                "created_at": datetime.fromtimestamp(file_stat.st_ctime).isoformat(),
                "modified_at": datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
            }

        except Exception as e:
            logger.error(f"获取备份信息异常: {str(e)}")
            raise

    def delete_backup(self, backup_name: str) -> dict[str, Any]:
        """
        删除指定的备份文件

        Args:
            backup_name: 备份名称

        Returns:
            删除结果信息
        """
        try:
            backup_path = self._find_backup_path(backup_name)

            if not backup_path or not os.path.exists(backup_path):
                raise FileNotFoundError(f"备份文件不存在: {backup_name}")

            logger.info(f"删除备份文件: {backup_path}")

            os.remove(backup_path)

            return {
                "deleted_backup": backup_name,
                "deleted_at": datetime.now().isoformat(),
            }

        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"删除备份文件异常: {str(e)}")
            raise

    def restore_backup(
        self,
        backup_name: str,
        database_url: str | None = None,
        create_current_backup: bool | None = None,
        should_create_current_backup: bool = True,
    ) -> dict[str, Any]:
        """
        从备份文件恢复数据

        Args:
            backup_name: 备份名称
            create_current_backup: 是否在恢复前创建当前状态的备份
            should_create_current_backup: 是否在恢复前创建当前状态的备份（兼容参数）

        Returns:
            恢复结果信息
        """
        try:
            backup_path = self._find_backup_path(backup_name)

            if not backup_path or not os.path.exists(backup_path):
                raise FileNotFoundError(f"备份文件不存在: {backup_name}")

            logger.info(f"开始恢复数据备份: {backup_path}")

            result = {
                "restored_backup": backup_name,
                "restored_at": datetime.now().isoformat(),
            }

            if not database_url:
                raise ConfigurationError(
                    "数据库恢复需要提供 PostgreSQL database_url",
                    config_key="DATABASE_URL",
                )
            if not database_url.startswith("postgresql"):
                raise ConfigurationError(
                    "仅支持 PostgreSQL 恢复",
                    config_key="DATABASE_URL",
                )

            if create_current_backup is None:
                create_current_backup = should_create_current_backup
            if create_current_backup:
                current_backup = (
                    f"current_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                )
                current_backup_result = self.create_backup(
                    backup_name=current_backup, database_url=database_url
                )
                result["current_backup"] = current_backup_result["backup_name"]
                logger.info(
                    "已创建当前状态备份: %s",
                    current_backup_result["backup_path"],
                )

            database_url = self._normalize_postgres_url(database_url)
            cmd = [
                "pg_restore",
                "--clean",
                "--if-exists",
                "--no-owner",
                "--no-privileges",
                "-d",
                database_url,
                backup_path,
            ]
            logger.info("执行 PostgreSQL 恢复命令: pg_restore")
            subprocess.run(cmd, check=True)  # nosec B603

            return result

        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"恢复数据备份异常: {str(e)}")
            raise

    def validate_backup(self, backup_name: str) -> dict[str, Any]:
        """
        验证备份文件的完整性

        Args:
            backup_name: 备份名称

        Returns:
            验证结果
        """
        try:
            backup_path = self._find_backup_path(backup_name)

            if not backup_path or not os.path.exists(backup_path):
                return {
                    "valid": False,
                    "error": f"备份文件不存在: {backup_name}",
                }

            # 基本文件完整性检查
            file_stat = os.stat(backup_path)
            file_size = file_stat.st_size

            # 检查文件大小是否合理（大于0）
            if file_size == 0:
                return {
                    "valid": False,
                    "error": "备份文件大小为0",
                }

            return {
                "valid": True,
                "backup_name": backup_name,
                "file_size": file_size,
                "validated_at": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"验证备份文件异常: {str(e)}")
            return {
                "valid": False,
                "error": str(e),
            }

    def cleanup_old_backups(self, keep_count: int = 10) -> dict[str, Any]:
        """
        清理旧的备份文件，保留最新的 N 个

        Args:
            keep_count: 保留的备份数量

        Returns:
            清理结果
        """
        try:
            backups = self.list_backups()

            if len(backups) <= keep_count:
                return {
                    "cleaned": 0,
                    "kept": len(backups),
                    "message": "备份数量未超过限制，无需清理",
                }

            # 删除超出限制的旧备份
            deleted_backups = []
            for backup in backups[keep_count:]:
                try:
                    self.delete_backup(backup["backup_name"])
                    deleted_backups.append(backup["backup_name"])
                except Exception as e:
                    logger.warning(f"删除旧备份失败: {backup['backup_name']}, {str(e)}")

            return {
                "cleaned": len(deleted_backups),
                "kept": keep_count,
                "deleted_backups": deleted_backups,
                "cleaned_at": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"清理旧备份异常: {str(e)}")
            raise

    def get_backup_stats(self) -> dict[str, Any]:
        """
        获取备份统计信息

        Returns:
            备份统计信息
        """
        try:
            backups = self.list_backups()

            if not backups:
                return {
                    "total_count": 0,
                    "total_size": 0,
                    "oldest_backup": None,
                    "newest_backup": None,
                }

            total_size = sum(b["file_size"] for b in backups)

            return {
                "total_count": len(backups),
                "total_size": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "oldest_backup": backups[-1]["created_at"] if backups else None,
                "newest_backup": backups[0]["created_at"] if backups else None,
            }

        except Exception as e:
            logger.error(f"获取备份统计异常: {str(e)}")
            raise

    @staticmethod
    def _normalize_postgres_url(database_url: str) -> str:
        """Convert SQLAlchemy PostgreSQL URLs to libpq-compatible URLs."""
        if database_url.startswith("postgresql+"):
            scheme_index = database_url.find("://")
            if scheme_index != -1:
                return "postgresql" + database_url[scheme_index:]
        return database_url

    def _find_backup_path(
        self, backup_name: str, allowed_extensions: tuple[str, ...] = (".dump",)
    ) -> str | None:
        """根据备份名查找实际备份文件路径"""
        for ext in allowed_extensions:
            candidate = os.path.join(self.backup_dir, f"{backup_name}{ext}")
            if os.path.exists(candidate):
                return candidate
        return None
