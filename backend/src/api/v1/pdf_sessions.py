"""
PDF会话管理API路由模块

从 pdf_import_unified.py 提取的会话管理相关端点

职责：
- 会话状态查询
- 会话列表和历史
- 确认导入
- 取消会话

端点：
- GET /progress/{session_id}: 获取会话进度
- GET /sessions: 获取活跃会话列表
- GET /sessions/history: 获取会话历史
- POST /confirm_import: 确认导入数据
- DELETE /session/{session_id}: 取消会话
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ...database import get_db
from ...middleware.auth import get_current_active_user
from ...schemas.pdf_import import (
    ActiveSessionResponse,
    ConfirmImportRequest,
    ConfirmImportResponse,
    SessionProgressResponse,
)
from ...services.document.pdf_import_service import PDFImportService
from .dependencies import get_optional_services, get_pdf_import_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["PDF会话管理"])


@router.get("/progress/{session_id}", response_model=SessionProgressResponse)
async def get_session_progress(
    session_id: str,
    db: Session = Depends(get_db),
    pdf_service: PDFImportService = Depends(get_pdf_import_service),
) -> SessionProgressResponse:
    """
    获取会话处理进度

    参数：
    - session_id: 会话ID

    返回：
    - SessionProgressResponse: 包含会话状态和进度信息
    """
    try:
        result = await pdf_service.get_session_status(db, session_id)
        return SessionProgressResponse(
            success=result["success"],
            session_status=result.get("session_status"),
            error=result.get("error"),
        )
    except Exception as e:
        logger.error(f"获取会话进度失败: {str(e)}")
        return SessionProgressResponse(success=False, error=str(e))


@router.get("/sessions", response_model=ActiveSessionResponse)
async def get_active_sessions(
    organization_id: int | None = Query(None),
    limit: int = Query(50, le=100),
    db: Session = Depends(get_db),
    optional: Any = Depends(get_optional_services),
) -> ActiveSessionResponse:
    """
    获取活跃会话列表

    参数：
    - organization_id: 组织ID（可选）
    - limit: 返回数量限制（最大100）

    返回：
    - ActiveSessionResponse: 包含活跃会话列表
    """
    try:
        session_service = optional.pdf_session_service
        if session_service is None:
            return ActiveSessionResponse(
                success=False,
                active_sessions=[],
                total_count=0,
                error="PDF会话服务不可用",
            )

        sessions = await session_service.get_active_sessions(
            db, organization_id=organization_id
        )

        session_data = []
        for session in sessions:
            session_data.append(
                {
                    "session_id": session.session_id,
                    "status": session.status.value,
                    "progress": session.progress_percentage,
                    "current_step": session.current_step.value
                    if session.current_step
                    else None,
                    "created_at": session.created_at.isoformat(),
                    "updated_at": session.updated_at.isoformat()
                    if session.updated_at
                    else None,
                    "file_name": session.original_filename,
                    "file_size": session.file_size,
                    "error_message": session.error_message,
                }
            )

        return ActiveSessionResponse(
            success=True,
            active_sessions=session_data[:limit],
            total_count=len(session_data),
        )

    except Exception as e:
        logger.error(f"获取活跃会话失败: {str(e)}")
        import traceback

        traceback.print_exc()
        return ActiveSessionResponse(
            success=False, active_sessions=[], total_count=0, error=str(e)
        )


@router.get("/sessions/history")
async def get_session_history(
    organization_id: int | None = Query(None),
    limit: int = Query(100, le=200),
    db: Session = Depends(get_db),
    optional: Any = Depends(get_optional_services),
) -> dict[str, Any]:
    """
    获取会话历史记录

    参数：
    - organization_id: 组织ID（可选）
    - limit: 返回数量限制（最大200）

    返回：
    - 包含历史会话列表的字典
    """
    try:
        session_service = optional.pdf_session_service
        if session_service is None:
            return {
                "success": False,
                "history": [],
                "total_count": 0,
                "error": "PDF会话服务不可用",
            }

        sessions = await session_service.get_session_history(
            db, organization_id=organization_id, limit=limit
        )

        history_data = []
        for session in sessions:
            history_data.append(
                {
                    "session_id": session.session_id,
                    "status": session.status.value,
                    "progress": session.progress_percentage,
                    "created_at": session.created_at.isoformat(),
                    "completed_at": session.completed_at.isoformat()
                    if session.completed_at
                    else None,
                    "file_name": session.original_filename,
                    "confidence_score": session.confidence_score,
                    "processing_method": session.processing_method,
                    "error_message": session.error_message,
                }
            )

        return {
            "success": True,
            "history": history_data,
            "total_count": len(history_data),
        }

    except Exception as e:
        logger.error(f"获取会话历史失败: {str(e)}")
        return {"success": False, "history": [], "total_count": 0, "error": str(e)}


@router.post("/confirm_import", response_model=ConfirmImportResponse)
async def confirm_import(
    request: ConfirmImportRequest,
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_active_user),
    pdf_service: PDFImportService = Depends(get_pdf_import_service),
) -> ConfirmImportResponse:
    """
    确认导入合同数据

    将提取的合同数据导入到数据库中。

    参数：
    - request: 确认导入请求，包含会话ID和确认的数据
    - selected_asset_id: 选择的资产ID（可选）
    - selected_ownership_id: 选择的权属方ID（可选）

    返回：
    - ConfirmImportResponse: 包含导入结果和合同ID
    """
    start_time = datetime.now()

    try:
        # 添加用户选择的关联ID
        if request.selected_asset_id:
            request.confirmed_data["asset_id"] = request.selected_asset_id
        if request.selected_ownership_id:
            request.confirmed_data["ownership_id"] = request.selected_ownership_id

        result = await pdf_service.confirm_import(
            db=db,
            session_id=request.session_id,
            confirmed_data=request.confirmed_data,
            user_id=current_user.id,
        )

        processing_time = (datetime.now() - start_time).total_seconds()

        if result["success"]:
            return ConfirmImportResponse(
                success=True,
                message="合同数据导入成功",
                contract_id=result.get("contract_id"),
                contract_number=request.confirmed_data.get("contract_number"),
                created_terms_count=len(request.confirmed_data.get("rent_terms", [])),
                processing_time=processing_time,
            )
        else:
            return ConfirmImportResponse(
                success=False,
                message="导入失败",
                error=result.get("error", "未知错误"),
            )

    except Exception as e:
        logger.error(f"确认导入失败: {str(e)}")
        return ConfirmImportResponse(
            success=False,
            message=f"导入失败: {str(e)}",
            error=str(e),
        )


@router.delete("/session/{session_id}")
async def cancel_session(
    session_id: str,
    reason: str = Query(default="用户取消"),
    db: Session = Depends(get_db),
    pdf_service: PDFImportService = Depends(get_pdf_import_service),
) -> dict[str, Any]:
    """
    取消会话处理

    取消正在处理的PDF导入会话。

    参数：
    - session_id: 会话ID
    - reason: 取消原因（默认: "用户取消"）

    返回：
    - 包含取消结果的字典
    """
    try:
        result = await pdf_service.cancel_processing(
            db=db, session_id=session_id, reason=reason
        )

        return {
            "success": result["success"],
            "message": result["message"],
            "session_id": session_id,
        }

    except Exception as e:
        logger.error(f"取消会话失败: {str(e)}")
        return {
            "success": False,
            "message": f"取消失败: {str(e)}",
            "session_id": session_id,
        }
