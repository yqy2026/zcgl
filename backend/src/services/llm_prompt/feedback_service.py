"""
反馈收集服务

将反馈收集逻辑从 API 层抽离到 Service 层
"""

import logging
from uuid import uuid4

from sqlalchemy.orm import Session

from ...core.exception_handler import ResourceNotFoundError
from ...models.llm_prompt import ExtractionFeedback
from ...schemas.llm_prompt import ExtractionFeedbackCreate, ExtractionFeedbackResponse
from .prompt_manager import PromptManager

logger = logging.getLogger(__name__)


class FeedbackService:
    """反馈收集服务"""

    def __init__(self, prompt_manager: PromptManager | None = None) -> None:
        """
        初始化反馈服务

        Args:
            prompt_manager: Prompt管理器实例，默认创建新实例
        """
        self.prompt_manager = prompt_manager or PromptManager()

    def collect(
        self,
        db: Session,
        feedback_in: ExtractionFeedbackCreate,
        user_id: str,
    ) -> ExtractionFeedbackResponse:
        """
        收集用户反馈

        Args:
            db: 数据库会话
            feedback_in: 反馈创建数据
            user_id: 当前用户ID

        Returns:
            ExtractionFeedbackResponse

        Raises:
            ValueError: 当模板不存在时
        """
        # 验证模板存在
        template = self.prompt_manager.get_by_id(db, template_id=feedback_in.template_id)
        if not template:
            raise ResourceNotFoundError("Prompt", feedback_in.template_id)

        # 获取当前版本ID（如果未指定）
        version_id = feedback_in.version_id or template.current_version_id

        # 创建反馈记录
        feedback = ExtractionFeedback()
        feedback.id = str(uuid4())
        feedback.template_id = feedback_in.template_id
        feedback.version_id = version_id
        feedback.doc_type = feedback_in.doc_type
        feedback.file_path = feedback_in.file_path
        feedback.session_id = feedback_in.session_id
        feedback.field_name = feedback_in.field_name
        feedback.original_value = feedback_in.original_value
        feedback.corrected_value = feedback_in.corrected_value
        feedback.confidence_before = feedback_in.confidence_before
        feedback.user_action = feedback_in.user_action
        feedback.user_id = user_id

        db.add(feedback)
        db.commit()
        db.refresh(feedback)

        logger.info(
            f"收集用户反馈: template={feedback_in.template_id}, "
            f"field={feedback_in.field_name}, user={user_id}"
        )

        return ExtractionFeedbackResponse.model_validate(feedback)

    def get_by_template(
        self,
        db: Session,
        template_id: str,
        limit: int = 100,
    ) -> list[ExtractionFeedback]:
        """
        获取模板的反馈列表

        Args:
            db: 数据库会话
            template_id: 模板ID
            limit: 返回数量限制

        Returns:
            反馈列表
        """
        return (
            db.query(ExtractionFeedback)
            .filter(ExtractionFeedback.template_id == template_id)
            .order_by(ExtractionFeedback.created_at.desc())
            .limit(limit)
            .all()
        )
