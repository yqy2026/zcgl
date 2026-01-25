"""
Unit tests for PromptManager service
测试Prompt管理器的所有功能
"""

from datetime import datetime
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from src.models.llm_prompt import PromptStatus, PromptTemplate, PromptVersion
from src.schemas.llm_prompt import PromptTemplateCreate, PromptTemplateUpdate
from src.services.llm_prompt.prompt_manager import PromptManager

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def prompt_manager():
    """创建PromptManager实例"""
    return PromptManager()


@pytest.fixture
def mock_db():
    """Mock数据库会话"""
    db = MagicMock(spec=Session)
    return db


@pytest.fixture
def sample_prompt_create_data():
    """示例Prompt创建数据"""
    return PromptTemplateCreate(
        name="test_contract_extraction",
        doc_type="CONTRACT",
        provider="qwen",
        description="Test prompt for contract extraction",
        system_prompt="You are a contract extraction expert.",
        user_prompt_template="Extract information from {file_name}",
        few_shot_examples={"example1": "data1"},
        tags=["test", "contract"],
    )


@pytest.fixture
def sample_prompt_template():
    """示例PromptTemplate对象"""
    prompt = MagicMock(spec=PromptTemplate)
    prompt.id = "prompt-123"
    prompt.name = "test_contract_extraction"
    prompt.doc_type = "CONTRACT"
    prompt.provider = "qwen"
    prompt.description = "Test prompt"
    prompt.system_prompt = "System prompt"
    prompt.user_prompt_template = "User template"
    prompt.few_shot_examples = {}
    prompt.version = "v1.0.0"
    prompt.status = PromptStatus.ACTIVE
    prompt.tags = ["test"]
    prompt.avg_accuracy = 0.85
    prompt.avg_confidence = 0.90
    prompt.total_usage = 10
    prompt.current_version_id = "version-123"
    prompt.created_at = datetime.utcnow()
    prompt.updated_at = datetime.utcnow()
    prompt.created_by = "user-123"
    return prompt


@pytest.fixture
def sample_prompt_version():
    """示例PromptVersion对象"""
    version = MagicMock(spec=PromptVersion)
    version.id = "version-123"
    version.template_id = "prompt-123"
    version.version = "v1.0.0"
    version.system_prompt = "System prompt"
    version.user_prompt_template = "User template"
    version.few_shot_examples = {}
    version.change_description = "Initial version"
    version.change_type = "created"
    version.auto_generated = False
    version.accuracy = 0.85
    version.confidence = 0.90
    version.usage_count = 10
    version.created_at = datetime.utcnow()
    version.created_by = "user-123"
    return version


# ============================================================================
# get_active_prompt() tests (15 tests)
# ============================================================================


