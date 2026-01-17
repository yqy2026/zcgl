"""
GLM-4V Contract Extractor Adapter
智谱 GLM-4V 合同提取适配器
"""

import logging

from ...core.zhipu_vision_service import get_zhipu_vision_service
from .base import BaseVisionAdapter

logger = logging.getLogger(__name__)


class GLMAdapter(BaseVisionAdapter):
    """
    Adapter for Zhipu GLM-4V.
    Inherits common extraction logic from BaseVisionAdapter.
    """

    def __init__(self):
        self._vision_service = get_zhipu_vision_service()

    @property
    def vision_service(self):
        return self._vision_service

    @property
    def provider_name(self) -> str:
        return "glm4v"

    @property
    def api_key_env_name(self) -> str:
        return "ZHIPU_API_KEY"


# Alias for backward compatibility with tests
GLMVisionAdapter = GLMAdapter
