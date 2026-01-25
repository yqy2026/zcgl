"""
File Validation Security Tests

Tests for file upload security validation including:
- File type detection
- File size limits
- Malicious content detection
- Filename security
"""

import hashlib
import io
from unittest.mock import Mock, MagicMock, patch

import pytest
from fastapi import UploadFile

from src.core.exception_handler import BusinessValidationError
from src.security.security import (
    FileValidationConfig,
    FileValidator,
)


class TestFileValidationConfig:
    """Test file validation configuration"""

    def test_allowed_mime_types(self):
        """Test that allowed MIME types are properly configured"""
        config = FileValidationConfig()

        assert "application/pdf" in config.ALLOWED_MIME_TYPES
        assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in config.ALLOWED_MIME_TYPES
        assert "image/jpeg" in config.ALLOWED_MIME_TYPES

    def test_max_file_sizes(self):
        """Test file size limits"""
        config = FileValidationConfig()

        assert config.MAX_FILE_SIZES["pdf"] == 50 * 1024 * 1024  # 50MB
        assert config.MAX_FILE_SIZES["excel"] == 100 * 1024 * 1024  # 100MB
        assert config.MAX_FILE_SIZES["image"] == 20 * 1024 * 1024  # 20MB

    def test_malicious_signatures(self):
        """Test malicious file signatures are defined"""
        config = FileValidationConfig()

        # Should detect PHP scripts
        assert b"<?php" in config.MALICIOUS_SIGNATURES

        # Should detect JavaScript
        assert b"<script" in config.MALICIOUS_SIGNATURES
        assert b"javascript:" in config.MALICIOUS_SIGNATURES

        # Should detect dangerous HTML
        assert b"<iframe" in config.MALICIOUS_SIGNATURES
        assert b"eval(" in config.MALICIOUS_SIGNATURES

    def test_blacklisted_patterns(self):
        """Test filename blacklist patterns"""
        config = FileValidationConfig()

        # Path traversal patterns
        assert r"\.\." in config.BLACKLISTED_PATTERNS

        # Dangerous extensions
        assert r"\.php$" in config.BLACKLISTED_PATTERNS
        assert r"\.exe$" in config.BLACKLISTED_PATTERNS
        assert r"\.bat$" in config.BLACKLISTED_PATTERNS


class TestFileValidator:
    """Test file validator"""

    @pytest.fixture
    def validator(self):
        """Create a file validator instance"""
        return FileValidator()

    @pytest.fixture
    def mock_pdf_file(self):
        """Create a mock PDF file"""
        file = Mock(spec=UploadFile)
        file.filename = "test.pdf"
        file.file = io.BytesIO(b"%PDF-1.4\n%fake pdf content")
        file.size = 100
        return file

    @pytest.fixture
    def mock_image_file(self):
        """Create a mock image file"""
        file = Mock(spec=UploadFile)
        file.filename = "test.jpg"
        file.file = io.BytesIO(b"\xff\xd8\xff\xe0\x00\x10JFIF")  # JPEG header
        file.size = 5000
        return file


class TestFilenameValidation:
    """Test filename security validation"""

    @pytest.fixture
    def validator(self):
        return FileValidator()

    def test_valid_filename(self, validator):
        """Test that valid filenames pass"""
        valid_filenames = [
            "document.pdf",
            "report_2024.xlsx",
            "image-test.jpg",
            "data_file_v1.csv",
            "我的文档.pdf",  # Unicode filename
        ]

        for filename in valid_filenames:
            assert validator.validate_filename(filename) is True

    def test_empty_filename(self, validator):
        """Test that empty filename is rejected"""
        with pytest.raises(BusinessValidationError, match="文件名不能为空"):
            validator.validate_filename("")

    def test_too_long_filename(self, validator):
        """Test that overly long filenames are rejected"""
        long_filename = "a" * 256 + ".pdf"

        with pytest.raises(BusinessValidationError, match="文件名过长"):
            validator.validate_filename(long_filename)

    def test_path_traversal_patterns(self, validator):
        """Test that path traversal patterns are blocked"""
        malicious_filenames = [
            "../../../etc/passwd",
            "..\\..\\system32\\config",
            "./../../sensitive.txt",
            "file../../../pdf",
        ]

        for filename in malicious_filenames:
            with pytest.raises(BusinessValidationError):
                validator.validate_filename(filename)

    def test_dangerous_extensions(self, validator):
        """Test that dangerous file extensions are blocked"""
        dangerous_files = [
            "script.php",
            "trojan.exe",
            "virus.bat",
            "malware.scr",
            "payload.asp",
            "exploit.aspx",
        ]

        for filename in dangerous_files:
            with pytest.raises(BusinessValidationError):
                validator.validate_filename(filename)

    def test_special_characters(self, validator):
        """Test that special characters are blocked"""
        special_char_files = [
            "file*.txt",
            "file?.pdf",
            "file<>.doc",
            'file".xlsx',
            "file|.csv",
        ]

        for filename in special_char_files:
            with pytest.raises(BusinessValidationError):
                validator.validate_filename(filename)


