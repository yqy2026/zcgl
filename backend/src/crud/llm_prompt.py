"""
LLM prompt CRUD operations.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.llm_prompt import (
    ExtractionFeedback,
    PromptStatus,
    PromptTemplate,
    PromptVersion,
)
from ..schemas.llm_prompt import PromptTemplateCreate, PromptTemplateUpdate
from .base import CRUDBase


class CRUDPromptTemplate(
    CRUDBase[PromptTemplate, PromptTemplateCreate, PromptTemplateUpdate]
):
    """CRUD for PromptTemplate."""

    async def get_by_name_async(
        self, db: AsyncSession, *, name: str
    ) -> PromptTemplate | None:
        stmt = select(PromptTemplate).where(PromptTemplate.name == name)
        return (await db.execute(stmt)).scalars().first()

    async def get_active_prompt_async(
        self, db: AsyncSession, *, doc_type: str, provider: str | None = None
    ) -> PromptTemplate | None:
        stmt = (
            select(PromptTemplate)
            .where(
                PromptTemplate.doc_type == doc_type,
                PromptTemplate.status == PromptStatus.ACTIVE,
            )
            .order_by(PromptTemplate.updated_at.desc())
        )
        if provider:
            stmt = stmt.where(PromptTemplate.provider == provider)
        return (await db.execute(stmt)).scalars().first()

    async def get_active_prompts_async(self, db: AsyncSession) -> list[PromptTemplate]:
        stmt = select(PromptTemplate).where(
            PromptTemplate.status == PromptStatus.ACTIVE
        )
        return list((await db.execute(stmt)).scalars().all())

    async def archive_active_by_doc_type_async(
        self,
        db: AsyncSession,
        *,
        doc_type: str,
        exclude_template_id: str | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        stmt = update(PromptTemplate).where(
            PromptTemplate.doc_type == doc_type,
            PromptTemplate.status == PromptStatus.ACTIVE,
        )
        if exclude_template_id:
            stmt = stmt.where(PromptTemplate.id != exclude_template_id)

        values: dict[str, Any] = {"status": PromptStatus.ARCHIVED}
        if updated_at is not None:
            values["updated_at"] = updated_at
        await db.execute(stmt.values(**values))

    async def get_list_with_filters_async(
        self,
        db: AsyncSession,
        *,
        doc_type: str | None = None,
        status: str | None = None,
        provider: str | None = None,
        skip: int = 0,
        limit: int = 10,
    ) -> tuple[list[PromptTemplate], int]:
        clauses: list[Any] = []
        if doc_type:
            clauses.append(PromptTemplate.doc_type == doc_type)
        if status:
            clauses.append(PromptTemplate.status == status)
        if provider:
            clauses.append(PromptTemplate.provider == provider)

        count_stmt = select(func.count()).select_from(PromptTemplate)
        if clauses:
            count_stmt = count_stmt.where(*clauses)
        total = int((await db.execute(count_stmt)).scalar() or 0)

        stmt = select(PromptTemplate)
        if clauses:
            stmt = stmt.where(*clauses)
        stmt = stmt.offset(skip).limit(limit)
        items = list((await db.execute(stmt)).scalars().all())
        return items, total

    async def get_average_accuracy_async(
        self, db: AsyncSession, *, template_id: str
    ) -> float | None:
        stmt = select(func.avg(PromptTemplate.avg_accuracy)).where(
            PromptTemplate.id == template_id
        )
        value = (await db.execute(stmt)).scalar()
        if value is None:
            return None
        return float(value)

    async def get_statistics_async(self, db: AsyncSession) -> dict[str, Any]:
        total_stmt = select(func.count()).select_from(PromptTemplate)
        total_prompts = int((await db.execute(total_stmt)).scalar() or 0)

        status_stmt = select(
            PromptTemplate.status, func.count(PromptTemplate.id)
        ).group_by(PromptTemplate.status)
        status_stats = (await db.execute(status_stmt)).all()

        doc_type_stmt = select(
            PromptTemplate.doc_type, func.count(PromptTemplate.id)
        ).group_by(PromptTemplate.doc_type)
        doc_type_stats = (await db.execute(doc_type_stmt)).all()

        provider_stmt = select(
            PromptTemplate.provider, func.count(PromptTemplate.id)
        ).group_by(PromptTemplate.provider)
        provider_stats = (await db.execute(provider_stmt)).all()

        avg_accuracy_stmt = select(func.avg(PromptTemplate.avg_accuracy))
        avg_accuracy = (await db.execute(avg_accuracy_stmt)).scalar() or 0.0
        avg_confidence_stmt = select(func.avg(PromptTemplate.avg_confidence))
        avg_confidence = (await db.execute(avg_confidence_stmt)).scalar() or 0.0

        return {
            "total_prompts": total_prompts,
            "status_distribution": [
                {"status": status, "count": count} for status, count in status_stats
            ],
            "doc_type_distribution": [
                {"doc_type": doc_type_name, "count": count}
                for doc_type_name, count in doc_type_stats
            ],
            "provider_distribution": [
                {"provider": provider_name, "count": count}
                for provider_name, count in provider_stats
            ],
            "overall_avg_accuracy": float(avg_accuracy),
            "overall_avg_confidence": float(avg_confidence),
        }


class CRUDPromptVersion:
    """CRUD helpers for PromptVersion."""

    async def get_async(
        self, db: AsyncSession, *, version_id: str
    ) -> PromptVersion | None:
        stmt = select(PromptVersion).where(PromptVersion.id == version_id)
        return (await db.execute(stmt)).scalars().first()

    async def get_by_template_async(
        self, db: AsyncSession, *, template_id: str
    ) -> list[PromptVersion]:
        stmt = (
            select(PromptVersion)
            .where(PromptVersion.template_id == template_id)
            .order_by(PromptVersion.created_at.desc())
        )
        return list((await db.execute(stmt)).scalars().all())


class CRUDExtractionFeedback:
    """CRUD helpers for ExtractionFeedback."""

    async def count_since_async(
        self, db: AsyncSession, *, template_id: str, created_after: datetime
    ) -> int:
        stmt = select(func.count(ExtractionFeedback.id)).where(
            ExtractionFeedback.template_id == template_id,
            ExtractionFeedback.created_at >= created_after,
        )
        return int((await db.execute(stmt)).scalar() or 0)

    async def get_by_template_async(
        self, db: AsyncSession, *, template_id: str, limit: int = 100
    ) -> list[ExtractionFeedback]:
        stmt = (
            select(ExtractionFeedback)
            .where(ExtractionFeedback.template_id == template_id)
            .order_by(ExtractionFeedback.created_at.desc())
            .limit(limit)
        )
        return list((await db.execute(stmt)).scalars().all())


prompt_template_crud = CRUDPromptTemplate(PromptTemplate)
prompt_version_crud = CRUDPromptVersion()
extraction_feedback_crud = CRUDExtractionFeedback()
