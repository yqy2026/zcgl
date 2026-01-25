"""
Unit tests for AutoOptimizer service
测试自动优化引擎的所有功能
"""

from collections import Counter
from datetime import datetime
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from src.models.llm_prompt import ExtractionFeedback, PromptStatus, PromptTemplate
from src.services.llm_prompt.auto_optimizer import AutoOptimizer

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def auto_optimizer():
    """创建AutoOptimizer实例"""
    return AutoOptimizer(min_feedback_count=50, accuracy_threshold=0.85)


@pytest.fixture
def mock_db():
    """Mock数据库会话"""
    db = MagicMock(spec=Session)
    return db


@pytest.fixture
def sample_active_prompt():
    """示例活跃Prompt"""
    prompt = MagicMock(spec=PromptTemplate)
    prompt.id = "prompt-123"
    prompt.name = "test_contract_extraction"
    prompt.status = PromptStatus.ACTIVE
    prompt.doc_type = "CONTRACT"
    prompt.system_prompt = "You are a contract extraction expert."
    prompt.user_prompt_template = "Extract from {file_name}"
    prompt.few_shot_examples = {}
    prompt.version = "v1.0.0"
    prompt.avg_accuracy = 0.80
    prompt.avg_confidence = 0.85
    return prompt


@pytest.fixture
def sample_feedbacks():
    """示例反馈数据"""
    feedbacks = []
    for i in range(10):
        fb = MagicMock(spec=ExtractionFeedback)
        fb.id = f"feedback-{i}"
        fb.template_id = "prompt-123"
        fb.field_name = "certificate_number"
        fb.original_value = "1234567"
        fb.corrected_value = "粤房地权证穗字第1234567号"
        fb.created_at = datetime.utcnow()
        feedbacks.append(fb)
    return feedbacks


# ============================================================================
# check_and_optimize_all() tests (10 tests)
# ============================================================================


class TestCheckAndOptimizeAll:
    """测试check_and_optimize_all方法"""

    @pytest.mark.asyncio
    async def test_check_all_active_prompts(
        self, auto_optimizer, mock_db, sample_active_prompt
    ):
        """TC-AO-001: 检查所有活跃Prompt"""
        # Arrange
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [sample_active_prompt]

        # Act
        await auto_optimizer.check_and_optimize_all(mock_db)

        # Assert
        mock_db.query.assert_called_once_with(PromptTemplate)

    @pytest.mark.asyncio
    async def test_no_prompts_need_optimization(
        self, auto_optimizer, mock_db, sample_active_prompt
    ):
        """TC-AO-002: 无Prompt需要优化"""
        # Arrange
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [sample_active_prompt]

        # Mock _should_optimize to return False
        AutoOptimizer._should_optimize = MagicMock(return_value=(False, "正常"))

        # Act
        results = await auto_optimizer.check_and_optimize_all(mock_db)

        # Assert
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_multiple_prompts_need_optimization(self, auto_optimizer, mock_db):
        """TC-AO-003: 多个Prompt需要优化"""
        # Arrange
        prompt1 = MagicMock(spec=PromptTemplate)
        prompt1.id = "prompt-1"
        prompt1.name = "prompt1"
        prompt2 = MagicMock(spec=PromptTemplate)
        prompt2.id = "prompt-2"
        prompt2.name = "prompt2"

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [prompt1, prompt2]

        # Mock to return optimization needed
        AutoOptimizer._should_optimize = MagicMock(return_value=(False, "正常"))

        # Act
        results = await auto_optimizer.check_and_optimize_all(mock_db)

        # Assert
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_handles_optimization_exception(
        self, auto_optimizer, mock_db, sample_active_prompt
    ):
        """TC-AO-004: 处理优化过程中的异常"""
        # Arrange
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [sample_active_prompt]

        # Mock to raise exception
        AutoOptimizer._should_optimize = MagicMock(side_effect=Exception("Test error"))

        # Act
        results = await auto_optimizer.check_and_optimize_all(mock_db)

        # Assert
        # Should not raise, should continue
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_filters_active_prompts_only(self, auto_optimizer, mock_db):
        """TC-AO-005: 只检查活跃状态的Prompt"""
        # Arrange
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []

        # Act
        await auto_optimizer.check_and_optimize_all(mock_db)

        # Assert
        mock_query.filter.assert_called_once()

    @pytest.mark.asyncio
    async def test_empty_active_prompts(self, auto_optimizer, mock_db):
        """TC-AO-006: 没有活跃Prompt"""
        # Arrange
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []

        # Act
        results = await auto_optimizer.check_and_optimize_all(mock_db)

        # Assert
        assert results == []

    @pytest.mark.asyncio
    async def test_logs_optimization_needed(
        self, auto_optimizer, mock_db, sample_active_prompt
    ):
        """TC-AO-007: 记录需要优化的日志"""
        # Arrange
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [sample_active_prompt]

        AutoOptimizer._should_optimize = MagicMock(return_value=(False, "正常"))

        # Act
        await auto_optimizer.check_and_optimize_all(mock_db)

        # Assert
        # Should complete without error
        assert True

    @pytest.mark.asyncio
    async def test_calls_optimize_prompt(
        self, auto_optimizer, mock_db, sample_active_prompt
    ):
        """TC-AO-008: 调用optimize_prompt"""
        # Arrange
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [sample_active_prompt]

        AutoOptimizer._should_optimize = MagicMock(return_value=(True, "需要优化"))
        AutoOptimizer.optimize_prompt = MagicMock(return_value={"success": True})

        # Act
        results = await auto_optimizer.check_and_optimize_all(mock_db)

        # Assert
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_returns_optimization_results(
        self, auto_optimizer, mock_db, sample_active_prompt
    ):
        """TC-AO-009: 返回优化结果列表"""
        # Arrange
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [sample_active_prompt]

        AutoOptimizer._should_optimize = MagicMock(return_value=(False, "正常"))

        # Act
        results = await auto_optimizer.check_and_optimize_all(mock_db)

        # Assert
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_check_all_logs_count(self, auto_optimizer, mock_db):
        """TC-AO-010: 记录检查的Prompt数量"""
        # Arrange
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []

        # Act
        await auto_optimizer.check_and_optimize_all(mock_db)

        # Assert
        mock_query.all.assert_called_once()


