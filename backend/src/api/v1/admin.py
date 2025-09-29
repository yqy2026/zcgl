"""
管理员API路由
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from ...database import get_db, drop_tables, create_tables
from ...models.asset import Asset, AssetHistory, AssetDocument

# 创建管理员路由器
router = APIRouter()


@router.post("/clear-database", summary="清空数据库")
async def clear_database(
    confirm: bool = False,
    db: Session = Depends(get_db)
):
    """
    清空数据库中的所有数据
    
    - **confirm**: 必须设置为 true 才能执行清空操作
    """
    if not confirm:
        raise HTTPException(
            status_code=400, 
            detail="必须设置 confirm=true 才能执行清空操作"
        )
    
    try:
        # 获取清空前的统计信息
        asset_count = db.query(Asset).count()
        history_count = db.query(AssetHistory).count()
        document_count = db.query(AssetDocument).count()
        
        # 清空所有表的数据
        db.query(AssetDocument).delete()
        db.query(AssetHistory).delete()
        db.query(Asset).delete()
        
        # 提交事务
        db.commit()
        
        return {
            "success": True,
            "message": "数据库清空成功",
            "cleared_data": {
                "assets": asset_count,
                "history_records": history_count,
                "documents": document_count
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, 
            detail=f"清空数据库失败: {str(e)}"
        )


@router.post("/reset-database", summary="重置数据库")
async def reset_database(
    confirm: bool = False,
    db: Session = Depends(get_db)
):
    """
    重置数据库（删除表结构并重新创建）
    
    - **confirm**: 必须设置为 true 才能执行重置操作
    """
    if not confirm:
        raise HTTPException(
            status_code=400, 
            detail="必须设置 confirm=true 才能执行重置操作"
        )
    
    try:
        # 关闭当前数据库连接
        db.close()
        
        # 删除所有表
        drop_tables()
        
        # 重新创建表
        create_tables()
        
        return {
            "success": True,
            "message": "数据库重置成功",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"重置数据库失败: {str(e)}"
        )


@router.get("/database-info", summary="获取数据库信息")
async def get_database_info(db: Session = Depends(get_db)):
    """
    获取数据库统计信息
    """
    try:
        asset_count = db.query(Asset).count()
        history_count = db.query(AssetHistory).count()
        document_count = db.query(AssetDocument).count()
        
        return {
            "success": True,
            "data": {
                "total_assets": asset_count,
                "total_history_records": history_count,
                "total_documents": document_count,
                "database_status": "connected"
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"获取数据库信息失败: {str(e)}"
        )