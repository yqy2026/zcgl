"""
增强文件安全处理工具
提供文件上传的全方位安全验证和处理
"""

import hashlib
import re
import uuid
from pathlib import Path

import magic
from fastapi import UploadFile


class EnhancedFileSecurityValidator:
    """增强文件安全验证器"""

    # 危险文件扩展名黑名单
    DANGEROUS_EXTENSIONS: set[str] = {
        ".exe",
        ".bat",
        ".cmd",
        ".com",
        ".pif",
        ".scr",
        ".vbs",
        ".js",
        ".jar",
        ".ps1",
        ".sh",
        ".php",
        ".asp",
        ".aspx",
        ".jsp",
        ".py",
        ".rb",
        ".pl",
        ".msi",
        ".deb",
        ".rpm",
        ".dmg",
        ".app",
        ".pkg",
        ".apk",
        ".ipa",
    }

    # 允许的文件类型
    ALLOWED_MIME_TYPES: set[str] = {
        # PDF文件
        "application/pdf",
        # Excel文件
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel.sheet.macroEnabled.12",
        # 图片文件
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        # 文本文件
        "text/plain",
        "text/csv",
        # 压缩文件
        "application/zip",
        "application/x-rar-compressed",
    }

    # 最大文件大小 (100MB)
    MAX_FILE_SIZE = 100 * 1024 * 1024

    def __init__(self):
        self.magic_mime = magic.Magic(mime=True)

    def validate_file_extension(self, filename: str) -> bool:
        """验证文件扩展名"""
        if not filename:
            return False

        ext = Path(filename).suffix.lower()
        return ext not in self.DANGEROUS_EXTENSIONS

    def validate_mime_type(self, file: UploadFile) -> bool:
        """验证MIME类型"""
        try:
            # 读取文件前几个字节来检测真实MIME类型
            content = file.file.read(1024)
            file.file.seek(0)  # 重置文件指针

            # 使用python-magic检测真实MIME类型
            detected_mime = self.magic_mime.from_buffer(content)

            return detected_mime in self.ALLOWED_MIME_TYPES
        except Exception:
            return False

    def validate_file_size(
        self, file: UploadFile, max_size: int | None = None
    ) -> bool:
        """验证文件大小"""
        try:
            file.file.seek(0, 2)  # 移动到文件末尾
            file_size = file.file.tell()
            file.file.seek(0)  # 重置文件指针

            limit = max_size or self.MAX_FILE_SIZE
            return file_size <= limit
        except Exception:
            return False

    def sanitize_filename(self, filename: str) -> str:
        """清理文件名"""
        if not filename:
            return f"file_{uuid.uuid4().hex[:8]}"

        # 移除路径分隔符和危险字符
        sanitized = re.sub(r'[<>:"/\\|?*]', "_", filename)
        sanitized = re.sub(r"\.{2,}", ".", sanitized)  # 防止目录遍历
        sanitized = sanitized.strip(". ")  # 移除开头结尾的点和空格

        # 如果文件名为空或只有扩展名，生成新的文件名
        if not sanitized or sanitized.startswith("."):
            ext = Path(filename).suffix
            sanitized = f"file_{uuid.uuid4().hex[:8]}{ext}"

        # 限制文件名长度
        if len(sanitized) > 255:
            ext = Path(sanitized).suffix
            name = sanitized[: 255 - len(ext)]
            sanitized = f"{name}{ext}"

        return sanitized

    def calculate_file_hash(self, file: UploadFile) -> str:
        """计算文件SHA256哈希值"""
        hasher = hashlib.sha256()

        file.file.seek(0)
        for chunk in iter(lambda: file.file.read(4096), b""):
            hasher.update(chunk)
        file.file.seek(0)

        return hasher.hexdigest()

    def scan_file_content(self, file: UploadFile) -> bool:
        """扫描文件内容是否包含恶意代码"""
        try:
            content = file.file.read(8192)  # 读取前8KB
            file.file.seek(0)

            # 检查常见的恶意代码模式
            malicious_patterns = [
                b"eval(",
                b"exec(",
                b"system(",
                b"shell_exec",
                b"passthru",
                b"<?php",
                b"<%",
                b"<script",
                b"javascript:",
                b"vbscript:",
            ]

            content_lower = content.lower()
            for pattern in malicious_patterns:
                if pattern in content_lower:
                    return False

            return True
        except Exception:
            return False

    def validate_file_path(self, upload_dir: str, filename: str) -> bool:
        """验证文件路径是否安全"""
        try:
            full_path = Path(upload_dir) / filename
            resolved_path = full_path.resolve()
            upload_dir_resolved = Path(upload_dir).resolve()

            # 确保文件在上传目录内
            return str(resolved_path).startswith(str(upload_dir_resolved))
        except Exception:
            return False

    async def comprehensive_validate(
        self,
        file: UploadFile,
        upload_dir: str,
        max_size: int | None = None,
        allowed_mime_types: set[str] | None = None,
    ) -> dict:
        """综合文件安全验证"""
        result = {
            "valid": False,
            "errors": [],
            "sanitized_filename": None,
            "file_hash": None,
            "detected_mime": None,
        }

        try:
            # 1. 验证文件名
            if not file.filename:
                result["errors"].append("文件名不能为空")
                return result

            if not self.validate_file_extension(file.filename):
                result["errors"].append(
                    f"不支持的文件类型: {Path(file.filename).suffix}"
                )
                return result

            # 2. 清理文件名
            sanitized_filename = self.sanitize_filename(file.filename)
            result["sanitized_filename"] = sanitized_filename

            # 3. 验证MIME类型
            allowed_types = allowed_mime_types or self.ALLOWED_MIME_TYPES
            if not self.validate_mime_type(file):
                result["errors"].append("文件类型验证失败")
                return result

            # 检测真实MIME类型
            file.file.seek(0)
            content = file.file.read(1024)
            file.file.seek(0)
            detected_mime = self.magic_mime.from_buffer(content)
            result["detected_mime"] = detected_mime

            if detected_mime not in allowed_types:
                result["errors"].append(f"不支持的MIME类型: {detected_mime}")
                return result

            # 4. 验证文件大小
            if not self.validate_file_size(file, max_size):
                limit = max_size or self.MAX_FILE_SIZE
                result["errors"].append(
                    f"文件大小超过限制: {limit / 1024 / 1024:.1f}MB"
                )
                return result

            # 5. 扫描文件内容
            if not self.scan_file_content(file):
                result["errors"].append("文件内容包含潜在恶意代码")
                return result

            # 6. 验证文件路径
            if not self.validate_file_path(upload_dir, sanitized_filename):
                result["errors"].append("文件路径不安全")
                return result

            # 7. 计算文件哈希
            file_hash = self.calculate_file_hash(file)
            result["file_hash"] = file_hash

            result["valid"] = True
            return result

        except Exception as e:
            result["errors"].append(f"验证过程中发生错误: {str(e)}")
            return result


