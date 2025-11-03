from typing import Any

"""
文件验证和安全模块
提供文件上传验证、请求限制和安全防护功能
"""

import hashlib
import logging
import re
from collections import defaultdict, deque
from datetime import UTC, datetime
from pathlib import Path
from time import time

import magic
from fastapi import Depends, HTTPException, Request, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..core.config_manager import get_config
from ..core.exception_handler import BusinessValidationError
from ..core.logging_security import security_auditor

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
    }

    # 文件大小限制（字节）
    MAX_FILE_SIZES = {
        "pdf": 50 * 1024 * 1024,  # 50MB
        "excel": 100 * 1024 * 1024,  # 100MB
        "image": 20 * 1024 * 1024,  # 20MB
        "default": 10 * 1024 * 1024,  # 10MB
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
    ]


class FileValidator:
    """文件验证器"""

    def __init__(self):
        self.config = FileValidationConfig()
        self.logger = logging.getLogger(__name__)

    def validate_file_type(
        self, file: UploadFile, allowed_types: list[str] = None
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

            # 读取文件前1024字节用于MIME类型检测（限制读取大小）
            file_content = file.file.read(1024)
            file.file.seek(original_position)  # 重置文件指针到原始位置

            detected_mime = magic.from_buffer(file_content, mime=True)

            if detected_mime not in allowed_types:
                raise BusinessValidationError(
                    f"不支持的文件类型: {detected_mime}",
                    details={"allowed_types": allowed_types},
                )

            # 验证扩展名与MIME类型匹配
            expected_ext = self.config.ALLOWED_MIME_TYPES.get(detected_mime, "")
            if expected_ext and file_ext not in expected_ext.split(","):
                raise BusinessValidationError(
                    f"文件扩展名与实际类型不匹配: {file_ext} != {expected_ext}",
                    details={
                        "detected_mime": detected_mime,
                        "expected_ext": expected_ext,
                    },
                )

        except Exception as e:
            if isinstance(e, BusinessValidationError):
                raise
            raise BusinessValidationError(
                f"文件类型验证失败: {str(e)}", details={"filename": file.filename}
            )

        return True

    def validate_file_size(self, file: UploadFile, max_size: int = None) -> bool:
        """
        验证文件大小

        Args:
            file: 上传的文件
            max_size: 最大文件大小（字节）

        Returns:
            bool: 验证是否通过
        """
        if max_size is None:
            # 根据文件类型确定最大大小
            file_ext = Path(file.filename or "").suffix.lower()
            if file_ext in [".pdf"]:
                max_size = self.config.MAX_FILE_SIZES["pdf"]
            elif file_ext in [".xlsx", ".xls", ".csv"]:
                max_size = self.config.MAX_FILE_SIZES["excel"]
            elif file_ext in [".jpg", ".jpeg", ".png", ".tiff", ".tif"]:
                max_size = self.config.MAX_FILE_SIZES["image"]
            else:
                max_size = self.config.MAX_FILE_SIZES["default"]

        # 检查文件大小
        if file.size and file.size > max_size:
            max_size_mb = max_size / (1024 * 1024)
            raise BusinessValidationError(
                f"文件过大: {file.size / (1024 * 1024):.2f}MB > {max_size_mb}MB",
                details={"max_size_bytes": max_size, "file_size_bytes": file.size},
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

    def scan_for_malicious_content(self, file: UploadFile) -> bool:
        """
        扫描文件恶意内容

        Args:
            file: 上传的文件

        Returns:
            bool: 扫描是否通过
        """
        try:
            # 保存当前位置
            original_position = file.file.tell()

            # 使用流式读取进行恶意软件扫描，避免内存耗尽
            max_scan_size = 10 * 1024 * 1024  # 限制扫描前10MB
            chunk_size = 8192  # 8KB chunks
            scanned_data = b""
            bytes_scanned = 0

            while bytes_scanned < max_scan_size:
                chunk = file.file.read(min(chunk_size, max_scan_size - bytes_scanned))
                if not chunk:
                    break

                scanned_data += chunk
                bytes_scanned += len(chunk)

                # 检查恶意签名（只扫描小签名）
                for signature in self.config.MALICIOUS_SIGNATURES:
                    if signature in chunk.lower():
                        raise BusinessValidationError(
                            "检测到可能的恶意内容",
                            details={
                                "malicious_signature": signature.decode(
                                    "utf-8", errors="ignore"
                                )
                            },
                        )

            # 重置文件指针
            file.file.seek(original_position)

            return True

        except Exception as e:
            if isinstance(e, BusinessValidationError):
                raise
            raise BusinessValidationError(f"恶意内容扫描失败: {str(e)}")

    def calculate_file_hash(self, file: UploadFile) -> str:
        """
        计算文件哈希值

        Args:
            file: 上传的文件

        Returns:
            str: 文件的SHA256哈希值
        """
        hash_sha256 = hashlib.sha256()

        # 分块读取文件以避免内存问题
        file.file.seek(0)
        for chunk in iter(lambda: file.file.read(4096), b""):
            hash_sha256.update(chunk)
        file.file.seek(0)

        return hash_sha256.hexdigest()

    def validate_upload(
        self, file: UploadFile, allowed_types: list[str] = None, max_size: int = None
    ) -> dict[str, Any]:
        """
        执行完整的文件上传验证

        Args:
            file: 上传的文件
            allowed_types: 允许的文件类型列表
            max_size: 最大文件大小（字节）

        Returns:
            Dict: 验证结果
        """
        try:
            # 验证文件名
            self.validate_filename(file.filename or "")

            # 验证文件类型
            self.validate_file_type(file, allowed_types)

            # 验证文件大小
            self.validate_file_size(file, max_size)

            # 扫描恶意内容
            self.scan_for_malicious_content(file)

            # 计算文件哈希
            file_hash = self.calculate_file_hash(file)

            validation_result = {
                "valid": True,
                "filename": file.filename,
                "size": file.size,
                "hash": file_hash,
                "validation_time": datetime.now(UTC).isoformat(),
            }

            # 记录安全审计
            security_auditor.log_security_event(
                event_type="FILE_VALIDATION_SUCCESS",
                message=f"File validation successful: {file.filename}",
                details=validation_result,
            )

            return validation_result

        except BusinessValidationError as e:
            # 记录验证失败
            security_auditor.log_security_event(
                event_type="FILE_VALIDATION_FAILED",
                message=f"File validation failed: {file.filename} - {str(e)}",
                details={
                    "filename": file.filename,
                    "error": str(e),
                    "validation_time": datetime.now(UTC).isoformat(),
                },
            )
            raise


class RateLimiter:
    """请求频率限制器"""

    def __init__(self):
        self.requests = defaultdict(deque)
        self.config = get_config("rate_limit", {})
        self.logger = logging.getLogger(__name__)

    def check_rate_limit(
        self, key: str, max_requests: int = None, time_window: int = None
    ) -> bool:
        """
        检查请求频率限制

        Args:
            key: 限制键（如IP地址或用户ID）
            max_requests: 最大请求数
            time_window: 时间窗口（秒）

        Returns:
            bool: 是否允许请求
        """
        if max_requests is None:
            max_requests = self.config.get("max_requests", 100)
        if time_window is None:
            time_window = self.config.get("time_window", 60)

        current_time = time()
        request_queue = self.requests[key]

        # 清理过期的请求记录
        while request_queue and request_queue[0] <= current_time - time_window:
            request_queue.popleft()

        # 检查是否超过限制
        if len(request_queue) >= max_requests:
            security_auditor.log_security_event(
                event_type="RATE_LIMIT_EXCEEDED",
                message=f"Rate limit exceeded for {key}: {len(request_queue)}/{max_requests}",
                details={
                    "key": key,
                    "request_count": len(request_queue),
                    "max_requests": max_requests,
                    "time_window": time_window,
                },
            )
            return False

        # 记录新请求
        request_queue.append(current_time)
        return True

    def get_remaining_requests(
        self, key: str, max_requests: int = None, time_window: int = None
    ) -> int:
        """
        获取剩余请求数

        Args:
            key: 限制键
            max_requests: 最大请求数
            time_window: 时间窗口（秒）

        Returns:
            int: 剩余请求数
        """
        if max_requests is None:
            max_requests = self.config.get("max_requests", 100)
        if time_window is None:
            time_window = self.config.get("time_window", 60)

        current_time = time()
        request_queue = self.requests[key]

        # 清理过期的请求记录
        while request_queue and request_queue[0] <= current_time - time_window:
            request_queue.popleft()

        return max(0, max_requests - len(request_queue))


class SecurityMiddleware:
    """安全中间件"""

    def __init__(self):
        self.rate_limiter = RateLimiter()
        self.file_validator = FileValidator()
        self.config = get_config("security", {})
        self.logger = logging.getLogger(__name__)

    async def validate_request(self, request: Request) -> bool:
        """
        验证请求安全性

        Args:
            request: FastAPI请求对象

        Returns:
            bool: 验证是否通过
        """
        # 获取客户端IP
        client_ip = request.client.host

        # 检查IP黑名单
        if self._is_ip_blacklisted(client_ip):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="IP地址已被封禁"
            )

        # 检查请求频率限制
        if not self.rate_limiter.check_rate_limit(client_ip):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="请求过于频繁，请稍后重试",
            )

        # 检查User-Agent
        user_agent = request.headers.get("User-Agent", "")
        if not user_agent or len(user_agent) < 10:
            security_auditor.log_security_event(
                event_type="SUSPICIOUS_USER_AGENT",
                message=f"Suspicious User-Agent from {client_ip}: '{user_agent}'",
                ip_address=client_ip,
                details={"user_agent": user_agent},
            )

        return True

    def _is_ip_blacklisted(self, ip: str) -> bool:
        """检查IP是否在黑名单中"""
        blacklist = self.config.get("ip_blacklist", [])
        return ip in blacklist

    async def validate_file_upload(
        self, file: UploadFile, allowed_types: list[str] = None, max_size: int = None
    ) -> dict[str, Any]:
        """
        验证文件上传

        Args:
            file: 上传的文件
            allowed_types: 允许的文件类型
            max_size: 最大文件大小

        Returns:
            Dict: 验证结果
        """
        return self.file_validator.validate_upload(file, allowed_types, max_size)


