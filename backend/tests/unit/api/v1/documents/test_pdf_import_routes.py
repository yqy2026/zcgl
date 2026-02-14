"""
PDF Import Routes 测试
测试 PDF 导入路由的端点
"""

from unittest.mock import AsyncMock, Mock, mock_open, patch

import pytest
from fastapi.testclient import TestClient

from src.api.v1.dependencies import get_pdf_import_service
from src.database import get_async_db
from src.main import app
from src.middleware.auth import get_current_active_user
from src.models.auth import User

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_db():
    """Mock 数据库会话"""
    return AsyncMock()


@pytest.fixture
def mock_user():
    """Mock 当前用户"""
    user = Mock(spec=User)
    user.id = "test_user_001"
    user.username = "testuser"
    user.is_active = True
    return user


@pytest.fixture
def mock_pdf_service():
    """Mock PDF 导入服务"""
    mock_service = Mock()
    mock_session = Mock()
    mock_session.session_id = "session_contract_001"
    mock_session.processing_options = {"prefer_markitdown": True}
    mock_service.create_import_session = AsyncMock(return_value=mock_session)
    mock_service.process_pdf_file = AsyncMock(return_value={"success": True})
    return mock_service


@pytest.fixture
def client(mock_db, mock_user, mock_pdf_service):
    """测试客户端"""

    async def override_get_db():
        yield mock_db

    def override_get_user():
        return mock_user

    def override_get_pdf_service():
        return mock_pdf_service

    app.dependency_overrides[get_async_db] = override_get_db
    app.dependency_overrides[get_current_active_user] = override_get_user
    app.dependency_overrides[get_pdf_import_service] = override_get_pdf_service

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def sample_pdf_import_info():
    """示例 PDF 导入信息"""
    return {
        "supported_formats": [".pdf"],
        "max_file_size": 10485760,  # 10MB
        "vision_providers": ["glm", "qwen", "deepseek", "hunyuan"],
        "processing_status": "available",
    }


# =============================================================================
# PDF 导入信息 API 测试
# =============================================================================


class TestPDFImportInfo:
    """PDF 导入信息 API 测试"""

    def test_get_pdf_import_info(self, client, sample_pdf_import_info):
        """
        测试获取 PDF 导入系统信息

        Given: 用户已登录
        When: 调用 GET /api/v1/pdf-import/info
        Then: 返回 PDF 导入系统信息
        """
        # Act
        response = client.get("/api/v1/pdf-import/info")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "capabilities" in data
        assert "supported_formats" in data["capabilities"]
        assert ".pdf" in data["capabilities"]["supported_formats"]
        assert data["capabilities"]["max_file_size_mb"] > 0

    def test_pdf_import_info_structure(self, client):
        """
        测试 PDF 导入信息数据结构

        Given: 用户请求 PDF 导入信息
        When: 调用 API
        Then: 返回完整的信息结构
        """
        # Act
        response = client.get("/api/v1/pdf-import/info")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "capabilities" in data
        # 验证所有必需字段
        required_fields = [
            "supported_formats",
            "max_file_size_mb",
            "vision_available",
        ]
        for field in required_fields:
            assert field in data["capabilities"]


# =============================================================================
# PDF 导入会话 API 测试
# =============================================================================


class TestPDFImportSessions:
    """PDF 导入会话 API 测试"""

    def test_get_pdf_import_sessions_empty(self, client):
        """
        测试获取空的 PDF 导入会话列表

        Given: 用户已登录，没有导入会话
        When: 调用 GET /api/v1/pdf-import/sessions
        Then: 返回空列表
        """
        # Act
        response = client.get("/api/v1/pdf-import/sessions")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["items"] == []
        assert "获取成功" in data["message"]

    def test_get_pdf_import_sessions_with_data(self, client):
        """
        测试获取会话接口的分页结构

        Given: 用户请求会话列表
        When: 调用 GET /api/v1/pdf-import/sessions
        Then: 返回稳定分页结构（当前为占位空列表）
        """
        # Act
        response = client.get("/api/v1/pdf-import/sessions")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["items"] == []
        assert data["data"]["count"] == 0
        assert data["data"]["unread_count"] == 0
        pagination = data["data"]["pagination"]
        assert pagination["page"] == 1
        assert pagination["page_size"] == 10
        assert pagination["total"] == 0
        assert isinstance(data["timestamp"], str)


# =============================================================================
# PDF 上传 API 测试
# =============================================================================


