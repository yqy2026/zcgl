"""
File size validation constants.

Provides standardized file size limits to avoid magic numbers
in file upload/download handlers.
"""

from typing import Final


class FileSizeLimits:
    """
    File size limit constants.

    These constants define the maximum allowed file sizes for different
    file types and contexts. All values are in megabytes (MB) unless
    otherwise specified.
    """

    # Small files (< 1MB)
    SMALL_FILE_MAX_MB: Final[int] = 1
    AVATAR_MAX_MB: Final[int] = 2

    # Medium files (1-10MB)
    MEDIUM_FILE_MAX_MB: Final[int] = 10
    IMAGE_MAX_MB: Final[int] = 5

    # Large files (10-100MB)
    LARGE_FILE_MAX_MB: Final[int] = 50
    EXCEL_MAX_MB: Final[int] = 50
    PDF_MAX_MB: Final[int] = 100

    # Very large files (> 100MB)
    VERY_LARGE_FILE_MAX_MB: Final[int] = 500
    ARCHIVE_MAX_MB: Final[int] = 500

    # Specific file type limits
    CSV_MAX_MB: Final[int] = 10
    JSON_MAX_MB: Final[int] = 5
    TEXT_MAX_MB: Final[int] = 1

    # Minimum file size (in bytes)
    MIN_FILE_SIZE_BYTES: Final[int] = 1024  # 1KB
    MIN_FILE_SIZE_MB: Final[float] = 0.001  # 1KB in MB

    # File size limits in bytes for validation
    EXCEL_MAX_BYTES: Final[int] = EXCEL_MAX_MB * 1024 * 1024
    PDF_MAX_BYTES: Final[int] = PDF_MAX_MB * 1024 * 1024
    IMAGE_MAX_BYTES: Final[int] = IMAGE_MAX_MB * 1024 * 1024

    @classmethod
    def mb_to_bytes(cls, size_mb: int) -> int:
        """
        Convert megabytes to bytes.

        Args:
            size_mb: Size in megabytes.

        Returns:
            Size in bytes.
        """
        return size_mb * 1024 * 1024

    @classmethod
    def bytes_to_mb(cls, size_bytes: int) -> float:
        """
        Convert bytes to megabytes.

        Args:
            size_bytes: Size in bytes.

        Returns:
            Size in megabytes.
        """
        return size_bytes / (1024 * 1024)

    @classmethod
    def validate_file_size(cls, file_size_bytes: int, max_size_mb: int) -> bool:
        """
        Validate if a file size is within the allowed limit.

        Args:
            file_size_bytes: The file size in bytes.
            max_size_mb: The maximum allowed size in megabytes.

        Returns:
            True if the file size is acceptable, False otherwise.
        """
        max_size_bytes = cls.mb_to_bytes(max_size_mb)
        return cls.MIN_FILE_SIZE_BYTES <= file_size_bytes <= max_size_bytes


# Legacy compatibility aliases (deprecated, will be removed in v2.0)
MAX_EXCEL_SIZE = FileSizeLimits.EXCEL_MAX_MB
MAX_PDF_SIZE = FileSizeLimits.PDF_MAX_MB
MAX_IMAGE_SIZE = FileSizeLimits.IMAGE_MAX_MB

