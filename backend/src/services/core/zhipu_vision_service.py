"""
智谱AI GLM-4.6V 多模态视觉服务
Zhipu AI GLM-4.6V Multimodal Vision Service

支持图片直接输入进行合同信息提取
Supports direct image input for contract information extraction
"""
import base64
import httpx
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class VisionResponse(BaseModel):
    """Response from vision model"""
    content: str
    raw_response: Any
    usage: Dict[str, Any] = {}


class ZhipuVisionService:
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
    
    def __init__(self):
        # Support both ZHIPU_API_KEY and LLM_API_KEY (for compatibility with existing config)
        self.api_key = os.getenv("ZHIPU_API_KEY") or os.getenv("LLM_API_KEY")
        self.base_url = os.getenv("ZHIPU_BASE_URL", self.DEFAULT_BASE_URL)
        # Note: glm-4v is the correct model name (glm-4v-flash causes error 1210)
        self.model = os.getenv("ZHIPU_VISION_MODEL", "glm-4v")
        self.timeout = int(os.getenv("ZHIPU_TIMEOUT", "120"))
        
        if not self.api_key:
            logger.warning("ZHIPU_API_KEY (or LLM_API_KEY) not set, vision service will be disabled")
        else:
            logger.info(f"ZhipuVisionService initialized with model: {self.model}")
    
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
        image_paths: List[str],
        prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 4096
    ) -> VisionResponse:
        """
        Send images to GLM-4V for contract extraction.
        
        Args:
            image_paths: List of image file paths (PNG/JPG)
            prompt: Extraction prompt (Chinese preferred)
            temperature: Model temperature (0.0-1.0, lower = more deterministic)
            max_tokens: Maximum tokens in response
            
        Returns:
            VisionResponse with extracted content
            
        Raises:
            RuntimeError: If API key not configured
            httpx.HTTPStatusError: If API request fails
        """
        if not self.is_available:
            raise RuntimeError("ZHIPU_API_KEY not configured")
        
        # Build multimodal content array
        content: List[Dict[str, Any]] = []
        
        for img_path in image_paths:
            img_base64 = self._encode_image(img_path)
            mime_type = self._get_mime_type(img_path)
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime_type};base64,{img_base64}"
                }
            })
        
        # Add text prompt
        content.append({
            "type": "text",
            "text": prompt
        })
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        # Note: GLM-4V does NOT support max_tokens parameter (causes error 1210)
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": content
                }
            ],
            "temperature": temperature
        }
        
        logger.info(f"Sending {len(image_paths)} images to {self.model}")
        
        # Debug: Log payload structure (without base64 content)
        logger.debug(f"API Key prefix: {self.api_key[:10]}...")
        logger.debug(f"Model: {self.model}")
        logger.debug(f"Temperature: {temperature}, max_tokens: {max_tokens}")
        logger.debug(f"Content items: {len(content)} (images + text)")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                data = response.json()
                
                result_content = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                
                logger.info(f"Vision extraction complete. Tokens used: {usage}")
                
                return VisionResponse(
                    content=result_content,
                    raw_response=data,
                    usage=usage
                )
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Zhipu API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Vision extraction failed: {e}")
            raise


# Singleton instance
_vision_service: Optional[ZhipuVisionService] = None


def get_zhipu_vision_service() -> ZhipuVisionService:
    """Get or create singleton ZhipuVisionService instance"""
    global _vision_service
    if _vision_service is None:
        _vision_service = ZhipuVisionService()
    return _vision_service
