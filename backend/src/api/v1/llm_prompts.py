"""
LLM Prompt管理API路由
提供Prompt模板的CRUD操作和版本管理
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception_handler import BaseBusinessError
from ...core.response_handler import APIResponse, PaginatedData, ResponseHandler
from ...database import get_async_db
from ...middleware.auth import get_current_active_user
from ...models.auth import User
from ...models.llm_prompt import PromptTemplate
from ...schemas.llm_prompt import (
    ExtractionFeedbackCreate,
    ExtractionFeedbackResponse,
    PromptRollbackRequest,
    PromptTemplateCreate,
    PromptTemplateResponse,
    PromptTemplateUpdate,
    PromptVersionResponse,
)
from ...services.llm_prompt.feedback_service import FeedbackService
from ...services.llm_prompt.prompt_manager import PromptManager

router = APIRouter(prefix="/llm-prompts", tags=["LLM Prompts"])


@router.post("/", response_model=PromptTemplateResponse)
async def create_prompt(
    *,
    db: AsyncSession = Depends(get_async_db),
    prompt_in: PromptTemplateCreate,
    current_user: User = Depends(get_current_active_user),
) -> PromptTemplate:
    """
    创建新Prompt模板

    - **name**: Prompt名称,必须唯一
    - **doc_type**: 文档类型 (CONTRACT, PROPERTY_CERT等)
    - **provider**: LLM提供商 (qwen, hunyuan, deepseek, glm)
    - **system_prompt**: 系统提示词
    - **user_prompt_template**: 用户提示词模板
    - **few_shot_examples**: Few-shot示例(可选)
    """

    manager = PromptManager()
    try:
        prompt = await manager.create_prompt_async(db, prompt_in, user_id=current_user.id)
        return prompt
    except BaseBusinessError:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=APIResponse[PaginatedData[PromptTemplateResponse]])
async def get_prompts(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页记录数"),
    doc_type: str | None = Query(None, description="文档类型筛选"),
    status: str | None = Query(None, description="状态筛选"),
    provider: str | None = Query(None, description="提供商筛选"),
) -> JSONResponse:
    """
    获取Prompt模板列表

    支持分页和多条件筛选
    """

    manager = PromptManager()
    result = await manager.list_templates_async(
        db,
        doc_type=doc_type,
        status=status,
        provider=provider,
        page=page,
        page_size=page_size,
    )

    return ResponseHandler.paginated(
        data=[PromptTemplateResponse.model_validate(p) for p in result["items"]],
        page=result["page"],
        page_size=result["page_size"],
        total=result["total"],
        message="获取Prompt模板列表成功",
    )


@router.get("/{prompt_id}", response_model=PromptTemplateResponse)
async def get_prompt(
    prompt_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> PromptTemplate:
    """获取Prompt模板详情"""

    manager = PromptManager()
    prompt = await manager.get_by_id_async(db, template_id=prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt不存在")
    return prompt


@router.put("/{prompt_id}", response_model=PromptTemplateResponse)
async def update_prompt(
    prompt_id: str,
    *,
    db: AsyncSession = Depends(get_async_db),
    prompt_in: PromptTemplateUpdate,
    current_user: User = Depends(get_current_active_user),
) -> PromptTemplate:
    """
    更新Prompt模板

    注意: 更新会自动创建新版本
    """

    manager = PromptManager()
    try:
        prompt = await manager.update_prompt_async(
            db, prompt_id, prompt_in, user_id=current_user.id
        )
        return prompt
    except BaseBusinessError:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # ============================================================================
    # 操作
    # ============================================================================

    return prompt


@router.post("/{prompt_id}/activate", response_model=PromptTemplateResponse)
async def activate_prompt(
    prompt_id: str,
    *,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> PromptTemplate:
    """
    激活Prompt模板

    - 停用同类型的其他活跃Prompt
    - 将指定Prompt设置为活跃状态
    """

    manager = PromptManager()
    try:
        prompt = await manager.activate_prompt_async(db, prompt_id)
        return prompt
    except BaseBusinessError:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{prompt_id}/rollback", response_model=PromptTemplateResponse)
async def rollback_prompt(
    prompt_id: str,
    *,
    db: AsyncSession = Depends(get_async_db),
    request: PromptRollbackRequest,
    current_user: User = Depends(get_current_active_user),
) -> PromptTemplate:
    """
    回滚Prompt到指定版本

    - **version_id**: 要回滚到的目标版本ID

    会创建一个新版本记录变更历史
    """

    manager = PromptManager()
    try:
        prompt = await manager.rollback_to_version_async(
            db, prompt_id, request.version_id, user_id=current_user.id
        )
        return prompt
    except BaseBusinessError:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{prompt_id}/versions", response_model=list[PromptVersionResponse])
async def get_prompt_versions(
    prompt_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> list[PromptVersionResponse]:
    """
    获取Prompt的所有历史版本

    返回按创建时间倒序的版本列表
    """

    manager = PromptManager()
    versions = await manager.get_prompt_history_async(db, prompt_id)
    return [PromptVersionResponse.model_validate(v) for v in versions]

    # ============================================================================
    # 统计查询
    # ============================================================================

    return versions


@router.get("/statistics/overview")
async def get_statistics(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    """
    获取Prompt统计概览

    - 总数统计(按状态、按类型、按提供商)
    - 平均准确率和置信度
    """

    manager = PromptManager()
    return await manager.get_statistics_async(db)

    # ============================================================================
    # 反馈收集
    # ============================================================================

    # ============================================================================
    # 反馈收集
    # ============================================================================


@router.post("/feedback", response_model=ExtractionFeedbackResponse)
async def collect_feedback(
    *,
    db: AsyncSession = Depends(get_async_db),
    feedback_in: ExtractionFeedbackCreate,
    current_user: User = Depends(get_current_active_user),
) -> ExtractionFeedbackResponse:
    """
    收集用户反馈(修正数据)

    前端在用户修正字段时自动调用此接口

    - **template_id**: Prompt模板ID
    - **field_name**: 字段名称
    - **original_value**: 原始识别值
    - **corrected_value**: 用户修正后的值
    - **confidence_before**: 修正前的置信度
    """

    service = FeedbackService()
    try:
        return await service.collect_async(db, feedback_in, user_id=current_user.id)
    except BaseBusinessError:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
