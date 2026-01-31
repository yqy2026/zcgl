"""
反馈服务单元测试

测试 FeedbackService 的所有主要方法
"""

from unittest.mock import MagicMock

import pytest

from src.core.exception_handler import ResourceNotFoundError
from src.services.llm_prompt.feedback_service import FeedbackService


class TestFeedbackServiceInit:
    """测试 FeedbackService 初始化"""

    def test_init_with_custom_prompt_manager(self):
        """测试使用自定义 PromptManager 初始化"""
        mock_pm = MagicMock()
        service = FeedbackService(prompt_manager=mock_pm)
        assert service.prompt_manager is mock_pm


class TestCollect:
    """测试 collect 方法"""

    @pytest.fixture
    def service(self):
        """创建测试服务实例"""
        mock_pm = MagicMock()
        return FeedbackService(prompt_manager=mock_pm)

    @pytest.fixture
    def mock_db(self):
        """使用Mock数据库会话"""
        mock_db = MagicMock()
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()
        return mock_db

    @pytest.fixture
    def feedback_create(self):
        """创建测试反馈数据"""
        mock_feedback = MagicMock()
        mock_feedback.template_id = "template-123"
        mock_feedback.version_id = "version-456"
        mock_feedback.doc_type = "contract"
        mock_feedback.file_path = "/path/to/file.pdf"
        mock_feedback.session_id = "session-789"
        mock_feedback.field_name = "tenant_name"
        mock_feedback.original_value = "原始值"
        mock_feedback.corrected_value = "修正值"
        mock_feedback.confidence_before = 0.85
        mock_feedback.user_action = "correct"
        return mock_feedback

    def test_collect_template_not_exists(self, service, mock_db, feedback_create):
        """测试模板不存在时抛出异常"""
        service.prompt_manager.get_by_id.return_value = None

        with pytest.raises(ResourceNotFoundError, match="Prompt"):
            service.collect(db=mock_db, feedback_in=feedback_create, user_id="user-001")


class TestGetByTemplate:
    """测试 get_by_template 方法"""

    @pytest.fixture
    def service(self):
        """创建测试服务实例"""
        mock_pm = MagicMock()
        return FeedbackService(prompt_manager=mock_pm)

    def test_get_by_template_returns_feedbacks(self, service):
        """测试获取模板反馈列表"""
        mock_db = MagicMock()
        mock_feedbacks = [MagicMock(), MagicMock(), MagicMock()]

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_feedbacks

        result = service.get_by_template(
            db=mock_db, template_id="template-123", limit=100
        )

        assert len(result) == 3

    def test_get_by_template_empty_result(self, service):
        """测试没有反馈时返回空列表"""
        mock_db = MagicMock()

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        result = service.get_by_template(db=mock_db, template_id="nonexistent-template")

        assert result == []
