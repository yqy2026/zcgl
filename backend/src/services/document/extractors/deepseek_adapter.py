"""
DeepSeek-VL Contract Extractor Adapter
深度求索 DeepSeek-VL 合同提取适配器
"""

import logging

from ...core.deepseek_vision_service import get_deepseek_vision_service
from .base import BaseVisionAdapter

logger = logging.getLogger(__name__)


class DeepSeekAdapter(BaseVisionAdapter):
    """
    Adapter for DeepSeek-VL.
    High cost-effectiveness with strong reasoning capabilities.
    Inherits common extraction logic from BaseVisionAdapter.
    """

    def __init__(self):
        self._vision_service = get_deepseek_vision_service()

    @property
    def vision_service(self):
        return self._vision_service

    @property
    def provider_name(self) -> str:
        return "deepseek_vl"

    @property
    def api_key_env_name(self) -> str:
        return "DEEPSEEK_API_KEY"


# Alias for backward compatibility with tests
DeepSeekVisionAdapter = DeepSeekAdapter
