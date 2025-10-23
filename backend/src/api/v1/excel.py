"""
Excel导入导出API路由 - 增强版，支持任务管理和状态跟踪
"""

# 标准库导入
import io
import os
import tempfile
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any

# 第三方库导入
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Body, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

# 本地导入
from ...database import get_db
from ...models.asset import Asset
from ...models.task import AsyncTask
from ...schemas.asset import AssetCreate, AssetResponse
from ...schemas.task import TaskCreate, TaskUpdate, TaskResponse
from ...schemas.excel_advanced import (
    ExcelImportRequest, ExcelExportRequest, ExcelPreviewRequest,
    ExcelImportResult, ExcelExportResult, ExcelPreviewResponse,
    ExcelConfigCreate, ExcelStatusResponse
)
from ...config.excel_config import STANDARD_SHEET_NAME
from ...crud.asset import asset_crud
from ...crud.task import task_crud
from ...enums.task import TaskStatus, TaskType
from ...core.security import security_middleware, validate_file_upload_dependency
from ...core.exception_handler import ValidationException
from ...core.logging_security import security_auditor
import logging

logger = logging.getLogger(__name__)

# 创建Excel路由器
router = APIRouter(prefix="/excel", tags=["Excel导入导出"])


@router.get("/template", summary="下载Excel导入模板")
async def download_template():
    """
    下载Excel导入模板文件 - 已优化与新增资产表单字段保持一致
    """
    try:
        # 创建示例数据 - 按照新增资产表单字段顺序排列，删除自动计算、高级选项和文件上传字段
        template_data = {
            # 基本信息
            "权属方": ["示例权属方1", "示例权属方2"],
            "权属类别": ["国有", "集体"],
            "项目名称": ["示例项目1", "示例项目2"],
            "物业名称": ["示例物业1", "示例物业2"],
            "物业地址": ["示例地址1", "示例地址2"],

            # 面积信息
            "土地面积(平方米)": [1000.0, 2000.0],
            "实际房产面积(平方米)": [800.0, 1800.0],
            "非经营物业面积(平方米)": [200.0, 300.0],
            "可出租面积(平方米)": [600.0, 1500.0],
            "已出租面积(平方米)": [400.0, 1200.0],

            # 状态信息
            "确权状态（已确权、未确权、部分确权）": ["已确权", "未确权"],
            "证载用途（商业、住宅、办公、厂房、车库等）": ["商业", "办公"],
            "实际用途（商业、住宅、办公、厂房、车库等）": ["商业", "办公"],
            "业态类别": ["零售", "餐饮"],
            "使用状态（出租、闲置、自用、公房、其他）": ["出租", "闲置"],
            "是否涉诉": ["否", "否"],
            "物业性质（经营类、非经营类）": ["经营类", "非经营类"],
            "是否计入出租率": ["是", "是"],

            # 接收信息
            "接收模式": ["自营", "合作"],
            "(当前)接收协议开始日期": ["2024-01-01", "2024-02-01"],
            "(当前)接收协议结束日期": ["2024-12-31", "2024-12-31"]
        }
        
        # 创建DataFrame
        df = pd.DataFrame(template_data)
        
        # 写入Excel文件
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name=STANDARD_SHEET_NAME, index=False)
        buffer.seek(0)

        # 返回文件流（避免重复读取buffer）
        async def file_generator():
            data = buffer.getvalue()
            yield data
            buffer.close()

        return StreamingResponse(
            file_generator(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=land_property_asset_template.xlsx"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成模板失败: {str(e)}")


@router.get("/test", summary="测试端点")
async def test_endpoint():
    """测试端点"""
    return {"message": "Excel API 测试成功", "timestamp": "2025-08-27"}


# ===== Excel配置管理 =====

@router.post("/configs", summary="创建Excel配置")
async def create_excel_config(
    config_in: ExcelConfigCreate,
    db: Session = Depends(get_db)
):
    """
    创建Excel导入导出配置

    - **config_in**: 配置信息
    """
    try:
        from ...crud.task import excel_task_config_crud
        config = excel_task_config_crud.create(db=db, obj_in=config_in)
        return {
            "message": "配置创建成功",
            "config_id": config.id,
            "config_name": config.config_name
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建配置失败: {str(e)}")


@router.get("/configs", summary="获取Excel配置列表")
async def get_excel_configs(
    config_type: Optional[str] = Query(None, description="配置类型"),
    task_type: Optional[str] = Query(None, description="任务类型"),
    db: Session = Depends(get_db)
):
    """
    获取Excel配置列表

    - **config_type**: 按配置类型筛选
    - **task_type**: 按任务类型筛选
    """
    try:
        from ...crud.task import excel_task_config_crud
        configs = excel_task_config_crud.get_multi(
            db=db,
            limit=50,
            config_type=config_type,
            task_type=task_type
        )
        return {
            "items": configs,
            "total": len(configs)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")


@router.get("/configs/default", summary="获取默认Excel配置")
async def get_default_excel_config(
    config_type: str = Query(..., description="配置类型"),
    task_type: str = Query(..., description="任务类型"),
    db: Session = Depends(get_db)
):
    """
    获取默认的Excel配置

    - **config_type**: 配置类型
    - **task_type**: 任务类型
    """
    try:
        from ...crud.task import excel_task_config_crud
        config = excel_task_config_crud.get_default(
            db=db,
            config_type=config_type,
            task_type=task_type
        )
        if not config:
            raise HTTPException(status_code=404, detail="未找到默认配置")
        return config
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取默认配置失败: {str(e)}")


@router.get("/configs/{config_id}", summary="获取Excel配置详情")
async def get_excel_config(
    config_id: str,
    db: Session = Depends(get_db)
):
    """
    获取单个Excel配置的详细信息

    - **config_id**: 配置ID
    """
    try:
        from ...crud.task import excel_task_config_crud
        config = excel_task_config_crud.get(db=db, id=config_id)
        if not config:
            raise HTTPException(status_code=404, detail="配置不存在")
        return config
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取配置详情失败: {str(e)}")


@router.put("/configs/{config_id}", summary="更新Excel配置")
async def update_excel_config(
    config_id: str,
    config_in: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    更新Excel配置

    - **config_id**: 配置ID
    - **config_in**: 更新数据
    """
    try:
        from ...crud.task import excel_task_config_crud
        config = excel_task_config_crud.get(db=db, id=config_id)
        if not config:
            raise HTTPException(status_code=404, detail="配置不存在")

        updated_config = excel_task_config_crud.update(
            db=db,
            db_obj=config,
            obj_in=config_in
        )
        return {
            "message": "配置更新成功",
            "config_id": updated_config.id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新配置失败: {str(e)}")


@router.delete("/configs/{config_id}", summary="删除Excel配置")
async def delete_excel_config(
    config_id: str,
    db: Session = Depends(get_db)
):
    """
    删除Excel配置

    - **config_id**: 配置ID
    """
    try:
        from ...crud.task import excel_task_config_crud
        excel_task_config_crud.delete(db=db, id=config_id)
        return {"message": "配置删除成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除配置失败: {str(e)}")


# ===== Excel预览增强 =====

@router.post("/preview/advanced", response_model=ExcelPreviewResponse, summary="高级Excel预览")
async def preview_excel_advanced(
    file: UploadFile = File(...),
    request: ExcelPreviewRequest = Body(...),
    db: Session = Depends(get_db)
):
    """
    高级Excel文件预览，支持字段映射检测

    - **file**: Excel文件
    - **request**: 预览配置参数
    """
    try:
        # 安全验证文件
        validation_result = await security_middleware.validate_file_upload(
            file,
            allowed_types=[
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'application/vnd.ms-excel'
            ],
            max_size=50 * 1024 * 1024  # 50MB
        )

        # 记录文件验证成功
        security_auditor.log_security_event(
            event_type="FILE_UPLOAD_VALIDATED",
            message=f"Excel file validated successfully: {file.filename}",
            details={
                "filename": file.filename,
                "size": file.size,
                "hash": validation_result.get("hash"),
                "validation_time": validation_result.get("validation_time")
            }
        )

        # 读取文件内容
        content = await file.read()

        # 直接从内存读取Excel
        df = pd.read_excel(io.BytesIO(content))

        # 获取基本信息
        total = len(df)
        columns = df.columns.tolist()

        # 限制预览行数
        preview_rows = min(request.max_rows, total)
        preview_df = df.head(preview_rows)

        # 转换为字典格式，处理NaN值
        preview_data = []
        for _, row in preview_df.iterrows():
            row_dict = {}
            for col in columns:
                value = row[col]
                # 处理NaN和None值
                if pd.isna(value):
                    row_dict[col] = None
                else:
                    row_dict[col] = str(value) if not isinstance(value, (str, int, float)) else value
            preview_data.append(row_dict)

        # 检测字段映射（简化版本）
        detected_mapping = []
        field_mapping_rules = {
            "物业名称": ["property_name", "物业名称", "资产名称"],
            "地址": ["address", "物业地址", "地址", "位置"],
            "确权状态": ["ownership_status", "确权状态", "权属状态"],
            "物业性质": ["property_nature", "物业性质", "资产性质"],
            "使用状态": ["usage_status", "使用状态", "状态"],
            "权属方": ["ownership_entity", "权属方", "所有权人"],
            "土地面积": ["land_area", "土地面积", "占地面积"],
            "实际房产面积": ["actual_property_area", "实际房产面积", "建筑面积"],
            "可出租面积": ["rentable_area", "可出租面积", "出租面积"],
            "已出租面积": ["rented_area", "已出租面积", "已租面积"],
        }

        for col in columns:
            for chinese_name, possible_names in field_mapping_rules.items():
                if any(name.lower() in str(col).lower() for name in possible_names):
                    detected_mapping.append({
                        "excel_column": col,
                        "system_field": possible_names[0],
                        "data_type": "string",
                        "required": chinese_name in ["物业名称", "地址"],
                        "confidence": 0.8
                    })
                    break

        return ExcelPreviewResponse(
            file_name=file.filename,
            sheet_names=[f"Sheet{i+1}" for i in range(1)],  # 简化处理
            total_rows=total,
            columns=columns,
            preview_data=preview_data,
            detected_field_mapping=detected_mapping
        )

    except ValidationException as e:
        logger.error(f"Excel preview validation failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Excel preview failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"预览Excel文件失败: {str(e)}"
        )

@router.post("/preview", summary="预览Excel文件内容")
async def preview_excel(
    file: UploadFile = File(...),
    max_rows: int = Query(10, ge=1, le=100, description="预览行数")
):
    """
    预览Excel文件内容，用于导入前确认
    """
    try:
        # 安全验证文件
        validation_result = await security_middleware.validate_file_upload(
            file,
            allowed_types=[
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'application/vnd.ms-excel'
            ],
            max_size=50 * 1024 * 1024  # 50MB
        )

        # 验证文件类型（额外检查）
        if not file.filename or not file.filename.endswith(('.xlsx', '.xls')):
            raise ValidationException(
                "文件格式不支持，请上传Excel文件(.xlsx/.xls)"
            )

        # 读取文件内容
        content = await file.read()
        
        # 直接从内存读取Excel
        df = pd.read_excel(io.BytesIO(content))
        
        # 获取基本信息
        total = len(df)
        columns = df.columns.tolist()
        
        # 限制预览行数
        preview_rows = min(max_rows, total)
        preview_df = df.head(preview_rows)
        
        # 转换为字典格式，处理NaN值
        preview_data = []
        for _, row in preview_df.iterrows():
            row_dict = {}
            for col in columns:
                value = row[col]
                # 处理NaN和None值
                if pd.isna(value):
                    row_dict[col] = None
                else:
                    row_dict[col] = str(value) if not isinstance(value, (str, int, float)) else value
            preview_data.append(row_dict)
        
        return {
            "message": "预览成功",
            "filename": file.filename,
            "total": total,
            "preview_rows": preview_rows,
            "columns": columns,
            "data": preview_data
        }
        
    except ValidationException as e:
        logger.error(f"Excel preview validation failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Excel preview failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"预览Excel文件失败: {str(e)}"
        )


@router.post("/import", summary="导入Excel数据（同步）")
async def import_excel(
    file: UploadFile = File(...),
    skip_errors: bool = Query(False, description="是否跳过错误行"),
    sheet_name: str = Query(STANDARD_SHEET_NAME, description="Excel工作表名称"),
    db: Session = Depends(get_db)
):
    """
    从Excel文件导入资产数据（同步版本）

    - **file**: Excel文件
    - **skip_errors**: 是否跳过错误行继续导入
    - **sheet_name**: Excel工作表名称，默认为"{STANDARD_SHEET_NAME}"
    """
    try:
        # 安全验证文件
        validation_result = await security_middleware.validate_file_upload(
            file,
            allowed_types=[
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'application/vnd.ms-excel'
            ],
            max_size=100 * 1024 * 1024  # 100MB for import
        )

        # 验证文件类型（额外检查）
        if not file.filename or not file.filename.endswith(('.xlsx', '.xls')):
            raise ValidationException(
                "文件格式不支持，请上传Excel文件(.xlsx/.xls)"
            )

        # 记录导入操作开始
        security_auditor.log_security_event(
            event_type="EXCEL_IMPORT_STARTED",
            message=f"Excel import started: {file.filename} (sheet: {sheet_name})",
            details={
                "filename": file.filename,
                "size": file.size,
                "sheet_name": sheet_name,
                "skip_errors": skip_errors
            }
        )

        # 保存上传的文件到临时位置
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
            # 写入上传的文件内容
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name

        try:
            # 使用ExcelImportService进行导入
            from ...services.excel_import import ExcelImportService
            import_service = ExcelImportService()

            # 执行导入
            result = await import_service.import_assets_from_excel(
                file_path=tmp_file_path,
                sheet_name=sheet_name,
                db=db
            )

            # 转换结果格式以匹配前端期望
            return {
                "message": "导入完成",
                "total": result.get("total", 0),
                "success": result.get("success", 0),
                "failed": result.get("failed", 0),
                "errors": result.get("errors", [])
            }

        finally:
            # 清理临时文件
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)

    except ValidationException as e:
        logger.error(f"Excel import validation failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Excel import failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")
    finally:
        # 清理临时文件
        if 'tmp_file_path' in locals() and os.path.exists(tmp_file_path):
            os.unlink(tmp_file_path)


@router.post("/import/async", summary="异步导入Excel数据")
async def import_excel_async(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    request: ExcelImportRequest = Body(...),
    db: Session = Depends(get_db)
):
    """
    异步导入Excel文件，返回任务ID用于跟踪进度

    - **file**: Excel文件
    - **request**: 导入配置参数
    """
    try:
        # 安全验证文件
        validation_result = await security_middleware.validate_file_upload(
            file,
            allowed_types=[
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'application/vnd.ms-excel'
            ],
            max_size=100 * 1024 * 1024  # 100MB for import
        )

        # 验证文件类型（额外检查）
        if not file.filename or not file.filename.endswith(('.xlsx', '.xls')):
            raise ValidationException(
                "文件格式不支持，请上传Excel文件(.xlsx/.xls)"
            )

        # 记录异步导入操作开始
        security_auditor.log_security_event(
            event_type="EXCEL_ASYNC_IMPORT_STARTED",
            message=f"Async Excel import started: {file.filename}",
            details={
                "filename": file.filename,
                "size": file.size,
                "request_config": request.dict(),
                "validation_hash": validation_result.get("hash")
            }
        )
        # 创建导入任务
        task_in = TaskCreate(
            task_type=TaskType.EXCEL_IMPORT,
            title=f"Excel导入任务 - {file.filename}",
            description=f"异步导入Excel文件: {file.filename}",
            parameters={
                "filename": file.filename,
                "sheet_name": request.sheet_name or STANDARD_SHEET_NAME,
                "validate_data": request.validate_data,
                "create_assets": request.create_assets,
                "update_existing": request.update_existing,
                "skip_errors": request.skip_errors,
                "batch_size": request.batch_size
            },
            config=request.config_id or {}
        )

        task = task_crud.create(db=db, obj_in=task_in)

        # 保存上传文件到临时位置
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name

        # 添加后台任务
        background_tasks.add_task(
            _process_excel_import_async,
            task_id=task.id,
            file_path=tmp_file_path,
            request=request,
            db_session=db
        )

        return {
            "message": "导入任务已创建",
            "task_id": task.id,
            "status": task.status,
            "estimated_time": "预计需要2-5分钟，请使用task_id查询进度"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建导入任务失败: {str(e)}")


async def _process_excel_import_async(
    task_id: str,
    file_path: str,
    request: ExcelImportRequest,
    db_session: Session
):
    """
    后台处理Excel导入任务
    """
    import os

    # 更新任务状态为运行中
    try:
        task_crud.update(
            db=db_session,
            db_obj=task_crud.get(db=db_session, id=task_id),
            obj_in=TaskUpdate(
                status=TaskStatus.RUNNING,
                started_at=datetime.utcnow()
            )
        )
        db_session.commit()

        # 使用ExcelImportService进行导入
        from ...services.excel_import import ExcelImportService
        import_service = ExcelImportService()

        # 执行导入
        result = await import_service.import_assets_from_excel(
            file_path=file_path,
            sheet_name=request.sheet_name or STANDARD_SHEET_NAME,
            db=db_session,
            validate_data=request.validate_data,
            create_assets=request.create_assets,
            update_existing=request.update_existing,
            skip_errors=request.skip_errors,
            batch_size=request.batch_size
        )

        # 更新任务完成状态
        task_crud.update(
            db=db_session,
            db_obj=task_crud.get(db=db_session, id=task_id),
            obj_in=TaskUpdate(
                status=TaskStatus.COMPLETED,
                completed_at=datetime.utcnow(),
                progress=100,
                result_data={
                    "total": result.get("total", 0),
                    "success": result.get("success", 0),
                    "failed": result.get("failed", 0),
                    "created_assets": result.get("created_assets", 0),
                    "updated_assets": result.get("updated_assets", 0),
                    "errors": result.get("errors", []),
                    "warnings": result.get("warnings", [])
                }
            )
        )
        db_session.commit()

    except Exception as e:
        # 更新任务失败状态
        task_crud.update(
            db=db_session,
            db_obj=task_crud.get(db=db_session, id=task_id),
            obj_in=TaskUpdate(
                status=TaskStatus.FAILED,
                completed_at=datetime.utcnow(),
                error_message=str(e)
            )
        )
        db_session.commit()

    finally:
        # 清理临时文件
        if os.path.exists(file_path):
            os.unlink(file_path)


@router.get("/export", summary="导出Excel文件")
async def export_excel(
    search: Optional[str] = Query(None, description="搜索关键词"),
    ownership_status: Optional[str] = Query(None, description="确权状态筛选"),
    property_nature: Optional[str] = Query(None, description="物业性质筛选"),
    usage_status: Optional[str] = Query(None, description="使用状态筛选"),
    db: Session = Depends(get_db)
):
    """
    导出资产数据为Excel文件
    
    支持按条件筛选导出
    """
    try:
        # 构建筛选条件
        filters = {}
        if ownership_status:
            filters["ownership_status"] = ownership_status
        if property_nature:
            filters["property_nature"] = property_nature
        if usage_status:
            filters["usage_status"] = usage_status
        
        # 从数据库获取资产数据
        assets, total = asset_crud.get_multi_with_search(
            db=db, 
            search=search,
            filters=filters,
            limit=1000  # 导出时获取更多数据
        )
        
        # 转换为导出格式
        export_data = []
        for asset in assets:
            export_data.append({
                "物业名称": getattr(asset, 'property_name', ''),
                "地址": getattr(asset, 'address', ''),
                "确权状态": getattr(asset, 'ownership_status', ''),
                "物业性质": getattr(asset, 'property_nature', ''),
                "使用状态": getattr(asset, 'usage_status', ''),
                "权属方": getattr(asset, 'ownership_entity', ''),
                "经营管理方": getattr(asset, 'management_entity', ''),
                "业态类别": getattr(asset, 'business_category', ''),
                "是否涉诉": "是" if getattr(asset, 'is_litigated', False) else "否",
                "备注": getattr(asset, 'notes', ''),
                "创建时间": asset.created_at.strftime("%Y-%m-%d %H:%M:%S") if asset.created_at else "",
                "更新时间": asset.updated_at.strftime("%Y-%m-%d %H:%M:%S") if asset.updated_at else ""
            })
        
        # 如果没有数据，提供示例数据
        if not export_data:
            export_data = [
                {
                    "物业名称": "暂无数据",
                    "地址": "请先导入资产数据",
                    "确权状态": "",
                    "物业性质": "",
                    "使用状态": "",
                    "权属方": "",
                    "经营管理方": "",
                    "业态类别": "",
                    "总面积": 0.0,
                    "可使用面积": 0.0,
                    "是否涉诉": "",
                    "备注": "",
                    "创建时间": "",
                    "更新时间": ""
                }
            ]
        
        # 创建DataFrame
        df = pd.DataFrame(export_data)
        
        # 写入Excel文件
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name=STANDARD_SHEET_NAME, index=False)
        buffer.seek(0)
        
        # 返回文件流（避免重复读取buffer）
        async def file_generator():
            data = buffer.getvalue()
            yield data
            buffer.close()

        return StreamingResponse(
            file_generator(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=assets_export.xlsx"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")


@router.post("/export/async", summary="异步导出Excel文件")
async def export_excel_async(
    background_tasks: BackgroundTasks,
    request: ExcelExportRequest = Body(...),
    db: Session = Depends(get_db)
):
    """
    异步导出Excel文件，返回任务ID用于跟踪进度

    - **request**: 导出配置参数
    """
    try:
        # 创建导出任务
        task_in = TaskCreate(
            task_type=TaskType.EXCEL_EXPORT,
            title="Excel导出任务",
            description="异步导出资产数据为Excel文件",
            parameters={
                "filters": request.filters or {},
                "fields": request.fields or [],
                "export_format": request.export_format,
                "sheet_name": request.sheet_name or STANDARD_SHEET_NAME,
                "include_headers": request.include_headers,
                "date_format": request.date_format
            },
            config=request.config_id or {}
        )

        task = task_crud.create(db=db, obj_in=task_in)

        # 添加后台任务
        background_tasks.add_task(
            _process_excel_export_async,
            task_id=task.id,
            request=request,
            db_session=db
        )

        return {
            "message": "导出任务已创建",
            "task_id": task.id,
            "status": task.status,
            "estimated_time": "预计需要1-3分钟，请使用task_id查询进度"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建导出任务失败: {str(e)}")


async def _process_excel_export_async(
    task_id: str,
    request: ExcelExportRequest,
    db_session: Session
):
    """
    后台处理Excel导出任务
    """
    try:
        # 更新任务状态为运行中
        task_crud.update(
            db=db_session,
            db_obj=task_crud.get(db=db_session, id=task_id),
            obj_in=TaskUpdate(
                status=TaskStatus.RUNNING,
                started_at=datetime.utcnow()
            )
        )
        db_session.commit()

        # 构建筛选条件
        filters = request.filters or {}

        # 从数据库获取资产数据
        assets, total = asset_crud.get_multi_with_search(
            db=db_session,
            search=filters.get("search"),
            filters=filters,
            limit=5000  # 导出时获取更多数据
        )

        # 更新进度
        task_crud.update(
            db=db_session,
            db_obj=task_crud.get(db=db_session, id=task_id),
            obj_in=TaskUpdate(
                progress=30,
                total_items=total,
                processed_items=0
            )
        )
        db_session.commit()

        # 确定导出字段
        fields = request.fields or [
            "property_name", "address", "ownership_status", "property_nature",
            "usage_status", "ownership_entity", "business_category", "is_litigated",
            "notes", "created_at", "updated_at"
        ]

        # 转换为导出格式
        export_data = []
        for i, asset in enumerate(assets):
            export_data.append({
                "物业名称": getattr(asset, 'property_name', ''),
                "地址": getattr(asset, 'address', ''),
                "确权状态": getattr(asset, 'ownership_status', ''),
                "物业性质": getattr(asset, 'property_nature', ''),
                "使用状态": getattr(asset, 'usage_status', ''),
                "权属方": getattr(asset, 'ownership_entity', ''),
                "业态类别": getattr(asset, 'business_category', ''),
                "是否涉诉": "是" if getattr(asset, 'is_litigated', False) else "否",
                "备注": getattr(asset, 'notes', ''),
                "创建时间": asset.created_at.strftime(request.date_format) if asset.created_at else "",
                "更新时间": asset.updated_at.strftime(request.date_format) if asset.updated_at else ""
            })

            # 更新进度
            if i % 100 == 0:
                progress = 30 + int((i / total) * 60)
                task_crud.update(
                    db=db_session,
                    db_obj=task_crud.get(db=db_session, id=task_id),
                    obj_in=TaskUpdate(
                        progress=progress,
                        processed_items=i
                    )
                )
                db_session.commit()

        # 创建DataFrame
        df = pd.DataFrame(export_data)

        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"assets_export_{timestamp}.{request.export_format}"

        # 创建导出文件
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(
                writer,
                sheet_name=request.sheet_name or STANDARD_SHEET_NAME,
                index=request.include_headers
            )
        buffer.seek(0)

        # 保存文件到临时位置
        import os
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, filename)

        with open(file_path, 'wb') as f:
            f.write(buffer.read())

        # 更新任务完成状态
        task_crud.update(
            db=db_session,
            db_obj=task_crud.get(db=db_session, id=task_id),
            obj_in=TaskUpdate(
                status=TaskStatus.COMPLETED,
                completed_at=datetime.utcnow(),
                progress=100,
                total_items=total,
                processed_items=total,
                result_data={
                    "file_path": file_path,
                    "file_name": filename,
                    "file_size": os.path.getsize(file_path),
                    "record_count": len(export_data),
                    "columns": list(df.columns),
                    "export_time": datetime.utcnow().isoformat(),
                    "download_url": f"/api/v1/excel/download/{task_id}"
                }
            )
        )
        db_session.commit()

    except Exception as e:
        # 更新任务失败状态
        task_crud.update(
            db=db_session,
            db_obj=task_crud.get(db=db_session, id=task_id),
            obj_in=TaskUpdate(
                status=TaskStatus.FAILED,
                completed_at=datetime.utcnow(),
                error_message=str(e)
            )
        )
        db_session.commit()


@router.get("/download/{task_id}", summary="下载导出文件")
async def download_export_file(
    task_id: str,
    db: Session = Depends(get_db)
):
    """
    下载异步导出的文件
    """
    try:
        # 获取任务信息
        task = task_crud.get(db=db, id=task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        if task.status != TaskStatus.COMPLETED:
            raise HTTPException(status_code=400, detail="任务尚未完成")

        # 获取文件信息
        result_data = task.result_data or {}
        file_path = result_data.get("file_path")
        file_name = result_data.get("file_name", f"export_{task_id}.xlsx")

        if not file_path or not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="导出文件不存在")

        # 返回文件流
        def file_iter():
            with open(file_path, 'rb') as f:
                while chunk := f.read(8192):
                    yield chunk

        return StreamingResponse(
            file_iter(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={file_name}"}
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下载文件失败: {str(e)}")


@router.get("/status/{task_id}", response_model=ExcelStatusResponse, summary="获取任务状态")
async def get_excel_task_status(
    task_id: str,
    db: Session = Depends(get_db)
):
    """
    获取Excel导入导出任务状态

    - **task_id**: 任务ID
    """
    try:
        task = task_crud.get(db=db, id=task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        return ExcelStatusResponse(
            task_id=task.id,
            status=task.status,
            progress=task.progress or 0,
            total_items=task.total_items,
            processed_items=task.processed_items or 0,
            error_message=task.error_message,
            created_at=task.created_at,
            started_at=task.started_at,
            completed_at=task.completed_at
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务状态失败: {str(e)}")


@router.get("/history", summary="获取Excel操作历史")
async def get_excel_history(
    task_type: Optional[str] = Query(None, description="任务类型筛选"),
    status: Optional[str] = Query(None, description="状态筛选"),
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    skip: int = Query(0, ge=0, description="跳过数量"),
    db: Session = Depends(get_db)
):
    """
    获取Excel操作历史记录

    - **task_type**: 按任务类型筛选
    - **status**: 按状态筛选
    - **limit**: 返回数量
    - **skip**: 跳过数量
    """
    try:
        tasks = task_crud.get_multi(
            db=db,
            skip=skip,
            limit=limit,
            task_type=task_type,
            status=status,
            order_by="created_at",
            order_dir="desc"
        )

        # 转换为响应格式
        history_items = []
        for task in tasks:
            result_data = task.result_data or {}
            history_items.append({
                "task_id": task.id,
                "task_type": task.task_type,
                "title": task.title,
                "status": task.status,
                "progress": task.progress or 0,
                "created_at": task.created_at,
                "completed_at": task.completed_at,
                "result_summary": {
                    "total": result_data.get("total", 0),
                    "success": result_data.get("success", 0),
                    "failed": result_data.get("failed", 0),
                    "record_count": result_data.get("record_count", 0)
                }
            })

        return {
            "items": history_items,
            "total": len(history_items),
            "skip": skip,
            "limit": limit
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取历史记录失败: {str(e)}")


@router.post("/export", summary="导出选中资产Excel文件")
async def export_selected_assets(
    asset_ids: Optional[List[str]] = Body(None, description="资产ID列表"),
    export_format: str = Query("excel", description="导出格式"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    ownership_status: Optional[str] = Query(None, description="确权状态筛选"),
    property_nature: Optional[str] = Query(None, description="物业性质筛选"),
    usage_status: Optional[str] = Query(None, description="使用状态筛选"),
    db: Session = Depends(get_db)
):
    """
    导出选中资产数据为Excel文件

    支持按条件筛选导出和指定资产ID导出
    """
    try:
        # 构建筛选条件
        filters = {}
        if ownership_status:
            filters["ownership_status"] = ownership_status
        if property_nature:
            filters["property_nature"] = property_nature
        if usage_status:
            filters["usage_status"] = usage_status

        # 如果指定了资产ID，添加到筛选条件中
        if asset_ids:
            filters["ids"] = asset_ids

        # 从数据库获取资产数据
        assets, total = asset_crud.get_multi_with_search(
            db=db,
            search=search,
            filters=filters,
            limit=1000  # 导出时获取更多数据
        )

        # 转换为导出格式 - 使用与GET端点相同的字段映射
        export_data = []
        for asset in assets:
            export_data.append({
                "物业名称": getattr(asset, 'property_name', ''),
                "地址": getattr(asset, 'address', ''),
                "确权状态": getattr(asset, 'ownership_status', ''),
                "物业性质": getattr(asset, 'property_nature', ''),
                "使用状态": getattr(asset, 'usage_status', ''),
                "权属方": getattr(asset, 'ownership_entity', ''),
                "经营管理方": getattr(asset, 'management_entity', ''),
                "业态类别": getattr(asset, 'business_category', ''),
                "是否涉诉": "是" if getattr(asset, 'is_litigated', False) else "否",
                "备注": getattr(asset, 'notes', ''),
                "创建时间": asset.created_at.strftime("%Y-%m-%d %H:%M:%S") if asset.created_at else "",
                "更新时间": asset.updated_at.strftime("%Y-%m-%d %H:%M:%S") if asset.updated_at else ""
            })

        # 如果没有数据，提供示例数据
        if not export_data:
            export_data = [
                {
                    "物业名称": "暂无数据",
                    "地址": "请先导入资产数据",
                    "确权状态": "",
                    "物业性质": "",
                    "使用状态": "",
                    "权属方": "",
                    "经营管理方": "",
                    "业态类别": "",
                    "是否涉诉": "",
                    "备注": "",
                    "创建时间": "",
                    "更新时间": ""
                }
            ]

        # 创建DataFrame
        df = pd.DataFrame(export_data)

        # 写入Excel文件
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name=STANDARD_SHEET_NAME, index=False)
        buffer.seek(0)

        # 根据导出类型确定文件名
        filename = "selected_assets_export.xlsx" if asset_ids else "filtered_assets_export.xlsx"

        # 返回文件流（避免重复读取buffer）
        async def file_generator():
            data = buffer.getvalue()
            yield data
            buffer.close()

        return StreamingResponse(
            file_generator(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出选中资产失败: {str(e)}")