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

from database import get_db
from models.asset import Asset
from schemas.asset import AssetCreate, AssetResponse
from crud.asset import asset_crud

# 创建Excel路由器
router = APIRouter()


@router.get("/template", summary="下载Excel导入模板")
async def download_template():
    """
    下载Excel导入模板文件
    """
    try:
        # 创建示例数据
        template_data = {
            "物业名称": ["示例物业1", "示例物业2"],
            "地址": ["示例地址1", "示例地址2"],
            "确权状态": ["已确权", "未确权"],
            "物业性质": ["经营性", "非经营性"],
            "使用状态": ["出租", "自用"],
            "权属方": ["示例权属方1", "示例权属方2"],
            "经营管理方": ["示例管理方1", "示例管理方2"],
            "业态类别": ["商业", "办公"],
            "总面积": [1000.0, 2000.0],
            "可使用面积": [800.0, 1800.0],
            "是否涉诉": ["否", "否"],
            "备注": ["示例备注1", "示例备注2"]
        }
        
        # 创建DataFrame
        df = pd.DataFrame(template_data)
        
        # 写入Excel文件
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name="资产导入模板", index=False)
        buffer.seek(0)
        
        # 返回文件流
        return StreamingResponse(
            io.BytesIO(buffer.read()),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=asset_import_template.xlsx"}
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
        total_rows = len(df)
        columns = df.columns.tolist()
        
        # 限制预览行数
        preview_rows = min(max_rows, total_rows)
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
            "total_rows": total_rows,
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
    db: Session = Depends(get_db)
):
    """
    从Excel文件导入资产数据
    
    - **file**: Excel文件
    - **skip_errors**: 是否跳过错误行继续导入
    """
    # 验证文件类型
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="文件格式不支持，请上传Excel文件(.xlsx/.xls)"
        )
    
    try:
        # 读取文件内容
        content = await file.read()
        
        # 直接从内存读取Excel
        df = pd.read_excel(io.BytesIO(content))
        
        # 字段映射
        field_mapping = {
            "物业名称": "property_name",
            "地址": "address",
            "确权状态": "ownership_status",
            "物业性质": "property_nature",
            "使用状态": "usage_status",
            "权属方": "ownership_entity",
            "经营管理方": "management_entity",
            "业态类别": "business_category",
            "总面积": "total_area",
            "可使用面积": "usable_area",
            "是否涉诉": "is_litigated",
            "备注": "notes"
        }
        
        # 重命名列
        df = df.rename(columns=field_mapping)
        
        # 转换为字典列表
        records = df.to_dict('records')
        
        success_count = 0
        error_count = 0
        errors = []
        
        for i, record in enumerate(records, 1):
            try:
                # 清理数据
                cleaned_record = {}
                for key, value in record.items():
                    if pd.notna(value) and str(value).strip():
                        cleaned_record[key] = value
                
                # 验证必填字段
                required_fields = ["property_name", "address", "ownership_status", "property_nature", "usage_status"]
                missing_fields = [field for field in required_fields if field not in cleaned_record or not cleaned_record[field]]
                
                if missing_fields:
                    raise ValueError(f"缺少必填字段: {', '.join(missing_fields)}")
                
                # 创建资产数据对象
                asset_create = AssetCreate(**cleaned_record)
                
                # 实际创建资产记录
                created_asset = asset_crud.create(db=db, obj_in=asset_create)
                
                if created_asset:
                    success_count += 1
                else:
                    raise ValueError("创建资产记录失败")
                
            except Exception as e:
                if skip_errors:
                    errors.append(f"第{i}行: {str(e)}")
                    error_count += 1
                else:
                    raise HTTPException(
                        status_code=400,
                        detail=f"第{i}行导入失败: {str(e)}"
                    )
        
        return {
            "message": "导入完成",
            "total_rows": len(records),
            "success_count": success_count,
            "error_count": error_count,
            "errors": errors
        }
            
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
                "总面积": asset.total_area or 0.0,
                "可使用面积": asset.usable_area or 0.0,
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
            df.to_excel(writer, sheet_name="资产数据", index=False)
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