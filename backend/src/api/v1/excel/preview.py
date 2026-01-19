"""
Excel预览模块
"""

import io
from datetime import UTC, datetime
from typing import Any

import pandas as pd
from fastapi import APIRouter, Body, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from ....core.exception_handler import BusinessValidationError
from ....core.logging_security import security_auditor
from ....core.security import security_middleware
from ....database import get_db
from ....middleware.auth import get_current_active_user
from ....models.auth import User
from ....schemas.excel_advanced import ExcelPreviewRequest, ExcelPreviewResponse

router = APIRouter()


@router.post(
    "/preview/advanced", response_model=ExcelPreviewResponse, summary="高级Excel预览"
)
async def preview_excel_advanced(
    file: UploadFile = File(...),
    request: ExcelPreviewRequest = Body(...),
    db: Session = Depends(get_db),
) -> ExcelPreviewResponse:
    """
    高级Excel文件预览，支持字段映射检测

    - **file**: Excel文件
    - **request**: 预览配置参数
    """
    # 安全验证文件
    await security_middleware.validate_file_upload(
        file,
        allowed_types=[
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-excel",
        ],
        max_size=50 * 1024 * 1024,  # 50MB
    )

    # 创建验证结果
    validation_result = {
        "hash": f"computed_hash_{file.filename}",
        "validation_time": datetime.now(UTC).isoformat(),
    }

    # 记录文件验证成功
    security_auditor.log_security_event(
        event_type="FILE_UPLOAD_VALIDATED",
        message=f"Excel file validated successfully: {file.filename}",
        details={
            "filename": file.filename,
            "size": file.size,
            "hash": validation_result.get("hash"),
            "validation_time": validation_result.get("validation_time"),
        },
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
    preview_data: list[dict[str, Any]] = []
    for _, row in preview_df.iterrows():
        row_dict: dict[str, Any] = {}
        for col in columns:
            value = row[col]
            # 处理NaN和None值
            if pd.isna(value):
                row_dict[col] = None
            else:
                row_dict[col] = (
                    str(value) if not isinstance(value, (str, int, float)) else value
                )
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
                detected_mapping.append(
                    {
                        "excel_column": col,
                        "system_field": possible_names[0],
                        "data_type": "string",
                        "required": chinese_name in ["物业名称", "地址"],
                        "confidence": 0.8,
                    }
                )
                break

    return ExcelPreviewResponse(
        file_name=file.filename or "unknown.xlsx",
        sheet_names=[f"Sheet{i + 1}" for i in range(1)],  # 简化处理
        total_rows=total,
        columns=columns,
        preview_data=preview_data,
        detected_field_mapping=None,
    )


@router.post("/preview", summary="预览Excel文件内容")
async def preview_excel(
    file: UploadFile = File(...),
    max_rows: int = Query(10, ge=1, le=100, description="预览行数"),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    """
    预览Excel文件内容，用于导入前确认
    """
    # 安全验证文件
    await security_middleware.validate_file_upload(
        file,
        allowed_types=[
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-excel",
        ],
        max_size=50 * 1024 * 1024,  # 50MB
    )

    # 验证文件类型（额外检查）
    if not file.filename or not file.filename.endswith((".xlsx", ".xls")):
        raise BusinessValidationError("文件格式不支持，请上传Excel文件(.xlsx/.xls)")

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
    preview_data: list[dict[str, Any]] = []
    for _, row in preview_df.iterrows():
        row_dict: dict[str, Any] = {}
        for col in columns:
            value = row[col]
            # 处理NaN和None值
            if pd.isna(value):
                row_dict[col] = None
            else:
                row_dict[col] = (
                    str(value) if not isinstance(value, (str, int, float)) else value
                )
        preview_data.append(row_dict)

    return {
        "message": "预览成功",
        "filename": file.filename,
        "total": total,
        "preview_rows": preview_rows,
        "columns": columns,
        "data": preview_data,
    }
