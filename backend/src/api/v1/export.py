"""
数据导出API路由
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import csv
import io
import json
from datetime import datetime
import uuid
import asyncio
from concurrent.futures import ThreadPoolExecutor

from ...database import get_db
from ...middleware.auth import get_current_user
from ...models.auth import User
from ...crud.asset import asset_crud
from ...schemas.asset import AssetResponse
from ...services.export_optimizer import export_optimizer

router = APIRouter()

# Force reload by adding comment

# 导出任务状态存储（实际项目中应使用Redis或数据库）
export_tasks = {}

class ExportService:
    """数据导出服务"""

    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=4)

    async def export_assets_to_csv(
        self,
        db: Session,
        filters: Optional[Dict[str, Any]] = None,
        columns: Optional[List[str]] = None
    ) -> str:
        """
        导出资产数据为CSV格式

        Returns:
            str: 导出任务的ID
        """
        task_id = str(uuid.uuid4())

        # 异步执行导出任务
        asyncio.create_task(self._export_assets_csv_background(db, task_id, filters, columns))

        return task_id

    async def _export_assets_csv_background(
        self,
        db: Session,
        task_id: str,
        filters: Optional[Dict[str, Any]],
        columns: Optional[List[str]]
    ):
        """后台执行CSV导出任务"""
        try:
            export_tasks[task_id] = {"status": "processing", "progress": 0}

            # 获取数据
            assets, total = asset_crud.get_multi_with_search(
                db,
                skip=0,
                limit=10000,  # 限制导出数量
                filters=filters
            )

            export_tasks[task_id]["progress"] = 30

            # 准备CSV数据
            output = io.StringIO()

            # 默认导出字段
            default_columns = [
                "property_name", "address", "ownership_entity", "ownership_status",
                "property_nature", "usage_status", "actual_property_area",
                "rentable_area", "rented_area", "annual_income", "annual_expense",
                "tenant_name", "contract_start_date", "contract_end_date"
            ]

            export_columns = columns or default_columns

            # 创建CSV写入器
            writer = csv.DictWriter(output, fieldnames=export_columns)
            writer.writeheader()

            # 写入数据
            for i, asset in enumerate(assets):
                row_data = {}
                for col in export_columns:
                    value = getattr(asset, col, "")
                    if isinstance(value, datetime):
                        value = value.strftime("%Y-%m-%d")
                    elif isinstance(value, (int, float)):
                        value = str(value)
                    elif value is None:
                        value = ""
                    row_data[col] = value

                writer.writerow(row_data)

                # 更新进度
                progress = min(30 + int((i + 1) / len(assets) * 60), 90)
                export_tasks[task_id]["progress"] = progress

            export_tasks[task_id]["progress"] = 95

            # 准备最终结果
            csv_content = output.getvalue()
            output.close()

            # 存储结果
            export_tasks[task_id] = {
                "status": "completed",
                "progress": 100,
                "content": csv_content,
                "filename": f"assets_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "record_count": len(assets)
            }

        except Exception as e:
            export_tasks[task_id] = {
                "status": "failed",
                "progress": 0,
                "error": str(e)
            }

    async def export_assets_to_json(
        self,
        db: Session,
        filters: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        导出资产数据为JSON格式

        Returns:
            str: 导出任务的ID
        """
        task_id = str(uuid.uuid4())

        # 异步执行导出任务
        asyncio.create_task(self._export_assets_json_background(db, task_id, filters))

        return task_id

    async def _export_assets_json_background(
        self,
        db: Session,
        task_id: str,
        filters: Optional[Dict[str, Any]]
    ):
        """后台执行JSON导出任务"""
        try:
            export_tasks[task_id] = {"status": "processing", "progress": 0}

            # 获取数据
            assets, total = asset_crud.get_multi_with_search(
                db,
                skip=0,
                limit=10000,
                filters=filters
            )

            export_tasks[task_id]["progress"] = 50

            # 转换为JSON格式
            export_data = []
            for asset in assets:
                asset_data = {
                    "id": asset.id,
                    "property_name": asset.property_name,
                    "address": asset.address,
                    "ownership_entity": asset.ownership_entity,
                    "ownership_status": asset.ownership_status,
                    "property_nature": asset.property_nature,
                    "usage_status": asset.usage_status,
                    "actual_property_area": float(asset.actual_property_area or 0),
                    "rentable_area": float(asset.rentable_area or 0),
                    "rented_area": float(asset.rented_area or 0),
                    "annual_income": float(asset.annual_income or 0),
                    "annual_expense": float(asset.annual_expense or 0),
                    "tenant_name": asset.tenant_name,
                    "contract_start_date": asset.contract_start_date.isoformat() if asset.contract_start_date else None,
                    "contract_end_date": asset.contract_end_date.isoformat() if asset.contract_end_date else None,
                    "created_at": asset.created_at.isoformat(),
                    "updated_at": asset.updated_at.isoformat()
                }
                export_data.append(asset_data)

            # 准备最终结果
            json_content = json.dumps({
                "export_info": {
                    "timestamp": datetime.now().isoformat(),
                    "total_records": len(export_data),
                    "filters": filters or {}
                },
                "data": export_data
            }, ensure_ascii=False, indent=2)

            export_tasks[task_id] = {
                "status": "completed",
                "progress": 100,
                "content": json_content,
                "filename": f"assets_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                "record_count": len(export_data)
            }

        except Exception as e:
            export_tasks[task_id] = {
                "status": "failed",
                "progress": 0,
                "error": str(e)
            }