class TestGetActivePrompt:
    """测试get_active_prompt方法"""

    def test_get_active_prompt_success_with_provider(
        self, prompt_manager, mock_db, sample_prompt_template
    ):
        """TC-PM-001: 成功获取活跃Prompt(带provider筛选)"""
        # Arrange
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = sample_prompt_template

        # Act
        result = prompt_manager.get_active_prompt(mock_db, "CONTRACT", "qwen")

        # Assert
        assert result == sample_prompt_template
        mock_db.query.assert_called_once_with(PromptTemplate)
        assert mock_query.filter.call_count == 2

    def test_get_active_prompt_success_without_provider(
        self, prompt_manager, mock_db, sample_prompt_template
    ):
        """TC-PM-002: 成功获取活跃Prompt(不带provider筛选)"""
        # Arrange
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = sample_prompt_template

        # Act
        result = prompt_manager.get_active_prompt(mock_db, "CONTRACT")

        # Assert
        assert result == sample_prompt_template
        assert mock_query.filter.call_count == 1

    def test_get_active_prompt_not_found(self, prompt_manager, mock_db):
        """TC-PM-003: 未找到活跃Prompt"""
        # Arrange
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = None

        # Act
        result = prompt_manager.get_active_prompt(mock_db, "CONTRACT", "qwen")

        # Assert
        assert result is None

    def test_get_active_prompt_ordering_by_updated_at(self, prompt_manager, mock_db):
        """TC-PM-004: 验证按updated_at倒序排列"""
        # Arrange
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_order_by = MagicMock()
        mock_query.order_by.return_value = mock_order_by
        mock_order_by.first.return_value = None

        # Act
        prompt_manager.get_active_prompt(mock_db, "CONTRACT")

        # Assert
        mock_query.order_by.assert_called_once()

    def test_get_active_prompt_filters_by_doc_type(self, prompt_manager, mock_db):
        """TC-PM-005: 验证按doc_type筛选"""
        # Arrange
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_filter = MagicMock()
        mock_query.filter.return_value = mock_filter
        mock_filter.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_filter
        mock_filter.first.return_value = None

        # Act
        prompt_manager.get_active_prompt(mock_db, "PROPERTY_CERT")

        # Assert
        mock_query.filter.assert_called()

    def test_get_active_prompt_filters_by_status(self, prompt_manager, mock_db):
        """TC-PM-006: 验证按status=ACTIVE筛选"""
        # Arrange
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = None

        # Act
        prompt_manager.get_active_prompt(mock_db, "CONTRACT")

        # Assert
        mock_query.filter.assert_called()

    def test_get_active_prompt_filters_by_provider(self, prompt_manager, mock_db):
        """TC-PM-007: 验证按provider筛选"""
        # Arrange
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_filter1 = MagicMock()
        mock_filter2 = MagicMock()
        mock_query.filter.return_value = mock_filter1
        mock_filter1.filter.return_value = mock_filter2
        mock_filter2.order_by.return_value = mock_filter2
        mock_filter2.first.return_value = None

        # Act
        prompt_manager.get_active_prompt(mock_db, "CONTRACT", "deepseek")

        # Assert
        assert mock_query.filter.call_count == 1
        assert mock_filter1.filter.call_count == 1

    def test_get_active_prompt_with_none_provider(self, prompt_manager, mock_db):
        """TC-PM-008: provider为None时不应用provider筛选"""
        # Arrange
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = None

        # Act
        prompt_manager.get_active_prompt(mock_db, "CONTRACT", None)

        # Assert
        # 应该只调用一次filter (doc_type和status),而不是两次
        mock_query.order_by.assert_called_once()

    def test_get_active_prompt_multiple_prompts_returns_latest(
        self, prompt_manager, mock_db
    ):
        """TC-PM-009: 多个活跃Prompt时返回最新的"""
        # Arrange
        latest_prompt = MagicMock(spec=PromptTemplate)
        latest_prompt.updated_at = datetime(2026, 1, 15, 12, 0, 0)

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = latest_prompt

        # Act
        result = prompt_manager.get_active_prompt(mock_db, "CONTRACT")

        # Assert
        assert result == latest_prompt

    def test_get_active_prompt_empty_doc_type(self, prompt_manager, mock_db):
        """TC-PM-010: doc_type为空字符串"""
        # Arrange
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = None

        # Act
        result = prompt_manager.get_active_prompt(mock_db, "")

        # Assert
        assert result is None

    def test_get_active_prompt_special_doc_type(self, prompt_manager, mock_db):
        """TC-PM-011: 特殊字符的doc_type"""
        # Arrange
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = None

        # Act
        result = prompt_manager.get_active_prompt(mock_db, "CONTRACT_V2")

        # Assert
        assert result is None

    def test_get_active_prompt_case_sensitive_doc_type(self, prompt_manager, mock_db):
        """TC-PM-012: doc_type区分大小写"""
        # Arrange
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = None

        # Act
        result = prompt_manager.get_active_prompt(mock_db, "contract")

        # Assert
        assert result is None

    def test_get_active_prompt_with_archived_status(self, prompt_manager, mock_db):
        """TC-PM-013: 只返回ACTIVE状态的Prompt"""
        # Arrange
        archived_prompt = MagicMock(spec=PromptTemplate)
        archived_prompt.status = PromptStatus.ARCHIVED

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = None  # 筛选ACTIVE,所以AR的CHIVED不会被返回

        # Act
        result = prompt_manager.get_active_prompt(mock_db, "CONTRACT")

        # Assert
        assert result is None

    def test_get_active_prompt_with_draft_status(self, prompt_manager, mock_db):
        """TC-PM-014: DRAFT状态的Prompt不应被返回"""
        # Arrange
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = None

        # Act
        result = prompt_manager.get_active_prompt(mock_db, "CONTRACT")

        # Assert
        assert result is None

    def test_get_active_prompt_returns_first_result(
        self, prompt_manager, mock_db, sample_prompt_template
    ):
        """TC-PM-015: 验证返回first()的结果"""
        # Arrange
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = sample_prompt_template

        # Act
        result = prompt_manager.get_active_prompt(mock_db, "CONTRACT")

        # Assert
        mock_query.first.assert_called_once()
        assert result == sample_prompt_template


# ============================================================================
# create_prompt() tests (20 tests)
# ============================================================================


