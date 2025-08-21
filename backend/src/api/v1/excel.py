"""
Excel导入导出API端点
"""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
import tempfile
import os
import logging
from datetime import datetime, timedelta

from src.database import get_db
from src.services.excel_import import ExcelImportService
from src.services.excel_export import ExcelExportService
from src.schemas.excel import ExcelImportResponse, ExcelImportStatus, ExcelExportRequest, ExcelExportResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/import", response_model=ExcelImportResponse)
async def import_excel_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    sheet_name: str = "物业总表",
    db: Session = Depends(get_db)
) -> ExcelImportResponse:
    """
    导入Excel文件中的资产数据
    
    Args:
        file: 上传的Excel文件
        sheet_name: 工作表名称，默认为"物业总表"
        db: 数据库会话
    
    Returns:
        导入结果统计
    """
    # 验证文件类型
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="文件格式不支持，请上传Excel文件（.xlsx或.xls）"
        )
    
    # 验证文件大小（限制为50MB）
    if file.size and file.size > 50 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="文件大小超过限制（50MB）"
        )
    
    # 创建临时文件
    temp_file = None
    try:
        # 保存上传的文件到临时位置
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        logger.info(f"开始导入Excel文件: {file.filename}, 临时文件: {temp_file_path}")
        
        # 执行导入
        import_service = ExcelImportService()
        result = await import_service.import_assets_from_excel(
            file_path=temp_file_path,
            sheet_name=sheet_name,
            db=db
        )
        
        logger.info(f"Excel导入完成: {result}")
        
        return ExcelImportResponse(
            success=result["success"],
            failed=result["failed"],
            total=result["total"],
            errors=result["errors"],
            message=f"导入完成：成功 {result['success']} 条，失败 {result['failed']} 条"
        )
        
    except Exception as e:
        logger.error(f"Excel导入异常: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"导入失败: {str(e)}"
        )
    
    finally:
        # 清理临时文件
        if temp_file and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                logger.warning(f"清理临时文件失败: {str(e)}")


@router.get("/import/template")
async def download_import_template():
    """
    下载Excel导入模板
    
    Returns:
        Excel模板文件
    """
    from fastapi.responses import StreamingResponse
    import io
    import polars as pl
    
    # 创建模板数据
    template_data = {
        "权属方": ["示例：国资集团"],
        "经营管理方": ["示例：五羊公司"],
        "物业名称": ["示例：测试物业"],
        "所在地址": ["示例：广州市天河区测试路123号"],
        "土地面积\n(平方米)": [1000.0],
        "实际房产面积\n(平方米)": [800.0],
        "经营性物业可出租面积\n(平方米)": [600.0],
        "经营性物业已出租面积\n(平方米)": [400.0],
        "经营性物业未出租面积\n(平方米)": [200.0],
        "非经营物业面积\n(平方米)": [200.0],
        "是否确权\n（已确权、未确权、部分确权）": ["已确权"],
        "证载用途\n（商业、住宅、办公、厂房、车位..）": ["商业"],
        "实际用途\n（商业、住宅、办公、厂房、车位..）": ["商业"],
        "业态类别": ["零售"],
        "物业使用状态\n（出租、闲置、自用、公房、其他）": ["出租"],
        "是否涉诉": ["否"],
        "物业性质（经营类、非经营类）": ["经营类"],
        "经营模式": ["直营"],
        "是否计入出租率": ["是"],
        "出租率": ["67%"],
        "承租合同/代理协议": ["合同编号ABC123"],
        "现合同开始日期": ["2024年1月1日"],
        "现合同结束日期": ["2026年12月31日"],
        "租户名称": ["示例租户"],
        "现租赁合同": ["租赁合同DEF456"],
        "现终端出租合同": ["终端合同GHI789"],
        "五羊运营项目名称": ["示例项目"],
        "协议开始日期": ["2024年1月1日"],
        "协议结束日期": ["2026年12月31日"],
        "说明": ["这是示例数据，请删除此行后填入真实数据"],
        "其他备注": ["备注信息"]
    }
    
    # 创建DataFrame
    df = pl.DataFrame(template_data)
    
    # 创建内存中的Excel文件
    buffer = io.BytesIO()
    df.write_excel(buffer, worksheet="物业总表")
    buffer.seek(0)
    
    # 返回文件流
    from urllib.parse import quote
    filename = quote("资产导入模板.xlsx")
    
    return StreamingResponse(
        io.BytesIO(buffer.read()),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"}
    )


