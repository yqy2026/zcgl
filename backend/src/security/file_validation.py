"""
File validation utilities.
"""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# magic模块的条件导入
try:
    import magic

    MAGIC_AVAILABLE = True
except ImportError:
    magic = None
    MAGIC_AVAILABLE = False
    logging.getLogger(__name__).warning("python-magic模块不可用，文件类型检测功能将受限")

from fastapi import UploadFile

from ..constants.file_size_constants import (
    DEFAULT_MAX_ARCHIVE_FILE_SIZE,
    DEFAULT_MAX_EXCEL_FILE_SIZE,
    DEFAULT_MAX_FILE_SIZE,
    DEFAULT_MAX_GENERIC_FILE_SIZE,
    DEFAULT_MAX_IMAGE_FILE_SIZE,
)
from ..core.exception_handler import BusinessValidationError

logger = logging.getLogger(__name__)

class FileValidationConfig:
    """文件验证配置"""

    # 允许的文件类型
    ALLOWED_MIME_TYPES = {
        "application/pdf": ".pdf",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
        "application/vnd.ms-excel": ".xls",
        "text/csv": ".csv",
        "application/json": ".json",
        "image/jpeg": ".jpg,.jpeg",
        "image/png": ".png",
        "image/tiff": ".tiff,.tif",
        "image/gif": ".gif",
        "application/zip": ".zip",
        "application/x-7z-compressed": ".7z",
        "application/x-rar-compressed": ".rar",
    }

    # 文件大小限制（字节）
    MAX_FILE_SIZES = {
        "pdf": DEFAULT_MAX_FILE_SIZE,
        "excel": DEFAULT_MAX_EXCEL_FILE_SIZE,
        "image": DEFAULT_MAX_IMAGE_FILE_SIZE,
        "default": DEFAULT_MAX_GENERIC_FILE_SIZE,
        "zip": DEFAULT_MAX_ARCHIVE_FILE_SIZE,
    }

    # 危险文件特征
    MALICIOUS_SIGNATURES = [
        b"<?php",
        b"<script",
        b"javascript:",
        b"vbscript:",
        b"onload=",
        b"onclick=",
        b"onerror=",
        b"eval(",
        b"document.",
        b"window.",
        b"alert(",
        b"<iframe",
        b"<object",
        b"<embed",
        b"data:text/html",
        b"vbs:",
        b".hta",
    ]

    # 文件名黑名单
    BLACKLISTED_PATTERNS = [
        r"\.\.",
        r"/",
        r"\\",
        r":",
        r"\*",
        r"\?",
        r'"',
        r"<",
        r">",
        r"\|",
        r"\.php$",
        r"\.asp$",
        r"\.aspx$",
        r"\.jsp$",
        r"\.exe$",
        r"\.bat$",
        r"\.cmd$",
        r"\.scr$",
        r"\.com$",
        r"\.pif$",
        r"\.dll$",
        r"\.sys$",
        r"\.lnk$",
        r"\.msi$",
        r"\.jar$",
        r"\.swf$",
    ]