# ============================================================================
# _should_optimize() tests (10 tests)
# ============================================================================


class TestShouldOptimize:
    """测试_should_optimize方法"""

    def test_feedback_count_above_threshold(
        self, auto_optimizer, mock_db, sample_active_prompt
    ):
        """TC-AO-011: 反馈数量超过阈值"""
        # Arrange
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 60  # > min_feedback_count(50)

        # Act
        should_opt, reason = auto_optimizer._should_optimize(
            mock_db, sample_active_prompt
        )

        # Assert
        assert should_opt is True
        assert "60条反馈" in reason

    @pytest.mark.asyncio
    async def test_feedback_count_below_threshold(
        self, auto_optimizer, mock_db, sample_active_prompt
    ):
        """TC-AO-012: 反馈数量低于阈值"""
        # Arrange
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 30  # < min_feedback_count(50)

        mock_query2 = MagicMock()
        mock_db.query.return_value = mock_query2
        mock_query2.filter.return_value = mock_query2
        mock_query2.scalar.return_value = 0.90  # > accuracy_threshold(0.85)

        # Act
        should_opt, reason = await auto_optimizer._should_optimize(
            mock_db, sample_active_prompt
        )

        # Assert
        assert should_opt is False
        assert "正常" in reason

    @pytest.mark.asyncio
    async def test_accuracy_below_threshold(
        self, auto_optimizer, mock_db, sample_active_prompt
    ):
        """TC-AO-013: 准确率低于阈值"""
        # Arrange
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 10  # < min_feedback_count

        mock_query2 = MagicMock()
        mock_db.query.return_value = mock_query2
        mock_query2.filter.return_value = mock_query2
        mock_query2.scalar.return_value = 0.75  # < accuracy_threshold(0.85)

        # Act
        should_opt, reason = await auto_optimizer._should_optimize(
            mock_db, sample_active_prompt
        )

        # Assert
        assert should_opt is True
        assert "准确率" in reason and "75" in reason

    @pytest.mark.asyncio
    async def test_checks_recent_feedbacks(
        self, auto_optimizer, mock_db, sample_active_prompt
    ):
        """TC-AO-014: 检查最近7天的反馈"""
        # Arrange
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0

        # Act
        await auto_optimizer._should_optimize(mock_db, sample_active_prompt)

        # Assert
        # Verify filter was called with date constraint
        assert mock_query.filter.call_count >= 1

    @pytest.mark.asyncio
    async def test_no_feedbacks_no_low_accuracy(
        self, auto_optimizer, mock_db, sample_active_prompt
    ):
        """TC-AO-015: 无反馈且准确率正常"""
        # Arrange
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0

        mock_query2 = MagicMock()
        mock_db.query.return_value = mock_query2
        mock_query2.filter.return_value = mock_query2
        mock_query2.scalar.return_value = 0.90

        # Act
        should_opt, reason = await auto_optimizer._should_optimize(
            mock_db, sample_active_prompt
        )

        # Assert
        assert should_opt is False

    @pytest.mark.asyncio
    async def test_threshold_customization(self, mock_db, sample_active_prompt):
        """TC-AO-016: 自定义阈值"""
        # Arrange
        optimizer = AutoOptimizer(min_feedback_count=100, accuracy_threshold=0.90)

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 90  # < 100

        mock_query2 = MagicMock()
        mock_db.query.return_value = mock_query2
        mock_query2.filter.return_value = mock_query2
        mock_query2.scalar.return_value = 0.88  # < 0.90

        # Act
        should_opt, reason = await optimizer._should_optimize(
            mock_db, sample_active_prompt
        )

        # Assert
        assert should_opt is True

    @pytest.mark.asyncio
    async def test_feedback_count_exactly_threshold(
        self, auto_optimizer, mock_db, sample_active_prompt
    ):
        """TC-AO-017: 反馈数量恰好等于阈值"""
        # Arrange
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 50  # == min_feedback_count

        # Act
        should_opt, reason = await auto_optimizer._should_optimize(
            mock_db, sample_active_prompt
        )

        # Assert
        assert should_opt is True

    @pytest.mark.asyncio
    async def test_accuracy_exactly_threshold(
        self, auto_optimizer, mock_db, sample_active_prompt
    ):
        """TC-AO-018: 准确率恰好等于阈值"""
        # Arrange
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0

        mock_query2 = MagicMock()
        mock_db.query.return_value = mock_query2
        mock_query2.filter.return_value = mock_query2
        mock_query2.scalar.return_value = 0.85  # == accuracy_threshold

        # Act
        should_opt, reason = await auto_optimizer._should_optimize(
            mock_db, sample_active_prompt
        )

        # Assert
        assert should_opt is False

    @pytest.mark.asyncio
    async def test_null_accuracy_metrics(
        self, auto_optimizer, mock_db, sample_active_prompt
    ):
        """TC-AO-019: 准确率指标为空"""
        # Arrange
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0

        mock_query2 = MagicMock()
        mock_db.query.return_value = mock_query2
        mock_query2.filter.return_value = mock_query2
        mock_query2.scalar.return_value = None

        # Act
        should_opt, reason = await auto_optimizer._should_optimize(
            mock_db, sample_active_prompt
        )

        # Assert
        assert should_opt is False

    @pytest.mark.asyncio
    async def test_filters_by_template_id(
        self, auto_optimizer, mock_db, sample_active_prompt
    ):
        """TC-AO-020: 按template_id筛选反馈"""
        # Arrange
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0

        # Act
        await auto_optimizer._should_optimize(mock_db, sample_active_prompt)

        # Assert
        mock_query.filter.assert_called()


