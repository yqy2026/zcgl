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
from threading import Lock
from time import time
from typing import Any

logger = logging.getLogger(__name__)

# magic模块的条件导入
try:
    import magic

    MAGIC_AVAILABLE = True
except ImportError:
    magic = None
    MAGIC_AVAILABLE = False
    logger.warning("python-magic模块不可用，文件类型检测功能将受限")

from fastapi import Depends, Request, UploadFile
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..core.config import get_config
from ..core.exception_handler import (
    BusinessValidationError,
    InvalidRequestError,
    PermissionDeniedError,
    RateLimitError,
)
from ..crud.field_whitelist import get_whitelist_for_model
from ..models.asset import Asset
from ..models.contact import Contact
from ..models.organization import Organization
from ..models.rent_contract import RentContract
from .logging_security import security_auditor


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
        "pdf": 50 * 1024 * 1024,  # 50MB
        "excel": 100 * 1024 * 1024,  # 100MB
        "image": 20 * 1024 * 1024,  # 20MB
        "default": 10 * 1024 * 1024,  # 10MB
        "zip": 200 * 1024 * 1024,  # 200MB
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

            # 读取文件内容进行安全检查（限制读取大小）
            file_content = file.file.read(1024 * 1024)  # 读取前1MB
            file.file.seek(original_position)  # 重置文件指针

            # 检查恶意文件特征
            for signature in self.config.MALICIOUS_SIGNATURES:
                if signature in file_content.lower():
                    raise BusinessValidationError(
                        "检测到可疑文件内容",
                        details={"signature": signature.decode("utf-8", errors="ignore")},
                    )

            # 额外检查：文件内容是否为空
            if len(file_content) == 0:
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


class RateLimitConfig:
    """速率限制配置"""

    # 默认限制配置
    DEFAULT_LIMITS = {
        "api": {"requests": 1000, "window": 3600},  # 1000次/小时
        "upload": {"requests": 50, "window": 3600},  # 50次/小时
        "auth": {"requests": 10, "window": 300},  # 10次/5分钟
        "search": {"requests": 100, "window": 3600},  # 100次/小时
    }

    # IP白名单（无限制）
    WHITELIST_IPS: set[str] = set()

    # IP黑名单（完全封禁）
    BLACKLIST_IPS: set[str] = set()

    # 自动封禁阈值
    AUTO_BLOCK_THRESHOLD = 100

    # 自动封禁持续时间（秒）
    AUTO_BLOCK_DURATION = 3600


class RateLimiter:
    """基础速率限制器"""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or RateLimitConfig.DEFAULT_LIMITS
        self.request_times: dict[str, deque] = defaultdict(deque)
        self.blocked_ips: dict[str, float] = {}
        self.lock = Lock()

    def _get_limit_config(self, endpoint: str) -> dict[str, int]:
        """获取端点限制配置"""
        return self.config.get(endpoint, self.config["api"])

    def check_rate_limit(self, client_ip: str, endpoint: str = "api") -> bool:
        """检查速率限制"""
        if client_ip in RateLimitConfig.WHITELIST_IPS:
            return True

        if client_ip in RateLimitConfig.BLACKLIST_IPS:
            return False

        current_time = time()

        with self.lock:
            # 检查自动封禁
            if client_ip in self.blocked_ips:
                if current_time - self.blocked_ips[client_ip] < RateLimitConfig.AUTO_BLOCK_DURATION:
                    return False
                else:
                    del self.blocked_ips[client_ip]

            # 获取限制配置
            limit_config = self._get_limit_config(endpoint)
            max_requests = limit_config["requests"]
            window = limit_config["window"]

            # 清理过期请求记录
            request_queue = self.request_times[client_ip]
            while request_queue and current_time - request_queue[0] > window:
                request_queue.popleft()

            # 检查是否超过限制
            if len(request_queue) >= max_requests:
                # 检查是否需要自动封禁
                if len(request_queue) >= RateLimitConfig.AUTO_BLOCK_THRESHOLD:
                    self.blocked_ips[client_ip] = current_time
                    security_auditor.log_security_event(
                        event_type="IP_AUTO_BLOCKED",
                        message=f"IP auto-blocked due to excessive requests: {client_ip}",
                        details={
                            "ip": client_ip,
                            "request_count": len(request_queue),
                            "threshold": RateLimitConfig.AUTO_BLOCK_THRESHOLD,
                        },
                    )
                return False

            # 记录请求
            request_queue.append(current_time)
            return True


