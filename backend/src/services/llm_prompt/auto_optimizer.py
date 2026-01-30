"""
自动优化引擎
基于用户反馈数据自动优化Prompt模板
"""

import logging
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import func
from sqlalchemy.orm import Session

from ...core.exception_handler import ResourceNotFoundError
from ...models.llm_prompt import (
    ExtractionFeedback,
    PromptStatus,
    PromptTemplate,
    PromptVersion,
)
from .prompt_manager import PromptManager

logger = logging.getLogger(__name__)


class AutoOptimizer:
    """自动优化引擎 - 数据驱动"""

    def __init__(self, min_feedback_count: int = 50, accuracy_threshold: float = 0.85):
        """
        初始化自动优化引擎

        Args:
            min_feedback_count: 触发优化的最小反馈数量
            accuracy_threshold: 准确率阈值,低于此值会触发优化
        """
        self.min_feedback_count = min_feedback_count
        self.accuracy_threshold = accuracy_threshold
        self.prompt_manager = PromptManager()

    async def check_and_optimize_all(self, db: Session) -> list[dict[str, Any]]:
        """
        检查所有活跃的Prompt是否需要优化

        Args:
            db: 数据库会话
        """
        # 获取所有活跃的Prompt
        active_prompts = (
            db.query(PromptTemplate)
            .filter(PromptTemplate.status == PromptStatus.ACTIVE)
            .all()
        )

        logger.info(f"🔍 检查{len(active_prompts)}个活跃Prompt...")

        optimization_results: list[dict[str, Any]] = []

        for prompt in active_prompts:
            try:
                # 判断是否需要优化
                should_optimize, reason = await self._should_optimize(db, prompt)

                if should_optimize:
                    logger.info(f"🔧 Prompt '{prompt.name}' 需要优化: {reason}")
                    result = await self.optimize_prompt(db, prompt.id)
                    optimization_results.append(result)
                else:
                    logger.info(f"✅ Prompt '{prompt.name}' 无需优化: {reason}")

            except Exception as e:
                logger.error(f"❌ 优化Prompt '{prompt.name}' 失败: {e}")

        return optimization_results

    async def _should_optimize(
        self, db: Session, prompt: PromptTemplate
    ) -> tuple[bool, str]:
        """
        判断Prompt是否需要优化

        Args:
            db: 数据库会话
            prompt: Prompt模板

        Returns:
            (是否需要优化, 原因)
        """
        # 1. 检查最近7天的反馈数量
        week_ago = datetime.now(UTC) - timedelta(days=7)
        feedback_count = (
            db.query(ExtractionFeedback)
            .filter(
                ExtractionFeedback.template_id == prompt.id,
                ExtractionFeedback.created_at >= week_ago,
            )
            .count()
        )

        if feedback_count >= self.min_feedback_count:
            return True, f"收集到{feedback_count}条反馈(≥{self.min_feedback_count})"

        # 2. 检查当前准确率
        latest_metrics = (
            db.query(func.avg(PromptTemplate.avg_accuracy))
            .filter(PromptTemplate.id == prompt.id)
            .scalar()
        )

        if latest_metrics and latest_metrics < self.accuracy_threshold:
            return (
                True,
                f"准确率{latest_metrics:.1%}低于阈值{self.accuracy_threshold:.1%}",
            )

        return False, "反馈数量和准确率均正常"

    async def optimize_prompt(self, db: Session, template_id: str) -> dict[str, Any]:
        """
        优化指定Prompt

        Args:
            db: 数据库会话
            template_id: Prompt模板ID

        Returns:
            优化结果字典
        """
        # 1. 收集反馈数据
        feedbacks = (
            db.query(ExtractionFeedback)
            .filter(ExtractionFeedback.template_id == template_id)
            .order_by(ExtractionFeedback.created_at.desc())
            .limit(100)
            .all()
        )

        if not feedbacks:
            logger.warning(f"❌ Prompt {template_id} 没有足够反馈数据,跳过优化")
            return {"success": False, "reason": "没有反馈数据"}

        logger.info(f"📊 收集到{len(feedbacks)}条反馈数据")

        # 2. 分析错误模式
        error_patterns = self._analyze_error_patterns(feedbacks)

        # 3. 生成优化规则
        new_rules = self._generate_optimization_rules(error_patterns)

        if not new_rules:
            logger.info(f"✅ Prompt {template_id} 无需优化,未发现明显错误模式")
            return {"success": False, "reason": "无明显错误模式"}

        # 4. 应用优化
        template = db.query(PromptTemplate).get(template_id)
        if not template:
            raise ResourceNotFoundError("Prompt", template_id)

        # 在"重要"部分后追加新规则
        updated_system_prompt = template.system_prompt
        if "⚠️ 重要:" in updated_system_prompt or "⚠️ 重要" in updated_system_prompt:
            updated_system_prompt = updated_system_prompt.replace(
                "⚠️ 重要:", f"⚠️ 重要:\n{chr(10).join(new_rules)}\n"
            )
        else:
            updated_system_prompt += f"\n\n⚠️ 重要:\n{chr(10).join(new_rules)}"

        # 5. 创建新版本
        new_version = self.prompt_manager._increment_version(template.version)

        version_record = PromptVersion()
        version_record.id = str(uuid4())
        version_record.template_id = template_id
        version_record.version = new_version
        version_record.system_prompt = updated_system_prompt
        version_record.user_prompt_template = template.user_prompt_template
        version_record.few_shot_examples = template.few_shot_examples
        version_record.change_description = (
            f"自动优化: 新增{len(new_rules)}条规则 (基于{len(feedbacks)}个反馈)"
        )
        version_record.change_type = "optimized"
        version_record.auto_generated = True

        # 6. 更新模板
        template.system_prompt = updated_system_prompt
        template.version = new_version
        template.current_version_id = version_record.id
        template.updated_at = datetime.now(UTC)

        db.add(version_record)
        db.commit()

        logger.info(f"✨ Prompt '{template.name}' 已自动优化到版本 {new_version}")

        return {
            "success": True,
            "template_id": template_id,
            "template_name": template.name,
            "old_version": template.version,
            "new_version": new_version,
            "rules_added": len(new_rules),
            "feedback_count": len(feedbacks),
            "rules": new_rules,
        }

    def _analyze_error_patterns(
        self, feedbacks: list[ExtractionFeedback]
    ) -> dict[str, Any]:
        """
        分析错误模式

        Args:
            feedbacks: 反馈列表

        Returns:
            错误模式字典
        """
        patterns: dict[str, Any] = {
            "by_field": Counter(),
            "by_error_type": Counter(),
            "examples": defaultdict(list),
        }

        for fb in feedbacks:
            # 统计字段错误
            patterns["by_field"][fb.field_name] += 1

            # 分析错误类型
            error_type = self._classify_error(fb.original_value, fb.corrected_value)
            patterns["by_error_type"][error_type] += 1

            # 保存示例(每个类型最多3个)
            if len(patterns["examples"][error_type]) < 3:
                patterns["examples"][error_type].append(
                    {
                        "field": fb.field_name,
                        "original": fb.original_value,
                        "corrected": fb.corrected_value,
                    }
                )

        logger.info(f"📊 错误分析完成: {dict(patterns['by_error_type'])}")
        return patterns

    @staticmethod
    def _classify_error(original: str, corrected: str) -> str:
        """
        分类错误类型

        Args:
            original: 原始值
            corrected: 修正后的值

        Returns:
            错误类型
        """
        if not original:
            return "missing"
        elif len(corrected) > len(original) and corrected.startswith(original):
            return "truncation"
        elif original.isdigit() and corrected.isdigit() and original != corrected:
            return "number_mismatch"
        elif AutoOptimizer._is_date_error(original, corrected):
            return "date_format"
        elif "号" not in original and "号" in corrected:
            return "certificate_format"
        else:
            return "other"

    @staticmethod
    def _is_date_error(original: str, corrected: str) -> bool:
        """检查是否为日期格式错误"""
        try:
            from datetime import datetime

            datetime.strptime(original, "%Y-%m-%d")
            datetime.strptime(corrected, "%Y-%m-%d")
            return False
        except ValueError:
            return True

    def _generate_optimization_rules(self, patterns: dict[str, Any]) -> list[str]:
        """
        生成优化规则

        Args:
            patterns: 错误模式字典

        Returns:
            规则列表
        """
        rules = []

        # 规则1: 截断问题
        truncation_errors = patterns["by_error_type"].get("truncation", 0)
        if truncation_errors >= 10:  # 截断错误≥10次
            top_field = patterns["by_field"].most_common(1)[0][0]
            example = patterns["examples"]["truncation"][0]
            rules.append(
                f"⚠️ {top_field}字段常见问题({truncation_errors}次):识别结果被截断\n"
                f"   示例:{example['original'][:50]}... → {example['corrected'][:50]}...\n"
                f"   解决:仔细核对完整性,确保包含所有字符"
            )

        # 规则2: 格式问题
        format_errors = patterns["by_error_type"].get("certificate_format", 0)
        if format_errors >= 10:
            rules.append(
                f"⚠️ 证书编号格式问题({format_errors}次):必须包含'号'字,确保提取完整编号\n"
                f"   正确格式示例:粤房地权证穗字第1234567号"
            )

        # 规则3: 日期格式
        date_errors = patterns["by_error_type"].get("date_format", 0)
        if date_errors >= 10:
            rules.append(
                f"⚠️ 日期格式问题({date_errors}次):必须统一为YYYY-MM-DD\n"
                f"   不要使用中文日期或其他格式"
            )

        # 规则4: 高频错误字段
        for field, count in patterns["by_field"].most_common(3):
            if count >= 20:  # 某个字段错误≥20次
                rules.append(f"⚠️ {field}字段需要特别仔细核对(错误{count}次),准确率较低")

        return rules