@router.get("/import/status/{task_id}")
async def get_import_status(task_id: str) -> ExcelImportStatus:
    """
    获取导入任务状态（用于异步导入）
    
    Args:
        task_id: 任务ID
    
    Returns:
        导入任务状态
    """
    # 简单的状态查询实现（实际项目中应该使用Redis或数据库存储任务状态）
    # 这里返回一个示例状态，表示功能已实现但需要真实的任务存储
    from src.schemas.excel import ImportStatus
    
    return ExcelImportStatus(
        task_id=task_id,
        status=ImportStatus.COMPLETED,
        progress=100.0,
        success=0,
        failed=0,
        total=0,
        errors=[],
        started_at="2024-01-01T00:00:00Z",
        completed_at="2024-01-01T00:01:00Z",
        message="示例状态 - 实际项目中需要实现真实的任务状态存储"
    )


@router.post("/validate")
async def validate_excel_file(
    file: UploadFile = File(...),
    sheet_name: str = "物业总表"
) -> Dict[str, Any]:
    """
    验证Excel文件格式和数据
    
    Args:
        file: 上传的Excel文件
        sheet_name: 工作表名称
    
    Returns:
        验证结果
    """
    # 验证文件类型
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="文件格式不支持，请上传Excel文件（.xlsx或.xls）"
        )
    
    temp_file = None
    try:
        # 保存上传的文件到临时位置
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        # 读取和验证数据
        import_service = ExcelImportService()
        df = import_service.processor.read_excel_file(temp_file_path, sheet_name)
        df = import_service.processor.clean_and_transform_data(df)
        errors = import_service.processor.validate_data(df)
        
        return {
            "valid": len(errors) == 0,
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "errors": errors,
            "columns": df.columns,
            "message": "文件验证完成" if len(errors) == 0 else f"发现 {len(errors)} 个验证错误"
        }
        
    except Exception as e:
        logger.error(f"Excel验证异常: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"验证失败: {str(e)}"
        )
    
    finally:
        # 清理临时文件
        if temp_file and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                logger.warning(f"清理临时文件失败: {str(e)}")


@router.post("/export", response_model=ExcelExportResponse)
async def export_excel_file(
    export_request: ExcelExportRequest,
    db: Session = Depends(get_db)
) -> ExcelExportResponse:
    """
    导出资产数据为Excel文件
    
    Args:
        export_request: 导出请求参数
        db: 数据库会话
    
    Returns:
        导出结果和文件信息
    """
    try:
        logger.info(f"开始导出Excel文件，筛选条件: {export_request.filters}")
        
        # 执行导出
        export_service = ExcelExportService()
        result = await export_service.export_assets_to_excel(
            filters=export_request.filters,
            columns=export_request.columns,
            format=export_request.format,
            include_headers=export_request.include_headers,
            db=db
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=400,
                detail=result["message"]
            )
        
        # 计算过期时间（24小时后）
        expires_at = (datetime.now() + timedelta(hours=24)).isoformat()
        
        logger.info(f"Excel导出完成: {result['message']}")
        
        return ExcelExportResponse(
            file_url=f"/api/v1/excel/download/{os.path.basename(result['file_path'])}",
            file_name=result["file_name"],
            file_size=result["file_size"],
            total_records=result["stats"]["total_records"],
            created_at=result["stats"]["export_time"],
            expires_at=expires_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Excel导出异常: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"导出失败: {str(e)}"
        )