class RequestSecurity:
    """请求安全工具类"""

    @staticmethod
    def sanitize_input(input_data: str) -> str:
        """
        清理输入数据

        Args:
            input_data: 输入字符串

        Returns:
            str: 清理后的字符串
        """
        if not isinstance(input_data, str):
            return input_data

        # 移除潜在的危险字符
        sanitized = re.sub(r'[<>"\'&]', "", input_data)

        # 防止SQL注入
        sanitized = re.sub(
            r"(\s|^)(select|insert|update|delete|drop|alter|exec|script)\s",
            "",
            sanitized,
            flags=re.IGNORECASE,
        )

        return sanitized.strip()

    @staticmethod
    def validate_email(email: str) -> bool:
        """验证邮箱格式"""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return re.match(pattern, email) is not None

    @staticmethod
    def validate_phone(phone: str) -> bool:
        """验证手机号格式"""
        pattern = r"^1[3-9]\d{9}$"
        return re.match(pattern, phone) is not None

    @staticmethod
    def is_safe_url(url: str) -> bool:
        """
        检查URL是否安全

        Args:
            url: 要检查的URL

        Returns:
            bool: URL是否安全
        """
        try:
            # 检查URL协议
            if not url.startswith(("http://", "https://")):
                return False

            # 检查是否包含危险字符
            dangerous_chars = [
                "<",
                ">",
                '"',
                "'",
                "#",
                "%",
                "{",
                "}",
                "|",
                "\\",
                "^",
                "`",
            ]
            if any(char in url for char in dangerous_chars):
                return False

            # 检查JavaScript协议
            if "javascript:" in url.lower():
                return False

            return True

        except Exception:
            return False


# 创建全局实例
security_middleware = SecurityMiddleware()
request_security = RequestSecurity()


# FastAPI依赖注入
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
):
    """获取当前用户"""
    # 这里可以实现JWT验证或其他身份验证逻辑
    pass


async def validate_file_upload_dependency(
    file: UploadFile, allowed_types: list[str] = None, max_size: int = None
) -> dict[str, Any]:
    """文件上传验证依赖"""
    return await security_middleware.validate_file_upload(file, allowed_types, max_size)