class FileValidator:
    """文件验证器"""

    def __init__(self) -> None:
        self.config = FileValidationConfig()
        self.logger = logging.getLogger(__name__)

    def validate_file_type(
        self, file: UploadFile, allowed_types: list[str] | None = None
    ) -> bool:
        """
        验证文件类型

        Args:
            file: 上传的文件
            allowed_types: 允许的文件类型列表

        Returns:
            bool: 验证是否通过
        """
        if not allowed_types:
            allowed_types = [
                "application/pdf",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ]

        # 检查文件扩展名
        file_ext = Path(file.filename or "").suffix.lower()
        if file_ext not in [
            ext
            for exts in self.config.ALLOWED_MIME_TYPES.values()
            for ext in exts.split(",")
        ]:
            raise BusinessValidationError(
                f"不支持的文件扩展名: {file_ext}",
                details={
                    "allowed_extensions": list(self.config.ALLOWED_MIME_TYPES.values())
                },
            )

        # 检查MIME类型 - 使用流式读取避免内存耗尽攻击
        try:
            # 保存当前位置
            original_position = file.file.tell()

            # 读取文件前4096字节用于MIME类型检测（增加读取大小以提高准确性）
            file_content = file.file.read(4096)
            file.file.seek(original_position)  # 重置文件指针到原始位置

            detected_mime = magic.from_buffer(file_content, mime=True)

            # 检查是否为可疑的MIME类型
            suspicious_mimes = [
                "text/x-php",
                "application/x-php",
                "application/x-executable",
                "application/x-sharedlib",
                "application/x-mach-binary",
            ]
            if detected_mime in suspicious_mimes:
                raise BusinessValidationError(
                    f"可疑的文件类型: {detected_mime}",
                    details={"detected_mime": detected_mime},
                )

            if detected_mime not in allowed_types:
                raise BusinessValidationError(
                    f"不支持的文件类型: {detected_mime}",
                    details={"allowed_types": allowed_types},
                )

            # 验证扩展名与MIME类型匹配
            expected_ext = self.config.ALLOWED_MIME_TYPES.get(detected_mime, "")
            if expected_ext and file_ext not in expected_ext.split(","):
                raise BusinessValidationError(
                    f"文件扩展名与MIME类型不匹配: {file_ext} vs {detected_mime}",
                    details={
                        "file_ext": file_ext,
                        "detected_mime": detected_mime,
                        "expected_ext": expected_ext,
                    },
                )

        except BusinessValidationError:
            raise
        except Exception as e:
            raise BusinessValidationError(
                f"文件类型检测失败: {str(e)}", details={"error": str(e)}
            ) from e

        return True

    def validate_file_size(self, file: UploadFile, max_size: int | None = None) -> bool:
        """
        验证文件大小

        Args:
            file: 上传的文件
            max_size: 最大文件大小（字节）

        Returns:
            bool: 验证是否通过
        """
        if max_size is None:
            # 根据文件类型设置默认大小限制
            file_ext = Path(file.filename or "").suffix.lower()
            if file_ext == ".pdf":
                max_size = self.config.MAX_FILE_SIZES["pdf"]
            elif file_ext in [".xlsx", ".xls", ".csv"]:
                max_size = self.config.MAX_FILE_SIZES["excel"]
            elif file_ext in [".jpg", ".jpeg", ".png", ".tiff", ".tif", ".gif"]:
                max_size = self.config.MAX_FILE_SIZES["image"]
            elif file_ext in [".zip", ".7z", ".rar"]:
                max_size = self.config.MAX_FILE_SIZES["zip"]
            else:
                max_size = self.config.MAX_FILE_SIZES["default"]

        # 获取文件大小
        if hasattr(file, "size") and file.size is not None:
            file_size = file.size
        else:
            # 通过读取文件计算大小
            original_position = file.file.tell()
            file.file.seek(0, 2)  # 移动到文件末尾
            file_size = file.file.tell()
            file.file.seek(original_position)  # 重置文件指针

        if file_size > max_size:
            raise BusinessValidationError(
                f"文件过大: {file_size} bytes，最大允许 {max_size} bytes",
                details={
                    "file_size": file_size,
                    "max_size": max_size,
                    "size_mb": file_size / (1024 * 1024),
                    "max_size_mb": max_size / (1024 * 1024),
                },
            )

        return True

    def validate_filename(self, filename: str) -> bool:
        """
        验证文件名安全性

        Args:
            filename: 文件名

        Returns:
            bool: 验证是否通过
        """
        if not filename:
            raise BusinessValidationError("文件名不能为空")

        # 检查文件名长度
        if len(filename) > 255:
            raise BusinessValidationError("文件名过长")

        # 检查黑名单模式
        for pattern in self.config.BLACKLISTED_PATTERNS:
            if re.search(pattern, filename, re.IGNORECASE):
                raise BusinessValidationError(
                    f"文件名包含非法字符或模式: {pattern}",
                    details={"blacklisted_pattern": pattern},
                )

        return True

    def validate_file_content(self, file: UploadFile) -> bool:
        """
        验证文件内容安全性

        Args:
            file: 上传的文件

        Returns:
            bool: 验证是否通过
        """
        try:
            # 保存当前位置
            original_position = file.file.tell()

            file.file.seek(0)

            chunk_size = 1024 * 1024
            signatures = self.config.MALICIOUS_SIGNATURES
            max_signature_len = max(
                (len(signature) for signature in signatures), default=0
            )
            tail = b""
            total_read = 0

            while True:
                chunk = file.file.read(chunk_size)
                if not chunk:
                    break
                total_read += len(chunk)
                data = tail + chunk
                data_lower = data.lower()
                for signature in signatures:
                    if signature in data_lower:
                        raise BusinessValidationError(
                            "检测到可疑文件内容",
                            details={
                                "signature": signature.decode("utf-8", errors="ignore")
                            },
                        )
                if max_signature_len > 1:
                    tail = data[-(max_signature_len - 1) :]
                else:
                    tail = b""

            file.file.seek(original_position)

            if total_read == 0:
                raise BusinessValidationError("文件内容为空")

        except BusinessValidationError:
            raise
        except Exception as e:
            raise BusinessValidationError(
                f"文件内容检测失败: {str(e)}", details={"error": str(e)}
            ) from e

        return True

    def calculate_file_hash(self, file: UploadFile) -> str:
        """
        计算文件哈希值

        Args:
            file: 上传的文件

        Returns:
            str: 文件哈希值
        """
        try:
            # 保存当前位置
            original_position = file.file.tell()

            # 计算SHA-256哈希
            sha256_hash = hashlib.sha256()
            for chunk in iter(lambda: file.file.read(4096), b""):
                sha256_hash.update(chunk)

            file.file.seek(original_position)  # 重置文件指针

            return sha256_hash.hexdigest()

        except Exception as e:
            logger.warning(f"文件哈希计算失败: {e}")
            return ""

    def validate_upload(
        self,
        file: UploadFile,
        allowed_types: list[str] | None = None,
        max_size: int | None = None,
    ) -> dict[str, Any]:
        """
        综合验证文件上传

        Args:
            file: 上传的文件
            allowed_types: 允许的文件类型
            max_size: 最大文件大小

        Returns:
            dict: 验证结果
        """
        if not file:
            raise BusinessValidationError("未提供文件")

        # 验证文件名
        self.validate_filename(file.filename or "")

        # 验证文件类型
        self.validate_file_type(file, allowed_types)

        # 验证文件大小
        self.validate_file_size(file, max_size)

        # 验证文件内容
        self.validate_file_content(file)

        # 计算文件哈希
        file_hash = self.calculate_file_hash(file)

        return {
            "valid": True,
            "filename": file.filename,
            "size": file.size,
            "hash": file_hash,
            "validation_time": datetime.now(UTC).isoformat(),
        }


async def validate_upload_file(
    file: UploadFile,
    allowed_types: str | list[str] | None = None,
    max_size: int | None = None,
) -> dict[str, Any]:
    """
    Async-friendly wrapper for upload validation.

    Args:
        file: 上传的文件
        allowed_types: 允许的文件类型（单个 MIME 或列表）
        max_size: 最大文件大小

    Returns:
        dict: 验证结果
    """
    validator = FileValidator()
    if isinstance(allowed_types, str):
        allowed_types = [allowed_types]
    return validator.validate_upload(
        file=file,
        allowed_types=allowed_types,
        max_size=max_size,
    )
