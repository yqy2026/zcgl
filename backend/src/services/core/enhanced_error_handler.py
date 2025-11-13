from typing import Any

"""
增强的错误处理服务
为PDF导入提供更好的错误处理、重试机制和用户友好的错误信息
"""

import logging

logger = logging.getLogger(__name__)


class EnhancedPDFImportError:
    """PDF导入增强错误处理"""

    def __init__(self):
        self.max_retries = 3
        self.max_file_size_mb = 50  # 最大文件大小限制
        self.retry_delays = [1, 5, 10]  # 重试延迟（秒）
        self.timeout_seconds = {
            "upload": 300,  # 文件上传超时
            "processing": 600,  # PDF处理超时
            "ocr_initialization": 120,  # OCR初始化超时
            "database_operation": 30,  # 数据库操作超时
            "api_call": 60,  # API调用超时
        }
        self.error_types = {
            "file_too_large": "文件大小超过限制",
            "file_format_unsupported": "不支持的文件格式",
            "corrupted_file": "PDF文件已损坏",
            "ocr_engine_failure": "OCR引擎初始化失败",
            "processing_timeout": "PDF处理超时",
            "database_error": "数据库操作失败",
            "network_error": "网络连接错误",
            "validation_error": "数据验证失败",
            "unknown_error": "未知错误",
        }

    def handle_error(
        self,
        error: Exception,
        context: dict[str, Any],
        error_type: str = "unknown_error",
        retry_count: int = 0,
    ) -> dict[str, Any]:
        """处理错误并提供用户友好的错误信息

        Args:
            error: 捕获的异常
            context: 请求上下文信息
            error_type: 错误类型标识

        Returns:
            用户友好的错误响应
        """
        retry_count += 1

        # 记录错误
        logger.error(
            f"PDF导入错误 - {error_type}: {str(error)}, "
            f"重试次数: {retry_count}, "
            f"上下文: {context}, "
            f"原始错误: {str(error)}"
        )

        # 根据错误类型提供不同的响应
        if error_type == "file_too_large":
            status_code = 413
            detail = f"文件过大，请上传小于 {self.max_file_size_mb}MB的文件"
            return {
                "success": False,
                "error": "文件大小超过限制",
                "retry_count": retry_count,
                "max_retries": self.max_retries,
                "error_type": error_type,
                "suggested_action": "压缩PDF文件或分批上传",
            }

        elif error_type == "file_format_unsupported":
            status_code = 415
            detail = "只支持PDF文件格式"
            return {
                "success": False,
                "error": "不支持的文件格式",
                "retry_count": retry_count,
                "max_retries": self.max_retries,
                "error_type": error_type,
                "suggested_action": "转换文件格式为PDF",
            }

        elif error_type == "corrupted_file":
            status_code = 422
            detail = "PDF文件可能已损坏，请检查后重新上传"
            return {
                "success": False,
                "error": "PDF文件可能已损坏",
                "retry_count": retry_count,
                "max_retries": self.max_retries,
                "error_type": error_type,
                "suggested_action": "重新扫描文件或修复文件",
            }

        elif error_type == "processing_timeout":
            status_code = 408
            detail = f"处理超时，请稍后重试。已处理{retry_count}/{self.max_retries}次"
            return {
                "success": False,
                "error": "处理超时",
                "retry_count": retry_count,
                "max_retries": self.max_retries,
                "error_type": error_type,
                "estimated_retry_time": f"{min(retry_count * 10)}秒",
                "suggested_action": "稍后重试或联系技术支持",
            }

        elif error_type == "ocr_engine_failure":
            status_code = 500
            detail = "OCR引擎初始化失败，将使用备用处理方式"
            return {
                "success": False,
                "error": "OCR引擎初始化失败",
                "retry_count": retry_count,
                "max_retries": self.max_retries,
                "error_type": error_type,
                "suggested_action": "继续处理，将使用其他OCR引擎",
            }

        elif error_type == "database_error":
            status_code = 500
            detail = "数据库操作失败，请稍后重试"
            return {
                "success": False,
                "error": "数据库操作失败",
                "retry_count": retry_count,
                "max_retries": self.max_retries,
                "error_type": error_type,
                "suggested_action": "检查数据库连接或联系技术支持",
            }

        elif error_type == "network_error":
            status_code = 503
            detail = "网络连接错误，请检查网络连接"
            return {
                "success": False,
                "error": "网络连接错误",
                "retry_count": retry_count,
                "max_retries": self.max_retries,
                "error_type": error_type,
                "suggested_action": "检查网络设置或重试",
            }

        else:
            status_code = 500
            detail = f"未知错误: {str(error)}"
            return {
                "success": False,
                "error": detail,
                "status_code": status_code,
                "retry_count": retry_count,
                "max_retries": self.max_retries,
                "error_type": error_type,
                "suggested_action": "请检查系统状态或联系技术支持",
            }

    def get_timeout_seconds(self, error_type: str) -> int:
        """根据错误类型获取超时秒数"""
        return self.timeout_seconds.get(error_type, 300)

    def should_retry(self, retry_count: int) -> bool:
        """判断是否应该重试"""
        return retry_count < self.max_retries


# 创建全局错误处理器实例
enhanced_error_handler = EnhancedPDFImportError()


async def monitor_processing_health() -> dict[str, Any]:
    """监控PDF处理系统的健康状态"""
    try:
        # 检查OCR服务状态
        from ...services.providers.ocr_provider import get_ocr_service

        ocr_service = get_ocr_service()
        ocr_status = {
            "available": ocr_service is not None,
            "service_type": type(ocr_service).__name__ if ocr_service else "None"
        }

        # 检查文件系统状态
        import os
        upload_dir = "uploads"
        upload_status = {
            "exists": os.path.exists(upload_dir),
            "writable": os.access(upload_dir, os.W_OK) if os.path.exists(upload_dir) else False
        }

        return {
            "ocr_service": ocr_status,
            "file_system": upload_status,
            "error_handler": {
                "status": "active",
                "max_retries": enhanced_error_handler.max_retries,
                "max_file_size_mb": enhanced_error_handler.max_file_size_mb
            }
        }
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }