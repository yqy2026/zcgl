"""
文件内容安全校验模块

通过 Magic Number 校验文件真实类型，防止恶意文件伪装上传。
"""

import logging
from typing import BinaryIO

from fastapi import HTTPException, UploadFile

logger = logging.getLogger(__name__)

# 常见文件类型的 Magic Number 签名
MAGIC_SIGNATURES: dict[str, list[bytes]] = {
    "application/pdf": [b"%PDF"],
    "image/png": [b"\x89PNG\r\n\x1a\n"],
    "image/jpeg": [b"\xff\xd8\xff"],
    "image/gif": [b"GIF87a", b"GIF89a"],
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [
        b"PK\x03\x04"
    ],  # xlsx (zip-based)
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [
        b"PK\x03\x04"
    ],  # docx (zip-based)
    "application/zip": [b"PK\x03\x04", b"PK\x05\x06"],
}

# MIME 类型别名映射
MIME_ALIASES: dict[str, str] = {
    "application/x-pdf": "application/pdf",
    "image/jpg": "image/jpeg",
}


def validate_file_magic(
    content: bytes,
    expected_mime: str,
    strict: bool = True,
) -> tuple[bool, str]:
    """
    通过 Magic Number 校验文件内容类型

    Args:
        content: 文件内容的前 2048 字节
        expected_mime: 期望的 MIME 类型
        strict: 严格模式下，未知类型会返回失败

    Returns:
        (is_valid, detected_mime_or_error)
    """
    # 处理 MIME 别名
    normalized_mime = MIME_ALIASES.get(expected_mime, expected_mime)

    # 检测实际文件类型
    detected_mime: str | None = None
    for mime_type, signatures in MAGIC_SIGNATURES.items():
        for sig in signatures:
            if content.startswith(sig):
                detected_mime = mime_type
                break
        if detected_mime:
            break

    if detected_mime is None:
        if strict:
            return False, "无法识别的文件格式"
        return True, "unknown"

    # 特殊处理：xlsx/docx/zip 都是 PK 开头，需要额外检查
    if detected_mime == "application/zip" and normalized_mime in [
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]:
        # xlsx 和 docx 本质上是 zip 文件，允许通过
        return True, normalized_mime

    if detected_mime != normalized_mime:
        return (
            False,
            f"文件内容与声明类型不符：期望 {normalized_mime}，检测到 {detected_mime}",
        )

    return True, detected_mime


async def validate_upload_file(
    file: UploadFile,
    expected_mime: str,
    raise_on_error: bool = True,
) -> bool:
    """
    校验上传文件的真实类型

    Args:
        file: FastAPI UploadFile 对象
        expected_mime: 期望的 MIME 类型
        raise_on_error: 校验失败时是否抛出 HTTPException

    Returns:
        校验是否通过
    """
    # 读取文件头用于校验
    header = await file.read(2048)
    await file.seek(0)  # 重置文件指针

    is_valid, result = validate_file_magic(header, expected_mime)

    if not is_valid:
        logger.warning(
            "文件类型校验失败: filename=%s, expected=%s, result=%s",
            file.filename,
            expected_mime,
            result,
        )
        if raise_on_error:
            raise HTTPException(status_code=400, detail=result)
        return False

    return True


def validate_file_content(
    file_handle: BinaryIO,
    expected_mime: str,
) -> tuple[bool, str]:
    """
    校验文件句柄的内容类型（同步版本）

    Args:
        file_handle: 文件句柄
        expected_mime: 期望的 MIME 类型

    Returns:
        (is_valid, detected_mime_or_error)
    """
    current_pos = file_handle.tell()
    header = file_handle.read(2048)
    file_handle.seek(current_pos)  # 恢复原位置

    return validate_file_magic(header, expected_mime)
