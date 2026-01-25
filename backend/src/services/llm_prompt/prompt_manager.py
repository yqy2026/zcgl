"""
Prompt管理服务
统一的LLM Prompt管理器
"""

import logging
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from ...models.llm_prompt import PromptStatus, PromptTemplate, PromptVersion
from ...schemas.llm_prompt import PromptTemplateCreate, PromptTemplateUpdate

logger = logging.getLogger(__name__)


class PromptManager:
    """Prompt管理器"""

    def get_active_prompt(
        self, db: Session, doc_type: str, provider: str | None = None
    ) -> PromptTemplate | None:
        """
        获取当前活跃的Prompt

        Args:
            db: 数据库会话
            doc_type: 文档类型 (CONTRACT, PROPERTY_CERT等)
            provider: LLM提供商 (qwen, hunyuan, deepseek, glm)

        Returns:
            PromptTemplate or None
        """
        query = db.query(PromptTemplate).filter(
            PromptTemplate.doc_type == doc_type,
            PromptTemplate.status == PromptStatus.ACTIVE,
        )

        if provider:
            query = query.filter(PromptTemplate.provider == provider)

        prompt = query.order_by(PromptTemplate.updated_at.desc()).first()

        if prompt:
            logger.info(f"✅ 获取活跃Prompt: {prompt.name} (v{prompt.version})")
        else:
            logger.warning(
                f"⚠️  未找到活跃的Prompt: doc_type={doc_type}, provider={provider}"
            )

        return prompt

    def create_prompt(
        self, db: Session, data: PromptTemplateCreate, user_id: str | None = None
    ) -> PromptTemplate:
        """
        创建新Prompt模板

        Args:
            db: 数据库会话
            data: Prompt创建数据
            user_id: 创建人ID

        Returns:
            PromptTemplate
        """
        # 1. 检查名称是否已存在
        existing = (
            db.query(PromptTemplate).filter(PromptTemplate.name == data.name).first()
        )

        if existing:
            raise ValueError(f"Prompt名称已存在: {data.name}")

        # 2. 生成版本号
        version = "v1.0.0"

        # 3. 创建Prompt模板
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

        # 4. 创建初始版本
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
        db.commit()
        db.refresh(template)

        logger.info(f"✅ 创建Prompt: {template.name} (v{version})")
        return template

    def update_prompt(
        self,
        db: Session,
        template_id: str,
        data: PromptTemplateUpdate,
        user_id: str | None = None,
    ) -> PromptTemplate:
        """
        更新Prompt(自动创建新版本)

        Args:
            db: 数据库会话
            template_id: Prompt模板ID
            data: 更新数据
            user_id: 操作人ID

        Returns:
            PromptTemplate
        """
        template = db.query(PromptTemplate).get(template_id)
        if not template:
            raise ValueError(f"Prompt不存在: {template_id}")

        # 1. 生成新版本号
        new_version = self._increment_version(template.version)

        # 2. 准备新内容
        new_system_prompt = data.system_prompt or template.system_prompt
        new_user_prompt = data.user_prompt_template or template.user_prompt_template
        new_examples = (
            data.few_shot_examples
            if data.few_shot_examples is not None
            else template.few_shot_examples
        )

        # 3. 创建版本记录
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

        # 4. 更新模板
        template.system_prompt = new_system_prompt
        template.user_prompt_template = new_user_prompt
        template.few_shot_examples = new_examples
        template.version = new_version
        template.current_version_id = version_record.id
        template.updated_at = datetime.now(UTC)

        if data.tags is not None:
            template.tags = data.tags

        db.add(version_record)
        db.commit()
        db.refresh(template)

        logger.info(
            f"✅ 更新Prompt: {template.name} (v{template.version} → {new_version})"
        )
        return template

    def activate_prompt(self, db: Session, template_id: str) -> PromptTemplate:
        """
        激活指定Prompt

        Args:
            db: 数据库会话
            template_id: 要激活的Prompt模板ID

        Returns:
            PromptTemplate
        """
        template = db.query(PromptTemplate).get(template_id)
        if not template:
            raise ValueError(f"Prompt不存在: {template_id}")

        # 1. 停用同类型的其他Prompt
        db.query(PromptTemplate).filter(
            PromptTemplate.doc_type == template.doc_type,
            PromptTemplate.status == PromptStatus.ACTIVE,
            PromptTemplate.id != template_id,
        ).update({"status": PromptStatus.ARCHIVED, "updated_at": datetime.now(UTC)})

        # 2. 激活目标Prompt
        template.status = PromptStatus.ACTIVE
        template.updated_at = datetime.now(UTC)
        db.commit()
        db.refresh(template)

        logger.info(f"✅ 激活Prompt: {template.name} (停用同类型的其他Prompt)")
        return template

    def rollback_to_version(
        self, db: Session, template_id: str, version_id: str, user_id: str | None = None
    ) -> PromptTemplate:
        """
        回滚到指定版本

        Args:
            db: 数据库会话
            template_id: Prompt模板ID
            version_id: 要回滚到的目标版本ID
            user_id: 操作人ID

        Returns:
            PromptTemplate
        """
        # 1. 获取目标版本
        target_version = db.query(PromptVersion).get(version_id)
        if not target_version or target_version.template_id != template_id:
            raise ValueError(f"版本不存在或不匹配: {version_id}")

        template = db.query(PromptTemplate).get(template_id)
        if not template:
            raise ValueError(f"Prompt不存在: {template_id}")

        # 2. 生成新版本号
        new_version = self._increment_version(template.version)

        # 3. 创建回滚版本
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

        # 4. 更新模板
        template.system_prompt = target_version.system_prompt
        template.user_prompt_template = target_version.user_prompt_template
        template.few_shot_examples = target_version.few_shot_examples
        template.version = new_version
        template.current_version_id = version_record.id
        template.updated_at = datetime.now(UTC)

        db.add(version_record)
        db.commit()
        db.refresh(template)

        logger.info(
            f"✅ 回滚Prompt: {template.name} (v{template.version} ← v{target_version.version})"
        )
        return template

    def get_prompt_history(self, db: Session, template_id: str) -> list[PromptVersion]:
        """
        获取Prompt的所有历史版本

        Args:
            db: 数据库会话
            template_id: Prompt模板ID

        Returns:
            版本列表(按创建时间倒序)
        """
        versions = (
            db.query(PromptVersion)
            .filter(PromptVersion.template_id == template_id)
            .order_by(PromptVersion.created_at.desc())
            .all()
        )

        logger.info(f"📜 Prompt历史: {template_id}, 共{len(versions)}个版本")
        return versions

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