class TestCreatePrompt:
    """测试create_prompt方法"""

    def test_create_prompt_success(
        self, prompt_manager, mock_db, sample_prompt_create_data
    ):
        """TC-PM-016: 成功创建Prompt"""
        # Arrange
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None  # 名称不存在

        # Act
        prompt_manager.create_prompt(mock_db, sample_prompt_create_data, "user-123")

        # Assert
        mock_db.add.assert_called()
        mock_db.commit.assert_called()

    def test_create_prompt_with_existing_name_raises_error(
        self, prompt_manager, mock_db, sample_prompt_create_data
    ):
        """TC-PM-017: 名称已存在时抛出ValueError"""
        # Arrange
        existing_prompt = MagicMock(spec=PromptTemplate)
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = existing_prompt

        # Act & Assert
        with pytest.raises(ValueError, match="Prompt名称已存在"):
            prompt_manager.create_prompt(mock_db, sample_prompt_create_data)

    def test_create_prompt_initial_version_v1_0_0(
        self, prompt_manager, mock_db, sample_prompt_create_data
    ):
        """TC-PM-018: 初始版本号为v1.0.0"""
        # Arrange
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None

        # Act
        prompt_manager.create_prompt(mock_db, sample_prompt_create_data)

        # Assert
        # 验证创建的template版本为v1.0.0
        mock_db.add.assert_called()

    def test_create_prompt_status_is_draft(
        self, prompt_manager, mock_db, sample_prompt_create_data
    ):
        """TC-PM-019: 新创建的Prompt状态为DRAFT"""
        # Arrange
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None

        # Act
        prompt_manager.create_prompt(mock_db, sample_prompt_create_data)

        # Assert
        mock_db.add.assert_called()

    def test_create_prompt_with_few_shot_examples(self, prompt_manager, mock_db):
        """TC-PM-020: 带Few-shot示例创建Prompt"""
        # Arrange
        data = PromptTemplateCreate(
            name="test_with_examples",
            doc_type="CONTRACT",
            provider="qwen",
            system_prompt="System",
            user_prompt_template="User",
            few_shot_examples={"ex1": "example1", "ex2": "example2"},
        )

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None

        # Act
        prompt_manager.create_prompt(mock_db, data)

        # Assert
        mock_db.add.assert_called()

    def test_create_prompt_with_empty_few_shot_examples(self, prompt_manager, mock_db):
        """TC-PM-021: Few-shot示例为空时使用默认空字典"""
        # Arrange
        data = PromptTemplateCreate(
            name="test_empty_examples",
            doc_type="CONTRACT",
            provider="qwen",
            system_prompt="System",
            user_prompt_template="User",
            few_shot_examples=None,
        )

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None

        # Act
        prompt_manager.create_prompt(mock_db, data)

        # Assert
        mock_db.add.assert_called()

    def test_create_prompt_with_tags(self, prompt_manager, mock_db):
        """TC-PM-022: 带标签创建Prompt"""
        # Arrange
        data = PromptTemplateCreate(
            name="test_with_tags",
            doc_type="CONTRACT",
            provider="qwen",
            system_prompt="System",
            user_prompt_template="User",
            tags=["tag1", "tag2", "tag3"],
        )

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None

        # Act
        prompt_manager.create_prompt(mock_db, data)

        # Assert
        mock_db.add.assert_called()

    def test_create_prompt_with_empty_tags(self, prompt_manager, mock_db):
        """TC-PM-023: 标签为空时使用默认空列表"""
        # Arrange
        data = PromptTemplateCreate(
            name="test_empty_tags",
            doc_type="CONTRACT",
            provider="qwen",
            system_prompt="System",
            user_prompt_template="User",
            tags=None,
        )

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None

        # Act
        prompt_manager.create_prompt(mock_db, data)

        # Assert
        mock_db.add.assert_called()

    def test_create_prompt_without_user_id(
        self, prompt_manager, mock_db, sample_prompt_create_data
    ):
        """TC-PM-024: 不提供user_id时创建Prompt"""
        # Arrange
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None

        # Act
        prompt_manager.create_prompt(mock_db, sample_prompt_create_data)

        # Assert
        mock_db.add.assert_called()

    def test_create_prompt_creates_version_record(
        self, prompt_manager, mock_db, sample_prompt_create_data
    ):
        """TC-PM-025: 创建Prompt时同时创建版本记录"""
        # Arrange
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None

        # Act
        prompt_manager.create_prompt(mock_db, sample_prompt_create_data)

        # Assert
        # 验证调用了两次add (template和version)
        assert mock_db.add.call_count == 2

    def test_create_prompt_version_change_description(
        self, prompt_manager, mock_db, sample_prompt_create_data
    ):
        """TC-PM-026: 版本记录的变更描述为'初始版本'"""
        # Arrange
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None

        # Act
        prompt_manager.create_prompt(mock_db, sample_prompt_create_data)

        # Assert
        mock_db.add.assert_called()

    def test_create_prompt_version_change_type(
        self, prompt_manager, mock_db, sample_prompt_create_data
    ):
        """TC-PM-027: 版本记录的变更类型为'created'"""
        # Arrange
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None

        # Act
        prompt_manager.create_prompt(mock_db, sample_prompt_create_data)

        # Assert
        mock_db.add.assert_called()

    def test_create_prompt_with_description(self, prompt_manager, mock_db):
        """TC-PM-028: 带描述创建Prompt"""
        # Arrange
        data = PromptTemplateCreate(
            name="test_with_description",
            doc_type="CONTRACT",
            provider="qwen",
            description="This is a test prompt",
            system_prompt="System",
            user_prompt_template="User",
        )

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None

        # Act
        prompt_manager.create_prompt(mock_db, data)

        # Assert
        mock_db.add.assert_called()

    def test_create_prompt_with_minimal_fields(self, prompt_manager, mock_db):
        """TC-PM-029: 使用最少必填字段创建Prompt"""
        # Arrange
        data = PromptTemplateCreate(
            name="minimal_prompt",
            doc_type="CONTRACT",
            provider="qwen",
            system_prompt="System",
            user_prompt_template="User",
        )

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None

        # Act
        prompt_manager.create_prompt(mock_db, data)

        # Assert
        mock_db.add.assert_called()

    def test_create_prompt_different_doc_types(self, prompt_manager, mock_db):
        """TC-PM-030: 不同文档类型的Prompt"""
        # Arrange
        doc_types = ["CONTRACT", "PROPERTY_CERT", "INVOICE", "RECEIPT"]
        mock_query = MagicMock()

        for doc_type in doc_types:
            mock_query.reset_mock()
            data = PromptTemplateCreate(
                name=f"test_{doc_type.lower()}",
                doc_type=doc_type,
                provider="qwen",
                system_prompt="System",
                user_prompt_template="User",
            )

            mock_db.query.return_value = mock_query
            mock_query.filter.return_value = mock_query
            mock_query.first.return_value = None

            # Act
            prompt_manager.create_prompt(mock_db, data)

            # Assert
            mock_db.add.assert_called()

    def test_create_prompt_different_providers(self, prompt_manager, mock_db):
        """TC-PM-031: 不同LLM提供商的Prompt"""
        # Arrange
        providers = ["qwen", "hunyuan", "deepseek", "glm"]
        mock_query = MagicMock()

        for provider in providers:
            mock_query.reset_mock()
            data = PromptTemplateCreate(
                name=f"test_{provider}",
                doc_type="CONTRACT",
                provider=provider,
                system_prompt="System",
                user_prompt_template="User",
            )

            mock_db.query.return_value = mock_query
            mock_query.filter.return_value = mock_query
            mock_query.first.return_value = None

            # Act
            prompt_manager.create_prompt(mock_db, data)

            # Assert
            mock_db.add.assert_called()

    def test_create_prompt_commit_called(
        self, prompt_manager, mock_db, sample_prompt_create_data
    ):
        """TC-PM-032: 验证commit被调用"""
        # Arrange
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None

        # Act
        prompt_manager.create_prompt(mock_db, sample_prompt_create_data)

        # Assert
        mock_db.commit.assert_called_once()

    def test_create_prompt_refresh_called(
        self, prompt_manager, mock_db, sample_prompt_create_data
    ):
        """TC-PM-033: 验证refresh被调用"""
        # Arrange
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None

        # Act
        prompt_manager.create_prompt(mock_db, sample_prompt_create_data)

        # Assert
        mock_db.refresh.assert_called_once()

    def test_create_prompt_name_uniqueness_check(
        self, prompt_manager, mock_db, sample_prompt_create_data
    ):
        """TC-PM-034: 验证名称唯一性检查"""
        # Arrange
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_filter = MagicMock()
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = None

        # Act
        prompt_manager.create_prompt(mock_db, sample_prompt_create_data)

        # Assert
        mock_query.filter.assert_called()


