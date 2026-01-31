#!/usr/bin/env python3
"""
PDF/OCR 统一配置
集中管理所有 PDF 处理和 OCR 相关的配置参数
"""

import logging
import os
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator
from pydantic_core import PydanticCustomError

from ...core.exception_handler import ConfigurationError

# ============================================================================
# LLM 提供商枚举 - 统一命名
# ============================================================================


class LLMProvider(str, Enum):
    """
    LLM 提供商枚举 - 统一命名规范

    标准化所有 LLM 提供商的名称，避免不一致的命名问题
    """

    QWEN = "qwen"  # 通义千问 (阿里云 DashScope)
    DEEPSEEK = "deepseek"  # DeepSeek-VL
    GLM = "glm"  # 智谱 GLM (GLM-4V)
    HUNYUAN = "hunyuan"  # 腾讯混元 (2026-01 新增)

    @classmethod
    def normalize(cls, value: str) -> "LLMProvider":
        """
        标准化提供商名称

        将各种可能的别名转换为标准名称

        Args:
            value: 提供商名称（可能是别名）

        Returns:
            标准化的 LLMProvider 枚举值

        Raises:
            ConfigurationError: 如果无法识别的提供商名称
        """
        value_map = {
            # GLM 别名
            "glm-4v": cls.GLM,
            "glm4v": cls.GLM,
            "zhipu": cls.GLM,
            "chatglm": cls.GLM,
            "智谱": cls.GLM,  # Chinese alias
            # Qwen 别名
            "qwen-vl": cls.QWEN,
            "qwen-vl-max": cls.QWEN,
            "qwen-vl-plus": cls.QWEN,
            "dashscope": cls.QWEN,
            "通义": cls.QWEN,  # Chinese alias
            "阿里": cls.QWEN,  # Chinese alias
            "alibaba": cls.QWEN,
            # DeepSeek 别名
            "deepseek-vl": cls.DEEPSEEK,
            "深度求索": cls.DEEPSEEK,
            # Hunyuan 别名 (2026-01 新增)
            "hunyuan-vision": cls.HUNYUAN,
            "tencent": cls.HUNYUAN,
            "腾讯": cls.HUNYUAN,  # Chinese alias
            "混元": cls.HUNYUAN,  # Chinese alias
        }

        normalized = value_map.get(value.lower())
        if normalized:
            return normalized

        # 尝试直接匹配
        try:
            return cls(value.lower())
        except ValueError as exc:
            raise ConfigurationError(
                f"Unsupported LLM provider: {value}. "
                f"Supported providers: {[p.value for p in cls]}",
                config_key="LLM_PROVIDER",
            ) from exc


class OCRConfig(BaseModel):
    """
    PDF 文件处理配置

    .. note::
        OCR 引擎（PaddleOCR, Tesseract）已在 v2.0 中完全移除。
        现在使用 LLM Vision API 进行合同提取：
        - Qwen3-VL-Flash: services/document/extractors/qwen_adapter.py
        - DeepSeek-VL: services/document/extractors/deepseek_adapter.py
        - GLM-4V: services/document/extractors/glm_adapter.py

        此配置类名称 OCRConfig 保留用于向后兼容，
        实际仅用于文件大小、页数限制等通用设置。
    """

    # 文件限制（通用配置）
    max_pdf_pages: int = Field(
        default=20,
        ge=1,
        le=100,
        description="最大处理页数",
    )
    max_pdf_size_mb: int = Field(
        default=50,
        ge=1,
        le=500,
        description="最大 PDF 文件大小（MB）",
    )
    max_concurrent_tasks: int = Field(
        default=3,
        ge=1,
        le=10,
        description="最大并发处理任务数",
    )

    @classmethod
    def from_env(cls) -> "OCRConfig":
        """
        从环境变量加载配置

        Environment variables:
            PDF_MAX_PAGES: 最大页数（默认: 20）
            PDF_MAX_SIZE_MB: 最大文件大小（MB）（默认: 50）
            PDF_MAX_CONCURRENT: 最大并发数（默认: 3）

        Returns:
            OCRConfig: 配置实例
        """
        return cls(
            max_pdf_pages=int(os.getenv("PDF_MAX_PAGES", "20")),
            max_pdf_size_mb=int(os.getenv("PDF_MAX_SIZE_MB", "50")),
            max_concurrent_tasks=int(os.getenv("PDF_MAX_CONCURRENT", "3")),
        )


