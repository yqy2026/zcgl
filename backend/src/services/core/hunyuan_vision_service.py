"""
腾讯混元 Hunyuan-Vision 多模态视觉服务
Tencent Hunyuan-Vision Multimodal Vision Service

支持图片直接输入进行合同信息提取
Supports direct image input for contract information extraction

API Documentation:
https://cloud.tencent.com/document/product/1729
"""

import base64
import logging
import os
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class HunyuanVisionResponse(BaseModel):
    """Response from Hunyuan vision model"""

    content: str
    raw_response: Any
    usage: dict[str, Any] = {}


class HunyuanVisionService:
    """
    腾讯混元 Hunyuan-Vision 多模态视觉服务

    Environment Variables:
    - HUNYUAN_API_KEY: 腾讯混元 API密钥 (required)
    - HUNYUAN_BASE_URL: API基础地址 (default: OpenAI兼容接口)
    - HUNYUAN_VISION_MODEL: 视觉模型 (default: hunyuan-vision)
    - HUNYUAN_TIMEOUT: API timeout in seconds (default: 120)

    Available Models (2026.01):
    - hunyuan-vision: 通用视觉理解
    - hunyuan-t1-vision: 深度思考视觉模型
    - hunyuan-vision-1.5-instruct: 增强版图生文
    - hunyuan-large-vision: 基于混元Large的视觉语言模型

    Pricing:
    - 新用户免费100万Tokens
    - 后付费按Token计费
    """

    DEFAULT_BASE_URL = "https://api.hunyuan.cloud.tencent.com/v1"

    def __init__(self) -> None:
        # 优先使用 centralized config，fallback 到环境变量
        try:
            from src.core.config import settings

            self.api_key = settings.HUNYUAN_API_KEY or os.getenv("HUNYUAN_API_KEY")
            self.base_url = settings.HUNYUAN_BASE_URL or os.getenv(
                "HUNYUAN_BASE_URL", self.DEFAULT_BASE_URL
            )
            self.model = settings.HUNYUAN_VISION_MODEL or os.getenv(
                "HUNYUAN_VISION_MODEL", "hunyuan-vision"
            )
        except ImportError:
            # Fallback for standalone usage
            self.api_key = os.getenv("HUNYUAN_API_KEY")
            self.base_url = os.getenv("HUNYUAN_BASE_URL", self.DEFAULT_BASE_URL)
            self.model = os.getenv("HUNYUAN_VISION_MODEL", "hunyuan-vision")

        self.timeout = int(os.getenv("HUNYUAN_TIMEOUT", "120"))

        if not self.api_key:
            logger.warning(
                "HUNYUAN_API_KEY not set, Hunyuan vision service will be disabled"
            )
        else:
            logger.info(f"HunyuanVisionService initialized with model: {self.model}")

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
    ) -> HunyuanVisionResponse:
        """
        Send images to Hunyuan-Vision for contract extraction.

        Args:
            image_paths: List of image file paths (PNG/JPG)
            prompt: Extraction prompt
            temperature: Model temperature (0.0-1.0)
            max_tokens: Maximum tokens in response

        Returns:
            HunyuanVisionResponse with extracted content
        """
        if not self.is_available:
            raise RuntimeError("HUNYUAN_API_KEY not configured")

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

                logger.info(f"Hunyuan vision extraction complete. Tokens: {usage}")

                return HunyuanVisionResponse(
                    content=result_content, raw_response=data, usage=usage
                )

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Hunyuan API error: {e.response.status_code} - {e.response.text}"
            )
            raise
        except Exception as e:
            logger.error(f"Hunyuan vision extraction failed: {e}")
            raise


# Singleton instance
_hunyuan_vision_service: HunyuanVisionService | None = None


def get_hunyuan_vision_service() -> HunyuanVisionService:
    """Get or create singleton HunyuanVisionService instance"""
    global _hunyuan_vision_service
    if _hunyuan_vision_service is None:
        _hunyuan_vision_service = HunyuanVisionService()
    return _hunyuan_vision_service
