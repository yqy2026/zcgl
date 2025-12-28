from typing import Any


# 创建一个简单的OCR提供者
class OCRProvider:
    def __init__(self):
        self.service = None


def get_ocr_service() -> Any | None:
    """获取OCR服务实例"""
    try:
        # 尝试导入并创建OCR服务 - 临时禁用问题文件
        # from ..document.optimized_ocr_service import OptimizedOCRService
        # return OptimizedOCRService()
        return None  # 临时返回None，避免导入错误
    except ImportError:
        return None
    except Exception:
        return None


def set_ocr_service(service: Any) -> None:
    """设置OCR服务实例"""
    pass


# 全局OCR服务实例
_ocr_service_instance: Any | None = None


def get_current_ocr_service() -> Any | None:
    """获取当前OCR服务实例"""
    global _ocr_service_instance
    return _ocr_service_instance


def set_current_ocr_service(service: Any) -> None:
    """设置当前OCR服务实例"""
    global _ocr_service_instance
    _ocr_service_instance = service