class TokenBucketRateLimiter:
    """令牌桶限流器"""

    def __init__(self, rate: float = 10.0, capacity: int = 100) -> None:
        self.rate = rate  # 令牌生成速率 (tokens/sec)
        self.capacity = capacity  # 桶容量
        self.tokens = capacity  # 当前令牌数
        self.last_update = time()
        self.lock = Lock()

    def allow_request(self) -> bool:
        """检查是否允许请求"""
        with self.lock:
            now = time()
            # 计算新增令牌
            elapsed = now - self.last_update
            new_tokens = elapsed * self.rate
            self.tokens = min(self.capacity, self.tokens + new_tokens)
            self.last_update = now

            if self.tokens >= 1:
                self.tokens -= 1
                return True

            return False


class AdaptiveRateLimiter:
    """自适应速率限制器"""

    def __init__(self) -> None:
        self.config = get_config("adaptive_rate_limit", {})
        self.request_stats: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "errors": 0, "last_reset": time()}
        )
        self.lock = Lock()

    def check_rate_limit(self, client_ip: str) -> bool:
        """基于错误率的自适应限流"""
        with self.lock:
            stats = self.request_stats[client_ip]
            current_time = time()

            # 每分钟重置统计
            if current_time - stats["last_reset"] > 60:
                stats["count"] = 0
                stats["errors"] = 0
                stats["last_reset"] = current_time

            stats["count"] += 1

            # 计算错误率
            error_rate = (
                stats["errors"] / stats["count"] if stats["count"] > 0 else 0
            )

            # 如果错误率过高，限制请求
            max_error_rate = self.config.get("max_error_rate", 0.3)
            if error_rate > max_error_rate:
                return False

            return True

    def record_error(self, client_ip: str) -> None:
        """记录错误"""
        with self.lock:
            self.request_stats[client_ip]["errors"] += 1


class RequestLimiter:
    """请求限制器"""

    def __init__(self) -> None:
        self.config = get_config("request_limit", {})
        self.request_counts: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "last_reset": time()}
        )
        self.lock = Lock()

    def check_request_limit(self, key: str) -> bool:
        """检查请求限制"""
        with self.lock:
            current_time = time()
            request_info = self.request_counts[key]

            # 每分钟重置
            if current_time - request_info["last_reset"] > 60:
                request_info["count"] = 0
                request_info["last_reset"] = current_time

            request_info["count"] += 1

            # 获取限制配置
            max_requests = self.config.get("max_requests_per_minute", 100)

            return request_info["count"] <= max_requests


class IPBlacklistManager:
    """IP黑名单管理器"""

    def __init__(self) -> None:
        self.config = get_config("ip_blacklist", {})
        self.blacklist: set[str] = set(self.config.get("blacklist", []))
        self.auto_block_enabled = self.config.get("auto_block_enabled", True)
        self.auto_block_threshold = self.config.get("auto_block_threshold", 10)
        self.auto_block_duration = self.config.get("auto_block_duration", 3600)
        self.blocked_ips: dict[str, float] = {}
        self.suspicious_ips: dict[str, int] = defaultdict(int)
        self.lock = Lock()

    def is_blacklisted(self, ip: str) -> bool:
        """检查IP是否在黑名单中"""
        with self.lock:
            if ip in self.blacklist:
                return True

            if ip in self.blocked_ips:
                # 检查封禁是否过期
                if time() - self.blocked_ips[ip] < self.auto_block_duration:
                    return True
                else:
                    del self.blocked_ips[ip]

            return False

    def add_to_blacklist(self, ip: str) -> None:
        """添加IP到黑名单"""
        with self.lock:
            self.blacklist.add(ip)
            self.config["blacklist"] = list(self.blacklist)

    def remove_from_blacklist(self, ip: str) -> None:
        """从黑名单移除IP"""
        with self.lock:
            self.blacklist.discard(ip)
            self.config["blacklist"] = list(self.blacklist)

    def report_suspicious_activity(self, ip: str) -> None:
        """报告可疑活动"""
        with self.lock:
            self.suspicious_ips[ip] += 1
            if (
                self.auto_block_enabled
                and self.suspicious_ips[ip] >= self.auto_block_threshold
            ):
                self.blocked_ips[ip] = time()
                security_auditor.log_security_event(
                    event_type="IP_AUTO_BLOCKED",
                    message=f"IP auto-blocked due to suspicious activity: {ip}",
                    details={
                        "ip": ip,
                        "suspicious_count": self.suspicious_ips[ip],
                        "threshold": self.auto_block_threshold,
                    },
                )