class TestFileSizeValidation:
    """Test file size validation"""

    @pytest.fixture
    def validator(self):
        return FileValidator()

    def test_valid_file_size(self, validator):
        """Test that valid file sizes pass"""
        file = Mock(spec=UploadFile)
        file.filename = "test.pdf"
        file.file = io.BytesIO(b"x" * 1000)
        file.size = 1000

        assert validator.validate_file_size(file) is True

    def test_file_too_large_pdf(self, validator):
        """Test that oversized PDF is rejected"""
        file = Mock(spec=UploadFile)
        file.filename = "large.pdf"
        file.file = io.BytesIO(b"x" * 100)
        file.size = 60 * 1024 * 1024  # 60MB - exceeds 50MB limit

        with pytest.raises(BusinessValidationError, match="文件过大"):
            validator.validate_file_size(file)

    def test_file_too_large_image(self, validator):
        """Test that oversized image is rejected"""
        file = Mock(spec=UploadFile)
        file.filename = "large.jpg"
        file.file = io.BytesIO(b"x" * 100)
        file.size = 25 * 1024 * 1024  # 25MB - exceeds 20MB limit

        with pytest.raises(BusinessValidationError, match="文件过大"):
            validator.validate_file_size(file)

    def test_custom_size_limit(self, validator):
        """Test custom file size limit"""
        file = Mock(spec=UploadFile)
        file.filename = "test.pdf"
        file.file = io.BytesIO(b"x" * 100)
        file.size = 2000

        # Set custom limit of 1KB
        with pytest.raises(BusinessValidationError):
            validator.validate_file_size(file, max_size=1024)

    def test_file_size_detection_without_size_attribute(self, validator):
        """Test file size detection when size attribute is missing"""
        file = Mock(spec=UploadFile)
        file.filename = "test.pdf"
        file.file = io.BytesIO(b"x" * 5000)

        # Mock file.seek and file.tell
        def seek_func(pos, whence=0):
            pass

        file.file.seek = seek_func
        file.file.tell = Mock(return_value=5000)
        file.size = None

        assert validator.validate_file_size(file) is True


class TestFileTypeValidation:
    """Test file type validation"""

    @pytest.fixture
    def validator(self):
        return FileValidator()

    @pytest.fixture
    def mock_file(self):
        """Create a mock file"""
        file = Mock(spec=UploadFile)
        file.filename = "test.pdf"
        file.file = io.BytesIO(b"%PDF-1.4\n%fake content")
        return file

    def test_valid_file_extension(self, validator, mock_file):
        """Test that valid file extensions pass"""
        with patch("src.security.security.magic") as mock_magic:
            mock_magic.from_buffer.return_value = "application/pdf"

            result = validator.validate_file_type(mock_file)
            assert result is True

    def test_invalid_file_extension(self, validator):
        """Test that invalid file extensions are rejected"""
        file = Mock(spec=UploadFile)
        file.filename = "test.exe"
        file.file = io.BytesIO(b"some content")

        with pytest.raises(BusinessValidationError, match="不支持的文件扩展名"):
            validator.validate_file_type(file)

    def test_extension_mime_mismatch(self, validator, mock_file):
        """Test that extension/MIME mismatch is detected"""
        with patch("src.security.security.magic") as mock_magic:
            # File says .pdf but MIME type is different
            mock_magic.from_buffer.return_value = "application/vnd.ms-excel"

            with pytest.raises(BusinessValidationError, match="文件扩展名与MIME类型不匹配"):
                validator.validate_file_type(mock_file)

    def test_suspicious_mime_type(self, validator, mock_file):
        """Test that suspicious MIME types are blocked"""
        with patch("src.security.security.magic") as mock_magic:
            mock_magic.from_buffer.return_value = "application/x-php"

            with pytest.raises(BusinessValidationError, match="可疑的文件类型"):
                validator.validate_file_type(mock_file)

    def test_file_pointer_reset(self, validator, mock_file):
        """Test that file pointer is reset after reading"""
        original_position = 100

        with patch("src.security.security.magic") as mock_magic:
            mock_magic.from_buffer.return_value = "application/pdf"
            mock_file.file.tell.return_value = original_position
            mock_file.file.read.return_value = b"content"

            validator.validate_file_type(mock_file)

            # Verify file pointer was reset
            mock_file.file.seek.assert_called_with(original_position)


