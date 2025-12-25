"""
pytest配置文件
提供测试所需的fixtures和配置
"""

import os
import sys
from unittest.mock import Mock

import pytest
from sqlalchemy.orm import Session

# 添加backend根目录到Python路径（这样 'from src.xxx' 可以正常工作）
backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, backend_root)

try:
    from src.models.asset import Asset
    from src.models.pdf_import_session import PDFImportSession
    from src.services.pdf_import_service import PDFImportService
    from src.services.pdf_session_service import PDFSessionService
except ImportError:
    # 如果导入失败，使用Mock
    PDFSessionService = Mock
    PDFImportService = Mock
    PDFImportSession = Mock
    Asset = Mock


@pytest.fixture(scope="session")
def mock_db_session():
    """模拟数据库会话"""
    session = Mock(spec=Session)
    session.add = Mock()
    session.commit = Mock()
    session.rollback = Mock()
    session.refresh = Mock()
    session.delete = Mock()
    session.query = Mock(return_value=Mock())
    session.execute = Mock(return_value=Mock())
    session.flush = Mock()
    return session


@pytest.fixture(scope="session")
def session_manager():
    """PDF会话管理器模拟"""
    manager = Mock()
    manager.get_session = Mock(return_value=None)
    manager.create_session = Mock(return_value="test_session_12345")
    manager.update_session = Mock(return_value=None)
    manager.delete_session = Mock(return_value=None)
    manager.cleanup_expired_sessions = Mock(return_value=None)
    return manager


@pytest.fixture(scope="session")
def pdf_import_service():
    """PDF导入服务模拟"""
    service = Mock(spec=PDFImportService)
    service.validate_pdf_file = Mock(return_value=(True, "文件格式正确", None))
    service.check_file_size = Mock(return_value=(True, "文件大小符合要求"))
    service.security_scan = Mock(return_value=(True, "安全扫描通过", []))
    service.extract_text_from_pdf = Mock(return_value=("提取的文本内容", ["mock_warnings"]))
    return service


@pytest.fixture(scope="session")
def pdf_session_service():
    """PDF会话服务模拟"""
    service = Mock(spec=PDFSessionService)
    service.create_session = Mock(return_value="mock_session_id_12345")
    service.get_session = Mock(return_value={
        "session_id": "mock_session_id_12345",
        "status": "created",
        "progress": 0,
        "created_at": "2025-10-24T01:30:00Z"
    })
    service.update_session = Mock(return_value=None)
    service.delete_session = Mock(return_value=None)
    return service


@pytest.fixture(scope="session")
def sample_asset_data():
    """示例资产数据"""
    return {
        "ownership_entity": "测试权属人",
        "management_entity": "测试管理人",
        "property_name": "测试物业API",
        "address": "测试地址123号",
        "actual_property_area": 1000.0,
        "rentable_area": 800.0,
        "rented_area": 600.0,
        "unrented_area": 200.0,
        "non_commercial_area": 200.0,
        "ownership_status": "已确权",
        "actual_usage": "商业",
        "usage_status": "出租",
        "is_litigated": "否",
        "property_nature": "经营类",
        "occupancy_rate": 75.0,
        "land_area": 1200.0,
        "project_name": "测试项目",
        "contract_start_date": "2023-01-01",
        "contract_end_date": "2025-12-31"
    }


@pytest.fixture(scope="session")
def sample_pdf_session_data():
    """示例PDF会话数据"""
    return {
        "session_id": "test_session_12345",
        "filename": "test.pdf",
        "file_size": 1024,
        "file_path": "/tmp/test.pdf",
        "status": "created",
        "progress": 0,
        "created_at": "2025-10-24T01:30:00Z"
    }
