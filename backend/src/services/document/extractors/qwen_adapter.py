"""
Qwen-VL Contract Extractor Adapter
阿里通义千问 Qwen-VL 合同提取适配器
"""

import logging

from ...core.qwen_vision_service import get_qwen_vision_service
from .base import BaseVisionAdapter

logger = logging.getLogger(__name__)


class QwenAdapter(BaseVisionAdapter):
    """
    Adapter for Alibaba Qwen-VL-Max.
    Excellent for table extraction and complex document layouts.
    Inherits common extraction logic from BaseVisionAdapter.
    """

    def __init__(self):
        self._vision_service = get_qwen_vision_service()

    @property
    def vision_service(self):
        return self._vision_service

    @property
    def provider_name(self) -> str:
        return "qwen_vl"

    @property
    def api_key_env_name(self) -> str:
        return "DASHSCOPE_API_KEY"


# Alias for backward compatibility with tests
QwenVisionAdapter = QwenAdapter