class SecurityAnalyzer:
    """安全分析器"""

    def __init__(self) -> None:
        self.config = get_config("security_analysis", {})
        self.suspicious_patterns = [
            r"<script",
            r"javascript:",
            r"vbscript:",
            r"onload=",
            r"onerror=",
            r"document\.cookie",
            r"eval\(",
            r"alert\(",
            r"window\.",
            r"select\s+.*\s+from",
            r"union\s+select",
            r"drop\s+table",
            r"delete\s+from",
            r"insert\s+into",
            r"update\s+.*\s+set",
        ]
        self.suspicious_ips: dict[str, int] = defaultdict(int)
        self.blocked_ips: dict[str, float] = {}
        self.lock = Lock()

    def analyze_request(self, request: Request) -> bool:
        """分析请求是否安全"""
        client_ip = request.client.host if request.client else "unknown"

        # 检查IP是否被封禁
        if client_ip in self.blocked_ips:
            if time() - self.blocked_ips[client_ip] < 3600:  # 1小时封禁
                return False
            else:
                del self.blocked_ips[client_ip]

        # 检查请求路径和参数
        request_data = str(request.url) + str(request.query_params)

        # 检查可疑模式
        for pattern in self.suspicious_patterns:
            if re.search(pattern, request_data, re.IGNORECASE):
                self._report_suspicious_activity(client_ip, pattern)
                return False

        return True

    def _report_suspicious_activity(self, ip: str, pattern: str) -> None:
        """报告可疑活动"""
        self.suspicious_ips[ip] += 1
        if self.suspicious_ips[ip] >= self.config.get("max_suspicious_requests", 5):
            self._block_ip(ip)

        security_auditor.log_security_event(
            event_type="SUSPICIOUS_REQUEST",
            message=f"Suspicious request pattern detected: {pattern}",
            details={
                "ip": ip,
                "pattern": pattern,
                "suspicious_count": self.suspicious_ips[ip],
            },
        )

    def _block_ip(self, ip: str) -> None:
        """封禁IP"""
        self.blocked_ips[ip] = time()
        security_auditor.log_security_event(
            event_type="IP_BLOCKED",
            message=f"IP blocked due to suspicious activity: {ip}",
            details={
                "ip": ip,
                "suspicious_count": self.suspicious_ips[ip],
                "block_time": time(),
            },
        )

    def report_suspicious_activity(self, key: str) -> None:
        """报告可疑活动"""
        self.suspicious_ips[key] += 1
        if self.suspicious_ips[key] >= self.config.get("max_suspicious_requests", 5):
            self._block_ip(key)


token_bucket_limiter = TokenBucketRateLimiter()
adaptive_limiter = AdaptiveRateLimiter()


class SecurityMiddleware:
    """安全中间件"""

    def __init__(self) -> None:
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
        client_ip = request.client.host if request.client else "unknown"

        # 检查IP黑名单
        if self._is_ip_blacklisted(client_ip):
            raise PermissionDeniedError("IP地址已被封禁")

        # 检查请求频率限制
        if not self.rate_limiter.check_rate_limit(client_ip):
            raise RateLimitError("请求过于频繁，请稍后重试")

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
        self,
        file: UploadFile,
        allowed_types: list[str] | None = None,
        max_size: int | None = None,
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
        # 确保参数有默认值
        if allowed_types is None:
            allowed_types = []
        if max_size is None:
            max_size = 0

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
            return "javascript:" not in url.lower()

        except Exception:
            return False


MODEL_REGISTRY: dict[str, type] = {
    "Asset": Asset,
    "RentContract": RentContract,
    "Organization": Organization,
    "Contact": Contact,
}