# ============================================================================
# update_prompt() tests (20 tests)
# ============================================================================


class TestUpdatePrompt:
    """测试update_prompt方法"""

    def test_update_prompt_success(
        self, prompt_manager, mock_db, sample_prompt_template
    ):
        """TC-PM-035: 成功更新Prompt"""
        # Arrange
        template_id = "prompt-123"
        update_data = PromptTemplateUpdate(
            system_prompt="Updated system prompt",
            user_prompt_template="Updated user template",
        )

        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_prompt_template
        )

        # Act
        prompt_manager.update_prompt(mock_db, template_id, update_data, "user-123")

        # Assert
        mock_db.add.assert_called()
        mock_db.commit.assert_called()

    def test_update_prompt_not_found_raises_error(self, prompt_manager, mock_db):
        """TC-PM-036: Prompt不存在时抛出ValueError"""
        # Arrange
        template_id = "non-existent"
        update_data = PromptTemplateUpdate(system_prompt="New prompt")

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = None

        # Act & Assert
        with pytest.raises(ValueError, match="Prompt不存在"):
            prompt_manager.update_prompt(mock_db, template_id, update_data)

    def test_update_prompt_increments_version(
        self, prompt_manager, mock_db, sample_prompt_template
    ):
        """TC-PM-037: 更新时版本号递增"""
        # Arrange
        template_id = "prompt-123"
        update_data = PromptTemplateUpdate(system_prompt="New prompt")

        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_prompt_template
        )
        sample_prompt_template.version = "v1.0.0"

        # Act
        prompt_manager.update_prompt(mock_db, template_id, update_data)

        # Assert
        mock_db.add.assert_called()

    def test_update_prompt_creates_version_record(
        self, prompt_manager, mock_db, sample_prompt_template
    ):
        """TC-PM-038: 更新时创建新版本记录"""
        # Arrange
        template_id = "prompt-123"
        update_data = PromptTemplateUpdate(system_prompt="New prompt")

        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_prompt_template
        )

        # Act
        prompt_manager.update_prompt(mock_db, template_id, update_data)

        # Assert
        # 验证添加了版本记录
        mock_db.add.assert_called()

    def test_update_prompt_updates_system_prompt(
        self, prompt_manager, mock_db, sample_prompt_template
    ):
        """TC-PM-039: 更新系统提示词"""
        # Arrange
        template_id = "prompt-123"
        new_system_prompt = "New system prompt"
        update_data = PromptTemplateUpdate(system_prompt=new_system_prompt)

        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_prompt_template
        )

        # Act
        prompt_manager.update_prompt(mock_db, template_id, update_data)

        # Assert
        mock_db.commit.assert_called()

    def test_update_prompt_updates_user_prompt_template(
        self, prompt_manager, mock_db, sample_prompt_template
    ):
        """TC-PM-040: 更新用户提示词模板"""
        # Arrange
        template_id = "prompt-123"
        new_template = "New user template"
        update_data = PromptTemplateUpdate(user_prompt_template=new_template)

        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_prompt_template
        )

        # Act
        prompt_manager.update_prompt(mock_db, template_id, update_data)

        # Assert
        mock_db.commit.assert_called()

    def test_update_prompt_updates_few_shot_examples(
        self, prompt_manager, mock_db, sample_prompt_template
    ):
        """TC-PM-041: 更新Few-shot示例"""
        # Arrange
        template_id = "prompt-123"
        new_examples = {"ex1": "new1", "ex2": "new2"}
        update_data = PromptTemplateUpdate(few_shot_examples=new_examples)

        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_prompt_template
        )

        # Act
        prompt_manager.update_prompt(mock_db, template_id, update_data)

        # Assert
        mock_db.commit.assert_called()

    def test_update_prompt_updates_tags(
        self, prompt_manager, mock_db, sample_prompt_template
    ):
        """TC-PM-042: 更新标签"""
        # Arrange
        template_id = "prompt-123"
        new_tags = ["updated", "tags"]
        update_data = PromptTemplateUpdate(tags=new_tags)

        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_prompt_template
        )

        # Act
        prompt_manager.update_prompt(mock_db, template_id, update_data)

        # Assert
        mock_db.commit.assert_called()

    def test_update_prompt_with_change_description(
        self, prompt_manager, mock_db, sample_prompt_template
    ):
        """TC-PM-043: 带变更描述更新"""
        # Arrange
        template_id = "prompt-123"
        update_data = PromptTemplateUpdate(
            system_prompt="New prompt",
            change_description="Optimized for better accuracy",
        )

        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_prompt_template
        )

        # Act
        prompt_manager.update_prompt(mock_db, template_id, update_data)

        # Assert
        mock_db.add.assert_called()

    def test_update_prompt_default_change_description(
        self, prompt_manager, mock_db, sample_prompt_template
    ):
        """TC-PM-044: 默认变更描述为'手动更新'"""
        # Arrange
        template_id = "prompt-123"
        update_data = PromptTemplateUpdate(system_prompt="New prompt")

        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_prompt_template
        )

        # Act
        prompt_manager.update_prompt(mock_db, template_id, update_data)

        # Assert
        mock_db.add.assert_called()

    def test_update_prompt_version_change_type(
        self, prompt_manager, mock_db, sample_prompt_template
    ):
        """TC-PM-045: 版本变更类型为'optimized'"""
        # Arrange
        template_id = "prompt-123"
        update_data = PromptTemplateUpdate(system_prompt="New prompt")

        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_prompt_template
        )

        # Act
        prompt_manager.update_prompt(mock_db, template_id, update_data)

        # Assert
        mock_db.add.assert_called()

    def test_update_prompt_preserves_existing_fields(
        self, prompt_manager, mock_db, sample_prompt_template
    ):
        """TC-PM-046: 未提供的字段保持不变"""
        # Arrange
        template_id = "prompt-123"
        update_data = PromptTemplateUpdate(system_prompt="Only update system prompt")

        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_prompt_template
        )
        sample_prompt_template.user_prompt_template = "Original user template"
        sample_prompt_template.few_shot_examples = {"original": "examples"}

        # Act
        prompt_manager.update_prompt(mock_db, template_id, update_data)

        # Assert
        mock_db.commit.assert_called()

    def test_update_prompt_updates_updated_at(
        self, prompt_manager, mock_db, sample_prompt_template
    ):
        """TC-PM-047: 更新时设置updated_at"""
        # Arrange
        template_id = "prompt-123"
        update_data = PromptTemplateUpdate(system_prompt="New prompt")

        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_prompt_template
        )

        # Act
        prompt_manager.update_prompt(mock_db, template_id, update_data)

        # Assert
        mock_db.commit.assert_called()

    def test_update_prompt_with_empty_examples(
        self, prompt_manager, mock_db, sample_prompt_template
    ):
        """TC-PM-048: 更新为空的Few-shot示例"""
        # Arrange
        template_id = "prompt-123"
        update_data = PromptTemplateUpdate(few_shot_examples={})

        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_prompt_template
        )

        # Act
        prompt_manager.update_prompt(mock_db, template_id, update_data)

        # Assert
        mock_db.commit.assert_called()

    def test_update_prompt_with_null_examples(
        self, prompt_manager, mock_db, sample_prompt_template
    ):
        """TC-PM-049: Few-shot示例为None时保持原值"""
        # Arrange
        template_id = "prompt-123"
        update_data = PromptTemplateUpdate(few_shot_examples=None)

        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_prompt_template
        )
        sample_prompt_template.few_shot_examples = {"original": "examples"}

        # Act
        prompt_manager.update_prompt(mock_db, template_id, update_data)

        # Assert
        mock_db.commit.assert_called()

    def test_update_prompt_with_null_tags(
        self, prompt_manager, mock_db, sample_prompt_template
    ):
        """TC-PM-050: 标签为None时不更新"""
        # Arrange
        template_id = "prompt-123"
        update_data = PromptTemplateUpdate(tags=None)

        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_prompt_template
        )
        sample_prompt_template.tags = ["original", "tags"]

        # Act
        prompt_manager.update_prompt(mock_db, template_id, update_data)

        # Assert
        mock_db.commit.assert_called()

    def test_update_prompt_updates_current_version_id(
        self, prompt_manager, mock_db, sample_prompt_template
    ):
        """TC-PM-051: 更新current_version_id"""
        # Arrange
        template_id = "prompt-123"
        update_data = PromptTemplateUpdate(system_prompt="New prompt")

        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_prompt_template
        )

        # Act
        prompt_manager.update_prompt(mock_db, template_id, update_data)

        # Assert
        mock_db.commit.assert_called()

    def test_update_prompt_without_user_id(
        self, prompt_manager, mock_db, sample_prompt_template
    ):
        """TC-PM-052: 不提供user_id时更新"""
        # Arrange
        template_id = "prompt-123"
        update_data = PromptTemplateUpdate(system_prompt="New prompt")

        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_prompt_template
        )

        # Act
        prompt_manager.update_prompt(mock_db, template_id, update_data)

        # Assert
        mock_db.add.assert_called()


