"""
企业微信 Webhook 服务

用于发送企业微信通知
"""

import logging
from typing import Any

import httpx

from ...constants.timeout_constants import WECOM_REQUEST_TIMEOUT_SECONDS
from ...core.config import settings

logger = logging.getLogger(__name__)


class WecomService:
    """企业微信服务"""

    def __init__(self) -> None:
        self.webhook_url = getattr(settings, "WECOM_WEBHOOK_URL", None)
        self.enabled = (
            getattr(settings, "WECOM_ENABLED", False) and self.webhook_url is not None
        )

    async def send_notification(
        self, message: str, mentioned_list: list[str] | None = None
    ) -> bool:
        """
        发送企业微信通知

        Args:
            message: 消息内容
            mentioned_list: @的用户列表，如 ["user1", "user2"]

        Returns:
            bool: 是否发送成功
        """
        if not self.enabled:
            logger.debug("企业微信通知未启用")
            return False

        try:
            # 构建消息体
            data: dict[str, Any] = {"msgtype": "text", "text": {"content": message}}

            # 添加@用户
            if mentioned_list:
                data["text"]["mentioned_list"] = mentioned_list

            # 发送请求
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    str(self.webhook_url),
                    json=data,
                    timeout=WECOM_REQUEST_TIMEOUT_SECONDS,
                )
                response.raise_for_status()

            result = response.json()
            if result.get("errcode") == 0:
                logger.info(f"企业微信通知发送成功: {message[:50]}...")
                return True
            else:
                logger.error(f"企业微信通知发送失败: {result}")
                return False

        except httpx.HTTPError as e:
            logger.error(f"企业微信通知发送HTTP错误: {e}")
            return False
        except Exception as e:
            logger.error(f"企业微信通知发送异常: {e}")
            return False

    async def send_markdown_notification(self, title: str, content: str) -> bool:
        """
        发送 Markdown 格式的企业微信通知

        Args:
            title: 标题
            content: Markdown 格式的内容

        Returns:
            bool: 是否发送成功
        """
        if not self.enabled:
            logger.debug("企业微信通知未启用")
            return False

        try:
            # 构建消息体
            data: dict[str, Any] = {
                "msgtype": "markdown",
                "markdown": {"content": f"# {title}\n\n{content}"},
            }

            # 发送请求
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    str(self.webhook_url),
                    json=data,
                    timeout=WECOM_REQUEST_TIMEOUT_SECONDS,
                )
                response.raise_for_status()

            result = response.json()
            if result.get("errcode") == 0:
                logger.info(f"企业微信 Markdown 通知发送成功: {title}")
                return True
            else:
                logger.error(f"企业微信 Markdown 通知发送失败: {result}")
                return False

        except Exception as e:
            logger.error(f"企业微信 Markdown 通知发送异常: {e}")
            return False


# 创建单例实例
wecom_service = WecomService()
