"""
Excel导入导出API路由
"""

import io
import tempfile
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import pandas as pd

from ...database import get_db
from ...models.asset import Asset
from ...schemas.asset import AssetCreate, AssetResponse
from ...crud.asset import asset_crud
from ...config.excel_config import STANDARD_SHEET_NAME

# 创建Excel路由器
router = APIRouter()


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
        
        # 返回文件流
        return StreamingResponse(
            io.BytesIO(buffer.read()),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=land_property_asset_template.xlsx"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成模板失败: {str(e)}")


@router.get("/test", summary="测试端点")
async def test_endpoint():
    """测试端点"""
    return {"message": "Excel API 测试成功", "timestamp": "2025-08-27"}

@router.post("/preview", summary="预览Excel文件内容")
async def preview_excel(
    file: UploadFile = File(...),
    max_rows: int = Query(10, ge=1, le=100, description="预览行数")
):
    """
    预览Excel文件内容，用于导入前确认
    """
    # 验证文件类型
    if not file.filename or not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="文件格式不支持，请上传Excel文件(.xlsx/.xls)"
        )
    
    try:
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
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"预览Excel文件失败: {str(e)}"
        )


@router.post("/import", summary="导入Excel数据")
async def import_excel(
    file: UploadFile = File(...),
    skip_errors: bool = Query(False, description="是否跳过错误行"),
    sheet_name: str = Query(STANDARD_SHEET_NAME, description="Excel工作表名称"),
    db: Session = Depends(get_db)
):
    """
    从Excel文件导入资产数据

    - **file**: Excel文件
    - **skip_errors**: 是否跳过错误行继续导入
    - **sheet_name**: Excel工作表名称，默认为"{STANDARD_SHEET_NAME}"
    """
    # 验证文件类型
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="文件格式不支持，请上传Excel文件(.xlsx/.xls)"
        )

    try:
        # 保存上传的文件到临时位置
        import tempfile
        import os
        from pathlib import Path

        # 创建临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
            # 写入上传的文件内容
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name

        try:
            # 使用修复过的ExcelImportService进行导入
            from src.services.excel_import import ExcelImportService
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

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")


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
                "物业名称": asset.property_name,
                "地址": asset.address,
                "确权状态": asset.ownership_status,
                "物业性质": asset.property_nature,
                "使用状态": asset.usage_status,
                "权属方": asset.ownership_entity,
                "经营管理方": asset.management_entity or "",
                "业态类别": asset.business_category or "",
                "是否涉诉": asset.is_litigated or "否",
                "备注": asset.notes or "",
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
        
        # 返回文件流
        return StreamingResponse(
            io.BytesIO(buffer.read()),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=assets_export.xlsx"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")