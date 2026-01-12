"""
Vision 服务基类和异常定义

提供所有 vision 服务共享的基类、异常类型和工具函数
"""

import base64
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)


# ============================================================================
# 自定义异常类型
# ============================================================================

class VisionAPIError(Exception):
    """
    Vision API 错误

    包含 HTTP 状态码和是否可重试的信息，帮助调用者做出更好的错误处理决策
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        retryable: bool = False,
        details: dict[str, Any] | None = None
    ):
        """
        初始化 Vision API 错误

        Args:
            message: 错误消息
            status_code: HTTP 状态码（如果有）
            retryable: 是否可重试
            details: 额外错误详情
        """
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable
        self.details = details or {}

    def __str__(self) -> str:
        base_msg = super().__str__()
        if self.status_code:
            base_msg = f"[HTTP {self.status_code}] {base_msg}"
        if self.retryable:
            base_msg += " (retryable)"
        return base_msg

    def to_dict(self) -> dict[str, Any]:
        """转换为字典，用于 API 响应"""
        return {
            "error": str(self),
            "error_code": f"HTTP_{self.status_code}" if self.status_code else "API_ERROR",
            "retryable": self.retryable,
            "suggested_action": "Retry later" if self.retryable else "Check API credentials or configuration",
            "details": self.details
        }


# ============================================================================
# Vision 服务基类
# ============================================================================

class BaseVisionService(ABC):
    """
    Vision 服务基类

    提供所有 vision 服务共享的工具方法：
    - 图像编码（base64）
    - MIME 类型检测
    """

    # MIME 类型映射表
    MIME_MAP = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
        ".tiff": "image/tiff",
        ".tif": "image/tiff",
    }

    def __init__(self, api_key: str | None = None):
        """
        初始化 vision 服务

        Args:
            api_key: API 密钥
        """
        self.api_key = api_key

    def _encode_image(self, image_path: str) -> str:
        """
        将图像文件编码为 base64 字符串

        Args:
            image_path: 图像文件路径

        Returns:
            str: base64 编码的图像数据

        Raises:
            FileNotFoundError: 文件不存在
            IOError: 读取文件失败
        """
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        if not path.is_file():
            raise ValueError(f"Path is not a file: {image_path}")

        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def _get_mime_type(self, image_path: str) -> str:
        """
        根据文件扩展名获取 MIME 类型

        Args:
            image_path: 图像文件路径

        Returns:
            str: MIME 类型（默认 "image/png"）
        """
        ext = Path(image_path).suffix.lower()
        return self.MIME_MAP.get(ext, "image/png")

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """
        检查服务是否可用

        Returns:
            bool: 服务是否可用
        """
        pass

    @abstractmethod
    async def extract_from_images(
        self,
        image_paths: list[str],
        prompt: str,
        **kwargs
    ) -> str:
        """
        从图像提取内容

        Args:
            image_paths: 图像文件路径列表
            prompt: 提取提示词
            **kwargs: 额外参数

        Returns:
            str: 提取结果（JSON 字符串）
        """
        pass


# ============================================================================
# HTTP 错误处理工具
# ============================================================================

def handle_http_status_error(error: httpx.HTTPStatusError) -> VisionAPIError:
    """
    将 HTTP 状态错误转换为 VisionAPIError

    Args:
        error: httpx.HTTPStatusError 异常

    Returns:
        VisionAPIError: 包含状态码和重试信息的异常
    """
    status = error.response.status_code

    # 确定是否可重试
    retryable = status in (
        408,  # Request Timeout
        429,  # Too Many Requests
        500,  # Internal Server Error
        502,  # Bad Gateway
        503,  # Service Unavailable
        504,  # Gateway Timeout
    )

    # 构建错误消息
    error_messages = {
        400: "Bad Request - Invalid parameters or request format",
        401: "Authentication failed - Invalid API key",
        403: "Forbidden - Insufficient permissions",
        404: "Not Found - Invalid endpoint or resource",
        408: "Request Timeout - Server took too long to respond",
        429: "Rate limit exceeded - Too many requests",
        500: "Internal Server Error - Server-side problem",
        502: "Bad Gateway - Upstream server error",
        503: "Service Unavailable - Server temporarily down",
        504: "Gateway Timeout - Upstream server timeout",
    }

    message = error_messages.get(status, f"HTTP {status} error")

    # 尝试从响应中获取更多详情
    details = {}
    try:
        response_json = error.response.json()
        if isinstance(response_json, dict):
            details = {"response": response_json}
    except Exception:
        pass

    return VisionAPIError(
        message=message,
        status_code=status,
        retryable=retryable,
        details=details
    )


def handle_network_error(error: Exception) -> VisionAPIError:
    """
    将网络错误转换为 VisionAPIError

    Args:
        error: 网络异常

    Returns:
        VisionAPIError: 可重试的网络错误
    """
    error_types = {
        httpx.ConnectError: "Connection failed - Could not reach server",
        httpx.RemoteProtocolError: "Protocol error - Invalid response from server",
        httpx.ReadTimeout: "Read timeout - Server took too long to respond",
        httpx.ConnectTimeout: "Connection timeout - Could not establish connection",
        TimeoutError: "Request timeout - Operation took too long",
        ConnectionError: "Connection error - Network problem",
    }

    error_type = type(error)
    message = error_types.get(error_type, f"Network error: {str(error)}")

    return VisionAPIError(
        message=message,
        status_code=None,
        retryable=True,  # 网络错误通常可以重试
        details={"original_error_type": error_type.__name__}
    )


# ============================================================================
# 验证工具
# ============================================================================

def validate_image_path(image_path: str) -> Path:
    """
    验证图像路径有效

    Args:
        image_path: 图像文件路径

    Returns:
        Path: 验证后的 Path 对象

    Raises:
        FileNotFoundError: 文件不存在
        ValueError: 不是文件或扩展名不支持
    """
    path = Path(image_path)

    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")

    if not path.is_file():
        raise ValueError(f"Path is not a file: {image_path}")

    # 检查扩展名
    ext = path.suffix.lower()
    if ext not in BaseVisionService.MIME_MAP and ext not in [".jpg", ".jpeg"]:
        logger.warning(f"Unusual image extension: {ext}")

    return path


def validate_image_paths(image_paths: list[str]) -> list[Path]:
    """
    批量验证图像路径

    Args:
        image_paths: 图像文件路径列表

    Returns:
        list[Path]: 验证后的 Path 对象列表

    Raises:
        ValueError: 任何路径无效
    """
    if not image_paths:
        raise ValueError("image_paths cannot be empty")

    validated_paths = []
    for path_str in image_paths:
        validated_paths.append(validate_image_path(path_str))

    return validated_paths
