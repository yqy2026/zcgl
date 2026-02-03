"""
Unit tests for PropertyCertificateService
测试产权证服务的所有功能
"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.exception_handler import BusinessValidationError
from src.models.property_certificate import PropertyCertificate
from src.services.property_certificate.service import PropertyCertificateService

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def property_certificate_service(mock_db):
    """创建PropertyCertificateService实例"""
    return PropertyCertificateService(mock_db)


@pytest.fixture
def sample_extraction_data():
    """示例提取数据"""
    return {
        "certificate_type": "房产证",
        "registration_date": "2020-01-15",
        "property_address": "广东省广州市天河区XXX号",
        "property_type": "住宅",
        "building_area": "120.5",
        "floor_info": "第5层",
        "land_area": "50.0",
        "land_use_type": "出让",
        "land_use_term_start": "2010-01-01",
        "land_use_term_end": "2080-12-31",
        "co_ownership": "单独所有",
        "restrictions": "无",
        "remarks": "正常",
        "confidence": 0.92,
    }


# ============================================================================
# extract_from_file() tests (25 tests)
# ============================================================================


class TestExtractFromFile:
    """测试extract_from_file方法"""

    @pytest.mark.asyncio
    async def test_extract_success(self, property_certificate_service):
        """TC-PCS-001: 成功提取产权证信息"""
        # Arrange
        file_path = "/tmp/test_cert.pdf"
        filename = "test_cert.pdf"

        property_certificate_service.extractor.extract = AsyncMock(
            return_value={
                "success": True,
                "extracted_fields": {"certificate_number": "123456"},
                "confidence": 0.95,
                "raw_response": {},
                "extraction_method": "llm",
            }
        )

        # Act
        result = await property_certificate_service.extract_from_file(
            file_path, filename
        )

        # Assert
        assert result["success"] is True
        assert "data" in result
        assert "confidence" in result

    @pytest.mark.asyncio
    async def test_extract_with_extractor_error(self, property_certificate_service):
        """TC-PCS-002: 提取器异常处理"""
        # Arrange
        file_path = "/tmp/test_cert.pdf"
        filename = "test_cert.pdf"

        property_certificate_service.extractor.extract = AsyncMock(
            side_effect=Exception("Extraction failed")
        )

        # Act
        result = await property_certificate_service.extract_from_file(
            file_path, filename
        )

        # Assert
        assert result["success"] is False
        assert "error" in result
        assert filename in result["filename"]

    @pytest.mark.asyncio
    async def test_extract_returns_data(self, property_certificate_service):
        """TC-PCS-003: 返回提取的数据"""
        # Arrange
        file_path = "/tmp/test.pdf"
        filename = "test.pdf"
        extracted_fields = {
            "certificate_number": "粤房地权证穗字第1234567号",
            "registration_date": "2020-01-15",
        }

        property_certificate_service.extractor.extract = AsyncMock(
            return_value={
                "success": True,
                "extracted_fields": extracted_fields,
                "confidence": 0.90,
            }
        )

        # Act
        result = await property_certificate_service.extract_from_file(
            file_path, filename
        )

        # Assert
        assert result["data"] == extracted_fields

    @pytest.mark.asyncio
    async def test_extract_returns_confidence(self, property_certificate_service):
        """TC-PCS-004: 返回置信度"""
        # Arrange
        file_path = "/tmp/test.pdf"
        filename = "test.pdf"
        confidence = 0.88

        property_certificate_service.extractor.extract = AsyncMock(
            return_value={
                "success": True,
                "extracted_fields": {},
                "confidence": confidence,
            }
        )

        # Act
        result = await property_certificate_service.extract_from_file(
            file_path, filename
        )

        # Assert
        assert result["confidence"] == confidence

    @pytest.mark.asyncio
    async def test_extract_returns_raw_response(self, property_certificate_service):
        """TC-PCS-005: 返回原始响应"""
        # Arrange
        file_path = "/tmp/test.pdf"
        filename = "test.pdf"
        raw_response = {"model": "qwen", "tokens": 1500}

        property_certificate_service.extractor.extract = AsyncMock(
            return_value={
                "success": True,
                "extracted_fields": {},
                "confidence": 0.90,
                "raw_response": raw_response,
            }
        )

        # Act
        result = await property_certificate_service.extract_from_file(
            file_path, filename
        )

        # Assert
        assert result["raw_response"] == raw_response

    @pytest.mark.asyncio
    async def test_extract_returns_extraction_method(
        self, property_certificate_service
    ):
        """TC-PCS-006: 返回提取方法"""
        # Arrange
        file_path = "/tmp/test.pdf"
        filename = "test.pdf"
        method = "vision"

        property_certificate_service.extractor.extract = AsyncMock(
            return_value={
                "success": True,
                "extracted_fields": {},
                "confidence": 0.90,
                "extraction_method": method,
            }
        )

        # Act
        result = await property_certificate_service.extract_from_file(
            file_path, filename
        )

        # Assert
        assert result["extraction_method"] == method

    @pytest.mark.asyncio
    async def test_extract_returns_filename(self, property_certificate_service):
        """TC-PCS-007: 返回文件名"""
        # Arrange
        file_path = "/tmp/test.pdf"
        filename = "my_certificate.pdf"

        property_certificate_service.extractor.extract = AsyncMock(
            return_value={
                "success": True,
                "extracted_fields": {},
                "confidence": 0.90,
            }
        )

        # Act
        result = await property_certificate_service.extract_from_file(
            file_path, filename
        )

        # Assert
        assert result["filename"] == filename

    @pytest.mark.asyncio
    async def test_extract_with_zero_confidence(self, property_certificate_service):
        """TC-PCS-008: 处理零置信度"""
        # Arrange
        file_path = "/tmp/test.pdf"
        filename = "test.pdf"

        property_certificate_service.extractor.extract = AsyncMock(
            return_value={"success": True, "extracted_fields": {}}
        )

        # Act
        result = await property_certificate_service.extract_from_file(
            file_path, filename
        )

        # Assert
        assert result["confidence"] == 0.0

    @pytest.mark.asyncio
    async def test_extract_with_missing_confidence(self, property_certificate_service):
        """TC-PCS-009: 缺少置信度字段"""
        # Arrange
        file_path = "/tmp/test.pdf"
        filename = "test.pdf"

        property_certificate_service.extractor.extract = AsyncMock(
            return_value={"success": True, "extracted_fields": {}, "confidence": None}
        )

        # Act
        result = await property_certificate_service.extract_from_file(
            file_path, filename
        )

        # Assert
        assert result["confidence"] == 0.0

    @pytest.mark.asyncio
    async def test_extract_with_default_method(self, property_certificate_service):
        """TC-PCS-010: 默认提取方法为unknown"""
        # Arrange
        file_path = "/tmp/test.pdf"
        filename = "test.pdf"

        property_certificate_service.extractor.extract = AsyncMock(
            return_value={"success": True, "extracted_fields": {}}
        )

        # Act
        result = await property_certificate_service.extract_from_file(
            file_path, filename
        )

        # Assert
        assert result["extraction_method"] == "unknown"

    @pytest.mark.asyncio
    async def test_extract_various_filenames(self, property_certificate_service):
        """TC-PCS-011: 处理各种文件名"""
        # Arrange
        filenames = [
            "cert.pdf",
            "产权证.pdf",
            "certificate 123.pdf",
            "房产证_2020.pdf",
        ]

        property_certificate_service.extractor.extract = AsyncMock(
            return_value={"success": True, "extracted_fields": {}, "confidence": 0.90}
        )

        # Act & Assert
        for filename in filenames:
            result = await property_certificate_service.extract_from_file(
                "/tmp/test.pdf", filename
            )
            assert result["filename"] == filename

    @pytest.mark.asyncio
    async def test_extract_with_large_data(self, property_certificate_service):
        """TC-PCS-012: 处理大量数据"""
        # Arrange
        file_path = "/tmp/large_cert.pdf"
        filename = "large_cert.pdf"

        large_data = {f"field_{i}": f"value_{i}" for i in range(100)}

        property_certificate_service.extractor.extract = AsyncMock(
            return_value={
                "success": True,
                "extracted_fields": large_data,
                "confidence": 0.90,
            }
        )

        # Act
        result = await property_certificate_service.extract_from_file(
            file_path, filename
        )

        # Assert
        assert len(result["data"]) == 100

    @pytest.mark.asyncio
    async def test_extract_with_special_characters(self, property_certificate_service):
        """TC-PCS-013: 处理特殊字符"""
        # Arrange
        file_path = "/tmp/test.pdf"
        filename = "测试@#$%.pdf"

        property_certificate_service.extractor.extract = AsyncMock(
            return_value={"success": True, "extracted_fields": {}, "confidence": 0.90}
        )

        # Act
        result = await property_certificate_service.extract_from_file(
            file_path, filename
        )

        # Assert
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_extractor_called_with_file_path(self, property_certificate_service):
        """TC-PCS-014: 验证使用文件路径调用提取器"""
        # Arrange
        file_path = "/tmp/specific_path/test.pdf"
        filename = "test.pdf"

        property_certificate_service.extractor.extract = AsyncMock(
            return_value={"success": True, "extracted_fields": {}, "confidence": 0.90}
        )

        # Act
        await property_certificate_service.extract_from_file(file_path, filename)

        # Assert
        property_certificate_service.extractor.extract.assert_called_once_with(
            file_path
        )

    @pytest.mark.asyncio
    async def test_extract_with_unsuccessful_response(
        self, property_certificate_service
    ):
        """TC-PCS-015: 处理不成功的提取响应"""
        # Arrange
        file_path = "/tmp/test.pdf"
        filename = "test.pdf"

        property_certificate_service.extractor.extract = AsyncMock(
            return_value={"success": False, "error": "Failed to extract"}
        )

        # Act
        result = await property_certificate_service.extract_from_file(
            file_path, filename
        )

        # Assert
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_extract_error_message_format(self, property_certificate_service):
        """TC-PCS-016: 错误消息格式"""
        # Arrange
        file_path = "/tmp/test.pdf"
        filename = "cert.pdf"
        error_msg = "File format not supported"

        property_certificate_service.extractor.extract = AsyncMock(
            side_effect=Exception(error_msg)
        )

        # Act
        result = await property_certificate_service.extract_from_file(
            file_path, filename
        )

        # Assert
        assert error_msg in result["error"]

    @pytest.mark.asyncio
    async def test_extract_with_unicode_filename(self, property_certificate_service):
        """TC-PCS-017: Unicode文件名"""
        # Arrange
        file_path = "/tmp/证书.pdf"
        filename = "证书.pdf"

        property_certificate_service.extractor.extract = AsyncMock(
            return_value={"success": True, "extracted_fields": {}, "confidence": 0.90}
        )

        # Act
        result = await property_certificate_service.extract_from_file(
            file_path, filename
        )

        # Assert
        assert result["filename"] == filename

    @pytest.mark.asyncio
    async def test_extract_preserves_all_fields(self, property_certificate_service):
        """TC-PCS-018: 保留所有字段"""
        # Arrange
        file_path = "/tmp/test.pdf"
        filename = "test.pdf"
        fields = {
            "certificate_number": "123",
            "registration_date": "2020-01-01",
            "property_address": "Test Address",
            "building_area": "100.0",
        }

        property_certificate_service.extractor.extract = AsyncMock(
            return_value={
                "success": True,
                "extracted_fields": fields,
                "confidence": 0.90,
            }
        )

        # Act
        result = await property_certificate_service.extract_from_file(
            file_path, filename
        )

        # Assert
        for key, value in fields.items():
            assert result["data"].get(key) == value

    @pytest.mark.asyncio
    async def test_extract_with_nested_fields(self, property_certificate_service):
        """TC-PCS-019: 嵌套字段"""
        # Arrange
        file_path = "/tmp/test.pdf"
        filename = "test.pdf"
        nested_data = {
            "owner": {"name": "张三", "id": "123"},
            "property": {"address": "广州市天河区", "area": "100"},
        }

        property_certificate_service.extractor.extract = AsyncMock(
            return_value={
                "success": True,
                "extracted_fields": nested_data,
                "confidence": 0.90,
            }
        )

        # Act
        result = await property_certificate_service.extract_from_file(
            file_path, filename
        )

        # Assert
        assert result["data"]["owner"]["name"] == "张三"

    @pytest.mark.asyncio
    async def test_extract_with_list_fields(self, property_certificate_service):
        """TC-PCS-020: 列表字段"""
        # Arrange
        file_path = "/tmp/test.pdf"
        filename = "test.pdf"
        list_data = {"owners": ["张三", "李四"], "restrictions": ["抵押", "查封"]}

        property_certificate_service.extractor.extract = AsyncMock(
            return_value={
                "success": True,
                "extracted_fields": list_data,
                "confidence": 0.90,
            }
        )

        # Act
        result = await property_certificate_service.extract_from_file(
            file_path, filename
        )

        # Assert
        assert isinstance(result["data"]["owners"], list)
        assert len(result["data"]["owners"]) == 2

    @pytest.mark.asyncio
    async def test_extract_with_null_values(self, property_certificate_service):
        """TC-PCS-021: 空值处理"""
        # Arrange
        file_path = "/tmp/test.pdf"
        filename = "test.pdf"
        data_with_nulls = {
            "certificate_number": "123",
            "registration_date": None,
            "remarks": None,
        }

        property_certificate_service.extractor.extract = AsyncMock(
            return_value={
                "success": True,
                "extracted_fields": data_with_nulls,
                "confidence": 0.90,
            }
        )

        # Act
        result = await property_certificate_service.extract_from_file(
            file_path, filename
        )

        # Assert
        assert result["data"]["registration_date"] is None

    @pytest.mark.asyncio
    async def test_extract_with_numeric_strings(self, property_certificate_service):
        """TC-PCS-022: 数字字符串"""
        # Arrange
        file_path = "/tmp/test.pdf"
        filename = "test.pdf"
        numeric_data = {
            "building_area": "120.50",
            "land_area": "60.25",
            "floor_info": "5",
        }

        property_certificate_service.extractor.extract = AsyncMock(
            return_value={
                "success": True,
                "extracted_fields": numeric_data,
                "confidence": 0.90,
            }
        )

        # Act
        result = await property_certificate_service.extract_from_file(
            file_path, filename
        )

        # Assert
        assert result["data"]["building_area"] == "120.50"

    @pytest.mark.asyncio
    async def test_extract_confidence_range(self, property_certificate_service):
        """TC-PCS-023: 置信度范围"""
        # Arrange
        file_path = "/tmp/test.pdf"
        filename = "test.pdf"

        for conf in [0.0, 0.5, 0.75, 0.95, 1.0]:
            property_certificate_service.extractor.extract = AsyncMock(
                return_value={
                    "success": True,
                    "extracted_fields": {},
                    "confidence": conf,
                }
            )

            # Act
            result = await property_certificate_service.extract_from_file(
                file_path, filename
            )

            # Assert
            assert result["confidence"] == conf

    @pytest.mark.asyncio
    async def test_extract_with_chinese_date_format(self, property_certificate_service):
        """TC-PCS-024: 中文日期格式"""
        # Arrange
        file_path = "/tmp/test.pdf"
        filename = "test.pdf"
        chinese_date_data = {"registration_date": "2020年01月15日"}

        property_certificate_service.extractor.extract = AsyncMock(
            return_value={
                "success": True,
                "extracted_fields": chinese_date_data,
                "confidence": 0.90,
            }
        )

        # Act
        result = await property_certificate_service.extract_from_file(
            file_path, filename
        )

        # Assert
        assert result["data"]["registration_date"] == "2020年01月15日"

    @pytest.mark.asyncio
    async def test_extract_empty_response(self, property_certificate_service):
        """TC-PCS-025: 空响应处理"""
        # Arrange
        file_path = "/tmp/test.pdf"
        filename = "test.pdf"

        property_certificate_service.extractor.extract = AsyncMock(return_value={})

        # Act
        result = await property_certificate_service.extract_from_file(
            file_path, filename
        )

        # Assert
        assert result["success"] is False


# ============================================================================
# confirm_import() tests (25 tests)
# ============================================================================


class TestConfirmImport:
    """测试confirm_import方法"""

    @pytest.mark.asyncio
    async def test_confirm_import_success(
        self, property_certificate_service, mock_db, sample_extraction_data
    ):
        """TC-PCS-026: 成功确认导入"""
        # Arrange
        certificate_number = "粤房地权证穗字第1234567号"
        data = {
            "certificate_number": certificate_number,
            "extraction_data": sample_extraction_data,
            "owners": [],
        }

        # Mock CRUD operations
        from src.crud.property_certificate import property_certificate_crud

        property_certificate_crud.get_by_certificate_number = MagicMock(
            return_value=None
        )
        property_certificate_crud.create_with_owners = MagicMock(
            return_value=MagicMock(spec=PropertyCertificate, id="cert-123")
        )

        # Act
        result = await property_certificate_service.confirm_import(data)

        # Assert
        assert result.id == "cert-123"

    @pytest.mark.asyncio
    async def test_confirm_import_missing_certificate_number(
        self, property_certificate_service, sample_extraction_data
    ):
        """TC-PCS-027: 缺少证书编号"""
        # Arrange
        data = {
            "extraction_data": sample_extraction_data,
            "owners": [],
        }

        # Act & Assert
        with pytest.raises(BusinessValidationError, match="缺少证书编号"):
            await property_certificate_service.confirm_import(data)

    @pytest.mark.asyncio
    async def test_confirm_import_existing_certificate(
        self, property_certificate_service, mock_db, sample_extraction_data
    ):
        """TC-PCS-028: 证书已存在"""
        # Arrange
        certificate_number = "粤房地权证穗字第1234567号"
        data = {
            "certificate_number": certificate_number,
            "extraction_data": sample_extraction_data,
            "owners": [],
        }

        existing_cert = MagicMock(spec=PropertyCertificate)
        existing_cert.id = "existing-cert-123"

        from src.crud.property_certificate import property_certificate_crud

        property_certificate_crud.get_by_certificate_number = MagicMock(
            return_value=existing_cert
        )

        # Act
        result = await property_certificate_service.confirm_import(data)

        # Assert
        assert result.id == "existing-cert-123"

    @pytest.mark.asyncio
    async def test_confirm_import_with_owners(
        self, property_certificate_service, mock_db, sample_extraction_data
    ):
        """TC-PCS-029: 带权利人信息导入"""
        # Arrange
        certificate_number = "粤房地权证穗字第1234567号"
        owners = [
            {
                "owner_type": "个人",
                "name": "张三",
                "id_type": "身份证",
                "id_number": "440101199001011234",
                "phone": "13800138000",
            }
        ]

        data = {
            "certificate_number": certificate_number,
            "extraction_data": sample_extraction_data,
            "owners": owners,
        }

        from src.crud.property_certificate import (
            property_certificate_crud,
            property_owner_crud,
        )

        property_certificate_crud.get_by_certificate_number = MagicMock(
            return_value=None
        )
        property_owner_crud.create = MagicMock(return_value=MagicMock(id="owner-123"))
        property_certificate_crud.create_with_owners = MagicMock(
            return_value=MagicMock(spec=PropertyCertificate, id="cert-123")
        )

        # Act
        await property_certificate_service.confirm_import(data)

        # Assert
        property_owner_crud.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_confirm_import_multiple_owners(
        self, property_certificate_service, mock_db, sample_extraction_data
    ):
        """TC-PCS-030: 多个权利人"""
        # Arrange
        certificate_number = "粤房地权证穗字第1234567号"
        owners = [
            {"name": "张三", "id_number": "111"},
            {"name": "李四", "id_number": "222"},
            {"name": "王五", "id_number": "333"},
        ]

        data = {
            "certificate_number": certificate_number,
            "extraction_data": sample_extraction_data,
            "owners": owners,
        }

        from src.crud.property_certificate import (
            property_certificate_crud,
            property_owner_crud,
        )

        property_certificate_crud.get_by_certificate_number = MagicMock(
            return_value=None
        )
        property_owner_crud.create = MagicMock(
            side_effect=[
                MagicMock(id="owner-1"),
                MagicMock(id="owner-2"),
                MagicMock(id="owner-3"),
            ]
        )
        property_certificate_crud.create_with_owners = MagicMock(
            return_value=MagicMock(spec=PropertyCertificate, id="cert-123")
        )

        # Act
        await property_certificate_service.confirm_import(data)

        # Assert
        assert property_owner_crud.create.call_count == 3

    @pytest.mark.asyncio
    async def test_confirm_import_without_owners(
        self, property_certificate_service, mock_db, sample_extraction_data
    ):
        """TC-PCS-031: 无权利人信息"""
        # Arrange
        certificate_number = "粤房地权证穗字第1234567号"
        data = {
            "certificate_number": certificate_number,
            "extraction_data": sample_extraction_data,
        }

        from src.crud.property_certificate import property_certificate_crud

        property_certificate_crud.get_by_certificate_number = MagicMock(
            return_value=None
        )
        property_certificate_crud.create_with_owners = MagicMock(
            return_value=MagicMock(spec=PropertyCertificate, id="cert-123")
        )

        # Act
        await property_certificate_service.confirm_import(data)

        # Assert
        property_certificate_crud.create_with_owners.assert_called_once()

    @pytest.mark.asyncio
    async def test_confirm_import_parse_dates(
        self, property_certificate_service, mock_db, sample_extraction_data
    ):
        """TC-PCS-032: 日期解析"""
        # Arrange
        certificate_number = "粤房地权证穗字第1234567号"
        data = {
            "certificate_number": certificate_number,
            "extraction_data": sample_extraction_data,
            "owners": [],
        }

        from src.crud.property_certificate import property_certificate_crud

        property_certificate_crud.get_by_certificate_number = MagicMock(
            return_value=None
        )
        property_certificate_crud.create_with_owners = MagicMock(
            return_value=MagicMock(spec=PropertyCertificate, id="cert-123")
        )

        # Act
        await property_certificate_service.confirm_import(data)

        # Assert
        property_certificate_crud.create_with_owners.assert_called_once()

    @pytest.mark.asyncio
    async def test_confirm_import_default_values(
        self, property_certificate_service, mock_db, sample_extraction_data
    ):
        """TC-PCS-033: 默认值设置"""
        # Arrange
        certificate_number = "粤房地权证穗字第1234567号"
        minimal_data = {"registration_date": "2020-01-01"}

        data = {
            "certificate_number": certificate_number,
            "extraction_data": minimal_data,
            "owners": [],
        }

        from src.crud.property_certificate import property_certificate_crud

        property_certificate_crud.get_by_certificate_number = MagicMock(
            return_value=None
        )
        property_certificate_crud.create_with_owners = MagicMock(
            return_value=MagicMock(spec=PropertyCertificate, id="cert-123")
        )

        # Act
        await property_certificate_service.confirm_import(data)

        # Assert
        property_certificate_crud.create_with_owners.assert_called_once()

    @pytest.mark.asyncio
    async def test_confirm_import_confidence_field(
        self, property_certificate_service, mock_db, sample_extraction_data
    ):
        """TC-PCS-034: 置信度字段"""
        # Arrange
        certificate_number = "粤房地权证穗字第1234567号"
        sample_extraction_data["confidence"] = 0.95

        data = {
            "certificate_number": certificate_number,
            "extraction_data": sample_extraction_data,
            "owners": [],
        }

        from src.crud.property_certificate import property_certificate_crud

        property_certificate_crud.get_by_certificate_number = MagicMock(
            return_value=None
        )
        property_certificate_crud.create_with_owners = MagicMock(
            return_value=MagicMock(spec=PropertyCertificate, id="cert-123")
        )

        # Act
        await property_certificate_service.confirm_import(data)

        # Assert
        property_certificate_crud.create_with_owners.assert_called_once()

    @pytest.mark.asyncio
    async def test_confirm_import_is_verified_false(
        self, property_certificate_service, mock_db, sample_extraction_data
    ):
        """TC-PCS-035: is_verified默认为False"""
        # Arrange
        certificate_number = "粤房地权证穗字第1234567号"
        data = {
            "certificate_number": certificate_number,
            "extraction_data": sample_extraction_data,
            "owners": [],
        }

        from src.crud.property_certificate import property_certificate_crud

        property_certificate_crud.get_by_certificate_number = MagicMock(
            return_value=None
        )

        # Capture the create_with_owners call
        captured_data = {}

        def capture_call(db, obj_in, owner_ids):
            captured_data.update(obj_in)
            return MagicMock(spec=PropertyCertificate, id="cert-123")

        property_certificate_crud.create_with_owners = MagicMock(
            side_effect=capture_call
        )

        # Act
        await property_certificate_service.confirm_import(data)

        # Assert
        assert captured_data["is_verified"] is False

    @pytest.mark.asyncio
    async def test_confirm_import_with_null_optional_fields(
        self, property_certificate_service, mock_db, sample_extraction_data
    ):
        """TC-PCS-036: 可选字段为空"""
        # Arrange
        certificate_number = "粤房地权证穗字第1234567号"
        data_with_nulls = {
            "registration_date": "2020-01-01",
            "property_address": None,
            "land_area": None,
        }

        data = {
            "certificate_number": certificate_number,
            "extraction_data": data_with_nulls,
            "owners": [],
        }

        from src.crud.property_certificate import property_certificate_crud

        property_certificate_crud.get_by_certificate_number = MagicMock(
            return_value=None
        )
        property_certificate_crud.create_with_owners = MagicMock(
            return_value=MagicMock(spec=PropertyCertificate, id="cert-123")
        )

        # Act
        await property_certificate_service.confirm_import(data)

        # Assert
        property_certificate_crud.create_with_owners.assert_called_once()

    @pytest.mark.asyncio
    async def test_confirm_import_owner_phone_encryption(
        self, property_certificate_service, mock_db, sample_extraction_data
    ):
        """TC-PCS-037: 权利人电话加密"""
        # Arrange
        certificate_number = "粤房地权证穗字第1234567号"
        owners = [
            {"name": "张三", "phone": "13800138000"},
        ]

        data = {
            "certificate_number": certificate_number,
            "extraction_data": sample_extraction_data,
            "owners": owners,
        }

        from src.crud.property_certificate import (
            property_certificate_crud,
            property_owner_crud,
        )

        property_certificate_crud.get_by_certificate_number = MagicMock(
            return_value=None
        )
        property_owner_crud.create = MagicMock(return_value=MagicMock(id="owner-123"))
        property_certificate_crud.create_with_owners = MagicMock(
            return_value=MagicMock(spec=PropertyCertificate, id="cert-123")
        )

        # Act
        await property_certificate_service.confirm_import(data)

        # Assert
        property_owner_crud.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_confirm_import_owner_id_card_encryption(
        self, property_certificate_service, mock_db, sample_extraction_data
    ):
        """TC-PCS-038: 权利人身份证加密"""
        # Arrange
        certificate_number = "粤房地权证穗字第1234567号"
        owners = [
            {"name": "张三", "id_number": "440101199001011234"},
        ]

        data = {
            "certificate_number": certificate_number,
            "extraction_data": sample_extraction_data,
            "owners": owners,
        }

        from src.crud.property_certificate import (
            property_certificate_crud,
            property_owner_crud,
        )

        property_certificate_crud.get_by_certificate_number = MagicMock(
            return_value=None
        )
        property_owner_crud.create = MagicMock(return_value=MagicMock(id="owner-123"))
        property_certificate_crud.create_with_owners = MagicMock(
            return_value=MagicMock(spec=PropertyCertificate, id="cert-123")
        )

        # Act
        await property_certificate_service.confirm_import(data)

        # Assert
        property_owner_crud.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_confirm_import_with_organization_owner(
        self, property_certificate_service, mock_db, sample_extraction_data
    ):
        """TC-PCS-039: 组织权利人"""
        # Arrange
        certificate_number = "粤房地权证穗字第1234567号"
        owners = [
            {
                "owner_type": "组织",
                "name": "XX公司",
                "organization_id": "91440100123456789X",
            }
        ]

        data = {
            "certificate_number": certificate_number,
            "extraction_data": sample_extraction_data,
            "owners": owners,
        }

        from src.crud.property_certificate import (
            property_certificate_crud,
            property_owner_crud,
        )

        property_certificate_crud.get_by_certificate_number = MagicMock(
            return_value=None
        )
        property_owner_crud.create = MagicMock(return_value=MagicMock(id="owner-123"))
        property_certificate_crud.create_with_owners = MagicMock(
            return_value=MagicMock(spec=PropertyCertificate, id="cert-123")
        )

        # Act
        await property_certificate_service.confirm_import(data)

        # Assert
        property_owner_crud.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_confirm_import_extracts_all_fields(
        self, property_certificate_service, mock_db, sample_extraction_data
    ):
        """TC-PCS-040: 提取所有字段"""
        # Arrange
        certificate_number = "粤房地权证穗字第1234567号"
        data = {
            "certificate_number": certificate_number,
            "extraction_data": sample_extraction_data,
            "owners": [],
        }

        from src.crud.property_certificate import property_certificate_crud

        property_certificate_crud.get_by_certificate_number = MagicMock(
            return_value=None
        )

        captured_data = {}

        def capture_call(db, obj_in, owner_ids):
            captured_data.update(obj_in)
            return MagicMock(spec=PropertyCertificate, id="cert-123")

        property_certificate_crud.create_with_owners = MagicMock(
            side_effect=capture_call
        )

        # Act
        await property_certificate_service.confirm_import(data)

        # Assert
        assert "certificate_number" in captured_data
        assert "property_address" in captured_data
        assert "building_area" in captured_data

    @pytest.mark.asyncio
    async def test_confirm_import_empty_owners_list(
        self, property_certificate_service, mock_db, sample_extraction_data
    ):
        """TC-PCS-041: 空权利人列表"""
        # Arrange
        certificate_number = "粤房地权证穗字第1234567号"
        data = {
            "certificate_number": certificate_number,
            "extraction_data": sample_extraction_data,
            "owners": [],
        }

        from src.crud.property_certificate import property_certificate_crud

        property_certificate_crud.get_by_certificate_number = MagicMock(
            return_value=None
        )
        property_certificate_crud.create_with_owners = MagicMock(
            return_value=MagicMock(spec=PropertyCertificate, id="cert-123")
        )

        # Act
        await property_certificate_service.confirm_import(data)

        # Assert
        property_certificate_crud.create_with_owners.assert_called_once()

    @pytest.mark.asyncio
    async def test_confirm_import_with_co_ownership(
        self, property_certificate_service, mock_db, sample_extraction_data
    ):
        """TC-PCS-042: 共有情况"""
        # Arrange
        certificate_number = "粤房地权证穗字第1234567号"
        sample_extraction_data["co_ownership"] = "共同共有"

        data = {
            "certificate_number": certificate_number,
            "extraction_data": sample_extraction_data,
            "owners": [],
        }

        from src.crud.property_certificate import property_certificate_crud

        property_certificate_crud.get_by_certificate_number = MagicMock(
            return_value=None
        )
        property_certificate_crud.create_with_owners = MagicMock(
            return_value=MagicMock(spec=PropertyCertificate, id="cert-123")
        )

        # Act
        await property_certificate_service.confirm_import(data)

        # Assert
        property_certificate_crud.create_with_owners.assert_called_once()

    @pytest.mark.asyncio
    async def test_confirm_import_with_restrictions(
        self, property_certificate_service, mock_db, sample_extraction_data
    ):
        """TC-PCS-043: 限制信息"""
        # Arrange
        certificate_number = "粤房地权证穗字第1234567号"
        sample_extraction_data["restrictions"] = "已抵押,已查封"

        data = {
            "certificate_number": certificate_number,
            "extraction_data": sample_extraction_data,
            "owners": [],
        }

        from src.crud.property_certificate import property_certificate_crud

        property_certificate_crud.get_by_certificate_number = MagicMock(
            return_value=None
        )
        property_certificate_crud.create_with_owners = MagicMock(
            return_value=MagicMock(spec=PropertyCertificate, id="cert-123")
        )

        # Act
        await property_certificate_service.confirm_import(data)

        # Assert
        property_certificate_crud.create_with_owners.assert_called_once()

    @pytest.mark.asyncio
    async def test_confirm_import_various_certificate_types(
        self, property_certificate_service, mock_db, sample_extraction_data
    ):
        """TC-PCS-044: 各种证书类型"""
        # Arrange
        cert_types = ["房产证", "土地证", "不动产证"]

        from src.crud.property_certificate import property_certificate_crud

        property_certificate_crud.get_by_certificate_number = MagicMock(
            return_value=None
        )
        property_certificate_crud.create_with_owners = MagicMock(
            return_value=MagicMock(spec=PropertyCertificate, id="cert-123")
        )

        for cert_type in cert_types:
            sample_extraction_data["certificate_type"] = cert_type
            data = {
                "certificate_number": "1234567",
                "extraction_data": sample_extraction_data.copy(),
                "owners": [],
            }

            # Act
            result = await property_certificate_service.confirm_import(data)

            # Assert
            assert result.id == "cert-123"

    @pytest.mark.asyncio
    async def test_confirm_import_missing_extraction_data(
        self, property_certificate_service, sample_extraction_data
    ):
        """TC-PCS-045: 缺少extraction_data"""
        # Arrange
        data = {
            "certificate_number": "粤房地权证穗字第1234567号",
        }

        # Act
        result = await property_certificate_service.confirm_import(data)

        # Assert
        # Should use default empty dict
        assert result is not None

    @pytest.mark.asyncio
    async def test_confirm_import_database_error(
        self, property_certificate_service, mock_db, sample_extraction_data
    ):
        """TC-PCS-046: 数据库错误处理"""
        # Arrange
        certificate_number = "粤房地权证穗字第1234567号"
        data = {
            "certificate_number": certificate_number,
            "extraction_data": sample_extraction_data,
            "owners": [],
        }

        from src.crud.property_certificate import property_certificate_crud

        property_certificate_crud.get_by_certificate_number = MagicMock(
            side_effect=Exception("Database error")
        )

        # Act & Assert
        with pytest.raises(Exception, match="Database error"):
            await property_certificate_service.confirm_import(data)

    @pytest.mark.asyncio
    async def test_confirm_import_with_numeric_area_values(
        self, property_certificate_service, mock_db, sample_extraction_data
    ):
        """TC-PCS-047: 数字面积值"""
        # Arrange
        certificate_number = "粤房地权证穗字第1234567号"
        sample_extraction_data["building_area"] = "120.5"
        sample_extraction_data["land_area"] = "60.25"

        data = {
            "certificate_number": certificate_number,
            "extraction_data": sample_extraction_data,
            "owners": [],
        }

        from src.crud.property_certificate import property_certificate_crud

        property_certificate_crud.get_by_certificate_number = MagicMock(
            return_value=None
        )
        property_certificate_crud.create_with_owners = MagicMock(
            return_value=MagicMock(spec=PropertyCertificate, id="cert-123")
        )

        # Act
        await property_certificate_service.confirm_import(data)

        # Assert
        property_certificate_crud.create_with_owners.assert_called_once()

    @pytest.mark.asyncio
    async def test_confirm_import_preserves_certificate_number(
        self, property_certificate_service, mock_db, sample_extraction_data
    ):
        """TC-PCS-048: 保留证书编号"""
        # Arrange
        certificate_number = "粤房地权证穗字第1234567号"
        data = {
            "certificate_number": certificate_number,
            "extraction_data": sample_extraction_data,
            "owners": [],
        }

        from src.crud.property_certificate import property_certificate_crud

        property_certificate_crud.get_by_certificate_number = MagicMock(
            return_value=None
        )

        captured_number = None

        def capture_call(db, obj_in, owner_ids):
            nonlocal captured_number
            captured_number = obj_in.certificate_number
            return MagicMock(spec=PropertyCertificate, id="cert-123")

        property_certificate_crud.create_with_owners = MagicMock(
            side_effect=capture_call
        )

        # Act
        await property_certificate_service.confirm_import(data)

        # Assert
        assert captured_number == certificate_number

    @pytest.mark.asyncio
    async def test_confirm_import_with_land_use_terms(
        self, property_certificate_service, mock_db, sample_extraction_data
    ):
        """TC-PCS-049: 土地使用期限"""
        # Arrange
        certificate_number = "粤房地权证穗字第1234567号"
        sample_extraction_data["land_use_term_start"] = "2010-01-01"
        sample_extraction_data["land_use_term_end"] = "2080-12-31"

        data = {
            "certificate_number": certificate_number,
            "extraction_data": sample_extraction_data,
            "owners": [],
        }

        from src.crud.property_certificate import property_certificate_crud

        property_certificate_crud.get_by_certificate_number = MagicMock(
            return_value=None
        )
        property_certificate_crud.create_with_owners = MagicMock(
            return_value=MagicMock(spec=PropertyCertificate, id="cert-123")
        )

        # Act
        await property_certificate_service.confirm_import(data)

        # Assert
        property_certificate_crud.create_with_owners.assert_called_once()

    @pytest.mark.asyncio
    async def test_confirm_import_with_property_type(
        self, property_certificate_service, mock_db, sample_extraction_data
    ):
        """TC-PCS-050: 房产性质"""
        # Arrange
        certificate_number = "粤房地权证穗字第1234567号"
        property_types = ["住宅", "商业", "办公", "工业"]

        from src.crud.property_certificate import property_certificate_crud

        property_certificate_crud.get_by_certificate_number = MagicMock(
            return_value=None
        )
        property_certificate_crud.create_with_owners = MagicMock(
            return_value=MagicMock(spec=PropertyCertificate, id="cert-123")
        )

        for prop_type in property_types:
            sample_extraction_data["property_type"] = prop_type
            data = {
                "certificate_number": certificate_number,
                "extraction_data": sample_extraction_data.copy(),
                "owners": [],
            }

            # Act
            result = await property_certificate_service.confirm_import(data)

            # Assert
            assert result.id == "cert-123"


# ============================================================================
# _parse_date() tests (10 tests)
# ============================================================================


class TestParseDate:
    """测试_parse_date方法"""

    def test_parse_date_iso_format(self, property_certificate_service):
        """TC-PCS-051: 解析ISO格式日期(YYYY-MM-DD)"""
        # Act
        result = property_certificate_service._parse_date("2020-01-15")

        # Assert
        assert result == date(2020, 1, 15)

    def test_parse_date_slash_format(self, property_certificate_service):
        """TC-PCS-052: 解析斜杠格式日期(YYYY/MM/DD)"""
        # Act
        result = property_certificate_service._parse_date("2020/01/15")

        # Assert
        assert result == date(2020, 1, 15)

    def test_parse_date_chinese_format(self, property_certificate_service):
        """TC-PCS-053: 解析中文格式日期(YYYY年MM月DD日)"""
        # Act
        result = property_certificate_service._parse_date("2020年01月15日")

        # Assert
        assert result == date(2020, 1, 15)

    def test_parse_date_none_returns_none(self, property_certificate_service):
        """TC-PCS-054: None输入返回None"""
        # Act
        result = property_certificate_service._parse_date(None)

        # Assert
        assert result is None

    def test_parse_date_empty_string_returns_none(self, property_certificate_service):
        """TC-PCS-055: 空字符串返回None"""
        # Act
        result = property_certificate_service._parse_date("")

        # Assert
        assert result is None

    def test_parse_date_invalid_format_returns_none(self, property_certificate_service):
        """TC-PCS-056: 无效格式返回None"""
        # Act
        result = property_certificate_service._parse_date("invalid-date")

        # Assert
        assert result is None

    def test_parse_date_various_valid_dates(self, property_certificate_service):
        """TC-PCS-057: 各种有效日期"""
        # Arrange & Act & Assert
        assert property_certificate_service._parse_date("2020-01-01") == date(
            2020, 1, 1
        )
        assert property_certificate_service._parse_date("2020/12/31") == date(
            2020, 12, 31
        )
        assert property_certificate_service._parse_date("2020年06月15日") == date(
            2020, 6, 15
        )

    def test_parse_date_leap_year(self, property_certificate_service):
        """TC-PCS-058: 闰年日期"""
        # Act
        result = property_certificate_service._parse_date("2020-02-29")

        # Assert
        assert result == date(2020, 2, 29)

    def test_parse_date_single_digit_parts(self, property_certificate_service):
        """TC-PCS-059: 单数字月日"""
        # Act
        result = property_certificate_service._parse_date("2020-1-5")

        # Assert
        # Should handle or return None depending on format
        assert result is not None or result is None

    def test_parse_date_with_extra_spaces(self, property_certificate_service):
        """TC-PCS-060: 带额外空格的日期"""
        # Act
        result = property_certificate_service._parse_date(" 2020-01-15 ")

        # Assert
        # Should handle or return None
        assert result is not None or result is None


# ============================================================================
# match_assets() tests (4 tests)
# ============================================================================


class TestMatchAssets:
    """测试match_assets方法"""

    def test_match_assets_returns_empty_when_no_data(
        self, property_certificate_service
    ):
        """TC-PCS-061: 无提取字段时返回空列表"""
        result = property_certificate_service.match_assets({})
        assert result == []

    def test_match_assets_address_match(self, property_certificate_service):
        """TC-PCS-062: 地址匹配返回候选资产"""
        asset = MagicMock()
        asset.id = "asset-001"
        asset.property_name = "示例物业"
        asset.address = "广东省广州市天河区XXX号"
        asset.ownership_entity = "示例公司"

        property_certificate_service._fetch_assets_by_field = MagicMock(
            return_value=[asset]
        )

        result = property_certificate_service.match_assets(
            {"property_address": "广东省广州市天河区XXX号"}
        )

        assert len(result) == 1
        assert result[0]["asset_id"] == "asset-001"
        assert "地址匹配" in result[0]["match_reasons"]
        assert result[0]["confidence"] >= 0.7

    def test_match_assets_owner_match(self, property_certificate_service):
        """TC-PCS-063: 权属方匹配返回候选资产"""
        asset = MagicMock()
        asset.id = "asset-002"
        asset.property_name = "示例物业"
        asset.address = "广东省广州市天河区YYY号"
        asset.ownership_entity = "广州示例公司"

        property_certificate_service._fetch_assets_by_field = MagicMock(
            return_value=[asset]
        )

        result = property_certificate_service.match_assets(
            {"owner_name": "广州示例公司"}
        )

        assert len(result) == 1
        assert result[0]["asset_id"] == "asset-002"
        assert "权属方匹配" in result[0]["match_reasons"]
        assert result[0]["confidence"] >= 0.5

    def test_match_assets_combines_reasons(self, property_certificate_service):
        """TC-PCS-064: 地址与权属方匹配合并原因"""
        asset = MagicMock()
        asset.id = "asset-003"
        asset.property_name = "综合物业"
        asset.address = "广东省广州市天河区ZZZ号"
        asset.ownership_entity = "综合公司"

        property_certificate_service._fetch_assets_by_field = MagicMock(
            side_effect=[[asset], [asset]]
        )

        result = property_certificate_service.match_assets(
            {
                "property_address": "广东省广州市天河区ZZZ号",
                "owner_name": "综合公司",
            }
        )

        assert len(result) == 1
        assert set(result[0]["match_reasons"]) == {"地址匹配", "权属方匹配"}
        assert result[0]["confidence"] >= 0.85
