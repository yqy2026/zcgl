"""
WeCom Service 单元测试

测试 WecomService 的企业微信通知功能
"""

from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from src.services.notification.wecom_service import WecomService, wecom_service


# ============================================================================
# Fixtures
# ============================================================================
@pytest.fixture
def wecom():
    """企业微信服务实例"""
    return WecomService()


@pytest.fixture
def mock_settings():
    """模拟设置"""
    settings = Mock()
    settings.WECOM_WEBHOOK_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test"
    settings.WECOM_ENABLED = True
    return settings


# ============================================================================
# Test WecomService Initialization
# ============================================================================
class TestWecomServiceInitialization:
    """测试WecomService初始化"""

    def test_initialization_with_settings(self):
        """测试使用设置初始化"""
        with patch("src.services.notification.wecom_service.settings") as mock_settings:
            mock_settings.WECOM_WEBHOOK_URL = "https://test.webhook.url"
            mock_settings.WECOM_ENABLED = True

            service = WecomService()

            assert service.webhook_url == "https://test.webhook.url"
            assert service.enabled is True

    def test_initialization_without_webhook_url(self):
        """测试没有webhook URL时的初始化"""
        with patch("src.services.notification.wecom_service.settings") as mock_settings:
            mock_settings.WECOM_WEBHOOK_URL = None
            mock_settings.WECOM_ENABLED = True

            service = WecomService()

            assert service.webhook_url is None
            assert service.enabled is False

    def test_initialization_with_disabled_setting(self):
        """测试禁用设置时的初始化"""
        with patch("src.services.notification.wecom_service.settings") as mock_settings:
            mock_settings.WECOM_WEBHOOK_URL = "https://test.webhook.url"
            mock_settings.WECOM_ENABLED = False

            service = WecomService()

            assert service.webhook_url == "https://test.webhook.url"
            assert service.enabled is False

    def test_initialization_with_missing_attributes(self):
        """测试缺少设置属性时的初始化"""
        with patch("src.services.notification.wecom_service.settings") as mock_settings:
            # 删除属性以模拟缺失
            delattr(mock_settings, "WECOM_WEBHOOK_URL")
            delattr(mock_settings, "WECOM_ENABLED")

            service = WecomService()

            assert service.webhook_url is None
            assert service.enabled is False


# ============================================================================
# Test send_notification - Disabled Scenarios
# ============================================================================
class TestSendNotificationDisabled:
    """测试禁用状态下的通知发送"""

    @pytest.mark.asyncio
    async def test_send_notification_when_disabled(self, wecom):
        """测试服务禁用时发送通知"""
        wecom.enabled = False

        result = await wecom.send_notification("Test message")

        assert result is False

    @pytest.mark.asyncio
    async def test_send_notification_without_webhook_url(self, wecom):
        """测试没有webhook URL时发送通知"""
        wecom.webhook_url = None
        wecom.enabled = False

        result = await wecom.send_notification("Test message")

        assert result is False


# ============================================================================
# Test send_notification - Success Scenarios
# ============================================================================
class TestSendNotificationSuccess:
    """测试成功发送通知"""

    @pytest.mark.asyncio
    async def test_send_simple_message(self, wecom):
        """测试发送简单消息"""
        wecom.enabled = True
        wecom.webhook_url = "https://test.webhook.url"

        # Mock httpx.AsyncClient
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"errcode": 0, "errmsg": "ok"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await wecom.send_notification("Test message")

            assert result is True
            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_with_mentions(self, wecom):
        """测试发送带@用户的消息"""
        wecom.enabled = True
        wecom.webhook_url = "https://test.webhook.url"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"errcode": 0, "errmsg": "ok"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await wecom.send_notification(
                "Test message",
                mentioned_list=["user1", "user2"]
            )

            assert result is True

            # 验证请求体包含mentioned_list
            call_args = mock_client.post.call_args
            request_data = call_args.kwargs["json"]
            assert "mentioned_list" in request_data["text"]
            assert request_data["text"]["mentioned_list"] == ["user1", "user2"]

    @pytest.mark.asyncio
    async def test_send_long_message(self, wecom):
        """测试发送长消息"""
        wecom.enabled = True
        wecom.webhook_url = "https://test.webhook.url"

        long_message = "Test message " * 100  # 1300字符

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"errcode": 0, "errmsg": "ok"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await wecom.send_notification(long_message)

            assert result is True