# 全局验证器实例
enhanced_file_validator = EnhancedFileSecurityValidator()


async def secure_upload_file(
    file: UploadFile,
    upload_dir: str,
    max_size: int | None = None,
    allowed_mime_types: set[str] | None = None,
) -> dict:
    """
    安全上传文件

    Args:
        file: 上传的文件
        upload_dir: 上传目录
        max_size: 最大文件大小
        allowed_mime_types: 允许的MIME类型

    Returns:
        dict: 上传结果
    """
    result = {
        "success": False,
        "filename": None,
        "file_path": None,
        "file_size": None,
        "file_hash": None,
        "errors": [],
    }

    try:
        # 创建上传目录
        upload_path = Path(upload_dir)
        upload_path.mkdir(parents=True, exist_ok=True)

        # 综合验证
        validation_result = await enhanced_file_validator.comprehensive_validate(
            file, upload_dir, max_size, allowed_mime_types
        )

        if not validation_result["valid"]:
            result["errors"] = validation_result["errors"]
            return result

        # 生成唯一文件名
        file_ext = Path(validation_result["sanitized_filename"]).suffix
        unique_filename = f"{uuid.uuid4().hex}{file_ext}"
        file_path = upload_path / unique_filename

        # 保存文件
        file.file.seek(0)
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        result.update(
            {
                "success": True,
                "filename": unique_filename,
                "file_path": str(file_path),
                "file_size": file_path.stat().st_size,
                "file_hash": validation_result["file_hash"],
                "original_filename": validation_result["sanitized_filename"],
            }
        )

        return result

    except Exception as e:
        result["errors"].append(f"文件上传失败: {str(e)}")
        return result


# 使用示例
if __name__ == "__main__":
    # 测试代码
    pass