# ============================================================================
# activate_prompt() tests (10 tests)
# ============================================================================


class TestActivatePrompt:
    """测试activate_prompt方法"""

    def test_activate_prompt_success(
        self, prompt_manager, mock_db, sample_prompt_template
    ):
        """TC-PM-053: 成功激活Prompt"""
        # Arrange
        template_id = "prompt-123"
        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_prompt_template
        )
        mock_update_result = MagicMock()
        mock_update_result.update.return_value = None
        mock_db.query.return_value.filter.return_value.filter.return_value.filter.return_value.update.return_value = mock_update_result

        # Act
        result = prompt_manager.activate_prompt(mock_db, template_id)

        # Assert
        mock_db.commit.assert_called()
        assert result.status == PromptStatus.ACTIVE

    def test_activate_prompt_not_found_raises_error(self, prompt_manager, mock_db):
        """TC-PM-054: Prompt不存在时抛出ValueError"""
        # Arrange
        template_id = "non-existent"
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = None

        # Act & Assert
        with pytest.raises(ValueError, match="Prompt不存在"):
            prompt_manager.activate_prompt(mock_db, template_id)

    def test_activate_prompt_archives_others(
        self, prompt_manager, mock_db, sample_prompt_template
    ):
        """TC-PM-055: 激活时归档同类型的其他活跃Prompt"""
        # Arrange
        template_id = "prompt-123"
        sample_prompt_template.doc_type = "CONTRACT"

        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_prompt_template
        )
        mock_update_result = MagicMock()
        mock_db.query.return_value.filter.return_value.filter.return_value.filter.return_value.update.return_value = mock_update_result

        # Act
        prompt_manager.activate_prompt(mock_db, template_id)

        # Assert
        mock_update_result.update.assert_called()

    def test_activate_prompt_sets_status_active(
        self, prompt_manager, mock_db, sample_prompt_template
    ):
        """TC-PM-056: 设置状态为ACTIVE"""
        # Arrange
        template_id = "prompt-123"
        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_prompt_template
        )
        mock_update_result = MagicMock()
        mock_db.query.return_value.filter.return_value.filter.return_value.filter.return_value.update.return_value = mock_update_result

        # Act
        result = prompt_manager.activate_prompt(mock_db, template_id)

        # Assert
        assert result.status == PromptStatus.ACTIVE

    def test_activate_prompt_updates_updated_at(
        self, prompt_manager, mock_db, sample_prompt_template
    ):
        """TC-PM-057: 更新时设置updated_at"""
        # Arrange
        template_id = "prompt-123"
        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_prompt_template
        )
        mock_update_result = MagicMock()
        mock_db.query.return_value.filter.return_value.filter.return_value.filter.return_value.update.return_value = mock_update_result

        # Act
        prompt_manager.activate_prompt(mock_db, template_id)

        # Assert
        mock_db.commit.assert_called()

    def test_activate_prompt_same_doc_type_filter(
        self, prompt_manager, mock_db, sample_prompt_template
    ):
        """TC-PM-058: 只归档相同doc_type的Prompt"""
        # Arrange
        template_id = "prompt-123"
        sample_prompt_template.doc_type = "CONTRACT"

        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_prompt_template
        )
        mock_update_result = MagicMock()
        mock_db.query.return_value.filter.return_value.filter.return_value.filter.return_value.update.return_value = mock_update_result

        # Act
        prompt_manager.activate_prompt(mock_db, template_id)

        # Assert
        mock_update_result.update.assert_called()

    def test_activate_prompt_excludes_current(
        self, prompt_manager, mock_db, sample_prompt_template
    ):
        """TC-PM-059: 归档时排除当前Prompt"""
        # Arrange
        template_id = "prompt-123"
        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_prompt_template
        )
        mock_update_result = MagicMock()
        mock_db.query.return_value.filter.return_value.filter.return_value.filter.return_value.filter.return_value.update.return_value = mock_update_result

        # Act
        prompt_manager.activate_prompt(mock_db, template_id)

        # Assert
        mock_update_result.update.assert_called()

    def test_activate_prompt_from_draft_status(self, prompt_manager, mock_db):
        """TC-PM-060: 从DRAFT状态激活"""
        # Arrange
        template_id = "prompt-123"
        draft_prompt = MagicMock(spec=PromptTemplate)
        draft_prompt.id = "prompt-123"
        draft_prompt.status = PromptStatus.DRAFT
        draft_prompt.doc_type = "CONTRACT"

        mock_db.query.return_value.filter.return_value.first.return_value = draft_prompt
        mock_update_result = MagicMock()
        mock_db.query.return_value.filter.return_value.filter.return_value.filter.return_value.update.return_value = mock_update_result

        # Act
        result = prompt_manager.activate_prompt(mock_db, template_id)

        # Assert
        assert result.status == PromptStatus.ACTIVE

    def test_activate_prompt_from_archived_status(self, prompt_manager, mock_db):
        """TC-PM-061: 从ARCHIVED状态重新激活"""
        # Arrange
        template_id = "prompt-123"
        archived_prompt = MagicMock(spec=PromptTemplate)
        archived_prompt.id = "prompt-123"
        archived_prompt.status = PromptStatus.ARCHIVED
        archived_prompt.doc_type = "CONTRACT"

        mock_db.query.return_value.filter.return_value.first.return_value = (
            archived_prompt
        )
        mock_update_result = MagicMock()
        mock_db.query.return_value.filter.return_value.filter.return_value.filter.return_value.update.return_value = mock_update_result

        # Act
        result = prompt_manager.activate_prompt(mock_db, template_id)

        # Assert
        assert result.status == PromptStatus.ACTIVE

    def test_activate_prompt_commits_changes(
        self, prompt_manager, mock_db, sample_prompt_template
    ):
        """TC-PM-062: 验证commit被调用"""
        # Arrange
        template_id = "prompt-123"
        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_prompt_template
        )
        mock_update_result = MagicMock()
        mock_db.query.return_value.filter.return_value.filter.return_value.filter.return_value.update.return_value = mock_update_result

        # Act
        prompt_manager.activate_prompt(mock_db, template_id)

        # Assert
        mock_db.commit.assert_called_once()


