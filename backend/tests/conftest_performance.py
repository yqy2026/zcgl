"""
性能优化专用测试配置
专注于解决PaddleOCR加载瓶颈问题
"""

import pytest
import os
from unittest.mock import Mock, MagicMock
from typing import Generator
import tempfile

# 设置PaddleOCR环境变量以减少模型加载时间
os.environ.setdefault('PADDLEOCR_USE_CPU', '1')
os.environ.setdefault('PADDLEOCR_USE_GPU', '0')
os.environ.setdefault('PADDLEOCR_PP_DEBUG', '0')  # 减少调试输出


@pytest.fixture(scope="session")
def fast_pdf_service():
    """快速PDF处理服务fixture"""
    from src.services.pdf_processing_service import PDFProcessingService

    service = Mock(spec=PDFProcessingService)
    service.ocr = Mock()
    service.supported_methods = ["pdfplumber", "pymupdf", "ocr"]

    return service


@pytest.fixture(scope="session")
def fast_pdf_import_service():
    """快速PDF导入服务fixture"""
    from src.services.pdf_import_service import PDFImportService

    service = Mock(spec=PDFImportService)
    service.process_pdf_file = Mock(
        return_value={
            "status": "success",
            "extracted_data": {
                "ownership_entity": "测试权属方",
                "property_name": "测试物业"
            },
            "processing_time": 0.1  # 快速处理
        }
    )

    return service


@pytest.fixture(scope="session")
def small_pdf_bytes():
    """小型PDF文件fixture"""
    import io

    # 创建一个最小的有效PDF文件用于测试
    return io.BytesIO(b'%PDF-1.4\nMinimal test PDF')


@pytest.fixture(scope="session")
def fast_db_session():
    """快速数据库会话fixture"""
    from sqlalchemy.orm import Session

    session = Mock(spec=Session)
    session.add = Mock()
    session.commit = Mock()
    session.query = Mock(return_value=Mock())
    session.refresh = Mock()

    return session


@pytest.fixture(scope="session")
def fast_session_service():
    """快速会话服务fixture"""
    service = Mock()

    # 使用同步版本避免异步复杂性
    service.create_session = Mock(return_value="fast_session_123")
    service.get_session = Mock(return_value={
        "session_id": "fast_session_123",
        "status": "created",
        "progress": 0
    })
    service.update_session = Mock(return_value=None)
    service.delete_session = Mock(return_value=None)

    return service


# 性能测试标记
pytest.mark.performance = pytest.mark.skipif(
    not os.getenv('SKIP_PERFORMANCE_TESTS', 'False'),
    reason="Performance tests disabled via SKIP_PERFORMANCE_TESTS"
)


def pytest_configure(config):
    """pytest性能配置"""
    # 禁用PaddleOCR以提高测试速度
    if os.getenv('SKIP_PERFORMANCE_TESTS', 'False'):
        # 如果有环境变量，跳过耗时的测试
        config.addinivalue_line(
            "filterwarnings = ignore::UserWarning:PaddlePaddle"
        )