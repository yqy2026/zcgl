#!/usr/bin/env python3
"""
OCR 服务提供者
统一的 OCR 服务访问接口，支持优雅降级

依赖安装: uv sync --extra pdf-ocr
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# 使用项目的 safe_import 机制
try:
    from ...core.import_utils import safe_import
except ImportError:
    # 回退到标准导入
    def safe_import(module_path: str, **kwargs):
        import importlib

        try:
            return importlib.import_module(module_path)
        except ImportError:
            return None


class OCRProvider:
    """
    OCR 服务提供者
    统一管理不同的 OCR 服务实现
    """

    def __init__(self):
        self._service = None
        self._service_type = None
        self._initialize_service()

    def _initialize_service(self):
        """初始化可用的 OCR 服务"""
        # 优先尝试 PaddleOCR (功能最完整)
        paddleocr_available = safe_import("paddleocr", critical=False) is not None

        if paddleocr_available:
            try:
                from ..document.paddleocr_service import get_paddleocr_service

                self._service = get_paddleocr_service()
                self._service_type = "paddleocr"
                if self._service.is_available:
                    logger.info("OCR 服务已就绪: PaddleOCR")
                else:
                    logger.warning("PaddleOCR 导入成功但服务不可用，可能需要额外依赖")
                    self._service = None
            except Exception as e:
                logger.warning(f"PaddleOCR 初始化失败: {e}")
                self._service = None

        # 如果 PaddleOCR 不可用，记录警告
        if self._service is None:
            logger.warning(
                "OCR 服务当前不可用。PDF 处理功能将受限。"
                "安装方法: uv sync --extra pdf-ocr"
            )
            self._service_type = "none"

    @property
    def is_available(self) -> bool:
        """检查 OCR 服务是否可用"""
        return (
            self._service is not None
            and hasattr(self._service, "is_available")
            and self._service.is_available
        )

    @property
    def service_type(self) -> str:
        """获取当前使用的 OCR 服务类型"""
        return self._service_type

    def get_service(self) -> Any | None:
        """
        获取 OCR 服务实例

        Returns:
            OCR 服务实例，如果不可用则返回 None
        """
        return self._service

    def reinitialize(self) -> bool:
        """
        重新初始化 OCR 服务（用于依赖安装后重新加载）

        Returns:
            bool: 初始化是否成功
        """
        self._service = None
        self._service_type = None
        self._initialize_service()
        return self.is_available


# 全局 OCR 服务实例
_ocr_provider_instance: OCRProvider | None = None


def get_ocr_service() -> Any | None:
    """
    获取 OCR 服务实例（兼容旧接口）

    Returns:
        OCR 服务实例，如果不可用则返回 None
    """
    global _ocr_provider_instance

    if _ocr_provider_instance is None:
        _ocr_provider_instance = OCRProvider()

    return _ocr_provider_instance.get_service()


def get_ocr_provider() -> OCRProvider:
    """
    获取 OCR 提供者实例（新接口，提供更多信息）

    Returns:
        OCRProvider 实例
    """
    global _ocr_provider_instance

    if _ocr_provider_instance is None:
        _ocr_provider_instance = OCRProvider()

    return _ocr_provider_instance


def set_ocr_service(service: Any) -> None:
    """
    设置 OCR 服务实例（用于测试或自定义服务）

    Args:
        service: 自定义 OCR 服务实例
    """
    global _ocr_provider_instance

    # 创建一个新的 provider 并设置自定义服务
    provider = OCRProvider()
    provider._service = service
    provider._service_type = "custom"
    _ocr_provider_instance = provider


def get_current_ocr_service() -> Any | None:
    """
    获取当前 OCR 服务实例（兼容旧接口）

    Returns:
        OCR 服务实例，如果不可用则返回 None
    """
    return get_ocr_service()


def set_current_ocr_service(service: Any) -> None:
    """
    设置当前 OCR 服务实例（兼容旧接口）

    Args:
        service: 自定义 OCR 服务实例
    """
    set_ocr_service(service)


# 便捷函数
def is_ocr_available() -> bool:
    """检查 OCR 服务是否可用"""
    provider = get_ocr_provider()
    return provider.is_available


def get_ocr_service_type() -> str:
    """获取当前使用的 OCR 服务类型"""
    provider = get_ocr_provider()
    return provider.service_type


def reinitialize_ocr_service() -> bool:
    """
    重新初始化 OCR 服务

    用于在运行时安装依赖后重新加载服务。

    Returns:
        bool: 初始化是否成功

    Example:
        >>> # 运行时安装依赖
        >>> subprocess.run(["uv", "sync", "--extra", "pdf-ocr"])
        >>> # 重新初始化服务
        >>> if reinitialize_ocr_service():
        ...     print("OCR 服务已就绪")
    """
    provider = get_ocr_provider()
    return provider.reinitialize()
