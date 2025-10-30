"""
中文OCR服务API
提供中文OCR识别能力查询和使用接口
"""

import logging
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ...services.chinese_ocr_service import CHINESE_OCR_CONFIG, chinese_ocr_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/info", summary="获取中文OCR服务信息")
async def get_chinese_ocr_info() -> dict[str, Any]:
    """
    获取中文OCR服务的状态和配置信息

    Returns:
        中文OCR服务信息
    """
    try:
        info = chinese_ocr_service.get_chinese_ocr_info()

        return {"success": True, "data": info, "config": CHINESE_OCR_CONFIG}

    except Exception as e:
        logger.error(f"获取中文OCR服务信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取服务信息失败: {str(e)}")


@router.post("/extract_text", summary="从图像提取中文文本")
async def extract_chinese_text(
    file: UploadFile = File(...), high_accuracy: bool = Form(True)
) -> dict[str, Any]:
    """
    从上传的图像文件中提取中文文本

    Args:
        file: 图像文件
        high_accuracy: 是否使用高精度模式

    Returns:
        OCR识别结果
    """
    try:
        # 检查文件类型
        if not CHINESE_OCR_CONFIG["available"]:
            raise HTTPException(
                status_code=503, detail="中文OCR服务不可用，请检查依赖安装"
            )

        # 检查文件格式
        allowed_extensions = CHINESE_OCR_CONFIG["supported_formats"]
        file_extension = file.filename.split(".")[-1].lower() if file.filename else ""

        # 确保格式统一比较（添加点号）
        if not file_extension.startswith("."):
            file_extension_with_dot = f".{file_extension}"
        else:
            file_extension_with_dot = file_extension

        if file_extension_with_dot not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件格式: {file_extension}，支持的格式: {', '.join(allowed_extensions)}",
            )

        # 保存临时文件
        import os
        import tempfile

        with tempfile.NamedTemporaryFile(
            delete=False, suffix=file_extension_with_dot
        ) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        try:
            # 执行中文OCR识别
            if file_extension_with_dot == ".pdf":
                # PDF文件处理
                result = chinese_ocr_service.extract_chinese_text_from_pdf(
                    temp_file_path
                )
            else:
                # 图像文件处理
                import numpy as np
                from PIL import Image

                # 读取图像
                image = Image.open(temp_file_path)
                image_array = np.array(image)

                # 图像预处理
                processed_image = chinese_ocr_service._preprocess_for_chinese_ocr(
                    image_array
                )

                # 文本提取
                result = chinese_ocr_service._extract_chinese_text_from_image(
                    processed_image
                )
                result["ocr_method"] = "chinese_optimized_paddleocr"
                result["high_accuracy_mode"] = high_accuracy

            return {
                "success": True,
                "data": result,
                "filename": file.filename,
                "file_size": len(content),
                "high_accuracy_mode": high_accuracy,
            }

        finally:
            # 清理临时文件
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"中文OCR处理失败: {e}")
        raise HTTPException(status_code=500, detail=f"OCR处理失败: {str(e)}")


@router.get("/features", summary="获取中文OCR功能特性")
async def get_chinese_ocr_features() -> dict[str, Any]:
    """
    获取中文OCR服务的功能特性

    Returns:
        功能特性列表
    """
    try:
        features = {
            "chinese_optimized": {
                "name": "中文优化",
                "description": "专门针对中文文档优化的OCR识别",
                "enabled": True,
            },
            "image_preprocessing": {
                "name": "图像预处理",
                "description": "包含对比度增强、降噪、锐化等预处理",
                "enabled": chinese_ocr_service.preprocessing_config.get(
                    "image_enhancement", False
                ),
            },
            "adaptive_threshold": {
                "name": "自适应阈值",
                "description": "使用自适应阈值处理提升扫描件质量",
                "enabled": chinese_ocr_service.preprocessing_config.get(
                    "adaptive_threshold", False
                ),
            },
            "noise_reduction": {
                "name": "降噪处理",
                "description": "应用形态学操作减少图像噪声",
                "enabled": chinese_ocr_service.preprocessing_config.get(
                    "noise_reduction", False
                ),
            },
            "chinese_error_correction": {
                "name": "中文错误修正",
                "description": "修复常见的中文OCR识别错误",
                "enabled": True,
            },
            "high_accuracy_mode": {
                "name": "高精度模式",
                "description": "使用高精度配置提高识别准确率",
                "enabled": True,
            },
            "no_markdown_conversion": {
                "name": "无Markdown转换",
                "description": "专注于纯文本提取，不转换为Markdown格式",
                "enabled": True,
            },
            "pdf_direct_processing": {
                "name": "PDF直接处理",
                "description": "直接从PDF页面进行OCR，无需中间转换",
                "enabled": True,
            },
        }

        return {
            "success": True,
            "data": {
                "features": features,
                "total_features": len(features),
                "enabled_features": len([f for f in features.values() if f["enabled"]]),
                "service_available": CHINESE_OCR_CONFIG["available"],
            },
        }

    except Exception as e:
        logger.error(f"获取中文OCR功能特性失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取功能特性失败: {str(e)}")


@router.get("/health", summary="中文OCR服务健康检查")
async def chinese_ocr_health() -> dict[str, Any]:
    """
    检查中文OCR服务的健康状态

    Returns:
        健康状态信息
    """
    try:
        # 检查服务可用性
        service_available = CHINESE_OCR_CONFIG["available"]
        engine_initialized = chinese_ocr_service.ocr_engine is not None

        # 检查依赖
        dependencies = {
            "paddleocr": service_available,
            "cv2": True,  # OpenCV
            "pil": True,  # Pillow
            "numpy": True,  # NumPy
            "pymupdf": True,  # PyMuPDF
        }

        # 尝试导入检查依赖
        try:
            import cv2  # noqa: F401
        except ImportError:
            dependencies["cv2"] = False

        try:
            from PIL import Image  # noqa: F401
        except ImportError:
            dependencies["pil"] = False

        try:
            import numpy as np  # noqa: F401
        except ImportError:
            dependencies["numpy"] = False

        try:
            import fitz  # noqa: F401
        except ImportError:
            dependencies["pymupdf"] = False

        # 计算健康评分
        total_deps = len(dependencies)
        healthy_deps = sum(dependencies.values())
        health_score = healthy_deps / total_deps if total_deps > 0 else 0.0

        # 判断整体健康状态
        if service_available and engine_initialized and health_score >= 0.8:
            status = "healthy"
        elif service_available and health_score >= 0.6:
            status = "degraded"
        else:
            status = "unhealthy"

        return {
            "success": True,
            "data": {
                "status": status,
                "health_score": round(health_score, 2),
                "service_available": service_available,
                "engine_initialized": engine_initialized,
                "dependencies": dependencies,
                "preprocessing_config": chinese_ocr_service.preprocessing_config,
                "paddle_config": chinese_ocr_service.paddle_config,
            },
        }

    except Exception as e:
        logger.error(f"中文OCR健康检查失败: {e}")
        return {
            "success": False,
            "data": {"status": "error", "health_score": 0.0, "error": str(e)},
        }