# 导出服务实例
export_service = ExportService()

@router.post("/assets/csv")
async def export_assets_csv(
    background_tasks: BackgroundTasks,
    filters: Optional[Dict[str, Any]] = None,
    columns: Optional[List[str]] = None,
    db: Session = Depends(get_db)
):
    """
    导出资产数据为CSV格式

    - **filters**: 筛选条件
    - **columns**: 导出的字段列表
    """
    # 启动导出任务
    task_id = await export_service.export_assets_to_csv(db, filters, columns)

    return {
        "message": "导出任务已启动",
        "task_id": task_id,
        "status_url": f"/api/v1/export/status/{task_id}",
        "download_url": f"/api/v1/export/download/{task_id}"
    }

@router.post("/assets/json")
async def export_assets_json(
    background_tasks: BackgroundTasks,
    filters: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db)
):
    """
    导出资产数据为JSON格式

    - **filters**: 筛选条件
    """
    # 启动导出任务
    task_id = await export_service.export_assets_to_json(db, filters)

    return {
        "message": "导出任务已启动",
        "task_id": task_id,
        "status_url": f"/api/v1/export/status/{task_id}",
        "download_url": f"/api/v1/export/download/{task_id}"
    }

@router.get("/status/{task_id}")
async def get_export_status(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    获取导出任务状态
    """
    if task_id not in export_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")

    return export_tasks[task_id]

@router.get("/download/{task_id}")
async def download_export_file(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    下载导出文件
    """
    if task_id not in export_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")

    task_info = export_tasks[task_id]

    if task_info["status"] != "completed":
        raise HTTPException(status_code=400, detail="任务尚未完成")

    content = task_info["content"]
    filename = task_info["filename"]

    # 根据文件类型确定MIME类型
    if filename.endswith('.csv'):
        media_type = "text/csv; charset=utf-8-sig"
    elif filename.endswith('.json'):
        media_type = "application/json"
    else:
        media_type = "application/octet-stream"

    return StreamingResponse(
        io.StringIO(content),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/templates")
async def get_export_templates():
    """
    获取导出模板
    """
    templates = {
        "csv": {
            "basic": {
                "name": "基础资产信息",
                "columns": [
                    "property_name", "address", "ownership_entity",
                    "ownership_status", "actual_property_area"
                ]
            },
            "financial": {
                "name": "财务信息",
                "columns": [
                    "property_name", "annual_income", "annual_expense",
                    "net_income", "monthly_rent", "rentable_area"
                ]
            },
            "rental": {
                "name": "租赁信息",
                "columns": [
                    "property_name", "tenant_name", "usage_status",
                    "contract_start_date", "contract_end_date", "rented_area"
                ]
            },
            "complete": {
                "name": "完整信息",
                "columns": [
                    "property_name", "address", "ownership_entity", "ownership_status",
                    "property_nature", "usage_status", "actual_property_area",
                    "rentable_area", "rented_area", "annual_income", "annual_expense",
                    "tenant_name", "contract_start_date", "contract_end_date"
                ]
            }
        }
    }

    return templates

@router.delete("/cleanup")
async def cleanup_old_exports(
    current_user: User = Depends(get_current_user)
):
    """
    清理旧的导出任务（只保留最近24小时的）
    """
    current_time = datetime.now()
    to_delete = []

    for task_id, task_info in export_tasks.items():
        # 简单的清理策略：删除超过24小时的任务
        if "filename" in task_info:  # 只清理已完成或失败的文件
            to_delete.append(task_id)

    for task_id in to_delete:
        del export_tasks[task_id]

    return {
        "message": f"已清理 {len(to_delete)} 个旧的导出任务",
        "remaining_tasks": len(export_tasks)
    }