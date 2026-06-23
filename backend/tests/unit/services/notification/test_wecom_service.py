from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.services.notification.wecom_service import WecomService, wecom_service


class _AsyncClientContext:
    def __init__(self, client: Mock) -> None:
        self.client = client

    async def __aenter__(self) -> Mock:
        return self.client

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


def _response(body: dict[str, object]) -> Mock:
    response = Mock()
    response.raise_for_status = Mock()
    response.json.return_value = body
    return response


def _configured_service() -> WecomService:
    service = WecomService()
    service.enabled = True
    service.corp_id = "corp-id"
    service.agent_id = "1000011"
    service.secret = "secret-value"
    return service


class TestWecomServiceInitialization:
    def test_service_reads_application_message_settings(self):
        service = WecomService()

        assert hasattr(service, "enabled")
        assert hasattr(service, "corp_id")
        assert hasattr(service, "agent_id")
        assert hasattr(service, "secret")


class TestSendNotification:
    @pytest.mark.asyncio
    async def test_send_notification_skips_http_when_not_configured(self):
        service = WecomService()
        service.enabled = True
        service.corp_id = None

        with patch("httpx.AsyncClient") as mock_client_class:
            result = await service.send_notification("Business body", touser="user1")

        assert result is False
        mock_client_class.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_notification_gets_token_and_sends_to_explicit_user(self):
        service = _configured_service()
        client = Mock()
        client.get = AsyncMock(
            return_value=_response(
                {"errcode": 0, "access_token": "token-value", "expires_in": 7200}
            )
        )
        client.post = AsyncMock(return_value=_response({"errcode": 0, "errmsg": "ok"}))

        with patch(
            "httpx.AsyncClient",
            return_value=_AsyncClientContext(client),
        ):
            result = await service.send_notification("Business body", touser="user1")

        assert result is True
        client.get.assert_awaited_once()
        client.post.assert_awaited_once()
        _, post_kwargs = client.post.call_args
        assert post_kwargs["params"] == {"access_token": "token-value"}
        assert post_kwargs["json"]["touser"] == "user1"
        assert post_kwargs["json"]["agentid"] == "1000011"
        assert post_kwargs["json"]["msgtype"] == "text"
        assert post_kwargs["json"]["text"] == {"content": "Business body"}

    @pytest.mark.asyncio
    async def test_send_notification_reuses_cached_token(self):
        service = _configured_service()
        service._access_token = type(
            "Token",
            (),
            {
                "value": "cached-token",
                "expires_at": datetime.now(UTC) + timedelta(minutes=10),
            },
        )()
        client = Mock()
        client.get = AsyncMock()
        client.post = AsyncMock(return_value=_response({"errcode": 0, "errmsg": "ok"}))

        with patch(
            "httpx.AsyncClient",
            return_value=_AsyncClientContext(client),
        ):
            result = await service.send_notification("Business body", touser="user1")

        assert result is True
        client.get.assert_not_awaited()
        client.post.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_notification_returns_false_on_wecom_error(self):
        service = _configured_service()
        service._access_token = type(
            "Token",
            (),
            {
                "value": "cached-token",
                "expires_at": datetime.now(UTC) + timedelta(minutes=10),
            },
        )()
        client = Mock()
        client.post = AsyncMock(
            return_value=_response({"errcode": 40003, "errmsg": "invalid touser"})
        )

        with patch(
            "httpx.AsyncClient",
            return_value=_AsyncClientContext(client),
        ):
            result = await service.send_notification("Business body", touser="bad-user")

        assert result is False


class TestSingletonInstance:
    def test_wecom_service_singleton_exists(self):
        assert wecom_service is not None
        assert isinstance(wecom_service, WecomService)

    def test_singleton_is_reusable(self):
        from src.services.notification import wecom_service as wecom_service2

        assert wecom_service is wecom_service2
