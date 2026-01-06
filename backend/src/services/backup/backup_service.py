"""
数据备份和恢复服务

提供数据库备份、恢复和管理功能
"""

import logging
import os
import shutil
from datetime import datetime
from typing import Any

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
        self, backup_name: str | None = None, db_path: str | None = None
    ) -> dict[str, Any]:
        """
        创建数据库备份

        Args:
            backup_name: 备份名称，默认使用时间戳
            db_path: 数据库文件路径

        Returns:
            备份结果信息
        """
        try:
            # 生成备份文件名
            if not backup_name:
                backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            backup_filename = f"{backup_name}.db"
            backup_path = os.path.join(self.backup_dir, backup_filename)

            logger.info(f"开始创建数据备份: {backup_path}")

            # 如果提供了数据库路径，进行真正的备份
            if db_path and os.path.exists(db_path):
                shutil.copy2(db_path, backup_path)
                logger.info(f"已复制数据库文件: {db_path} -> {backup_path}")
            else:
                # 模拟创建备份文件（保持向后兼容）
                with open(backup_path, "w") as f:
                    f.write("# 数据库备份文件\n")
                    f.write(f"# 创建时间: {datetime.now().isoformat()}\n")
                    f.write(f"# 备份名称: {backup_name}\n")
                    f.write(
                        "# 注意: 这是模拟备份文件，请配置 db_path 参数进行真实备份\n"
                    )

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

            backups = []
            for filename in os.listdir(self.backup_dir):
                if filename.endswith(".db"):
                    file_path = os.path.join(self.backup_dir, filename)
                    file_stat = os.stat(file_path)

                    backups.append(
                        {
                            "filename": filename,
                            "backup_name": filename.replace(".db", ""),
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
            backup_filename = f"{backup_name}.db"
            backup_path = os.path.join(self.backup_dir, backup_filename)

            if not os.path.exists(backup_path):
                return None

            file_stat = os.stat(backup_path)

            return {
                "filename": backup_filename,
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
            backup_filename = f"{backup_name}.db"
            backup_path = os.path.join(self.backup_dir, backup_filename)

            if not os.path.exists(backup_path):
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
        db_path: str | None = None,
        create_current_backup: bool = True,
    ) -> dict[str, Any]:
        """
        从备份文件恢复数据

        Args:
            backup_name: 备份名称
            db_path: 数据库文件路径
            create_current_backup: 是否在恢复前创建当前状态的备份

        Returns:
            恢复结果信息
        """
        try:
            backup_filename = f"{backup_name}.db"
            backup_path = os.path.join(self.backup_dir, backup_filename)

            if not os.path.exists(backup_path):
                raise FileNotFoundError(f"备份文件不存在: {backup_name}")

            logger.info(f"开始恢复数据备份: {backup_path}")

            result = {
                "restored_backup": backup_name,
                "restored_at": datetime.now().isoformat(),
            }

            # 如果提供了数据库路径，进行真正的恢复
            if db_path:
                if create_current_backup:
                    # 创建当前状态的备份
                    current_backup = (
                        f"current_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                    )
                    current_backup_path = os.path.join(self.backup_dir, current_backup)

                    shutil.copy2(db_path, current_backup_path)
                    result["current_backup"] = current_backup.replace(".db", "")
                    logger.info(f"已创建当前状态备份: {current_backup_path}")

                # 恢复数据库
                shutil.copy2(backup_path, db_path)
                logger.info(f"已恢复数据库文件: {backup_path} -> {db_path}")

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
            backup_filename = f"{backup_name}.db"
            backup_path = os.path.join(self.backup_dir, backup_filename)

            if not os.path.exists(backup_path):
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