class FieldValidator:
    """
    统一的字段验证器

    Prevents arbitrary field access attacks by validating all field names
    against model-specific whitelists before allowing database queries.
    """

    @staticmethod
    def _get_model_class(model_name: str) -> type:
        """
        根据模型名称获取模型类

        Args:
            model_name: 模型名称

        Returns:
            type: 模型类
        """
        model_class = MODEL_REGISTRY.get(model_name)
        if not model_class:
            raise InvalidRequestError(
                f"未知的模型: {model_name}",
                model_name=model_name,
                details={"available_models": list(MODEL_REGISTRY.keys())},
            )

        return model_class

    @staticmethod
    def validate_field(
        model_name: str, field: str, raise_on_invalid: bool = True
    ) -> bool:
        """
        验证字段是否允许查询

        Args:
            model_name: 模型名称
            field: 字段名
            raise_on_invalid: 是否在无效时抛出异常

        Returns:
            bool: 字段是否有效
        """
        model_class = FieldValidator._get_model_class(model_name)
        whitelist = get_whitelist_for_model(model_class)

        is_valid = whitelist.can_filter(field)

        if not is_valid and raise_on_invalid:
            logger.warning(
                f"Blocked attempt to filter by unauthorized field: {field} "
                f"for model {model_name}"
            )
            raise InvalidRequestError(
                f"不允许按字段查询: {field}",
                field=field,
                details={
                    "error": "Invalid filter field",
                },
            )

        return is_valid

    @staticmethod
    def validate_sort_field(
        model_name: str, field: str, raise_on_invalid: bool = True
    ) -> bool:
        """
        验证排序字段是否允许

        Args:
            model_name: 模型名称
            field: 排序字段
            raise_on_invalid: 是否在无效时抛出异常

        Returns:
            bool: 字段是否有效
        """
        model_class = FieldValidator._get_model_class(model_name)
        whitelist = get_whitelist_for_model(model_class)

        is_valid = whitelist.can_sort(field)

        if not is_valid and raise_on_invalid:
            logger.warning(
                f"Blocked attempt to sort by unauthorized field: {field} "
                f"for model {model_name}"
            )
            raise InvalidRequestError(
                f"不允许按字段排序: {field}",
                field=field,
                details={
                    "error": "Invalid sort field",
                },
            )

        return is_valid

    @staticmethod
    def validate_search_field(
        model_name: str, field: str, raise_on_invalid: bool = True
    ) -> bool:
        """
        验证搜索字段是否允许

        Args:
            model_name: 模型名称
            field: 搜索字段
            raise_on_invalid: 是否在无效时抛出异常

        Returns:
            bool: 字段是否有效
        """
        model_class = FieldValidator._get_model_class(model_name)
        whitelist = get_whitelist_for_model(model_class)

        is_valid = whitelist.can_search(field)

        if not is_valid and raise_on_invalid:
            logger.warning(
                f"Blocked attempt to search by unauthorized field: {field} "
                f"for model {model_name}"
            )
            raise InvalidRequestError(
                f"不允许按字段搜索: {field}",
                field=field,
                details={
                    "error": "Invalid search field",
                },
            )

        return is_valid

    @staticmethod
    def validate_group_by_field(
        model_name: str, field: str, raise_on_invalid: bool = True
    ) -> bool:
        """
        验证分组字段是否允许

        Args:
            model_name: 模型名称
            field: Group by 字段
            raise_on_invalid: 是否在无效时抛出异常

        Returns:
            bool: 字段是否有效
        """
        model_class = FieldValidator._get_model_class(model_name)
        whitelist = get_whitelist_for_model(model_class)

        is_valid = whitelist.can_filter(field)

        if not is_valid and raise_on_invalid:
            logger.warning(
                f"Blocked attempt to group by unauthorized field: {field} "
                f"for model {model_name}"
            )
            raise InvalidRequestError(
                f"不允许按字段分组: {field}",
                field=field,
                details={
                    "error": "Invalid group_by field",
                },
            )

        return is_valid


# 创建全局实例
security_middleware = SecurityMiddleware()
request_security = RequestSecurity()


# FastAPI依赖注入
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
) -> None:
    """获取当前用户"""
    # 这里可以实现JWT验证或其他身份验证逻辑
    pass


async def validate_file_upload_dependency(
    file: UploadFile,
    allowed_types: list[str] | None = None,
    max_size: int | None = None,
) -> dict[str, Any]:
    """文件上传验证依赖"""
    return await security_middleware.validate_file_upload(file, allowed_types, max_size)