class TestFileContentValidation:
    """Test file content security validation"""

    @pytest.fixture
    def validator(self):
        return FileValidator()

    def test_clean_content(self, validator):
        """Test that clean content passes"""
        file = Mock(spec=UploadFile)
        file.filename = "test.pdf"
        file.file = io.BytesIO(b"Clean PDF content here")

        assert validator.validate_file_content(file) is True

    def test_php_script_detection(self, validator):
        """Test PHP script detection"""
        file = Mock(spec=UploadFile)
        file.filename = "test.pdf"
        file.file = io.BytesIO(b"<?php system('ls'); ?>")

        with pytest.raises(BusinessValidationError, match="可疑文件内容"):
            validator.validate_file_content(file)

    def test_javascript_detection(self, validator):
        """Test JavaScript injection detection"""
        file = Mock(spec=UploadFile)
        file.filename = "test.pdf"
        file.file = io.BytesIO(b"<script>alert('XSS')</script>")

        with pytest.raises(BusinessValidationError, match="可疑文件内容"):
            validator.validate_file_content(file)

    def test_eval_detection(self, validator):
        """Test eval() function detection"""
        file = Mock(spec=UploadFile)
        file.filename = "test.pdf"
        file.file = io.BytesIO(b"eval(malicious_code())")

        with pytest.raises(BusinessValidationError, match="可疑文件内容"):
            validator.validate_file_content(file)

    def test_empty_file(self, validator):
        """Test empty file detection"""
        file = Mock(spec=UploadFile)
        file.filename = "test.pdf"
        file.file = io.BytesIO(b"")

        with pytest.raises(BusinessValidationError, match="文件内容为空"):
            validator.validate_file_content(file)

    def test_case_insensitive_detection(self, validator):
        """Test that detection is case-insensitive"""
        file = Mock(spec=UploadFile)
        file.filename = "test.pdf"
        # Lowercase version should still be detected
        file.file = io.BytesIO(b"<SCRIPT>alert('xss')</script>")

        with pytest.raises(BusinessValidationError, match="可疑文件内容"):
            validator.validate_file_content(file)


class TestFileHashCalculation:
    """Test file hash calculation"""

    @pytest.fixture
    def validator(self):
        return FileValidator()

    def test_sha256_hash_calculation(self, validator):
        """Test SHA-256 hash calculation"""
        content = b"Test content for hashing"
        file = Mock(spec=UploadFile)
        file.file = io.BytesIO(content)

        # Calculate expected hash
        expected_hash = hashlib.sha256(content).hexdigest()

        result = validator.calculate_file_hash(file)
        assert result == expected_hash

    def test_hash_calculation_empty_file(self, validator):
        """Test hash calculation for empty file"""
        file = Mock(spec=UploadFile)
        file.file = io.BytesIO(b"")

        expected_hash = hashlib.sha256(b"").hexdigest()
        result = validator.calculate_file_hash(file)

        assert result == expected_hash

    def test_hash_calculation_large_file(self, validator):
        """Test hash calculation for large file (chunked reading)"""
        # Create 1MB of data
        content = b"x" * (1024 * 1024)
        file = Mock(spec=UploadFile)
        file.file = io.BytesIO(content)

        expected_hash = hashlib.sha256(content).hexdigest()
        result = validator.calculate_file_hash(file)

        assert result == expected_hash

    def test_hash_error_handling(self, validator):
        """Test hash calculation error handling"""
        file = Mock(spec=UploadFile)
        file.file = Mock()

        # Mock file.read to raise an exception
        file.file.read.side_effect = IOError("Read error")

        result = validator.calculate_file_hash(file)
        assert result == ""  # Should return empty string on error


class TestComprehensiveValidation:
    """Test comprehensive file upload validation"""

    @pytest.fixture
    def validator(self):
        return FileValidator()

    def test_validate_upload_success(self, validator):
        """Test successful upload validation"""
        file = Mock(spec=UploadFile)
        file.filename = "test.pdf"
        file.file = io.BytesIO(b"Clean PDF content")
        file.size = 100

        with patch("src.security.security.magic") as mock_magic:
            mock_magic.from_buffer.return_value = "application/pdf"

            result = validator.validate_upload(file)

            assert result["valid"] is True
            assert result["filename"] == "test.pdf"
            assert "hash" in result
            assert "validation_time" in result

    def test_validate_upload_no_file(self, validator):
        """Test validation with no file provided"""
        with pytest.raises(BusinessValidationError, match="未提供文件"):
            validator.validate_upload(None)

    def test_validate_upload_all_failures(self, validator):
        """Test that all validations are performed"""
        file = Mock(spec=UploadFile)
        file.filename = ""  # Invalid filename

        with pytest.raises(BusinessValidationError, match="文件名"):
            validator.validate_upload(file)
