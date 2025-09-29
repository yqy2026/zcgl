"""
异步Excel导入API路由
解决长时间导入操作的超时问题
"""

import asyncio
import uuid
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, BackgroundTasks
from sqlalchemy.orm import Session
import json
from pathlib import Path
import tempfile
import os

from ...database import get_db
from ...services.excel_import import ExcelImportService
from ...config.excel_config import STANDARD_SHEET_NAME

# 创建路由器
router = APIRouter()

# 存储导入任务的内存字典（生产环境应使用Redis等）
import_tasks = {}

class AsyncImportService:
    """异步导入服务"""

    def __init__(self):
        self.import_service = ExcelImportService()

    async def start_import(self, file_path: str, sheet_name: str, task_id: str, db: Session) -> Dict[str, Any]:
        """在后台执行导入任务"""
        try:
            # 更新任务状态为处理中
            import_tasks[task_id]['status'] = 'processing'
            import_tasks[task_id]['progress'] = 0

            # 执行导入
            result = await self.import_service.import_assets_from_excel(
                file_path=file_path,
                sheet_name=sheet_name,
                db=db
            )

            # 更新任务状态为完成
            import_tasks[task_id]['status'] = 'completed'
            import_tasks[task_id]['progress'] = 100
            import_tasks[task_id]['result'] = result
            import_tasks[task_id]['completed_at'] = asyncio.get_event_loop().time()

            return result

        except Exception as e:
            # 更新任务状态为失败
            import_tasks[task_id]['status'] = 'failed'
            import_tasks[task_id]['error'] = str(e)
            import_tasks[task_id]['completed_at'] = asyncio.get_event_loop().time()

            return {
                "success": 0,
                "failed": 0,
                "total": 0,
                "errors": [f"导入失败: {str(e)}"]
            }

        finally:
            # 清理临时文件
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
            except:
                pass

async_import_service = AsyncImportService()

@router.post("/import/async", summary="异步导入Excel数据")
async def import_excel_async(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    skip_errors: bool = Query(False, description="是否跳过错误行"),
    sheet_name: str = Query(STANDARD_SHEET_NAME, description="Excel工作表名称"),
    db: Session = Depends(get_db)
):
    """
    异步从Excel文件导入资产数据，避免长时间请求超时

    返回任务ID，可以通过轮询查询导入状态
    """
    # 验证文件类型
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="文件格式不支持，请上传Excel文件(.xlsx/.xls)"
        )

    # 生成任务ID
    task_id = str(uuid.uuid4())

    # 保存上传的文件到临时位置
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_file_path = tmp_file.name

    # 创建任务记录
    import_tasks[task_id] = {
        'task_id': task_id,
        'filename': file.filename,
        'status': 'pending',
        'progress': 0,
        'created_at': asyncio.get_event_loop().time(),
        'result': None,
        'error': None
    }

    # 在后台执行导入任务
    background_tasks.add_task(
        async_import_service.start_import,
        tmp_file_path,
        sheet_name,
        task_id,
        db
    )

    return {
        "task_id": task_id,
        "message": "导入任务已提交，请在后台处理",
        "status": "pending"
    }

@router.get("/import/status/{task_id}", summary="查询导入任务状态")
async def get_import_status(task_id: str):
    """
    查询异步导入任务的状态和结果
    """
    if task_id not in import_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")

    task = import_tasks[task_id]

    return {
        "task_id": task_id,
        "filename": task['filename'],
        "status": task['status'],
        "progress": task['progress'],
        "created_at": task['created_at'],
        "completed_at": task.get('completed_at'),
        "result": task.get('result'),
        "error": task.get('error')
    }

@router.get("/import/tasks", summary="获取所有导入任务")
async def get_import_tasks():
    """
    获取所有导入任务列表
    """
    return {
        "tasks": list(import_tasks.values()),
        "total": len(import_tasks)
    }

@router.delete("/import/tasks/{task_id}", summary="删除导入任务")
async def delete_import_task(task_id: str):
    """
    删除已完成的导入任务
    """
    if task_id not in import_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")

    task = import_tasks[task_id]

    # 只能删除已完成的任务
    if task['status'] not in ['completed', 'failed']:
        raise HTTPException(status_code=400, detail="只能删除已完成的任务")

    del import_tasks[task_id]

    return {
        "message": "任务已删除",
        "task_id": task_id
    }