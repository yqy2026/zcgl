"""
优化的Excel导入API路由
专注于性能优化和用户体验
"""

import tempfile
import os
from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
import logging
import time

from ...database import get_db
from ...services.excel_import import ExcelImportService
from ...config.excel_config import STANDARD_SHEET_NAME

# 创建路由器
router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/import/optimized", summary="优化的Excel数据导入")
async def import_excel_optimized(
    file: UploadFile = File(...),
    skip_errors: bool = Query(False, description="是否跳过错误行"),
    sheet_name: str = Query(STANDARD_SHEET_NAME, description="Excel工作表名称"),
    db: Session = Depends(get_db)
):
    """
    优化的Excel导入API - 解决超时问题和性能瓶颈

    主要优化：
    1. 批量数据库插入，大幅提升性能
    2. 增强的错误处理和验证
    3. 更好的用户反馈
    4. 优化的内存使用
    """
    # 验证文件类型
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="文件格式不支持，请上传Excel文件(.xlsx/.xls)"
        )

    # 验证文件大小 (限制为50MB)
    max_size = 50 * 1024 * 1024  # 50MB
    if file.size > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"文件大小超过限制 (最大 {max_size // (1024*1024)}MB)"
        )

    start_time = time.time()
    temp_file_path = None

    try:
        # 创建临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            temp_file_path = tmp_file.name

        logger.info(f"开始优化导入: 文件={file.filename}, 大小={file.size}")

        # 使用优化的导入服务
        import_service = ExcelImportService()

        # 执行导入
        result = await import_service.import_assets_from_excel(
            file_path=temp_file_path,
            sheet_name=sheet_name,
            db=db
        )

        # 计算处理时间
        processing_time = time.time() - start_time
        logger.info(f"导入完成: 处理时间={processing_time:.2f}秒, 结果={result}")

        # 添加性能信息到响应
        enhanced_result = {
            **result,
            "processing_time": round(processing_time, 2),
            "file_size": file.size,
            "filename": file.filename,
            "performance_metrics": {
                "records_per_second": round(result.get("total", 0) / processing_time, 2) if processing_time > 0 else 0,
                "estimated_time_for_1000": round(1000 / (result.get("total", 0) / processing_time), 2) if result.get("total", 0) > 0 and processing_time > 0 else 0
            }
        }

        return enhanced_result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"优化导入失败: {str(e)}")
        import traceback
        logger.error(f"错误详情: {traceback.format_exc()}")

        # 返回详细的错误信息
        return {
            "success": 0,
            "failed": 0,
            "total": 0,
            "errors": [f"导入失败: {str(e)}"],
            "processing_time": round(time.time() - start_time, 2),
            "filename": file.filename,
            "error_details": str(e)
        }

    finally:
        # 清理临时文件
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
                logger.info("临时文件已清理")
            except Exception as e:
                logger.warning(f"清理临时文件失败: {e}")

@router.get("/import/health", summary="导入服务健康检查")
async def import_health_check():
    """导入服务健康检查"""
    return {
        "status": "healthy",
        "service": "excel-import",
        "timestamp": time.time(),
        "features": {
            "batch_insert": True,
            "error_handling": True,
            "validation": True,
            "performance_tracking": True
        }
    }