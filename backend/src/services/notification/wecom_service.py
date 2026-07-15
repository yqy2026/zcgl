"""WeCom application-message notification delivery.

Group webhook delivery is retired because it cannot isolate business message
content per recipient. This adapter only sends self-built application messages
to an explicit WeCom ``touser``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from ...constants.timeout_constants import WECOM_REQUEST_TIMEOUT_SECONDS
from ...core.config import settings

logger = logging.getLogger(__name__)

WECOM_API_BASE_URL = "https://qyapi.weixin.qq.com/cgi-bin"
TOKEN_REFRESH_SKEW_SECONDS = 120


@dataclass
class WecomAccessToken:
    value: str
    expires_at: datetime


class WecomService:
    """Send WeCom self-built application messages to explicit recipients."""

    def __init__(self) -> None:
        self.enabled = bool(settings.WECOM_ENABLED)
        self.corp_id = settings.WECOM_CORP_ID
        self.agent_id = settings.WECOM_AGENT_ID
        self.secret = settings.WECOM_SECRET
        self._access_token: WecomAccessToken | None = None

    @property
    def configured(self) -> bool:
        return bool(self.enabled and self.corp_id and self.agent_id and self.secret)

    async def send_notification(
        self,
        message: str,
        *,
        touser: str,
    ) -> bool:
        """Send a text application message to one or more WeCom userids."""
        normalized_touser = touser.strip()
        if normalized_touser == "":
            logger.warning("WeCom application message skipped: blank touser")
            return False
        if not self.configured:
            logger.warning(
                "WeCom application message skipped: service disabled or incomplete"
            )
            return False

        access_token = await self._get_access_token()
        payload = {
            "touser": normalized_touser,
            "msgtype": "text",
            "agentid": self.agent_id,
            "text": {"content": message},
            "safe": 0,
            "enable_id_trans": 0,
            "enable_duplicate_check": 1,
        }

        async with httpx.AsyncClient(timeout=WECOM_REQUEST_TIMEOUT_SECONDS) as client:
            response = await client.post(
                f"{WECOM_API_BASE_URL}/message/send",
                params={"access_token": access_token},
                json=payload,
            )
            response.raise_for_status()
            body = response.json()

        if body.get("errcode") == 0:
            return True

        logger.warning(
            "WeCom application message failed: errcode=%s errmsg=%s",
            body.get("errcode"),
            body.get("errmsg"),
        )
        return False

    async def send_markdown_notification(
        self,
        title: str,
        content: str,
        *,
        touser: str,
    ) -> bool:
        """Compatibility wrapper; WeCom app messages use text for MVP."""
        return await self.send_notification(f"【{title}】\n{content}", touser=touser)

    async def _get_access_token(self) -> str:
        if (
            self._access_token is not None
            and datetime.now(UTC) < self._access_token.expires_at
        ):
            return self._access_token.value

        body = await self._fetch_access_token()
        errcode = body.get("errcode")
        if errcode != 0:
            raise RuntimeError(
                f"WeCom gettoken failed: errcode={errcode}, errmsg={body.get('errmsg')}"
            )

        token = str(body.get("access_token") or "").strip()
        if not token:
            raise RuntimeError("WeCom gettoken returned blank access_token")

        expires_in = int(body.get("expires_in") or 7200)
        self._access_token = WecomAccessToken(
            value=token,
            expires_at=datetime.now(UTC)
            + timedelta(seconds=max(expires_in - TOKEN_REFRESH_SKEW_SECONDS, 0)),
        )
        return token

    async def _fetch_access_token(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=WECOM_REQUEST_TIMEOUT_SECONDS) as client:
            response = await client.get(
                f"{WECOM_API_BASE_URL}/gettoken",
                params={"corpid": self.corp_id, "corpsecret": self.secret},
            )
            response.raise_for_status()
            data = response.json()
        if not isinstance(data, dict):
            raise RuntimeError("WeCom gettoken returned non-object response")
        return data


wecom_service = WecomService()
