"""
Prompt管理服务
统一的LLM Prompt管理器
"""

import logging
from typing import Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception_handler import (
    DuplicateResourceError,
    ResourceConflictError,
    ResourceNotFoundError,
)
from ...crud.llm_prompt import prompt_template_crud, prompt_version_crud
from ...models.llm_prompt import PromptStatus, PromptTemplate, PromptVersion
from ...schemas.llm_prompt import PromptTemplateCreate, PromptTemplateUpdate
from ...utils.time import utcnow_naive

logger = logging.getLogger(__name__)


class PromptManager:
    """Prompt管理器"""

    async def get_active_prompt_async(
        self, db: AsyncSession, doc_type: str, provider: str | None = None
    ) -> PromptTemplate | None:
        prompt = await prompt_template_crud.get_active_prompt_async(
            db, doc_type=doc_type, provider=provider
        )

        if prompt:
            logger.info(f"✅ 获取活跃Prompt: {prompt.name} (v{prompt.version})")
        else:
            logger.warning(
                f"⚠️  未找到活跃的Prompt: doc_type={doc_type}, provider={provider}"
            )

        return prompt

    async def create_prompt_async(
        self, db: AsyncSession, data: PromptTemplateCreate, user_id: str | None = None
    ) -> PromptTemplate:
        existing = await prompt_template_crud.get_by_name_async(db, name=data.name)
        if existing:
            raise DuplicateResourceError("Prompt", "name", data.name)

        version = "v1.0.0"

        template = PromptTemplate()
        template.id = str(uuid4())
        template.name = data.name
        template.doc_type = data.doc_type
        template.provider = data.provider
        template.description = data.description
        template.system_prompt = data.system_prompt
        template.user_prompt_template = data.user_prompt_template
        template.few_shot_examples = data.few_shot_examples or {}
        template.version = version
        template.status = PromptStatus.DRAFT
        template.tags = data.tags or []
        template.created_by = user_id

        version_record = PromptVersion()
        version_record.id = str(uuid4())
        version_record.template_id = template.id
        version_record.version = version
        version_record.system_prompt = data.system_prompt
        version_record.user_prompt_template = data.user_prompt_template
        version_record.few_shot_examples = data.few_shot_examples or {}
        version_record.change_description = "初始版本"
        version_record.change_type = "created"
        version_record.created_by = user_id

        db.add(template)
        db.add(version_record)
        await db.commit()
        await db.refresh(template)

        logger.info(f"✅ 创建Prompt: {template.name} (v{version})")
        return template

    async def update_prompt_async(
        self,
        db: AsyncSession,
        template_id: str,
        data: PromptTemplateUpdate,
        user_id: str | None = None,
    ) -> PromptTemplate:
        template = await prompt_template_crud.get(db, id=template_id)
        if not template:
            raise ResourceNotFoundError("Prompt", template_id)

        new_version = self._increment_version(template.version)

        new_system_prompt = data.system_prompt or template.system_prompt
        new_user_prompt = data.user_prompt_template or template.user_prompt_template
        new_examples = (
            data.few_shot_examples
            if data.few_shot_examples is not None
            else template.few_shot_examples
        )

        version_record = PromptVersion()
        version_record.id = str(uuid4())
        version_record.template_id = template_id
        version_record.version = new_version
        version_record.system_prompt = new_system_prompt
        version_record.user_prompt_template = new_user_prompt
        version_record.few_shot_examples = new_examples
        version_record.change_description = data.change_description or "手动更新"
        version_record.change_type = "optimized"
        version_record.created_by = user_id

        template.system_prompt = new_system_prompt
        template.user_prompt_template = new_user_prompt
        template.few_shot_examples = new_examples
        template.version = new_version
        template.current_version_id = version_record.id
        template.updated_at = utcnow_naive()

        if data.tags is not None:
            template.tags = data.tags

        db.add(version_record)
        await db.commit()
        await db.refresh(template)

        logger.info(
            f"✅ 更新Prompt: {template.name} (v{template.version} → {new_version})"
        )
        return template

    async def activate_prompt_async(
        self, db: AsyncSession, template_id: str
    ) -> PromptTemplate:
        template = await prompt_template_crud.get(db, id=template_id)
        if not template:
            raise ResourceNotFoundError("Prompt", template_id)

        await prompt_template_crud.archive_active_by_doc_type_async(
            db,
            doc_type=template.doc_type,
            exclude_template_id=template_id,
            updated_at=utcnow_naive(),
        )

        template.status = PromptStatus.ACTIVE
        template.updated_at = utcnow_naive()
        await db.commit()
        await db.refresh(template)

        logger.info(f"✅ 激活Prompt: {template.name} (停用同类型的其他Prompt)")
        return template

    async def rollback_to_version_async(
        self,
        db: AsyncSession,
        template_id: str,
        version_id: str,
        user_id: str | None = None,
    ) -> PromptTemplate:
        target_version = await prompt_version_crud.get_async(db, version_id=version_id)
        if not target_version:
            raise ResourceNotFoundError("Prompt版本", version_id)
        if target_version.template_id != template_id:
            raise ResourceConflictError(
                f"版本不存在或不匹配: {version_id}",
                resource_type="Prompt",
                details={"template_id": template_id, "version_id": version_id},
            )

        template = await prompt_template_crud.get(db, id=template_id)
        if not template:
            raise ResourceNotFoundError("Prompt", template_id)

        new_version = self._increment_version(template.version)

        version_record = PromptVersion()
        version_record.id = str(uuid4())
        version_record.template_id = template_id
        version_record.version = new_version
        version_record.system_prompt = target_version.system_prompt
        version_record.user_prompt_template = target_version.user_prompt_template
        version_record.few_shot_examples = target_version.few_shot_examples
        version_record.change_description = f"回滚到版本{target_version.version}"
        version_record.change_type = "rollback"
        version_record.created_by = user_id

        template.system_prompt = target_version.system_prompt
        template.user_prompt_template = target_version.user_prompt_template
        template.few_shot_examples = target_version.few_shot_examples
        template.version = new_version
        template.current_version_id = version_record.id
        template.updated_at = utcnow_naive()

        db.add(version_record)
        await db.commit()
        await db.refresh(template)

        logger.info(
            f"✅ 回滚Prompt: {template.name} (v{template.version} ← v{target_version.version})"
        )
        return template

    async def get_prompt_history_async(
        self, db: AsyncSession, template_id: str
    ) -> list[PromptVersion]:
        versions = await prompt_version_crud.get_by_template_async(
            db, template_id=template_id
        )

        logger.info(f"📜 Prompt历史: {template_id}, 共{len(versions)}个版本")
        return versions

    async def list_templates_async(
        self,
        db: AsyncSession,
        *,
        doc_type: str | None = None,
        status: str | None = None,
        provider: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> dict[str, Any]:
        skip = (page - 1) * page_size
        prompts, total = await prompt_template_crud.get_list_with_filters_async(
            db,
            doc_type=doc_type,
            status=status,
            provider=provider,
            skip=skip,
            limit=page_size,
        )

        return {"items": prompts, "total": total, "page": page, "page_size": page_size}

    async def get_by_id_async(
        self, db: AsyncSession, *, template_id: str
    ) -> PromptTemplate | None:
        return await prompt_template_crud.get(db, id=template_id)

    async def get_statistics_async(self, db: AsyncSession) -> dict[str, Any]:
        return await prompt_template_crud.get_statistics_async(db)

    @staticmethod
    def _increment_version(current_version: str) -> str:
        """
        递增版本号: v1.0.0 -> v1.0.1

        Args:
            current_version: 当前版本号

        Returns:
            新版本号
        """
        try:
            # 移除'v'前缀，分割版本号
            version_str = current_version.replace("v", "")
            parts = version_str.split(".")

            if len(parts) == 3:
                major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
                return f"v{major}.{minor}.{patch + 1}"
            else:
                # 如果格式不符合预期，简单追加.1
                return f"{current_version}.1"
        except (ValueError, IndexError):
            # 如果解析失败，简单追加.1
            return f"{current_version}.1"
