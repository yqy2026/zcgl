"""
深度求索 DeepSeek-VL 多模态视觉服务
DeepSeek-VL Multimodal Vision Service

支持图片直接输入进行合同信息提取
Supports direct image input for contract information extraction

API Documentation:
https://platform.deepseek.com/api-reference
"""

import base64
import logging
import os
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class DeepSeekVisionResponse(BaseModel):
    """Response from DeepSeek vision model"""

    content: str
    raw_response: Any
    usage: dict[str, Any] = {}


class DeepSeekVisionService:
    """
    深度求索 DeepSeek-VL 多模态视觉服务

    Environment Variables:
    - DEEPSEEK_API_KEY: DeepSeek API密钥 (required)
    - DEEPSEEK_VISION_MODEL: 视觉模型 (default: deepseek-vl)
    - DEEPSEEK_TIMEOUT: API timeout in seconds (default: 120)

    Available Models (2026.01):
    - deepseek-vl: 开源视觉模型，支持1024x1024高分辨率
    - deepseek-vl-v2: 增强版，更好的表格理解

    Pricing:
    - 输入: ¥1/M tokens (非常便宜)
    - 输出: ¥2/M tokens
    """

    DEFAULT_BASE_URL = "https://api.deepseek.com/v1"

    def __init__(self):
        # 优先使用 centralized config，fallback 到环境变量
        try:
            from src.core.config import settings
            self.api_key = settings.DEEPSEEK_API_KEY or os.getenv("DEEPSEEK_API_KEY")
            self.base_url = settings.DEEPSEEK_BASE_URL or os.getenv("DEEPSEEK_BASE_URL", self.DEFAULT_BASE_URL)
            self.model = settings.DEEPSEEK_VISION_MODEL or os.getenv("DEEPSEEK_VISION_MODEL", "deepseek-vl")
        except ImportError:
            # Fallback for standalone usage
            self.api_key = os.getenv("DEEPSEEK_API_KEY")
            self.base_url = os.getenv("DEEPSEEK_BASE_URL", self.DEFAULT_BASE_URL)
            self.model = os.getenv("DEEPSEEK_VISION_MODEL", "deepseek-vl")
        
        self.timeout = int(os.getenv("DEEPSEEK_TIMEOUT", "120"))

        if not self.api_key:
            logger.warning(
                "DEEPSEEK_API_KEY not set, DeepSeek vision service will be disabled"
            )
        else:
            logger.info(f"DeepSeekVisionService initialized with model: {self.model}")

    @property
    def is_available(self) -> bool:
        """Check if service is configured and available"""
        return bool(self.api_key)

    def _encode_image(self, image_path: str) -> str:
        """Encode image file to base64 string"""
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def _get_mime_type(self, image_path: str) -> str:
        """Get MIME type from file extension"""
        ext = Path(image_path).suffix.lower()
        mime_map = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        return mime_map.get(ext, "image/png")

    async def extract_from_images(
        self,
        image_paths: list[str],
        prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> DeepSeekVisionResponse:
        """
        Send images to DeepSeek-VL for contract extraction.

        Args:
            image_paths: List of image file paths (PNG/JPG)
            prompt: Extraction prompt
            temperature: Model temperature (0.0-1.0)
            max_tokens: Maximum tokens in response

        Returns:
            DeepSeekVisionResponse with extracted content
        """
        if not self.is_available:
            raise RuntimeError("DEEPSEEK_API_KEY not configured")

        # Build multimodal content array (OpenAI-compatible format)
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

        content.append({"type": "text", "text": prompt})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": content}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        logger.info(f"Sending {len(image_paths)} images to {self.model}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions", json=payload, headers=headers
                )
                response.raise_for_status()
                data = response.json()

                result_content = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})

                logger.info(f"DeepSeek vision extraction complete. Tokens: {usage}")

                return DeepSeekVisionResponse(
                    content=result_content, raw_response=data, usage=usage
                )

        except httpx.HTTPStatusError as e:
            logger.error(
                f"DeepSeek API error: {e.response.status_code} - {e.response.text}"
            )
            raise
        except Exception as e:
            logger.error(f"DeepSeek vision extraction failed: {e}")
            raise


# Singleton instance
_deepseek_vision_service: DeepSeekVisionService | None = None


def get_deepseek_vision_service() -> DeepSeekVisionService:
    """Get or create singleton DeepSeekVisionService instance"""
    global _deepseek_vision_service
    if _deepseek_vision_service is None:
        _deepseek_vision_service = DeepSeekVisionService()
    return _deepseek_vision_service
