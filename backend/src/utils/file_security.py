"""
文件安全工具
用于处理文件上传的安全验证和文件名安全化
"""

import os
import re
import uuid
from pathlib import Path
from typing import Any

from ..core.exception_handler import BusinessValidationError

# 危险的文件名字符
DANGEROUS_FILENAME_CHARS = r'[<>:"/\\|?*\x00-\x1f]'
DANGEROUS_PATH_PATTERNS = [
    r"\.\./",  # 路径遍历
    r"\.\.\\",  # Windows路径遍历
    r"^[A-Za-z]:",  # Windows驱动器路径
    r"//",  # 网络路径
    r"\\\\",  # Windows网络路径
]

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {
    # 图片文件
    "jpg",
    "jpeg",
    "png",
    "gif",
    "bmp",
    "webp",
    "svg",
    # 文档文件
    "pdf",
    "doc",
    "docx",
    "xls",
    "xlsx",
    "ppt",
    "pptx",
    "txt",
    "rtf",
    "odt",
    "ods",
    "odp",
    # 压缩文件
    "zip",
    "rar",
    "7z",
    "tar",
    "gz",
    "bz2",
    # 其他
    "csv",
    "json",
    "xml",
    "yaml",
    "yml",
}

# 危险的文件扩展名
DANGEROUS_EXTENSIONS = {
    "exe",
    "bat",
    "cmd",
    "com",
    "pif",
    "scr",
    "vbs",
    "js",
    "jar",
    "php",
    "asp",
    "aspx",
    "jsp",
    "sh",
    "ps1",
    "py",
    "rb",
    "pl",
    "msi",
    "deb",
    "rpm",
    "dmg",
    "app",
    "appimage",
}


def secure_filename(filename: str) -> str:
    """
    生成安全的文件名

    Args:
        filename: 原始文件名

    Returns:
        str: 安全的文件名
    """
    if not filename:
        return "unknown_file"

    # 获取文件名（不含路径）
    filename = os.path.basename(filename)

    # 移除危险字符
    filename = re.sub(DANGEROUS_FILENAME_CHARS, "_", filename)

    # 移除路径遍历模式
    for pattern in DANGEROUS_PATH_PATTERNS:
        filename = re.sub(pattern, "", filename)

    # 限制文件名长度
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        max_name_length = 255 - len(ext)
        filename = name[:max_name_length] + ext

    # 确保文件名不为空
    if not filename or filename in [".", ".."]:
        filename = f"file_{uuid.uuid4().hex[:8]}"

    return filename


def validate_file_extension(
    filename: str, allowed_extensions: list[str] | None = None
) -> bool:
    """
    验证文件扩展名是否安全

    Args:
        filename: 文件名
        allowed_extensions: 允许的扩展名列表，None表示使用默认允许列表

    Returns:
        bool: 是否安全
    """
    if not filename:
        return False

    # 获取扩展名（小写，不含点）
    _, ext = os.path.splitext(filename.lower())
    ext = ext.lstrip(".")

    if not ext:
        return False

    # 检查是否为危险扩展名
    if ext in DANGEROUS_EXTENSIONS:
        return False

    # 如果指定了允许的扩展名，检查是否在列表中
    if allowed_extensions is not None:
        return ext in [e.lower().lstrip(".") for e in allowed_extensions]

    # 否则使用默认允许列表
    return ext in ALLOWED_EXTENSIONS


def generate_safe_filename(
    original_filename: str,
    prefix: str = "",
    suffix: str = "",
    allowed_extensions: list[str] | None = None,
) -> str:
    """
    生成唯一的安全文件名

    🔒 安全增强:
    - 验证文件扩展名（防止双重扩展名攻击）
    - 清理prefix/suffix参数（防止注入）
    - 强制小写扩展名
    - 验证UUID安全性

    Args:
        original_filename: 原始文件名
        prefix: 文件名前缀（将被安全化）
        suffix: 文件名后缀（将被安全化）
        allowed_extensions: 允许的扩展名列表（默认只允许安全类型）

    Returns:
        str: 安全的唯一文件名

    Raises:
        ValueError: 如果文件扩展名不被允许
    """
    if not original_filename:
        raise BusinessValidationError(
            "文件名不能为空",
            field_errors={"filename": ["empty"]},
        )

    # 🔒 安全修复: 验证文件扩展名
    if not validate_file_extension(original_filename, allowed_extensions):
        _, ext = os.path.splitext(original_filename.lower())
        raise BusinessValidationError(
            f"不允许的文件扩展名: {ext}",
            field_errors={"extension": ["not_allowed"]},
        )

    # 获取文件扩展名（已验证过）
    name, ext = os.path.splitext(original_filename)

    # 🔒 安全修复: 清理prefix和suffix参数
    safe_prefix = secure_filename(prefix) if prefix else ""
    safe_suffix = secure_filename(suffix) if suffix else ""

    # 🔒 安全修复: 生成cryptographically安全的UUID
    unique_id = uuid.uuid4().hex

    # 构建新文件名
    parts = []
    if safe_prefix:
        parts.append(safe_prefix)
    parts.append(secure_filename(name))
    parts.append(unique_id[:16])  # 使用前16个字符（128位）
    if safe_suffix:
        parts.append(safe_suffix)

    # 🔒 安全修复: 强制小写扩展名，防止Windows双扩展名攻击
    ext = ext.lower()

    # 🔒 安全修复: 再次检查没有危险模式
    safe_name = "_".join(parts) + ext

    # 最终验证：确保生成的文件名安全
    if ".." in safe_name or "/" in safe_name or "\\" in safe_name:
        raise BusinessValidationError(
            f"生成的文件名不安全: {safe_name}",
            field_errors={"filename": ["unsafe"]},
        )

    return safe_name


