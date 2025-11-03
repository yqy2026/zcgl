from typing import Any

"""
文件管理服务
负责处理PDF文件的上传、存储、清理和管理
"""

import asyncio
import logging
import shutil
from datetime import datetime
from pathlib import Path

import aiofiles
from sqlalchemy.orm import Session

from .pdf_session_service import pdf_session_service

logger = logging.getLogger(__name__)


class FileManagementService:
    """文件管理服务"""

    def __init__(self):
        self.temp_dir = Path("temp_uploads")
        self.storage_dir = Path("file_storage")
        self.max_file_age_days = 7  # 临时文件保留7天
        self.max_storage_size_gb = 10  # 最大存储空间10GB

        # 确保目录存在
        self.temp_dir.mkdir(exist_ok=True)
        self.storage_dir.mkdir(exist_ok=True)

    async def save_uploaded_file(
        self, file_content: bytes, filename: str, session_id: str
    ) -> dict[str, Any]:
        """保存上传的文件"""

        try:
            # 创建唯一的文件名
            file_id = f"{session_id}_{filename}"
            temp_file_path = self.temp_dir / file_id

            # 异步保存文件
            async with aiofiles.open(temp_file_path, "wb") as f:
                await f.write(file_content)

            file_info = {
                "success": True,
                "file_path": str(temp_file_path),
                "file_size": len(file_content),
                "file_id": file_id,
                "original_filename": filename,
                "saved_at": datetime.now().isoformat(),
            }

            logger.info(f"文件保存成功: {filename} -> {temp_file_path}")
            return file_info

        except Exception as e:
            logger.error(f"文件保存失败: {filename}, 错误: {str(e)}")
            return {"success": False, "error": str(e), "file_path": None}

    async def get_file_info(self, file_path: str) -> dict[str, Any]:
        """获取文件信息"""
        try:
            path = Path(file_path)
            if not path.exists():
                return {"exists": False, "error": "文件不存在"}

            stat = path.stat()
            return {
                "exists": True,
                "file_size": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "file_extension": path.suffix,
                "mime_type": self._get_mime_type(path),
            }

        except Exception as e:
            logger.error(f"获取文件信息失败: {file_path}, 错误: {str(e)}")
            return {"exists": False, "error": str(e)}

    def _get_mime_type(self, file_path: Path) -> str:
        """获取MIME类型"""
        extension_map = {
            ".pdf": "application/pdf",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".tiff": "image/tiff",
            ".bmp": "image/bmp",
        }
        return extension_map.get(file_path.suffix.lower(), "application/octet-stream")

    async def cleanup_temp_files(
        self, db: Session, force: bool = False
    ) -> dict[str, Any]:
        """清理临时文件"""

        try:
            cleanup_start = datetime.now()
            deleted_files = []
            freed_space_bytes = 0
            errors = []

            # 获取所有活跃会话的文件路径
            active_sessions = await pdf_session_service.get_active_sessions(db)
            active_file_paths = {
                Path(session.file_path)
                for session in active_sessions
                if session.file_path
            }

            # 遍历临时文件目录
            for file_path in self.temp_dir.iterdir():
                if file_path.is_file():
                    try:
                        # 检查文件是否仍被活跃会话使用
                        if file_path in active_file_paths and not force:
                            continue

                        # 检查文件年龄
                        file_age = datetime.now() - datetime.fromtimestamp(
                            file_path.stat().st_mtime
                        )

                        if file_age.days >= self.max_file_age_days or force:
                            file_size = file_path.stat().st_size
                            file_path.unlink()

                            deleted_files.append(str(file_path))
                            freed_space_bytes += file_size

                            logger.info(
                                f"删除临时文件: {file_path.name} ({file_size} bytes)"
                            )

                    except Exception as e:
                        errors.append(f"删除文件失败 {file_path}: {str(e)}")
                        logger.error(f"删除临时文件失败: {file_path}, 错误: {str(e)}")

            cleanup_duration = (datetime.now() - cleanup_start).total_seconds()

            result = {
                "success": True,
                "deleted_files_count": len(deleted_files),
                "deleted_files": deleted_files,
                "freed_space_bytes": freed_space_bytes,
                "freed_space_mb": round(freed_space_bytes / (1024 * 1024), 2),
                "cleanup_duration_seconds": cleanup_duration,
                "errors": errors,
            }

            logger.info(
                f"临时文件清理完成: 删除 {len(deleted_files)} 个文件, "
                f"释放空间 {result['freed_space_mb']} MB"
            )
            return result

        except Exception as e:
            logger.error(f"临时文件清理失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "deleted_files_count": 0,
                "freed_space_mb": 0,
            }

    async def storage_statistics(self) -> dict[str, Any]:
        """获取存储统计信息"""

        try:
            temp_stats = await self._directory_statistics(self.temp_dir)
            storage_stats = await self._directory_statistics(self.storage_dir)

            total_size = (
                temp_stats["total_size_bytes"] + storage_stats["total_size_bytes"]
            )
            total_files = temp_stats["file_count"] + storage_stats["file_count"]

            return {
                "temp_directory": temp_stats,
                "storage_directory": storage_stats,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "total_size_gb": round(total_size / (1024 * 1024 * 1024), 2),
                "total_files": total_files,
                "max_storage_size_gb": self.max_storage_size_gb,
                "storage_usage_percentage": round(
                    (total_size / (1024 * 1024 * 1024 * self.max_storage_size_gb))
                    * 100,
                    2,
                ),
            }

        except Exception as e:
            logger.error(f"获取存储统计失败: {str(e)}")
            return {"error": str(e), "total_size_mb": 0, "total_files": 0}

    async def _directory_statistics(self, directory: Path) -> dict[str, Any]:
        """获取目录统计信息"""
        if not directory.exists():
            return {
                "exists": False,
                "file_count": 0,
                "total_size_bytes": 0,
                "file_types": {},
            }

        file_count = 0
        total_size = 0
        file_types = {}

        try:
            for file_path in directory.iterdir():
                if file_path.is_file():
                    file_count += 1
                    size = file_path.stat().st_size
                    total_size += size

                    # 统计文件类型
                    extension = file_path.suffix.lower()
                    if extension not in file_types:
                        file_types[extension] = {"count": 0, "total_size": 0}
                    file_types[extension]["count"] += 1
                    file_types[extension]["total_size"] += size

            return {
                "exists": True,
                "path": str(directory),
                "file_count": file_count,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "file_types": file_types,
            }

        except Exception as e:
            logger.error(f"获取目录统计失败: {directory}, 错误: {str(e)}")
            return {
                "exists": True,
                "path": str(directory),
                "file_count": 0,
                "total_size_bytes": 0,
                "file_types": {},
                "error": str(e),
            }

    async def archive_session_file(
        self, session_id: str, db: Session
    ) -> dict[str, Any]:
        """归档会话文件到永久存储"""

        try:
            from ..models.pdf_import_session import PDFImportSession

            # 获取会话信息
            session = (
                db.query(PDFImportSession)
                .filter(PDFImportSession.session_id == session_id)
                .first()
            )

            if not session or not session.file_path:
                return {"success": False, "error": "会话不存在或文件路径为空"}

            source_path = Path(session.file_path)
            if not source_path.exists():
                return {"success": False, "error": "源文件不存在"}

            # 创建归档目录结构
            archive_date = datetime.now().strftime("%Y/%m")
            archive_dir = self.storage_dir / archive_date
            archive_dir.mkdir(parents=True, exist_ok=True)

            # 生成归档文件名
            archive_filename = f"{session_id}_{session.original_filename}"
            archive_path = archive_dir / archive_filename

            # 移动文件到归档目录
            shutil.move(str(source_path), str(archive_path))

            # 更新会话记录
            session.file_path = str(archive_path)
            db.commit()

            result = {
                "success": True,
                "original_path": str(source_path),
                "archive_path": str(archive_path),
                "file_size": archive_path.stat().st_size,
                "archived_at": datetime.now().isoformat(),
            }

            logger.info(f"文件归档成功: {session_id} -> {archive_path}")
            return result

        except Exception as e:
            logger.error(f"文件归档失败: {session_id}, 错误: {str(e)}")
            return {"success": False, "error": str(e)}

    async def delete_session_file(self, session_id: str, db: Session) -> dict[str, Any]:
        """删除会话文件"""

        try:
            from ..models.pdf_import_session import PDFImportSession

            # 获取会话信息
            session = (
                db.query(PDFImportSession)
                .filter(PDFImportSession.session_id == session_id)
                .first()
            )

            if not session:
                return {"success": False, "error": "会话不存在"}

            result = {"deleted_files": [], "errors": []}

            # 删除主文件
            if session.file_path:
                file_path = Path(session.file_path)
                if file_path.exists():
                    try:
                        file_size = file_path.stat().st_size
                        file_path.unlink()
                        result["deleted_files"].append(
                            {"path": str(file_path), "size": file_size}
                        )
                        logger.info(f"删除会话文件: {file_path}")
                    except Exception as e:
                        result["errors"].append(f"删除文件失败 {file_path}: {str(e)}")

            return {
                "success": len(result["errors"]) == 0,
                "deleted_files": result["deleted_files"],
                "errors": result["errors"],
            }

        except Exception as e:
            logger.error(f"删除会话文件失败: {session_id}, 错误: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "deleted_files": [],
                "errors": [str(e)],
            }

    async def schedule_cleanup(self, db: Session, interval_hours: int = 24):
        """定时清理任务"""

        while True:
            try:
                logger.info("开始定时清理任务")
                await self.cleanup_temp_files(db)

                # 清理过期的会话数据
                deleted_sessions = await pdf_session_service.cleanup_old_sessions(
                    db, days=7
                )
                logger.info(f"清理过期会话数据: {deleted_sessions} 条记录")

            except Exception as e:
                logger.error(f"定时清理任务失败: {str(e)}")

            # 等待下次执行
            await asyncio.sleep(interval_hours * 3600)

    def validate_file(self, file_content: bytes, filename: str) -> dict[str, Any]:
        """验证文件"""

        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "file_info": {
                "size_bytes": len(file_content),
                "size_mb": round(len(file_content) / (1024 * 1024), 2),
                "filename": filename,
                "extension": Path(filename).suffix.lower(),
            },
        }

        # 检查文件大小
        max_size_mb = 50
        if validation_result["file_info"]["size_mb"] > max_size_mb:
            validation_result["is_valid"] = False
            validation_result["errors"].append(f"文件大小超过限制 ({max_size_mb}MB)")

        # 检查文件扩展名
        allowed_extensions = [".pdf", ".jpg", ".jpeg", ".png", ".tiff"]
        if validation_result["file_info"]["extension"] not in allowed_extensions:
            validation_result["is_valid"] = False
            validation_result["errors"].append(
                f"不支持的文件类型: {validation_result['file_info']['extension']}"
            )

        # 检查文件内容是否为空
        if len(file_content) == 0:
            validation_result["is_valid"] = False
            validation_result["errors"].append("文件内容为空")

        # PDF文件特殊检查
        if validation_result["file_info"]["extension"] == ".pdf":
            if not file_content.startswith(b"%PDF"):
                validation_result["is_valid"] = False
                validation_result["errors"].append("不是有效的PDF文件")

        return validation_result


# 创建全局实例
file_management_service = FileManagementService()