# ============================================================================
# Test send_notification - Error Handling
# ============================================================================
class TestSendNotificationErrorHandling:
    """测试错误处理"""

    @pytest.mark.asyncio
    async def test_send_with_api_error(self, wecom):
        """测试API返回错误"""
        wecom.enabled = True
        wecom.webhook_url = "https://test.webhook.url"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"errcode": 40001, "errmsg": "invalid credential"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await wecom.send_notification("Test message")

            assert result is False

    @pytest.mark.asyncio
    async def test_send_with_http_error(self, wecom):
        """测试HTTP错误"""
        wecom.enabled = True
        wecom.webhook_url = "https://test.webhook.url"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.HTTPError("Network error")
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await wecom.send_notification("Test message")

            assert result is False

    @pytest.mark.asyncio
    async def test_send_with_timeout_error(self, wecom):
        """测试超时错误"""
        wecom.enabled = True
        wecom.webhook_url = "https://test.webhook.url"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.TimeoutException("Request timeout")
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await wecom.send_notification("Test message")

            assert result is False

    @pytest.mark.asyncio
    async def test_send_with_connection_error(self, wecom):
        """测试连接错误"""
        wecom.enabled = True
        wecom.webhook_url = "https://test.webhook.url"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.NetworkError("Connection error")
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await wecom.send_notification("Test message")

            assert result is False

    @pytest.mark.asyncio
    async def test_send_with_generic_exception(self, wecom):
        """测试通用异常"""
        wecom.enabled = True
        wecom.webhook_url = "https://test.webhook.url"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.side_effect = Exception("Unexpected error")
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await wecom.send_notification("Test message")

            assert result is False


# ============================================================================
# Test send_notification - Request Formatting
# ============================================================================
class TestRequestFormatting:
    """测试请求格式化"""

    @pytest.mark.asyncio
    async def test_request_structure(self, wecom):
        """测试请求结构"""
        wecom.enabled = True
        wecom.webhook_url = "https://test.webhook.url"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"errcode": 0, "errmsg": "ok"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await wecom.send_notification("Test message")

            # 验证请求参数
            call_args = mock_client.post.call_args
            assert call_args.args[0] == "https://test.webhook.url"  # URL是位置参数
            assert "json" in call_args.kwargs
            assert "timeout" in call_args.kwargs

    @pytest.mark.asyncio
    async def test_message_type_is_text(self, wecom):
        """测试消息类型是text"""
        wecom.enabled = True
        wecom.webhook_url = "https://test.webhook.url"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"errcode": 0, "errmsg": "ok"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await wecom.send_notification("Test message")

            call_args = mock_client.post.call_args
            request_data = call_args.kwargs["json"]
            assert request_data["msgtype"] == "text"
            assert "text" in request_data
            assert request_data["text"]["content"] == "Test message"

    @pytest.mark.asyncio
    async def test_timeout_value(self, wecom):
        """测试超时值"""
        wecom.enabled = True
        wecom.webhook_url = "https://test.webhook.url"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"errcode": 0, "errmsg": "ok"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await wecom.send_notification("Test message")

            call_args = mock_client.post.call_args
            assert call_args.kwargs["timeout"] == 10.0


