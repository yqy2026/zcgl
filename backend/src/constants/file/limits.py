"""
File handling limits and constraints.

This module provides comprehensive file handling constants including
size limits, name length limits, and other file-related constraints.
"""

from typing import Final

from .types import FileTypes


class FileLimits:
    """
    File handling limit constants.

    These constants define limits for file operations including
    naming, sizing, and validation constraints.
    """

    # Filename length limits
    MAX_FILENAME_LENGTH: Final[int] = 255  # Standard filesystem limit
    MAX_FILEPATH_LENGTH: Final[int] = 1000  # Maximum path length

    # File size limits (from FileSizeLimits for convenience)
    MAX_FILE_SIZE_MB: Final[int] = 500
    MAX_IMAGE_SIZE_MB: Final[int] = 5
    MAX_EXCEL_SIZE_MB: Final[int] = 50
    MAX_PDF_SIZE_MB: Final[int] = 100
    MIN_FILE_SIZE_BYTES: Final[int] = 1024  # 1KB

    # Allowed file types
    ALLOWED_IMPORT_TYPES: Final[list[str]] = [
        FileTypes.EXCEL_TYPE,
        FileTypes.CSV_TYPE,
    ]

    ALLOWED_EXPORT_TYPES: Final[list[str]] = [
        FileTypes.EXCEL_TYPE,
        FileTypes.CSV_TYPE,
        FileTypes.PDF_TYPE,
        FileTypes.JSON_TYPE,
    ]

    # File upload limits by context
    AVATAR_UPLOAD_MAX_MB: Final[int] = 2
    DOCUMENT_UPLOAD_MAX_MB: Final[int] = 100
    SPREADSHEET_UPLOAD_MAX_MB: Final[int] = 50
    ARCHIVE_UPLOAD_MAX_MB: Final[int] = 500

    # Batch operation limits
    MAX_FILES_PER_BATCH: Final[int] = 100
    MAX_TOTAL_BATCH_SIZE_MB: Final[int] = 500

    # File validation rules
    ALLOWED_SPECIAL_CHARS_IN_FILENAME: Final[str] = "._-"
    FORBIDDEN_CHARS_IN_FILENAME: Final[str] = '/\\?%*:|"<>'

    @classmethod
    def validate_filename(cls, filename: str) -> tuple[bool, str | None]:
        """
        Validate a filename.

        Args:
            filename: The filename to validate.

        Returns:
            A tuple of (is_valid, error_message). If valid, error_message is None.
        """
        if not filename:
            return False, "Filename cannot be empty"

        if len(filename) > cls.MAX_FILENAME_LENGTH:
            return False, f"Filename too long (max {cls.MAX_FILENAME_LENGTH} characters)"

        # Check for forbidden characters
        for char in filename:
            if char in cls.FORBIDDEN_CHARS_IN_FILENAME:
                return False, f"Filename contains forbidden character: {char}"

        # Check extension
        if "." not in filename:
            return False, "Filename must have an extension"

        return True, None

    @classmethod
    def get_upload_limit_for_type(cls, file_type: str) -> int:
        """
        Get the upload size limit for a specific file type.

        Args:
            file_type: The file type identifier.

        Returns:
            The maximum file size in megabytes.

        Raises:
            ValueError: If the file type is not recognized.
        """
        limits = {
            FileTypes.PDF_TYPE: cls.MAX_PDF_SIZE_MB,
            FileTypes.EXCEL_TYPE: cls.MAX_EXCEL_SIZE_MB,
            FileTypes.IMAGE_TYPE: cls.MAX_IMAGE_SIZE_MB,
        }

        if file_type not in limits:
            raise ValueError(f"Unknown file type: {file_type}")
        return limits[file_type]


# Legacy compatibility aliases (deprecated, will be removed in v2.0)
MAX_FILENAME = FileLimits.MAX_FILENAME_LENGTH
MAX_FILEPATH = FileLimits.MAX_FILEPATH_LENGTH

