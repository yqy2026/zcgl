"""
智谱AI GLM-4.6V 多模态视觉服务
Zhipu AI GLM-4.6V Multimodal Vision Service

支持图片直接输入进行合同信息提取
Supports direct image input for contract information extraction
"""

import logging
import os
from typing import Any

import httpx
from httpx import HTTPStatusError, NetworkError, TimeoutException
from pydantic import BaseModel

from ...core.exception_handler import ConfigurationError
from .base_vision_service import (
    BaseVisionService,
    VisionAPIError,
    handle_http_status_error,
    handle_network_error,
)

logger = logging.getLogger(__name__)


class VisionResponse(BaseModel):
    """Response from vision model"""

    content: str
    raw_response: Any
    usage: dict[str, Any] = {}


class ZhipuVisionService(BaseVisionService):
    """
    智谱AI GLM-4.6V 多模态视觉服务

    Environment Variables:
    - ZHIPU_API_KEY: 智谱AI API密钥 (required)
    - ZHIPU_VISION_MODEL: 视觉模型 (default: glm-4v-flash for free tier)
    - ZHIPU_TIMEOUT: API timeout in seconds (default: 120)

    Available Models (2026.01):
    - glm-4v-flash: Free tier, 8K context
    - glm-4.5v: ¥2/M input, 64K context, thinking mode
    - glm-4.6v: 128K context, native function calling (recommended for production)
    """

    DEFAULT_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"

    def __init__(self) -> None:
        # 优先使用 centralized config，fallback 到环境变量
        try:
            from src.core.config import settings

            api_key = (
                settings.ZHIPU_API_KEY
                or os.getenv("ZHIPU_API_KEY")
                or os.getenv("LLM_API_KEY")
            )
            self.base_url = settings.ZHIPU_BASE_URL or os.getenv(
                "ZHIPU_BASE_URL", self.DEFAULT_BASE_URL
            )
            self.model = settings.ZHIPU_VISION_MODEL or os.getenv(
                "ZHIPU_VISION_MODEL", "glm-4v"
            )
        except ImportError:
            # Fallback for standalone usage
            api_key = os.getenv("ZHIPU_API_KEY") or os.getenv("LLM_API_KEY")
            self.base_url = os.getenv("ZHIPU_BASE_URL", self.DEFAULT_BASE_URL)
            self.model = os.getenv("ZHIPU_VISION_MODEL", "glm-4v")

        super().__init__(api_key=api_key)
        self.timeout = int(os.getenv("ZHIPU_TIMEOUT", "120"))

        if not self.api_key:
            logger.warning(
                "ZHIPU_API_KEY (or LLM_API_KEY) not set, vision service will be disabled"
            )
        else:
            logger.info(f"ZhipuVisionService initialized with model: {self.model}")

    @property
    def is_available(self) -> bool:
        """Check if service is configured and available"""
        return bool(self.api_key)

    async def extract_from_images(
        self,
        image_paths: list[str],
        prompt: str,
        **kwargs: Any,
    ) -> str:
        """
        Send images to GLM-4V for contract extraction.

        Args:
            image_paths: List of image file paths (PNG/JPG)
            prompt: Extraction prompt (Chinese preferred)
            **kwargs: Additional parameters (temperature, max_tokens, etc.)
                - temperature: float (default: 0.1) - Model temperature (0.0-1.0)
                - max_tokens: int (default: 4096) - Max tokens in response (ignored by API)

        Returns:
            str: Extracted content (JSON string)

        Raises:
            VisionAPIError: If API request fails (with status code and retry info)
            ConfigurationError: If API key not configured
        """
        if not self.is_available:
            raise ConfigurationError(
                "ZHIPU_API_KEY not configured", config_key="ZHIPU_API_KEY"
            )

        # Extract kwargs with defaults
        temperature: float = kwargs.get("temperature", 0.1)
        max_tokens: int = kwargs.get("max_tokens", 4096)

        # Build multimodal content array
        content: list[dict[str, Any]] = []

        for img_path in image_paths:
            img_base64 = self._encode_image(img_path)
            mime_type = self._get_mime_type(img_path)
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime_type};base64,{img_base64}"},
                }
            )

        # Add text prompt
        content.append({"type": "text", "text": prompt})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        # Note: GLM-4V does NOT support max_tokens parameter (causes error 1210)
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": content}],
            "temperature": temperature,
        }

        logger.info(f"Sending {len(image_paths)} images to {self.model}")

        # Debug: Log payload structure (without base64 content)
        if self.api_key:
            logger.debug(f"API Key prefix: {self.api_key[:10]}...")
        logger.debug(f"Model: {self.model}")
        logger.debug(f"Temperature: {temperature}, max_tokens: {max_tokens}")
        logger.debug(f"Content items: {len(content)} (images + text)")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions", json=payload, headers=headers
                )
                response.raise_for_status()
                if response.status_code >= 400:
                    request = getattr(response, "request", None) or httpx.Request(
                        "POST", f"{self.base_url}/chat/completions"
                    )
                    raise HTTPStatusError(
                        f"HTTP {response.status_code} error",
                        request=request,
                        response=response,
                    )
                data: dict[str, Any] = response.json()

                choices = data.get("choices", [])
                if not choices:
                    raise VisionAPIError(
                        message="API returned no choices",
                        status_code=response.status_code,
                        retryable=True,
                    )

                first_choice = choices[0]
                if not isinstance(first_choice, dict):
                    raise VisionAPIError(
                        message=f"Invalid choice format: {type(first_choice)}",
                        status_code=response.status_code,
                        retryable=True,
                    )

                message = first_choice.get("message", {})
                if not isinstance(message, dict):
                    raise VisionAPIError(
                        message=f"Invalid message format: {type(message)}",
                        status_code=response.status_code,
                        retryable=True,
                    )

                result_content: str = message.get("content", "")
                usage: dict[str, Any] = data.get("usage", {})

                logger.info(f"Vision extraction complete. Tokens used: {usage}")

                return result_content

        except HTTPStatusError as e:
            # 使用增强的错误处理
            vision_error = handle_http_status_error(e)
            logger.error(
                f"Zhipu API error: {vision_error.status_code} - {vision_error}",
                extra={
                    "error_id": "ZHIPU_API_ERROR",
                    "status_code": vision_error.status_code,
                    "retryable": vision_error.retryable,
                },
            )
            raise vision_error from e

        except (NetworkError, TimeoutException, ConnectionError) as e:
            # 使用增强的网络错误处理
            vision_error = handle_network_error(e)
            logger.error(
                f"Zhipu network error: {vision_error}",
                extra={"error_id": "ZHIPU_NETWORK_ERROR"},
            )
            raise vision_error from e

        except VisionAPIError:
            raise
        except Exception as e:
            logger.error(
                f"Vision extraction failed: {e}",
                exc_info=True,
                extra={"error_id": "ZHIPU_UNKNOWN_ERROR"},
            )
            raise VisionAPIError(
                message=f"Unexpected error: {str(e)}", status_code=None, retryable=False
            ) from e


# Singleton instance
_vision_service: ZhipuVisionService | None = None


def get_zhipu_vision_service() -> ZhipuVisionService:
    """Get or create singleton ZhipuVisionService instance"""
    global _vision_service
    if _vision_service is None:
        _vision_service = ZhipuVisionService()
    assert _vision_service is not None  # nosec B101  # Type narrowing for singleton pattern
    return _vision_service
