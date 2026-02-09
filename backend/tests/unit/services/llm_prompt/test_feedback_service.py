"""
反馈服务单元测试 (异步)
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.exception_handler import ResourceNotFoundError
from src.services.llm_prompt import feedback_service as feedback_service_module
from src.services.llm_prompt.feedback_service import FeedbackService

pytestmark = pytest.mark.asyncio


def test_feedback_service_module_avoids_datetime_utcnow() -> None:
    """服务模块不应直接调用 datetime.utcnow."""
    module_path = Path(feedback_service_module.__file__)
    content = module_path.read_text(encoding="utf-8")

    assert "datetime.utcnow(" not in content


class TestFeedbackServiceInit:
    def test_init_with_custom_prompt_manager(self):
        mock_pm = MagicMock()
        service = FeedbackService(prompt_manager=mock_pm)
        assert service.prompt_manager is mock_pm


class TestCollectAsync:
    @pytest.fixture
    def service(self):
        mock_pm = MagicMock()
        mock_pm.get_by_id_async = AsyncMock(return_value=None)
        return FeedbackService(prompt_manager=mock_pm)

    @pytest.fixture
    def mock_db(self):
        mock_db = MagicMock()
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        return mock_db

    @pytest.fixture
    def feedback_create(self):
        mock_feedback = MagicMock()
        mock_feedback.template_id = 'template-123'
        mock_feedback.version_id = 'version-456'
        mock_feedback.doc_type = 'contract'
        mock_feedback.file_path = '/path/to/file.pdf'
        mock_feedback.session_id = 'session-789'
        mock_feedback.field_name = 'tenant_name'
        mock_feedback.original_value = '原始值'
        mock_feedback.corrected_value = '修正值'
        mock_feedback.confidence_before = 0.85
        mock_feedback.user_action = 'correct'
        return mock_feedback

    async def test_collect_template_not_exists(self, service, mock_db, feedback_create):
        service.prompt_manager.get_by_id_async.return_value = None

        with pytest.raises(ResourceNotFoundError, match='Prompt'):
            await service.collect_async(
                db=mock_db, feedback_in=feedback_create, user_id='user-001'
            )

    async def test_collect_success(self, service, mock_db, feedback_create):
        template = MagicMock()
        template.current_version_id = 'version-456'
        service.prompt_manager.get_by_id_async.return_value = template

        result = await service.collect_async(
            db=mock_db, feedback_in=feedback_create, user_id='user-001'
        )

        assert result.template_id == feedback_create.template_id
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once()


class TestGetByTemplateAsync:
    async def test_get_by_template_returns_feedbacks(self):
        service = FeedbackService(prompt_manager=MagicMock())
        mock_db = MagicMock()
        mock_db.execute = AsyncMock()

        result_proxy = MagicMock()
        result_proxy.scalars.return_value.all.return_value = [MagicMock(), MagicMock()]
        mock_db.execute.return_value = result_proxy

        result = await service.get_by_template_async(
            db=mock_db, template_id='template-123', limit=100
        )

        assert len(result) == 2

    async def test_get_by_template_empty_result(self):
        service = FeedbackService(prompt_manager=MagicMock())
        mock_db = MagicMock()
        mock_db.execute = AsyncMock()

        result_proxy = MagicMock()
        result_proxy.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = result_proxy

        result = await service.get_by_template_async(
            db=mock_db, template_id='nonexistent-template'
        )

        assert result == []
