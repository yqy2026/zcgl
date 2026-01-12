#!/usr/bin/env python3
"""
合同提取器统一接口定义
定义所有提取器的抽象基类和通用数据模型
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class ExtractionMethod(str, Enum):
    """提取方法枚举"""

    LLM_HYBRID = "llm_hybrid"  # LLM 文本提取
    VISION_GLM4V = "vision_glm4v"  # GLM-4V 视觉提取
    REGEX_PATTERN = "regex_pattern"  # 正则表达式提取
    SMART_AUTO = "smart_auto"  # 智能自动检测
    OCR_PADDLE = "ocr_paddle"  # PaddleOCR 提取
    NVIDIA_CLOUD = "nvidia_cloud"  # NVIDIA Cloud OCR
    UNKNOWN = "unknown"  # 未知方法


class ExtractionStatus(str, Enum):
    """提取状态枚举"""

    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"  # 部分成功
    SKIPPED = "skipped"  # 已跳过


class ErrorCode(str, Enum):
    """标准错误码"""

    # 网络相关
    NETWORK_ERROR = "NETWORK_ERROR"
    API_TIMEOUT = "API_TIMEOUT"
    API_RATE_LIMIT = "API_RATE_LIMIT"
    API_KEY_INVALID = "API_KEY_INVALID"

    # 文件相关
    INVALID_PDF = "INVALID_PDF"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    CORRUPTED_FILE = "CORRUPTED_FILE"

    # 服务相关
    OCR_UNAVAILABLE = "OCR_UNAVAILABLE"
    LLM_UNAVAILABLE = "LLM_UNAVAILABLE"
    VISION_UNAVAILABLE = "VISION_UNAVAILABLE"
    SERVICE_ERROR = "SERVICE_ERROR"

    # 提取相关
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    NO_TEXT_DETECTED = "NO_TEXT_DETECTED"
    PARSE_ERROR = "PARSE_ERROR"

    # 系统相关
    OUT_OF_MEMORY = "OUT_OF_MEMORY"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"


class ExtractionResult(BaseModel):
    """
    统一的提取结果格式
    所有提取器必须返回此格式
    """

    # 基础状态
    success: bool
    status: ExtractionStatus = ExtractionStatus.SUCCESS

    # 提取的数据
    extracted_fields: dict[str, Any] = Field(default_factory=dict)
    raw_llm_json: dict[str, Any] | None = None

    # 元数据
    extraction_method: ExtractionMethod = ExtractionMethod.UNKNOWN
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)

    # 性能指标
    processing_time_ms: int | None = None

    # 错误信息
    error: str | None = None
    error_code: ErrorCode | None = None
    error_details: dict[str, Any] | None = None

    # 重试建议
    retry_suggested: bool = False

    # 额外信息
    pdf_analysis: dict[str, Any] | None = None
    usage: dict[str, Any] | None = None
    warnings: list[str] = Field(default_factory=list)

    class Config:
        use_enum_values = True

    @model_validator(mode="after")
    def validate_success_consistency(self) -> "ExtractionResult":
        """
        验证成功/错误状态的一致性

        规则:
        - success=True 时，error 必须为 None，且必须有 extracted_fields
        - success=False 时，error 必须有值
        """
        if self.success:
            if self.error is not None:
                raise ValueError(
                    f"success=True 时 error 必须为 None，当前值: '{self.error}'"
                )
            if not self.extracted_fields and self.status != ExtractionStatus.SKIPPED:
                # 允许空字段在跳过状态下，但成功时应该有数据
                pass  # 可以改为强制要求：raise ValueError("success=True 时 extracted_fields 不能为空")
        else:
            if self.error is None:
                raise ValueError("success=False 时必须提供 error 信息")
            # 根据错误自动设置状态
            if self.status == ExtractionStatus.SUCCESS:
                self.status = ExtractionStatus.FAILED

        return self


class ProgressCallback:
    """进度回调类型定义"""

    def __call__(
        self,
        progress: int,  # 0-100
        message: str,  # 状态消息
        stage: str | None = None,  # 阶段标识
    ) -> None:
        """
        报告处理进度

        Args:
            progress: 进度百分比 (0-100)
            message: 状态消息
            stage: 当前阶段标识（如 "analyzing", "extracting"）
        """
        pass


# 类型别名
ProgressCallbackType = Callable[[int, str, str | None], None]


class ContractExtractorInterface(ABC):
    """
    合同提取器统一接口

    所有合同提取器必须实现此接口，确保一致的 API 和行为
    """

    @abstractmethod
    async def extract(self, source: str, **kwargs) -> ExtractionResult:
        """
        从源文本中提取合同信息

        Args:
            source: 输入源（文本内容或文件路径）
            **kwargs: 额外参数（如 confidence_threshold, fields 等）

        Returns:
            ExtractionResult: 统一格式的提取结果

        Raises:
            NotImplementedError: 子类必须实现
        """
        pass

    @property
    def is_available(self) -> bool:
        """
        检查提取器是否可用

        Returns:
            bool: 是否可用
        """
        return True

    @property
    def name(self) -> str:
        """
        获取提取器名称

        Returns:
            str: 提取器名称
        """
        return self.__class__.__name__

    def supports_batch(self) -> bool:
        """
        是否支持批量处理

        Returns:
            bool: 是否支持
        """
        return False

    def get_supported_methods(self) -> list[ExtractionMethod]:
        """
        获取支持的提取方法

        Returns:
            list[ExtractionMethod]: 支持的方法列表
        """
        return [ExtractionMethod.UNKNOWN]


class BatchExtractorInterface(ContractExtractorInterface):
    """
    批量提取器接口
    扩展自基础接口，添加批量处理能力
    """

    @abstractmethod
    async def extract_batch(
        self,
        sources: list[str],
        progress_callback: ProgressCallbackType | None = None,
        **kwargs,
    ) -> list[ExtractionResult]:
        """
        批量提取合同信息

        Args:
            sources: 输入源列表
            progress_callback: 进度回调函数
            **kwargs: 额外参数

        Returns:
            list[ExtractionResult]: 提取结果列表
        """
        pass

    def supports_batch(self) -> bool:
        """批量提取器支持批量处理"""
        return True


class ExtractionConfig(BaseModel):
    """
    提取配置模型
    统一管理各种提取参数
    """

    # 基础配置
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    timeout_seconds: int = Field(default=180, ge=1, le=600)
    max_retries: int = Field(default=3, ge=0, le=10)

    # PDF 处理配置
    max_pdf_pages: int = Field(default=20, ge=1, le=100)
    max_pdf_size_mb: int = Field(default=50, ge=1, le=500)
    dpi: int = Field(default=200, ge=100, le=600)

    # 提取配置
    force_method: ExtractionMethod | None = None
    enable_regex_validation: bool = True
    enable_llm_fallback: bool = True

    # 性能配置
    max_concurrent_tasks: int = Field(default=3, ge=1, le=10)
    batch_size: int = Field(default=3, ge=1, le=10)

    # 缓存配置
    enable_cache: bool = True
    cache_ttl_seconds: int = Field(default=3600, ge=0)

    # 调试配置
    debug_mode: bool = False
    save_intermediate: bool = False

    class Config:
        use_enum_values = True


class ExtractorFactory:
    """
    提取器工厂
    根据配置创建合适的提取器实例
    """

    _extractors: dict[str, type] = {}

    @classmethod
    def register(
        cls, name: str, extractor_class: type[ContractExtractorInterface]
    ) -> None:
        """
        注册提取器

        Args:
            name: 提取器名称
            extractor_class: 提取器类
        """
        cls._extractors[name] = extractor_class

    @classmethod
    def create(cls, name: str, **kwargs) -> ContractExtractorInterface | None:
        """
        创建提取器实例

        Args:
            name: 提取器名称
            **kwargs: 传递给提取器的参数

        Returns:
            提取器实例，如果不存在则返回 None
        """
        extractor_class = cls._extractors.get(name)
        if extractor_class:
            return extractor_class(**kwargs)
        return None

    @classmethod
    def list_available(cls) -> list[str]:
        """
        列出所有已注册的提取器

        Returns:
            list[str]: 提取器名称列表
        """
        return list(cls._extractors.keys())


# 便捷函数
def create_error_result(
    error_message: str,
    error_code: ErrorCode = ErrorCode.INTERNAL_ERROR,
    method: ExtractionMethod = ExtractionMethod.UNKNOWN,
    retry_suggested: bool = False,
    details: dict[str, Any] | None = None,
) -> ExtractionResult:
    """
    创建错误结果

    Args:
        error_message: 错误消息
        error_code: 错误码
        method: 提取方法
        retry_suggested: 是否建议重试
        details: 错误详情

    Returns:
        ExtractionResult: 错误结果
    """
    return ExtractionResult(
        success=False,
        status=ExtractionStatus.FAILED,
        error=error_message,
        error_code=error_code,
        extraction_method=method,
        retry_suggested=retry_suggested,
        error_details=details,
    )


def create_success_result(
    extracted_fields: dict[str, Any],
    method: ExtractionMethod,
    confidence: float = 0.8,
    **kwargs,
) -> ExtractionResult:
    """
    创建成功结果

    Args:
        extracted_fields: 提取的字段
        method: 提取方法
        confidence: 置信度
        **kwargs: 其他字段

    Returns:
        ExtractionResult: 成功结果
    """
    return ExtractionResult(
        success=True,
        status=ExtractionStatus.SUCCESS,
        extracted_fields=extracted_fields,
        extraction_method=method,
        confidence=confidence,
        **kwargs,
    )