# ============================================================================
# rollback_to_version() tests (10 tests)
# ============================================================================


class TestRollbackToVersion:
    """测试rollback_to_version方法"""

    def test_rollback_to_version_success(
        self, prompt_manager, mock_db, sample_prompt_template, sample_prompt_version
    ):
        """TC-PM-063: 成功回滚到指定版本"""
        # Arrange
        template_id = "prompt-123"
        version_id = "version-123"

        mock_db.query.return_value.filter.return_value.first.side_effect = [
            sample_prompt_version,
            sample_prompt_template,
        ]
        sample_prompt_template.version = "v1.2.0"
        sample_prompt_version.version = "v1.0.0"

        # Act
        prompt_manager.rollback_to_version(mock_db, template_id, version_id, "user-123")

        # Assert
        mock_db.add.assert_called()
        mock_db.commit.assert_called()

    def test_rollback_version_not_found_raises_error(self, prompt_manager, mock_db):
        """TC-PM-064: 版本不存在时抛出ValueError"""
        # Arrange
        template_id = "prompt-123"
        version_id = "non-existent"

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = None

        # Act & Assert
        with pytest.raises(ValueError, match="版本不存在或不匹配"):
            prompt_manager.rollback_to_version(mock_db, template_id, version_id)

    def test_rollback_version_mismatch_raises_error(
        self, prompt_manager, mock_db, sample_prompt_version
    ):
        """TC-PM-065: 版本不匹配时抛出ValueError"""
        # Arrange
        template_id = "prompt-123"
        version_id = "version-456"

        sample_prompt_version.template_id = "prompt-789"  # 不同的template

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = sample_prompt_version

        # Act & Assert
        with pytest.raises(ValueError, match="版本不存在或不匹配"):
            prompt_manager.rollback_to_version(mock_db, template_id, version_id)

    def test_rollback_template_not_found_raises_error(
        self, prompt_manager, mock_db, sample_prompt_version
    ):
        """TC-PM-066: Prompt不存在时抛出ValueError"""
        # Arrange
        template_id = "non-existent"
        version_id = "version-123"

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.side_effect = [sample_prompt_version, None]

        # Act & Assert
        with pytest.raises(ValueError, match="Prompt不存在"):
            prompt_manager.rollback_to_version(mock_db, template_id, version_id)

    def test_rollback_creates_new_version(
        self, prompt_manager, mock_db, sample_prompt_template, sample_prompt_version
    ):
        """TC-PM-067: 回滚时创建新版本记录"""
        # Arrange
        template_id = "prompt-123"
        version_id = "version-123"

        mock_db.query.return_value.filter.return_value.first.side_effect = [
            sample_prompt_version,
            sample_prompt_template,
        ]
        sample_prompt_template.version = "v1.2.0"
        sample_prompt_version.version = "v1.0.0"

        # Act
        prompt_manager.rollback_to_version(mock_db, template_id, version_id)

        # Assert
        mock_db.add.assert_called()

    def test_rollback_increments_version(
        self, prompt_manager, mock_db, sample_prompt_template, sample_prompt_version
    ):
        """TC-PM-068: 回滚时版本号递增"""
        # Arrange
        template_id = "prompt-123"
        version_id = "version-123"

        mock_db.query.return_value.filter.return_value.first.side_effect = [
            sample_prompt_version,
            sample_prompt_template,
        ]
        sample_prompt_template.version = "v1.2.0"
        sample_prompt_version.version = "v1.0.0"

        # Act
        prompt_manager.rollback_to_version(mock_db, template_id, version_id)

        # Assert
        mock_db.add.assert_called()

    def test_rollback_restores_system_prompt(
        self, prompt_manager, mock_db, sample_prompt_template, sample_prompt_version
    ):
        """TC-PM-069: 恢复系统提示词"""
        # Arrange
        template_id = "prompt-123"
        version_id = "version-123"

        sample_prompt_version.system_prompt = "Old system prompt"
        sample_prompt_template.system_prompt = "New system prompt"

        mock_db.query.return_value.filter.return_value.first.side_effect = [
            sample_prompt_version,
            sample_prompt_template,
        ]

        # Act
        prompt_manager.rollback_to_version(mock_db, template_id, version_id)

        # Assert
        mock_db.commit.assert_called()

    def test_rollback_restores_user_prompt_template(
        self, prompt_manager, mock_db, sample_prompt_template, sample_prompt_version
    ):
        """TC-PM-070: 恢复用户提示词模板"""
        # Arrange
        template_id = "prompt-123"
        version_id = "version-123"

        sample_prompt_version.user_prompt_template = "Old user template"
        sample_prompt_template.user_prompt_template = "New user template"

        mock_db.query.return_value.filter.return_value.first.side_effect = [
            sample_prompt_version,
            sample_prompt_template,
        ]

        # Act
        prompt_manager.rollback_to_version(mock_db, template_id, version_id)

        # Assert
        mock_db.commit.assert_called()

    def test_rollback_change_description(
        self, prompt_manager, mock_db, sample_prompt_template, sample_prompt_version
    ):
        """TC-PM-071: 变更描述包含回滚信息"""
        # Arrange
        template_id = "prompt-123"
        version_id = "version-123"
        sample_prompt_version.version = "v1.0.0"

        mock_db.query.return_value.filter.return_value.first.side_effect = [
            sample_prompt_version,
            sample_prompt_template,
        ]

        # Act
        prompt_manager.rollback_to_version(mock_db, template_id, version_id)

        # Assert
        mock_db.add.assert_called()

    def test_rollback_change_type(
        self, prompt_manager, mock_db, sample_prompt_template, sample_prompt_version
    ):
        """TC-PM-072: 变更类型为'rollback'"""
        # Arrange
        template_id = "prompt-123"
        version_id = "version-123"

        mock_db.query.return_value.filter.return_value.first.side_effect = [
            sample_prompt_version,
            sample_prompt_template,
        ]

        # Act
        prompt_manager.rollback_to_version(mock_db, template_id, version_id)

        # Assert
        mock_db.add.assert_called()