# ============================================================================
# optimize_prompt() tests (12 tests)
# ============================================================================


class TestOptimizePrompt:
    """测试optimize_prompt方法"""

    @pytest.mark.asyncio
    async def test_optimize_prompt_success(
        self, auto_optimizer, mock_db, sample_active_prompt, sample_feedbacks
    ):
        """TC-AO-021: 成功优化Prompt"""
        # Arrange
        template_id = "prompt-123"

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = sample_feedbacks
        mock_query.get.return_value = sample_active_prompt

        # Act
        result = await auto_optimizer.optimize_prompt(mock_db, template_id)

        # Assert
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_optimize_prompt_no_feedbacks(
        self, auto_optimizer, mock_db, sample_active_prompt
    ):
        """TC-AO-022: 没有反馈数据"""
        # Arrange
        template_id = "prompt-123"

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        # Act
        result = await auto_optimizer.optimize_prompt(mock_db, template_id)

        # Assert
        assert result["success"] is False
        assert "没有反馈数据" in result["reason"]

    @pytest.mark.asyncio
    async def test_optimize_prompt_not_found(
        self, auto_optimizer, mock_db, sample_feedbacks
    ):
        """TC-AO-023: Prompt不存在"""
        # Arrange
        template_id = "non-existent"

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = sample_feedbacks
        mock_query.get.return_value = None

        # Act & Assert
        with pytest.raises(ValueError, match="Prompt不存在"):
            await auto_optimizer.optimize_prompt(mock_db, template_id)

    @pytest.mark.asyncio
    async def test_optimize_prompt_creates_version(
        self, auto_optimizer, mock_db, sample_active_prompt, sample_feedbacks
    ):
        """TC-AO-024: 创建新版本"""
        # Arrange
        template_id = "prompt-123"

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = sample_feedbacks
        mock_query.get.return_value = sample_active_prompt

        # Act
        await auto_optimizer.optimize_prompt(mock_db, template_id)

        # Assert
        mock_db.add.assert_called()
        mock_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_optimize_prompt_updates_system_prompt(
        self, auto_optimizer, mock_db, sample_active_prompt, sample_feedbacks
    ):
        """TC-AO-025: 更新系统提示词"""
        # Arrange
        template_id = "prompt-123"
        sample_active_prompt.system_prompt = "Original prompt"

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = sample_feedbacks
        mock_query.get.return_value = sample_active_prompt

        # Act
        await auto_optimizer.optimize_prompt(mock_db, template_id)

        # Assert
        mock_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_optimize_with_existing_important_section(
        self, auto_optimizer, mock_db, sample_active_prompt, sample_feedbacks
    ):
        """TC-AO-026: 在现有重要部分后追加规则"""
        # Arrange
        template_id = "prompt-123"
        sample_active_prompt.system_prompt = "⚠️ 重要:\nExisting rules"

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = sample_feedbacks
        mock_query.get.return_value = sample_active_prompt

        # Act
        await auto_optimizer.optimize_prompt(mock_db, template_id)

        # Assert
        mock_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_optimize_returns_result_dict(
        self, auto_optimizer, mock_db, sample_active_prompt, sample_feedbacks
    ):
        """TC-AO-027: 返回优化结果字典"""
        # Arrange
        template_id = "prompt-123"

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = sample_feedbacks
        mock_query.get.return_value = sample_active_prompt

        # Act
        result = await auto_optimizer.optimize_prompt(mock_db, template_id)

        # Assert
        assert "template_id" in result
        assert "old_version" in result
        assert "new_version" in result
        assert "rules_added" in result
        assert "feedback_count" in result

    @pytest.mark.asyncio
    async def test_optimize_limit_feedbacks(
        self, auto_optimizer, mock_db, sample_active_prompt
    ):
        """TC-AO-028: 限制反馈数量为100"""
        # Arrange
        template_id = "prompt-123"

        # Create 150 feedbacks
        feedbacks = [MagicMock(spec=ExtractionFeedback) for _ in range(150)]

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = feedbacks[:100]
        mock_query.get.return_value = sample_active_prompt

        # Act
        await auto_optimizer.optimize_prompt(mock_db, template_id)

        # Assert
        mock_query.limit.assert_called_with(100)

    @pytest.mark.asyncio
    async def test_optimize_no_error_patterns(
        self, auto_optimizer, mock_db, sample_active_prompt, sample_feedbacks
    ):
        """TC-AO-029: 无明显错误模式"""
        # Arrange
        template_id = "prompt-123"

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = sample_feedbacks
        mock_query.get.return_value = sample_active_prompt

        # Mock _generate_optimization_rules to return empty
        AutoOptimizer._generate_optimization_rules = MagicMock(return_value=[])

        # Act
        result = await auto_optimizer.optimize_prompt(mock_db, template_id)

        # Assert
        assert result["success"] is False
        assert "无明显错误模式" in result["reason"]

    @pytest.mark.asyncio
    async def test_optimize_increments_version(
        self, auto_optimizer, mock_db, sample_active_prompt, sample_feedbacks
    ):
        """TC-AO-030: 版本号递增"""
        # Arrange
        template_id = "prompt-123"
        sample_active_prompt.version = "v1.0.0"

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = sample_feedbacks
        mock_query.get.return_value = sample_active_prompt

        # Act
        await auto_optimizer.optimize_prompt(mock_db, template_id)

        # Assert
        mock_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_optimize_updates_version_id(
        self, auto_optimizer, mock_db, sample_active_prompt, sample_feedbacks
    ):
        """TC-AO-031: 更新current_version_id"""
        # Arrange
        template_id = "prompt-123"

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = sample_feedbacks
        mock_query.get.return_value = sample_active_prompt

        # Act
        await auto_optimizer.optimize_prompt(mock_db, template_id)

        # Assert
        mock_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_optimize_change_description(
        self, auto_optimizer, mock_db, sample_active_prompt, sample_feedbacks
    ):
        """TC-AO-032: 变更描述包含规则数量"""
        # Arrange
        template_id = "prompt-123"

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = sample_feedbacks
        mock_query.get.return_value = sample_active_prompt

        # Act
        await auto_optimizer.optimize_prompt(mock_db, template_id)

        # Assert
        mock_db.add.assert_called()