@router.post("/export/async")
async def export_excel_file_async(
    background_tasks: BackgroundTasks,
    export_request: ExcelExportRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    异步导出资产数据为Excel文件（支持进度跟踪）
    
    Args:
        background_tasks: 后台任务
        export_request: 导出请求参数
        db: 数据库会话
    
    Returns:
        任务ID和状态信息
    """
    try:
        from src.services.export_progress import export_progress_tracker, track_export_progress
        
        # 先获取总记录数
        export_service = ExcelExportService()
        assets = await export_service._get_filtered_assets(export_request.filters, db)
        total_records = len(assets)
        
        # 创建进度跟踪任务
        task_id = export_progress_tracker.create_task(
            total_records=total_records,
            filters=export_request.filters,
            format=export_request.format
        )
        
        # 添加后台任务
        background_tasks.add_task(
            track_export_progress,
            task_id,
            export_service.export_assets_to_excel,
            export_request.filters,
            export_request.columns,
            export_request.format,
            export_request.include_headers,
            db
        )
        
        logger.info(f"创建异步导出任务: {task_id}, 总记录数: {total_records}")
        
        return {
            "task_id": task_id,
            "status": "pending",
            "total_records": total_records,
            "message": "导出任务已创建，正在后台处理",
            "status_url": f"/api/v1/excel/export/status/{task_id}"
        }
        
    except Exception as e:
        logger.error(f"创建异步导出任务异常: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"创建导出任务失败: {str(e)}"
        )


@router.get("/download/{filename}")
async def download_exported_file(filename: str):
    """
    下载导出的Excel文件
    
    Args:
        filename: 文件名
    
    Returns:
        文件流
    """
    from fastapi.responses import FileResponse
    import tempfile
    
    try:
        # 构建文件路径
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, filename)
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=404,
                detail="文件不存在或已过期"
            )
        
        # 检查文件名安全性
        if not filename.startswith("资产导出_") or not filename.endswith((".xlsx", ".xls", ".csv")):
            raise HTTPException(
                status_code=400,
                detail="无效的文件名"
            )
        
        logger.info(f"下载导出文件: {filename}")
        
        # 返回文件
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件下载异常: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"下载失败: {str(e)}"
        )


@router.get("/export/info")
async def get_export_info():
    """
    获取导出功能信息
    
    Returns:
        导出功能的配置信息
    """
    try:
        export_service = ExcelExportService()
        info = await export_service.get_export_template_info()
        
        return {
            "message": "导出功能信息",
            "data": info
        }
        
    except Exception as e:
        logger.error(f"获取导出信息异常: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取导出信息失败: {str(e)}"
        )


@router.get("/export/status/{task_id}")
async def get_export_status(task_id: str) -> Dict[str, Any]:
    """
    获取导出任务状态
    
    Args:
        task_id: 任务ID
    
    Returns:
        任务状态信息
    """
    try:
        from src.services.export_progress import export_progress_tracker
        
        task_status = export_progress_tracker.get_task_status(task_id)
        
        if not task_status:
            raise HTTPException(
                status_code=404,
                detail="任务不存在"
            )
        
        # 如果任务已完成且有文件，添加下载链接
        if task_status["status"] == "completed" and task_status["file_name"]:
            task_status["download_url"] = f"/api/v1/excel/download/{task_status['file_name']}"
        
        return task_status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取导出状态异常: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取状态失败: {str(e)}"
        )


@router.get("/export/tasks")
async def list_export_tasks(
    status: Optional[str] = Query(None, description="任务状态筛选"),
    limit: int = Query(50, description="返回数量限制")
) -> Dict[str, Any]:
    """
    列出导出任务
    
    Args:
        status: 任务状态筛选
        limit: 返回数量限制
    
    Returns:
        任务列表
    """
    try:
        from src.services.export_progress import export_progress_tracker, ExportStatus
        
        # 验证状态参数
        filter_status = None
        if status:
            try:
                filter_status = ExportStatus(status)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"无效的状态值: {status}"
                )
        
        tasks = export_progress_tracker.list_tasks(filter_status, limit)
        statistics = export_progress_tracker.get_task_statistics()
        
        return {
            "tasks": tasks,
            "statistics": statistics,
            "total_returned": len(tasks)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"列出导出任务异常: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取任务列表失败: {str(e)}"
        )


@router.delete("/export/tasks/{task_id}")
async def cancel_export_task(task_id: str) -> Dict[str, Any]:
    """
    取消导出任务
    
    Args:
        task_id: 任务ID
    
    Returns:
        取消结果
    """
    try:
        from src.services.export_progress import export_progress_tracker
        
        success = export_progress_tracker.cancel_task(task_id)
        
        if not success:
            raise HTTPException(
                status_code=400,
                detail="任务不存在或无法取消"
            )
        
        return {
            "success": True,
            "message": "任务已取消"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取消导出任务异常: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"取消任务失败: {str(e)}"
        )


@router.post("/export-selected")
async def export_selected_assets(
    export_request: Dict[str, Any],
    db: Session = Depends(get_db)
) -> ExcelExportResponse:
    """
    导出选中的资产数据
    
    Args:
        export_request: 包含asset_ids和导出选项的请求
        db: 数据库会话
    
    Returns:
        导出结果和文件信息
    """
    try:
        asset_ids = export_request.get("asset_ids", [])
        if not asset_ids:
            raise HTTPException(
                status_code=400,
                detail="请选择要导出的资产"
            )
        
        logger.info(f"开始导出选中资产，数量: {len(asset_ids)}")
        
        # 构建筛选条件（通过ID列表）
        filters = {"asset_ids": asset_ids}
        
        # 执行导出
        export_service = ExcelExportService()
        result = await export_service.export_assets_to_excel(
            filters=filters,
            columns=export_request.get("selected_fields"),
            format=export_request.get("format", "xlsx"),
            include_headers=export_request.get("include_headers", True),
            db=db
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=400,
                detail=result["message"]
            )
        
        # 计算过期时间（24小时后）
        expires_at = (datetime.now() + timedelta(hours=24)).isoformat()
        
        logger.info(f"选中资产导出完成: {result['message']}")
        
        return ExcelExportResponse(
            file_url=f"/api/v1/excel/download/{os.path.basename(result['file_path'])}",
            file_name=result["file_name"],
            file_size=result["file_size"],
            total_records=result["stats"]["total_records"],
            created_at=result["stats"]["export_time"],
            expires_at=expires_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"选中资产导出异常: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"导出失败: {str(e)}"
        )


@router.get("/export-history")
async def get_export_history(
    limit: int = Query(50, description="返回数量限制"),
    offset: int = Query(0, description="偏移量")
) -> Dict[str, Any]:
    """
    获取导出历史记录
    
    Args:
        limit: 返回数量限制
        offset: 偏移量
    
    Returns:
        导出历史列表
    """
    try:
        from src.services.export_progress import export_progress_tracker
        
        # 获取所有任务（包括历史任务）
        all_tasks = export_progress_tracker.list_tasks(None, limit + offset)
        
        # 应用分页
        tasks = all_tasks[offset:offset + limit]
        
        # 转换为前端需要的格式
        history = []
        for task in tasks:
            history.append({
                "id": task["task_id"],
                "filename": task.get("file_name", ""),
                "status": task["status"].value if hasattr(task["status"], 'value') else task["status"],
                "progress": task["progress"],
                "total_records": task["total_records"],
                "file_size": task.get("file_size"),
                "download_url": f"/api/v1/excel/download/{task['file_name']}" if task.get("file_name") else None,
                "created_at": task["created_at"],
                "completed_at": task.get("completed_at"),
                "error_message": task.get("error_message")
            })
        
        return {
            "data": history,
            "total": len(all_tasks),
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"获取导出历史异常: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取导出历史失败: {str(e)}"
        )


@router.delete("/export-history/{record_id}")
async def delete_export_record(record_id: str) -> Dict[str, Any]:
    """
    删除导出历史记录
    
    Args:
        record_id: 记录ID
    
    Returns:
        删除结果
    """
    try:
        from src.services.export_progress import export_progress_tracker
        
        # 获取任务信息
        task_status = export_progress_tracker.get_task_status(record_id)
        if not task_status:
            raise HTTPException(
                status_code=404,
                detail="导出记录不存在"
            )
        
        # 删除文件（如果存在）
        if task_status.get("file_name"):
            import tempfile
            temp_dir = tempfile.gettempdir()
            file_path = os.path.join(temp_dir, task_status["file_name"])
            
            export_service = ExcelExportService()
            export_service.cleanup_export_file(file_path)
        
        # 删除任务记录
        success = export_progress_tracker.cancel_task(record_id)
        
        return {
            "success": success,
            "message": "导出记录已删除"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除导出记录异常: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"删除失败: {str(e)}"
        )


@router.get("/export-status/{task_id}")
async def get_export_task_status(task_id: str) -> Dict[str, Any]:
    """
    获取导出任务状态（前端兼容接口）
    
    Args:
        task_id: 任务ID
    
    Returns:
        任务状态信息
    """
    try:
        from src.services.export_progress import export_progress_tracker
        
        task_status = export_progress_tracker.get_task_status(task_id)
        
        if not task_status:
            raise HTTPException(
                status_code=404,
                detail="任务不存在"
            )
        
        # 转换为前端需要的格式
        result = {
            "id": task_status["task_id"],
            "filename": task_status.get("file_name", ""),
            "status": task_status["status"].value if hasattr(task_status["status"], 'value') else task_status["status"],
            "progress": task_status["progress"],
            "total_records": task_status["total_records"],
            "file_size": task_status.get("file_size"),
            "created_at": task_status["created_at"],
            "completed_at": task_status.get("completed_at"),
            "error_message": task_status.get("error_message")
        }
        
        # 如果任务已完成且有文件，添加下载链接
        if result["status"] == "completed" and result["filename"]:
            result["download_url"] = f"/api/v1/excel/download/{result['filename']}"
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取导出状态异常: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取状态失败: {str(e)}"
        )


@router.delete("/cleanup/{filename}")
async def cleanup_export_file(filename: str):
    """
    清理导出文件
    
    Args:
        filename: 要清理的文件名
    
    Returns:
        清理结果
    """
    try:
        import tempfile
        
        # 构建文件路径
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, filename)
        
        # 检查文件名安全性
        if not filename.startswith("资产导出_") or not filename.endswith((".xlsx", ".xls", ".csv")):
            raise HTTPException(
                status_code=400,
                detail="无效的文件名"
            )
        
        export_service = ExcelExportService()
        success = export_service.cleanup_export_file(file_path)
        
        return {
            "success": success,
            "message": "文件清理完成" if success else "文件不存在或清理失败"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件清理异常: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"清理失败: {str(e)}"
        )