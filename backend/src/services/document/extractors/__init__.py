"""
Contract Extractors Package

Provides a modular, multi-model architecture for contract data extraction.
Supports GLM-4V, Qwen-VL, DeepSeek-VL via the Adapter Pattern.

Usage:
    from services.document.extractors import get_llm_extractor

    # Use configured provider
    extractor = get_llm_extractor()

    # Or force specific provider
    extractor = get_llm_extractor(force_provider="qwen")

    result = await extractor.extract("/path/to/contract.pdf")
"""

from .base import BaseVisionAdapter, ContractExtractorInterface
from .deepseek_adapter import DeepSeekAdapter
from .factory import ExtractorFactory, get_llm_extractor, reset_extractor
from .glm_adapter import GLMAdapter
from .qwen_adapter import QwenAdapter

__all__ = [
    # Interfaces
    "ContractExtractorInterface",
    "BaseVisionAdapter",
    # Factory
    "ExtractorFactory",
    "get_llm_extractor",
    "reset_extractor",
    # Adapters
    "GLMAdapter",
    "QwenAdapter",
    "DeepSeekAdapter",
]