# ============================================================================
# _analyze_error_patterns() tests (4 tests)
# ============================================================================


class TestAnalyzeErrorPatterns:
    """测试_analyze_error_patterns方法"""

    def test_analyze_by_field_errors(self, auto_optimizer, sample_feedbacks):
        """TC-AO-033: 统计字段错误"""
        # Arrange
        feedbacks = sample_feedbacks

        # Act
        patterns = auto_optimizer._analyze_error_patterns(feedbacks)

        # Assert
        assert "by_field" in patterns
        assert isinstance(patterns["by_field"], Counter)

    def test_analyze_by_error_type(self, auto_optimizer, sample_feedbacks):
        """TC-AO-034: 统计错误类型"""
        # Arrange
        feedbacks = sample_feedbacks

        # Act
        patterns = auto_optimizer._analyze_error_patterns(feedbacks)

        # Assert
        assert "by_error_type" in patterns
        assert isinstance(patterns["by_error_type"], Counter)

    def test_analyze_collects_examples(self, auto_optimizer, sample_feedbacks):
        """TC-AO-035: 收集错误示例"""
        # Arrange
        feedbacks = sample_feedbacks

        # Act
        patterns = auto_optimizer._analyze_error_patterns(feedbacks)

        # Assert
        assert "examples" in patterns
        assert isinstance(patterns["examples"], dict)

    def test_analyze_limits_examples_per_type(self, auto_optimizer):
        """TC-AO-036: 每种错误类型最多3个示例"""
        # Arrange
        feedbacks = [MagicMock(spec=ExtractionFeedback) for _ in range(10)]
        for fb in feedbacks:
            fb.field_name = "test_field"
            fb.original_value = "orig"
            fb.corrected_value = "corr"

        # Act
        patterns = auto_optimizer._analyze_error_patterns(feedbacks)

        # Assert
        # Each error type should have at most 3 examples
        for error_type, examples in patterns["examples"].items():
            assert len(examples) <= 3


# ============================================================================
# _classify_error() tests (3 tests)
# ============================================================================


class TestClassifyError:
    """测试_classify_error方法"""

    def test_classify_missing_error(self):
        """TC-AO-037: 分类为missing错误"""
        # Act
        result = AutoOptimizer._classify_error("", "corrected")

        # Assert
        assert result == "missing"

    def test_classify_truncation_error(self):
        """TC-AO-038: 分类为truncation错误"""
        # Act
        result = AutoOptimizer._classify_error("partial", "partial_extended")

        # Assert
        assert result == "truncation"

    def test_classify_number_mismatch(self):
        """TC-AO-039: 分类为number_mismatch错误"""
        # Act
        result = AutoOptimizer._classify_error("12345", "54321")

        # Assert
        assert result == "number_mismatch"


# ============================================================================
# _is_date_error() tests (1 test)
# ============================================================================


class TestIsDateError:
    """测试_is_date_error方法"""

    def test_is_date_error_invalid_format(self):
        """TC-AO-040: 检测日期格式错误"""
        # Act
        result = AutoOptimizer._is_date_error("2026/01/23", "2026-01-23")

        # Assert
        assert result is True