def validate_file_path(file_path: str, allowed_directories: list[str]) -> bool:
    """
    验证文件路径是否安全（不在允许的目录之外）

    Args:
        file_path: 文件路径
        allowed_directories: 允许的目录列表

    Returns:
        bool: 路径是否安全
    """
    try:
        # 规范化路径
        normalized_path = os.path.normpath(os.path.abspath(file_path))

        # 检查路径是否在允许的目录中
        for allowed_dir in allowed_directories:
            allowed_abs = os.path.abspath(allowed_dir)
            if (
                normalized_path.startswith(allowed_abs + os.sep)
                or normalized_path == allowed_abs
            ):
                return True

        return False
    except (OSError, ValueError):
        return False


def create_safe_upload_directory(base_path: str, subfolder: str = "") -> Path:
    """
    创建安全的上传目录

    Args:
        base_path: 基础路径
        subfolder: 子文件夹名

    Returns:
        Path: 安全的目录路径
    """
    # 清理和验证路径
    safe_subfolder = secure_filename(subfolder) if subfolder else ""

    # 构建完整路径
    full_path = Path(base_path) / safe_subfolder if safe_subfolder else Path(base_path)

    # 创建目录
    full_path.mkdir(parents=True, exist_ok=True)

    return full_path


def sanitize_file_content(
    filename: str, content: bytes, max_size: int = 100 * 1024 * 1024
) -> bytes:
    """
    清理文件内容（移除潜在的恶意代码）

    Args:
        filename: 文件名
        content: 文件内容
        max_size: 最大文件大小（字节）

    Returns:
        bytes: 清理后的文件内容
    """
    # 检查文件大小
    if len(content) > max_size:
        raise BusinessValidationError(
            f"文件大小超过限制: {len(content)} > {max_size}",
            field_errors={"file_size": ["exceeds_limit"]},
        )

    # 获取文件扩展名
    _, ext = os.path.splitext(filename.lower())

    # 对于文本文件，可以进行内容清理
    if ext in [".txt", ".csv", ".json", ".xml", ".yaml", ".yml"]:
        try:
            # 尝试解码为文本
            text_content = content.decode("utf-8")

            # 移除潜在的恶意脚本标签
            text_content = re.sub(
                r"<script[^>]*>.*?</script>",
                "",
                text_content,
                flags=re.DOTALL | re.IGNORECASE,
            )
            text_content = re.sub(
                r"<iframe[^>]*>.*?</iframe>",
                "",
                text_content,
                flags=re.DOTALL | re.IGNORECASE,
            )
            text_content = re.sub(
                r"<object[^>]*>.*?</object>",
                "",
                text_content,
                flags=re.DOTALL | re.IGNORECASE,
            )
            text_content = re.sub(
                r"<embed[^>]*>", "", text_content, flags=re.IGNORECASE
            )

            # 重新编码
            return text_content.encode("utf-8")
        except UnicodeDecodeError:
            # 如果不是有效的UTF-8文本，返回原始内容
            pass

    return content


def validate_upload_file(
    filename: str,
    content_type: str | None,
    file_size: int,
    allowed_extensions: list[str] | None = None,
    max_size: int = 50 * 1024 * 1024,
) -> dict[str, Any]:
    """
    全面验证上传的文件

    Args:
        filename: 文件名
        content_type: MIME类型
        file_size: 文件大小
        allowed_extensions: 允许的扩展名列表
        max_size: 最大文件大小

    Returns:
        dict: 验证结果
    """
    result: dict[str, Any] = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "safe_filename": None,
    }

    # 验证文件名
    if not filename:
        result["valid"] = False
        result["errors"].append("文件名不能为空")
        return result

    # 生成安全文件名
    safe_filename = secure_filename(filename)
    result["safe_filename"] = safe_filename

    # 检查文件名是否被改变
    if safe_filename != filename:
        result["warnings"].append(f'文件名已从 "{filename}" 修改为 "{safe_filename}"')

    # 验证文件扩展名
    if not validate_file_extension(filename, allowed_extensions):
        result["valid"] = False
        result["errors"].append(f"不允许的文件类型: {filename}")
        return result

    # 验证文件大小
    if file_size > max_size:
        result["valid"] = False
        result["errors"].append(f"文件大小超过限制: {file_size} > {max_size}")
        return result

    # 验证MIME类型
    if content_type:
        _, ext = os.path.splitext(filename.lower())
        ext = ext.lstrip(".")

        # 常见的MIME类型映射
        mime_extensions = {
            "application/pdf": "pdf",
            "image/jpeg": "jpg",
            "image/png": "png",
            "image/gif": "gif",
            "text/plain": "txt",
            "application/json": "json",
            "text/csv": "csv",
        }

        if content_type in mime_extensions and mime_extensions[content_type] != ext:
            result["warnings"].append(
                f"MIME类型与文件扩展名不匹配: {content_type} vs {ext}"
            )

    return result


# 导出主要函数
__all__ = [
    "secure_filename",
    "validate_file_extension",
    "generate_safe_filename",
    "validate_file_path",
    "create_safe_upload_directory",
    "sanitize_file_content",
    "validate_upload_file",
]