class ExtractionConfig(BaseModel):
    """
    提取配置

    控制合同信息提取的行为
    """

    # 置信度阈值
    confidence_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="提取置信度阈值",
    )

    # 重试配置
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="最大重试次数",
    )

    # 方法选择
    force_method: str | None = Field(
        default=None,
        description="强制使用的提取方法: text, vision, smart",
    )

    # 验证选项
    enable_regex_validation: bool = Field(
        default=True,
        description="是否启用正则验证",
    )
    enable_llm_fallback: bool = Field(
        default=True,
        description="是否启用 LLM 降级",
    )

    # LLM 配置
    llm_provider: LLMProvider = Field(
        default=LLMProvider.GLM,
        description="默认 LLM 提供商",
    )
    llm_timeout: int = Field(
        default=30,
        ge=5,
        le=300,
        description="LLM 请求超时时间（秒）",
    )
    llm_max_tokens: int = Field(
        default=1500,
        ge=100,
        le=8000,
        description="LLM 最大 tokens",
    )

    # OCR 配置
    ocr_enabled: bool = Field(
        default=True,
        description="是否启用 OCR 文字识别",
    )
    ocr_fallback: bool = Field(
        default=True,
        description="LLM 失败时是否回退到 OCR",
    )

    # 批处理配置
    batch_size: int = Field(
        default=3,
        ge=1,
        le=10,
        description="批处理大小（多页 PDF）",
    )

    # 缓存配置
    enable_cache: bool = Field(
        default=True,
        description="是否启用缓存",
    )
    cache_dir: str | None = Field(
        default=None,
        description="缓存目录路径（默认为系统临时目录）",
    )
    cache_ttl_seconds: int = Field(
        default=3600,
        ge=0,
        description="缓存过期时间（秒）",
    )

    @field_validator("force_method")
    @classmethod
    def validate_force_method(cls, v: str | None) -> str | None:
        """验证强制方法"""
        if v is not None:
            valid_methods = ["text", "vision", "smart", "ocr", "llm"]
            if v not in valid_methods:
                raise PydanticCustomError(
                    "invalid_method",
                    "Invalid method. Must be one of: {valid_methods}",
                    {"valid_methods": valid_methods},
                )
        return v

    @classmethod
    def from_env(cls) -> "ExtractionConfig":
        """从环境变量加载配置"""
        # 解析 LLM 提供商（使用标准化方法）
        llm_provider_str = os.getenv("EXTRACTION_LLM_PROVIDER", "glm")
        try:
            llm_provider = LLMProvider.normalize(llm_provider_str)
        except ConfigurationError:
            llm_provider = LLMProvider.GLM  # 默认值

        return cls(
            confidence_threshold=float(
                os.getenv("EXTRACTION_CONFIDENCE_THRESHOLD", "0.7")
            ),
            max_retries=int(os.getenv("EXTRACTION_MAX_RETRIES", "3")),
            force_method=os.getenv("EXTRACTION_FORCE_METHOD"),
            enable_regex_validation=os.getenv("EXTRACTION_ENABLE_REGEX", "true").lower()
            == "true",
            enable_llm_fallback=os.getenv(
                "EXTRACTION_ENABLE_LLM_FALLBACK", "true"
            ).lower()
            == "true",
            llm_provider=llm_provider,
            llm_timeout=int(os.getenv("EXTRACTION_LLM_TIMEOUT", "30")),
            llm_max_tokens=int(os.getenv("EXTRACTION_LLM_MAX_TOKENS", "1500")),
            ocr_enabled=os.getenv("EXTRACTION_OCR_ENABLED", "true").lower() == "true",
            ocr_fallback=os.getenv("EXTRACTION_OCR_FALLBACK", "true").lower() == "true",
            batch_size=int(os.getenv("EXTRACTION_BATCH_SIZE", "3")),
            enable_cache=os.getenv("EXTRACTION_ENABLE_CACHE", "true").lower() == "true",
            cache_ttl_seconds=int(os.getenv("EXTRACTION_CACHE_TTL", "3600")),
        )


class PDFImportConfig(BaseModel):
    """
    PDF 导入完整配置

    聚合所有相关配置
    """

    ocr: OCRConfig = Field(default_factory=OCRConfig)
    extraction: ExtractionConfig = Field(default_factory=ExtractionConfig)

    # 调试选项
    debug_mode: bool = Field(
        default=False,
        description="调试模式",
    )
    save_intermediate: bool = Field(
        default=False,
        description="保存中间结果",
    )

    @classmethod
    def from_env(cls) -> "PDFImportConfig":
        """从环境变量加载完整配置"""
        return cls(
            ocr=OCRConfig.from_env(),
            extraction=ExtractionConfig.from_env(),
            debug_mode=os.getenv("DEBUG", "false").lower() == "true",
            save_intermediate=os.getenv("SAVE_INTERMEDIATE", "false").lower() == "true",
        )


