"""
反馈收集服务

将反馈收集逻辑从 API 层抽离到 Service 层
"""

import logging
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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

    async def collect_async(
        self,
        db: AsyncSession,
        feedback_in: ExtractionFeedbackCreate,
        user_id: str,
    ) -> ExtractionFeedbackResponse:
        template = await self.prompt_manager.get_by_id_async(
            db, template_id=feedback_in.template_id
        )
        if not template:
            raise ResourceNotFoundError("Prompt", feedback_in.template_id)

        version_id = feedback_in.version_id or template.current_version_id

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
        await db.commit()
        await db.refresh(feedback)

        logger.info(
            f"收集用户反馈: template={feedback_in.template_id}, "
            f"field={feedback_in.field_name}, user={user_id}"
        )

        return ExtractionFeedbackResponse.model_validate(feedback)

    async def get_by_template_async(
        self, db: AsyncSession, template_id: str, limit: int = 100
    ) -> list[ExtractionFeedback]:
        stmt = (
            select(ExtractionFeedback)
            .where(ExtractionFeedback.template_id == template_id)
            .order_by(ExtractionFeedback.created_at.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())
