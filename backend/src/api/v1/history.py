"""
资产变更历史API端点
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional

from src.database import get_db
from src.services.history_tracker import HistoryService
from src.schemas.asset import AssetHistoryResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/assets/{asset_id}/history")
async def get_asset_history(
    asset_id: str,
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页记录数"),
    change_type: Optional[str] = Query(None, description="变更类型筛选"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    获取资产变更历史
    
    Args:
        asset_id: 资产ID
        page: 页码
        limit: 每页记录数
        change_type: 变更类型筛选 (create/update/delete)
        db: 数据库会话
    
    Returns:
        分页的变更历史记录
    """
    try:
        # 验证资产是否存在
        from src.crud.asset import CRUDAsset
        from src.models.asset import Asset
        
        asset_crud = CRUDAsset(Asset)
        asset = asset_crud.get(db, id=asset_id)
        if not asset:
            raise HTTPException(status_code=404, detail="资产不存在")
        
        # 获取历史记录
        history_service = HistoryService()
        skip = (page - 1) * limit
        
        result = history_service.get_asset_history(
            db=db,
            asset_id=asset_id,
            skip=skip,
            limit=limit,
            change_type=change_type
        )
        
        # 转换为响应格式
        history_responses = []
        for history in result["data"]:
            history_responses.append(AssetHistoryResponse(
                id=history.id,
                asset_id=history.asset_id,
                change_type=history.change_type,
                changed_fields=history.changed_fields or [],
                old_values=history.old_values or {},
                new_values=history.new_values or {},
                changed_by=history.changed_by,
                changed_at=history.changed_at,
                reason=history.reason
            ))
        
        return {
            "data": history_responses,
            "total": result["total"],
            "page": result["page"],
            "limit": result["limit"],
            "has_next": result["has_next"],
            "has_prev": result["has_prev"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取资产历史失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取历史记录失败: {str(e)}")


@router.get("/history/{history_id}")
async def get_history_detail(
    history_id: str,
    db: Session = Depends(get_db)
) -> AssetHistoryResponse:
    """
    获取历史记录详情
    
    Args:
        history_id: 历史记录ID
        db: 数据库会话
    
    Returns:
        历史记录详情
    """
    try:
        history_service = HistoryService()
        history = history_service.get_history_by_id(db, history_id)
        
        if not history:
            raise HTTPException(status_code=404, detail="历史记录不存在")
        
        return AssetHistoryResponse(
            id=history.id,
            asset_id=history.asset_id,
            change_type=history.change_type,
            changed_fields=history.changed_fields or [],
            old_values=history.old_values or {},
            new_values=history.new_values or {},
            changed_by=history.changed_by,
            changed_at=history.changed_at,
            reason=history.reason
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取历史记录详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取历史记录详情失败: {str(e)}")


@router.get("/history/compare/{history_id1}/{history_id2}")
async def compare_history_records(
    history_id1: str,
    history_id2: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    比较两个历史记录
    
    Args:
        history_id1: 第一个历史记录ID
        history_id2: 第二个历史记录ID
        db: 数据库会话
    
    Returns:
        比较结果
    """
    try:
        history_service = HistoryService()
        comparison = history_service.compare_history_records(
            db=db,
            history_id1=history_id1,
            history_id2=history_id2
        )
        
        return {
            "comparison": comparison,
            "message": f"成功比较历史记录，发现 {comparison['total_changes']} 个差异"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"比较历史记录失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"比较历史记录失败: {str(e)}")


@router.get("/assets/{asset_id}/field-history/{field_name}")
async def get_field_history(
    asset_id: str,
    field_name: str,
    limit: int = Query(10, ge=1, le=50, description="限制记录数"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    获取特定字段的变更历史
    
    Args:
        asset_id: 资产ID
        field_name: 字段名
        limit: 限制记录数
        db: 数据库会话
    
    Returns:
        字段变更历史
    """
    try:
        # 验证资产是否存在
        from src.crud.asset import CRUDAsset
        from src.models.asset import Asset
        
        asset_crud = CRUDAsset(Asset)
        asset = asset_crud.get(db, id=asset_id)
        if not asset:
            raise HTTPException(status_code=404, detail="资产不存在")
        
        # 获取字段历史
        history_service = HistoryService()
        field_history = history_service.get_field_history(
            db=db,
            asset_id=asset_id,
            field_name=field_name,
            limit=limit
        )
        
        return {
            "asset_id": asset_id,
            "field_name": field_name,
            "history": field_history,
            "total_changes": len(field_history)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取字段历史失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取字段历史失败: {str(e)}")


@router.get("/history/recent")
async def get_recent_changes(
    limit: int = Query(50, ge=1, le=100, description="限制记录数"),
    change_type: Optional[str] = Query(None, description="变更类型筛选"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    获取最近的变更记录
    
    Args:
        limit: 限制记录数
        change_type: 变更类型筛选
        db: 数据库会话
    
    Returns:
        最近的变更记录
    """
    try:
        history_service = HistoryService()
        recent_changes = history_service.get_recent_changes(
            db=db,
            limit=limit,
            change_type=change_type
        )
        
        # 转换为响应格式
        changes_responses = []
        for history in recent_changes:
            changes_responses.append(AssetHistoryResponse(
                id=history.id,
                asset_id=history.asset_id,
                change_type=history.change_type,
                changed_fields=history.changed_fields or [],
                old_values=history.old_values or {},
                new_values=history.new_values or {},
                changed_by=history.changed_by,
                changed_at=history.changed_at,
                reason=history.reason
            ))
        
        return {
            "data": changes_responses,
            "total": len(changes_responses),
            "message": f"获取到 {len(changes_responses)} 条最近变更记录"
        }
        
    except Exception as e:
        logger.error(f"获取最近变更失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取最近变更失败: {str(e)}")


@router.get("/history/statistics")
async def get_change_statistics(
    asset_id: Optional[str] = Query(None, description="资产ID（可选）"),
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    获取变更统计信息
    
    Args:
        asset_id: 资产ID（可选，为空则统计所有资产）
        days: 统计天数
        db: 数据库会话
    
    Returns:
        变更统计信息
    """
    try:
        # 如果指定了资产ID，验证资产是否存在
        if asset_id:
            from src.crud.asset import CRUDAsset
            from src.models.asset import Asset
            
            asset_crud = CRUDAsset(Asset)
            asset = asset_crud.get(db, id=asset_id)
            if not asset:
                raise HTTPException(status_code=404, detail="资产不存在")
        
        # 获取统计信息
        history_service = HistoryService()
        statistics = history_service.get_change_statistics(
            db=db,
            asset_id=asset_id,
            days=days
        )
        
        return {
            "statistics": statistics,
            "message": f"成功获取 {days} 天内的变更统计信息"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取变更统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取变更统计失败: {str(e)}")


@router.post("/assets/{asset_id}/history/manual")
async def create_manual_history_record(
    asset_id: str,
    change_data: Dict[str, Any],
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    手动创建历史记录（用于数据修复或特殊情况）
    
    Args:
        asset_id: 资产ID
        change_data: 变更数据
        db: 数据库会话
    
    Returns:
        创建结果
    """
    try:
        # 验证资产是否存在
        from src.crud.asset import CRUDAsset
        from src.models.asset import Asset
        
        asset_crud = CRUDAsset(Asset)
        asset = asset_crud.get(db, id=asset_id)
        if not asset:
            raise HTTPException(status_code=404, detail="资产不存在")
        
        # 验证必要字段
        required_fields = ["change_type", "changed_by", "reason"]
        for field in required_fields:
            if field not in change_data:
                raise HTTPException(status_code=400, detail=f"缺少必要字段: {field}")
        
        # 创建历史记录
        from src.services.history_tracker import HistoryTracker
        
        history = HistoryTracker.create_history_record(
            db=db,
            asset_id=asset_id,
            change_type=change_data["change_type"],
            old_values=change_data.get("old_values"),
            new_values=change_data.get("new_values"),
            changed_by=change_data["changed_by"],
            reason=change_data["reason"]
        )
        
        db.commit()
        
        return {
            "history_id": history.id,
            "message": "手动历史记录创建成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建手动历史记录失败: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建手动历史记录失败: {str(e)}")