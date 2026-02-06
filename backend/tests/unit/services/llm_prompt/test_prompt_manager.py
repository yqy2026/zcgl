"""
PromptManager async unit tests
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.exception_handler import DuplicateResourceError, ResourceNotFoundError
from src.models.llm_prompt import PromptStatus, PromptTemplate
from src.schemas.llm_prompt import PromptTemplateCreate, PromptTemplateUpdate
from src.services.llm_prompt.prompt_manager import PromptManager

pytestmark = pytest.mark.asyncio


def _result_with_first(value):
    result = MagicMock()
    scalars = MagicMock()
    scalars.first.return_value = value
    result.scalars.return_value = scalars
    return result


def _result_with_all(values):
    result = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = values
    result.scalars.return_value = scalars
    return result


def _result_with_scalar(value):
    result = MagicMock()
    result.scalar.return_value = value
    return result


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.get = AsyncMock()
    return db


class TestPromptManagerAsync:
    async def test_get_active_prompt_async_found(self, mock_db):
        manager = PromptManager()
        prompt = MagicMock(spec=PromptTemplate)
        prompt.name = 'Test'
        prompt.version = 'v1.0.0'
        mock_db.execute.return_value = _result_with_first(prompt)

        result = await manager.get_active_prompt_async(
            mock_db, doc_type='CONTRACT', provider='qwen'
        )

        assert result is prompt

    async def test_get_active_prompt_async_not_found(self, mock_db):
        manager = PromptManager()
        mock_db.execute.return_value = _result_with_first(None)

        result = await manager.get_active_prompt_async(mock_db, doc_type='CONTRACT')

        assert result is None

    async def test_create_prompt_async_duplicate(self, mock_db):
        manager = PromptManager()
        existing = MagicMock()
        mock_db.execute.return_value = _result_with_first(existing)

        with pytest.raises(DuplicateResourceError):
            await manager.create_prompt_async(
                mock_db,
                PromptTemplateCreate(
                    name='dup',
                    doc_type='CONTRACT',
                    provider='qwen',
                    system_prompt='sys',
                    user_prompt_template='user',
                ),
            )

    async def test_create_prompt_async_success(self, mock_db):
        manager = PromptManager()
        mock_db.execute.return_value = _result_with_first(None)

        data = PromptTemplateCreate(
            name='new',
            doc_type='CONTRACT',
            provider='qwen',
            system_prompt='sys',
            user_prompt_template='user',
        )

        result = await manager.create_prompt_async(mock_db, data, user_id='u1')

        assert result.name == 'new'
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once()

    async def test_update_prompt_async_not_found(self, mock_db):
        manager = PromptManager()
        mock_db.get.return_value = None

        with pytest.raises(ResourceNotFoundError):
            await manager.update_prompt_async(
                mock_db, 'missing', PromptTemplateUpdate()
            )

    async def test_update_prompt_async_success(self, mock_db):
        manager = PromptManager()
        template = MagicMock(spec=PromptTemplate)
        template.version = 'v1.0.0'
        template.system_prompt = 'sys'
        template.user_prompt_template = 'user'
        template.few_shot_examples = {}
        mock_db.get.return_value = template

        result = await manager.update_prompt_async(
            mock_db,
            'tmpl-1',
            PromptTemplateUpdate(system_prompt='new'),
        )

        assert result is template
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once()

    async def test_activate_prompt_async_not_found(self, mock_db):
        manager = PromptManager()
        mock_db.get.return_value = None

        with pytest.raises(ResourceNotFoundError):
            await manager.activate_prompt_async(mock_db, 'missing')

    async def test_list_templates_async(self, mock_db):
        manager = PromptManager()
        mock_db.execute.side_effect = [
            _result_with_scalar(2),
            _result_with_all([MagicMock(), MagicMock()]),
        ]

        result = await manager.list_templates_async(
            mock_db, doc_type='CONTRACT', page=1, page_size=2
        )

        assert result['total'] == 2
        assert len(result['items']) == 2

    async def test_get_statistics_async(self, mock_db):
        manager = PromptManager()
        mock_db.execute.side_effect = [
            _result_with_scalar(3),
            MagicMock(all=MagicMock(return_value=[(PromptStatus.ACTIVE, 2)])),
            MagicMock(all=MagicMock(return_value=[('CONTRACT', 3)])),
            MagicMock(all=MagicMock(return_value=[('qwen', 3)])),
            _result_with_scalar(0.9),
            _result_with_scalar(0.8),
        ]

        result = await manager.get_statistics_async(mock_db)

        assert result['total_prompts'] == 3
        assert result['overall_avg_accuracy'] == 0.9
        assert result['overall_avg_confidence'] == 0.8


class TestIncrementVersion:
    def test_increment_version(self):
        assert PromptManager._increment_version('v1.0.0') == 'v1.0.1'
        assert PromptManager._increment_version('v2.5.9') == 'v2.5.10'
        assert PromptManager._increment_version('invalid') == 'invalid.1'