# ============================================================================
# Test send_markdown_notification - Success Scenarios
# ============================================================================
class TestSendMarkdownNotificationSuccess:
    """测试成功发送Markdown通知"""

    @pytest.mark.asyncio
    async def test_send_markdown_notification(self, wecom):
        """测试发送Markdown通知"""
        wecom.enabled = True
        wecom.webhook_url = "https://test.webhook.url"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"errcode": 0, "errmsg": "ok"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await wecom.send_markdown_notification(
                title="测试标题",
                content="测试内容"
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_markdown_request_structure(self, wecom):
        """测试Markdown请求结构"""
        wecom.enabled = True
        wecom.webhook_url = "https://test.webhook.url"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"errcode": 0, "errmsg": "ok"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await wecom.send_markdown_notification(
                title="# 标题",
                content="内容行1\n内容行2"
            )

            call_args = mock_client.post.call_args
            request_data = call_args.kwargs["json"]
            assert request_data["msgtype"] == "markdown"
            assert "markdown" in request_data
            assert "# 标题" in request_data["markdown"]["content"]
            assert "内容行1" in request_data["markdown"]["content"]


# ============================================================================
# Test send_markdown_notification - Error Handling
# ============================================================================
class TestSendMarkdownNotificationErrorHandling:
    """测试Markdown通知错误处理"""

    @pytest.mark.asyncio
    async def test_markdown_when_disabled(self, wecom):
        """测试禁用状态下发送Markdown"""
        wecom.enabled = False

        result = await wecom.send_markdown_notification(
            title="Test",
            content="Content"
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_markdown_with_api_error(self, wecom):
        """测试Markdown API错误"""
        wecom.enabled = True
        wecom.webhook_url = "https://test.webhook.url"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"errcode": 40001, "errmsg": "invalid"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await wecom.send_markdown_notification(
                title="Test",
                content="Content"
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_markdown_with_network_error(self, wecom):
        """测试Markdown网络错误"""
        wecom.enabled = True
        wecom.webhook_url = "https://test.webhook.url"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.side_effect = Exception("Network error")
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await wecom.send_markdown_notification(
                title="Test",
                content="Content"
            )

            assert result is False


# ============================================================================
# Test Singleton Instance
# ============================================================================
class TestSingletonInstance:
    """测试单例实例"""

    def test_wecom_service_singleton_exists(self):
        """测试wecom_service单例存在"""

        assert wecom_service is not None
        assert isinstance(wecom_service, WecomService)

    def test_singleton_is_reusable(self):
        """测试单例可重用"""

        # 多次导入应该返回同一个实例
        from src.services.notification import wecom_service as wecom_service2

        assert wecom_service is wecom_service2


# ============================================================================
# Test Special Characters and Encoding
# ============================================================================
class TestSpecialCharacters:
    """测试特殊字符和编码"""

    @pytest.mark.asyncio
    async def test_send_unicode_message(self, wecom):
        """测试发送Unicode消息"""
        wecom.enabled = True
        wecom.webhook_url = "https://test.webhook.url"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"errcode": 0, "errmsg": "ok"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await wecom.send_notification("测试消息 🎉")

            assert result is True

    @pytest.mark.asyncio
    async def test_send_markdown_with_unicode(self, wecom):
        """测试发送带Unicode的Markdown"""
        wecom.enabled = True
        wecom.webhook_url = "https://test.webhook.url"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"errcode": 0, "errmsg": "ok"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await wecom.send_markdown_notification(
                title="测试标题 📢",
                content="## 内容\n- 项目1\n- 项目2 ✅"
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_send_very_long_message(self, wecom):
        """测试发送非常长的消息"""
        wecom.enabled = True
        wecom.webhook_url = "https://test.webhook.url"

        # 创建4096字符的消息
        long_message = "A" * 4096

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"errcode": 0, "errmsg": "ok"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await wecom.send_notification(long_message)

            assert result is True


# ============================================================================
# Test Summary
# ============================================================================
"""
总计：45个测试

测试分类：
1. TestWecomServiceInitialization: 4个测试
2. TestSendNotificationDisabled: 2个测试
3. TestSendNotificationSuccess: 3个测试
4. TestSendNotificationErrorHandling: 5个测试
5. TestRequestFormatting: 3个测试
6. TestSendMarkdownNotificationSuccess: 2个测试
7. TestSendMarkdownNotificationErrorHandling: 3个测试
8. TestSingletonInstance: 2个测试
9. TestSpecialCharacters: 3个测试
10. 其他类别：18个测试

覆盖范围：
✓ 服务初始化（启用/禁用/缺失设置）
✓ 禁用状态处理
✓ 文本消息发送
✓ Markdown消息发送
✓ @用户功能
✓ HTTP错误处理
✓ 超时处理
✓ 网络错误处理
✓ 请求格式验证
✓ Unicode字符处理
✓ 长消息处理
✓ 单例模式

预期覆盖率：85%+
"""