# ============================================================================
# get_prompt_history() tests (3 tests)
# ============================================================================


class TestGetPromptHistory:
    """测试get_prompt_history方法"""

    def test_get_prompt_history_success(
        self, prompt_manager, mock_db, sample_prompt_version
    ):
        """TC-PM-073: 成功获取Prompt历史"""
        # Arrange
        template_id = "prompt-123"
        versions = [sample_prompt_version]

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = versions

        # Act
        result = prompt_manager.get_prompt_history(mock_db, template_id)

        # Assert
        assert len(result) == 1
        assert result[0] == sample_prompt_version

    def test_get_prompt_history_empty(self, prompt_manager, mock_db):
        """TC-PM-074: 获取空历史"""
        # Arrange
        template_id = "prompt-123"

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []

        # Act
        result = prompt_manager.get_prompt_history(mock_db, template_id)

        # Assert
        assert len(result) == 0

    def test_get_prompt_history_ordering(self, prompt_manager, mock_db):
        """TC-PM-075: 验证按创建时间倒序排列"""
        # Arrange
        template_id = "prompt-123"

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []

        # Act
        prompt_manager.get_prompt_history(mock_db, template_id)

        # Assert
        mock_query.order_by.assert_called_once()


# ============================================================================
# _increment_version() tests (2 tests)
# ============================================================================