# ============================================================================
# 全局配置实例
# ============================================================================

_config: PDFImportConfig | None = None


def get_config() -> PDFImportConfig:
    """
    获取全局配置实例（单例）

    Returns:
        PDFImportConfig: 配置实例
    """
    global _config
    if _config is None:
        _config = PDFImportConfig.from_env()
    return _config


def reload_config() -> PDFImportConfig:
    """
    重新加载配置（从环境变量）

    Returns:
        PDFImportConfig: 新的配置实例
    """
    global _config
    _config = PDFImportConfig.from_env()
    return _config


def set_config(config: PDFImportConfig) -> None:
    """
    设置全局配置（用于测试）

    Args:
        config: 配置实例
    """
    global _config
    _config = config


# ============================================================================
# 便捷访问函数
# ============================================================================


def get_ocr_config() -> OCRConfig:
    """获取 OCR 配置"""
    return get_config().ocr


def get_extraction_config() -> ExtractionConfig:
    """获取提取配置"""
    return get_config().extraction


def is_debug_mode() -> bool:
    """是否为调试模式"""
    return get_config().debug_mode


def should_save_intermediate() -> bool:
    """是否保存中间结果"""
    return get_config().save_intermediate


# ============================================================================
# 配置验证
# ============================================================================


def validate_config(config: PDFImportConfig) -> list[str]:
    """
    验证配置

    Args:
        config: 要验证的配置

    Returns:
        list[str]: 警告信息列表（空表示无警告）
    """
    warnings = []

    # 检查内存相关的配置
    if config.ocr.max_concurrent_tasks > 5:
        warnings.append(
            f"max_concurrent_tasks={config.ocr.max_concurrent_tasks} may cause memory issues"
        )

    if config.ocr.max_pdf_pages > 50 and config.ocr.max_pdf_size_mb > 100:
        warnings.append(
            "Large max_pdf_pages and max_pdf_size_mb may cause memory issues"
        )

    return warnings


# ============================================================================
# 配置导出（用于调试）
# ============================================================================


def export_config_dict(config: PDFImportConfig | None = None) -> dict[str, Any]:
    """
    导出配置为字典

    Args:
        config: 要导出的配置（默认使用全局配置）

    Returns:
        dict: 配置字典
    """
    if config is None:
        config = get_config()
    return config.model_dump()


def export_config_env() -> list[str]:
    """
    导出配置为环境变量格式

    Returns:
        list[str]: 环境变量赋值语句列表
    """
    config = get_config()
    lines = [
        "# PDF/LLM Vision Configuration",
        "",
        "# File Limits",
        f"export PDF_MAX_PAGES={config.ocr.max_pdf_pages}",
        f"export PDF_MAX_SIZE_MB={config.ocr.max_pdf_size_mb}",
        f"export PDF_MAX_CONCURRENT={config.ocr.max_concurrent_tasks}",
        "",
        "# Extraction",
        f"export EXTRACTION_CONFIDENCE_THRESHOLD={config.extraction.confidence_threshold}",
        f"export EXTRACTION_MAX_RETRIES={config.extraction.max_retries}",
        f"export EXTRACTION_ENABLE_CACHE={'true' if config.extraction.enable_cache else 'false'}",
    ]
    return lines


# ============================================================================
# 使用示例
# ============================================================================

if __name__ == "__main__":  # pragma: no cover
    # 加载配置
    config = get_config()

    logger = logging.getLogger(__name__)

    logger.info("=== PDF Processing Configuration ===")
    logger.info(f"Max Pages: {config.ocr.max_pdf_pages}")
    logger.info(f"Max File Size: {config.ocr.max_pdf_size_mb}MB")
    logger.info(f"Max Concurrent Tasks: {config.ocr.max_concurrent_tasks}")

    logger.info("=== Extraction Configuration ===")
    logger.info(f"LLM Provider: {config.extraction.llm_provider}")
    logger.info(f"Confidence Threshold: {config.extraction.confidence_threshold}")
    logger.info(f"Max Retries: {config.extraction.max_retries}")
    logger.info(f"Cache: {config.extraction.enable_cache}")

    # 验证配置
    warnings = validate_config(config)
    if warnings:
        logger.warning("=== Warnings ===")
        for warning in warnings:
            logger.warning(f"⚠️  {warning}")
    else:
        logger.info("✅ Configuration is valid")

    # 导出环境变量
    logger.info("=== Environment Variables ===")
    for line in export_config_env():
        logger.info(line)
