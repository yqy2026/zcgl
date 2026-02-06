"""
AutoOptimizer async unit tests
"""

from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.exception_handler import ResourceNotFoundError
from src.models.llm_prompt import ExtractionFeedback, PromptTemplate
from src.services.llm_prompt.auto_optimizer import AutoOptimizer

pytestmark = pytest.mark.asyncio


def _result_with_scalar(value):
    result = MagicMock()
    result.scalar.return_value = value
    return result


def _result_with_all(values):
    result = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = values
    result.scalars.return_value = scalars
    return result


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.execute = AsyncMock()
    db.get = AsyncMock()
    db.commit = AsyncMock()
    return db


class TestAutoOptimizerAsync:
    async def test_check_and_optimize_all_no_prompts(self, mock_db):
        optimizer = AutoOptimizer(min_feedback_count=1, accuracy_threshold=0.5)
        mock_db.execute.return_value = _result_with_all([])

        result = await optimizer.check_and_optimize_all(mock_db)

        assert result == []

    async def test_check_and_optimize_all_runs_optimizer(self, mock_db):
        optimizer = AutoOptimizer(min_feedback_count=1, accuracy_threshold=0.5)
        prompt = MagicMock(spec=PromptTemplate)
        prompt.id = 'prompt-1'
        prompt.name = 'p1'
        mock_db.execute.return_value = _result_with_all([prompt])

        optimizer._should_optimize = AsyncMock(return_value=(True, 'reason'))
        optimizer.optimize_prompt = AsyncMock(return_value={'success': True})

        result = await optimizer.check_and_optimize_all(mock_db)

        assert result == [{'success': True}]

    async def test_should_optimize_by_feedback_count(self, mock_db):
        optimizer = AutoOptimizer(min_feedback_count=2, accuracy_threshold=0.9)
        prompt = SimpleNamespace(id='p1')

        mock_db.execute.side_effect = [
            _result_with_scalar(3),
            _result_with_scalar(1.0),
        ]

        should_optimize, reason = await optimizer._should_optimize(mock_db, prompt)

        assert should_optimize is True
        assert '反馈' in reason

    async def test_should_optimize_by_accuracy(self, mock_db):
        optimizer = AutoOptimizer(min_feedback_count=50, accuracy_threshold=0.9)
        prompt = SimpleNamespace(id='p1')

        mock_db.execute.side_effect = [
            _result_with_scalar(0),
            _result_with_scalar(0.5),
        ]

        should_optimize, reason = await optimizer._should_optimize(mock_db, prompt)

        assert should_optimize is True
        assert '准确率' in reason

    async def test_optimize_prompt_no_feedback(self, mock_db):
        optimizer = AutoOptimizer(min_feedback_count=1, accuracy_threshold=0.5)
        mock_db.execute.return_value = _result_with_all([])

        result = await optimizer.optimize_prompt(mock_db, 'prompt-1')

        assert result['success'] is False

    async def test_optimize_prompt_missing_template(self, mock_db):
        optimizer = AutoOptimizer(min_feedback_count=1, accuracy_threshold=0.5)
        feedback = MagicMock(spec=ExtractionFeedback)
        feedback.template_id = 'prompt-1'
        feedback.created_at = datetime.utcnow() - timedelta(days=1)

        mock_db.execute.return_value = _result_with_all([feedback])
        mock_db.get.return_value = None

        with pytest.raises(ResourceNotFoundError):
            await optimizer.optimize_prompt(mock_db, 'prompt-1')