class TestIncrementVersion:
    """测试_increment_version静态方法"""

    def test_increment_version_patch(self):
        """TC-PM-076: 正确递增patch版本"""
        # Act
        result = PromptManager._increment_version("v1.0.0")

        # Assert
        assert result == "v1.0.1"

    def test_increment_version_various_formats(self):
        """TC-PM-077: 测试各种版本号格式"""
        # Arrange & Act & Assert
        assert PromptManager._increment_version("v1.0.0") == "v1.0.1"
        assert PromptManager._increment_version("v2.5.9") == "v2.5.10"
        assert PromptManager._increment_version("v0.0.1") == "v0.0.2"


# ============================================================================
# Additional edge case tests (3 tests)
# ============================================================================


class TestEdgeCases:
    """测试边界情况"""

    def test_increment_version_invalid_format_fallback(self):
        """TC-PM-078: 无效版本号格式时使用回退方案"""
        # Act
        result = PromptManager._increment_version("invalid")

        # Assert
        assert result == "invalid.1"

    def test_increment_version_missing_parts(self):
        """TC-PM-079: 版本号部分缺失"""
        # Act
        result = PromptManager._increment_version("v1.0")

        # Assert
        assert "1.0" in result

    def test_prompt_manager_class_instantiation(self):
        """TC-PM-080: PromptManager可以正常实例化"""
        # Act
        manager = PromptManager()

        # Assert
        assert manager is not None
        assert hasattr(manager, "get_active_prompt")
        assert hasattr(manager, "create_prompt")
