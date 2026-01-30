"""
Hunyuan-Vision Contract Extractor Adapter
腾讯混元视觉合同提取适配器
"""

import logging
from typing import Any

from ...core.hunyuan_vision_service import get_hunyuan_vision_service
from .base import BaseVisionAdapter

logger = logging.getLogger(__name__)


class HunyuanAdapter(BaseVisionAdapter):
    """
    Adapter for Tencent Hunyuan-Vision.
    Good for general document understanding with free tier available.
    Inherits common extraction logic from BaseVisionAdapter.
    """

    def __init__(self) -> None:
        self._vision_service = get_hunyuan_vision_service()

    @property
    def vision_service(self) -> Any:
        return self._vision_service

    @property
    def provider_name(self) -> str:
        return "hunyuan_vision"

    @property
    def api_key_env_name(self) -> str:
        return "HUNYUAN_API_KEY"
