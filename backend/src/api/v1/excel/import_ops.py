"""
Excel导入操作模块 - 同步与异步导入
"""

import logging
import os
import tempfile
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Body, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from ....config.excel_config import STANDARD_SHEET_NAME
from ....constants.message_constants import ErrorIDs
from ....core.exception_handler import BusinessValidationError
from ....crud.task import task_crud
from ....database import get_db
from ....enums.task import TaskStatus, TaskType
from ....middleware.auth import get_current_active_user
from ....models.auth import User
from ....schemas.excel_advanced import ExcelImportRequest
from ....schemas.task import TaskCreate, TaskUpdate
from ....security.logging_security import security_auditor
from ....security.security import security_middleware
from ....services.excel import ExcelImportService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/import", summary="导入Excel数据（同步）")
async def import_excel(
    file: UploadFile = File(...),
    should_skip_errors: bool = Query(False, description="是否跳过错误行"),
    sheet_name: str = Query(STANDARD_SHEET_NAME, description="Excel工作表名称"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    """
    从Excel文件导入资产数据（同步版本）

    - **file**: Excel文件
    - **should_skip_errors**: 是否跳过错误行继续导入
    - **sheet_name**: Excel工作表名称
    """
    # 安全验证文件
    await security_middleware.validate_file_upload(
        file,
        allowed_types=[
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-excel",
        ],
        max_size=100 * 1024 * 1024,  # 100MB for import
    )

    # 验证文件类型（额外检查）
    if not file.filename or not file.filename.endswith((".xlsx", ".xls")):
        raise BusinessValidationError("文件格式不支持，请上传Excel文件(.xlsx/.xls)")

    # 记录导入操作开始
    security_auditor.log_security_event(
        event_type="EXCEL_IMPORT_STARTED",
        message=f"Excel import started: {file.filename} (sheet: {sheet_name})",
        details={
            "filename": file.filename,
            "size": file.size,
            "sheet_name": sheet_name,
            "skip_errors": should_skip_errors,
        },
    )

    # 保存上传的文件到临时位置
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_file:
        # 写入上传的文件内容
        content = await file.read()
        tmp_file.write(content)
        tmp_file_path = tmp_file.name

    try:
        # 使用ExcelImportService进行导入
        import_service = ExcelImportService(db)

        # 执行导入
        result = await import_service.import_assets_from_excel(
            file_path=tmp_file_path,
            sheet_name=sheet_name,
            should_skip_errors=should_skip_errors,
        )

        # 转换结果格式以匹配前端期望
        return {
            "message": "导入完成",
            "total": result.get("total", 0),
            "success": result.get("success", 0),
            "failed": result.get("failed", 0),
            "errors": result.get("errors", []),
        }

    finally:
        # 清理临时文件
        if os.path.exists(tmp_file_path):
            os.unlink(tmp_file_path)


@router.post("/import/async", summary="异步导入Excel数据")
async def import_excel_async(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    request: ExcelImportRequest = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    """
    异步导入Excel文件，返回任务ID用于跟踪进度

    - **file**: Excel文件
    - **request**: 导入配置参数
    """
    # 安全验证文件
    validation_result = await security_middleware.validate_file_upload(
        file,
        allowed_types=[
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-excel",
        ],
        max_size=100 * 1024 * 1024,  # 100MB for import
    )

    # 验证文件类型（额外检查）
    if not file.filename or not file.filename.endswith((".xlsx", ".xls")):
        raise BusinessValidationError("文件格式不支持，请上传Excel文件(.xlsx/.xls)")

    # 记录异步导入操作开始
    security_auditor.log_security_event(
        event_type="EXCEL_ASYNC_IMPORT_STARTED",
        message=f"Async Excel import started: {file.filename}",
        details={
            "filename": file.filename,
            "size": file.size,
            "request_config": request.model_dump(),
            "validation_hash": validation_result.get("hash"),
        },
    )

    # 创建导入任务
    task_in = TaskCreate(
        task_type=TaskType.EXCEL_IMPORT,
        title=f"Excel导入任务 - {file.filename}",
        description=f"异步导入Excel文件: {file.filename}",
        parameters={
            "filename": file.filename,
            "sheet_name": STANDARD_SHEET_NAME,
            "validate_data": request.validate_data,
            "create_assets": request.create_assets,
            "update_existing": request.update_existing,
            "skip_errors": request.skip_errors,
            "batch_size": request.batch_size,
        },
        config={"config_id": request.config_id} if request.config_id else None,
    )

    task = task_crud.create(db=db, obj_in=task_in)

    # 保存上传文件到临时位置
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_file_path = tmp_file.name

    # 添加后台任务
    background_tasks.add_task(
        _process_excel_import_async,
        task_id=str(task.id),
        file_path=tmp_file_path,
        request=request,
        db_session=db,
    )

    return {
        "message": "导入任务已创建",
        "task_id": task.id,
        "status": task.status,
        "estimated_time": "预计需要2-5分钟，请使用task_id查询进度",
    }


async def _process_excel_import_async(
    task_id: str, file_path: str, request: ExcelImportRequest, db_session: Session
) -> None:
    """
    后台处理Excel导入任务
    """
    # 更新任务状态为运行中
    try:
        db_obj = task_crud.get(db=db_session, id=task_id)
        if db_obj is not None:
            task_crud.update(
                db=db_session,
                db_obj=db_obj,
                obj_in=TaskUpdate(
                    status=TaskStatus.RUNNING,
                    progress=0,
                    processed_items=0,
                    failed_items=0,
                    error_message=None,
                    result_data=None,
                ),
            )
        db_session.commit()

        # 使用ExcelImportService进行导入
        import_service = ExcelImportService(db_session)

        # 执行导入
        result = await import_service.import_assets_from_excel(
            file_path=file_path,
            sheet_name=STANDARD_SHEET_NAME,
            should_validate_data=request.should_validate_data,
            should_create_assets=request.should_create_assets,
            should_update_existing=request.should_update_existing,
            should_skip_errors=request.should_skip_errors,
            batch_size=request.batch_size,
        )

        # 更新任务完成状态
        db_obj = task_crud.get(db=db_session, id=task_id)
        if db_obj is not None:
            task_crud.update(
                db=db_session,
                db_obj=db_obj,
                obj_in=TaskUpdate(
                    status=TaskStatus.COMPLETED,
                    progress=100,
                    processed_items=0,
                    failed_items=0,
                    error_message=None,
                    result_data={
                        "total": result.get("total", 0),
                        "success": result.get("success", 0),
                        "failed": result.get("failed", 0),
                        "created_assets": result.get("created_assets", 0),
                        "updated_assets": result.get("updated_assets", 0),
                        "errors": result.get("errors", []),
                        "warnings": result.get("warnings", []),
                    },
                ),
            )
        db_session.commit()

    except Exception as e:
        # 记录关键错误到监控系统
        logger.critical(
            f"异步Excel导入任务失败: task_id={task_id}",
            exc_info=True,
            extra={
                "error_id": ErrorIDs.Task.IMPORT_FAILED,
                "task_id": task_id,
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
        )

        # 更新任务失败状态
        try:
            db_obj = task_crud.get(db=db_session, id=task_id)
            if db_obj is not None:
                task_crud.update(
                    db=db_session,
                    db_obj=db_obj,
                    obj_in=TaskUpdate(
                        status=TaskStatus.FAILED,
                        error_message=str(e),
                        progress=0,
                        processed_items=0,
                        failed_items=0,
                        result_data=None,
                    ),
                )
            db_session.commit()
        except Exception as commit_error:
            logger.error(
                f"无法更新任务失败状态: task_id={task_id}",
                exc_info=True,
                extra={
                    "error_id": ErrorIDs.Task.STATUS_UPDATE_FAILED,
                    "task_id": task_id,
                    "original_error": str(e),
                    "commit_error": str(commit_error),
                },
            )
            # 不抛出异常 - 让原始异常传播

    finally:
        # 清理临时文件
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
        except Exception as cleanup_error:
            logger.warning(
                f"清理临时文件失败: {file_path}",
                extra={
                    "error_id": ErrorIDs.Filesystem.PERMISSION_DENIED,
                    "file_path": file_path,
                    "cleanup_error": str(cleanup_error),
                },
            )
            # 不抛出异常 - 清理失败不应隐藏原始错误