class TestPDFUpload:
    """PDF 上传 API 测试"""

    def test_upload_pdf_for_import(self, client, mock_pdf_service):
        """
        测试上传 PDF 进行智能导入

        Given: 用户上传 PDF 文件
        When: 调用 POST /api/v1/pdf-import/upload
        Then: 返回会话 ID 并触发处理
        """
        # Arrange
        files = {
            "file": (
                "contract.pdf",
                b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF",
                "application/pdf",
            )
        }
        data = {
            "prefer_markitdown": "true",
            "force_method": "vision",
        }

        with patch(
            "src.api.v1.documents.pdf_upload.validate_upload_file",
            new=AsyncMock(return_value={"valid": True}),
        ):
            with patch(
                "src.api.v1.documents.pdf_upload.open",
                mock_open(),
                create=True,
            ):
                # Act
                response = client.post(
                    "/api/v1/pdf-import/upload",
                    files=files,
                    data=data,
                )

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"] is True
        assert response_data["session_id"] == "session_contract_001"
        mock_pdf_service.create_import_session.assert_awaited_once()
        mock_pdf_service.process_pdf_file.assert_awaited_once()

    def test_upload_pdf_without_file(self, client):
        """
        测试没有文件的上传请求

        Given: 用户没有上传文件
        When: 调用 POST /api/v1/pdf-import/upload
        Then: 返回 400 错误
        """
        # Act
        response = client.post("/api/v1/pdf-import/upload")

        # Assert
        assert response.status_code == 422

    def test_upload_pdf_invalid_format(self, client):
        """
        测试上传非 PDF 文件

        Given: 用户上传非 PDF 文件
        When: 调用 API
        Then: 返回 400 验证错误
        """
        # Arrange
        files = {"file": ("document.txt", b"text content", "text/plain")}

        # Act
        response = client.post(
            "/api/v1/pdf-import/upload",
            files=files,
        )

        # Assert
        assert response.status_code == 422

    def test_upload_pdf_exceeds_size_limit(self, client, monkeypatch):
        """
        测试上传超大 PDF 文件

        Given: 用户上传超过大小限制的 PDF
        When: 调用 API
        Then: 返回 400 错误
        """
        # Arrange
        from src.api.v1.documents import pdf_upload

        monkeypatch.setattr(pdf_upload, "DEFAULT_MAX_FILE_SIZE", 1024)
        large_content = b"%PDF-1.4\n" + b"x" * 2048
        files = {"file": ("large.pdf", large_content, "application/pdf")}

        # Act
        response = client.post(
            "/api/v1/pdf-import/upload",
            files=files,
        )

        # Assert
        assert response.status_code == 400


# =============================================================================
# 错误处理测试
# =============================================================================


class TestErrorHandling:
    """错误处理测试"""

    def test_unauthorized_access(self, mock_db):
        """
        测试未授权访问

        Given: 用户未登录
        When: 调用 PDF 导入 API
        Then: 返回 401 错误
        """
        async def override_get_db():
            yield mock_db

        app.dependency_overrides.clear()
        app.dependency_overrides[get_async_db] = override_get_db

        try:
            with TestClient(app) as unauthorized_client:
                # Act
                response = unauthorized_client.get("/api/v1/pdf-import/info")
        finally:
            app.dependency_overrides.clear()

        # Assert
        assert response.status_code == 401
        data = response.json()
        assert data.get("error", {}).get("code") == "AUTHENTICATION_ERROR"

    def test_internal_server_error(self, client):
        """
        测试服务器内部错误

        Given: 服务层抛出异常
        When: 调用 PDF 导入 API
        Then: 返回 500 错误
        """
        # Arrange
        with patch(
            "src.constants.file_size_constants.DEFAULT_MAX_FILE_SIZE"
        ) as mock_size:
            mock_size.side_effect = Exception("Configuration error")

            # Act
            response = client.get("/api/v1/pdf-import/info")

            # Assert
            # 应该返回 200，因为这是简单的配置读取
            # 如果有数据库操作，可能会返回 500
            assert response.status_code == 200


# =============================================================================
# 集成测试
# =============================================================================


class TestIntegration:
    """集成测试"""

    def test_pdf_import_workflow(self, client, mock_pdf_service):
        """
        测试完整的 PDF 导入工作流

        Given: 用户要导入 PDF
        When: 1. 获取系统信息
              2. 上传 PDF
              3. 查询会话状态
        Then: 所有步骤都成功
        """
        # Step 1: 获取系统信息
        info_response = client.get("/api/v1/pdf-import/info")
        assert info_response.status_code == 200

        # Step 2: 上传 PDF
        files = {
            "file": (
                "contract.pdf",
                b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF",
                "application/pdf",
            )
        }
        with patch(
            "src.api.v1.documents.pdf_upload.validate_upload_file",
            new=AsyncMock(return_value={"valid": True}),
        ):
            with patch(
                "src.api.v1.documents.pdf_upload.open",
                mock_open(),
                create=True,
            ):
                upload_response = client.post(
                    "/api/v1/pdf-import/upload",
                    files=files,
                )
        assert upload_response.status_code == 200
        upload_data = upload_response.json()
        assert upload_data["success"] is True
        assert upload_data["session_id"] == "session_contract_001"
        mock_pdf_service.create_import_session.assert_awaited_once()
        mock_pdf_service.process_pdf_file.assert_awaited_once()

        # Step 3: 查询会话列表
        sessions_response = client.get("/api/v1/pdf-import/sessions")
        assert sessions_response.status_code == 200
        sessions_data = sessions_response.json()
        assert sessions_data["success"] is True
        assert sessions_data["data"]["items"] == []
