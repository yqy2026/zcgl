"""
Storage and file handling constants.

Consolidated from:
- file/types.py
- file/limits.py
- database/pool.py

This module provides all storage-related constants including
file types, file limits, and database pool configuration.
"""

from typing import Final


class FileTypes:
    """
    File type constants.

    These constants define the supported file types, their MIME types,
    and file extensions used throughout the application.
    """

    PDF: Final[str] = ".pdf"
    EXCEL: Final[str] = ".xlsx"
    EXCEL_LEGACY: Final[str] = ".xls"
    CSV: Final[str] = ".csv"
    JSON: Final[str] = ".json"
    TEXT: Final[str] = ".txt"
    IMAGE_PNG: Final[str] = ".png"
    IMAGE_JPG: Final[str] = ".jpg"
    IMAGE_JPEG: Final[str] = ".jpeg"
    IMAGE_GIF: Final[str] = ".gif"
    WORD: Final[str] = ".docx"
    WORD_LEGACY: Final[str] = ".doc"
    ARCHIVE_ZIP: Final[str] = ".zip"
    ARCHIVE_RAR: Final[str] = ".rar"
    PDF_TYPE: Final[str] = "pdf"
    EXCEL_TYPE: Final[str] = "excel"
    CSV_TYPE: Final[str] = "csv"
    JSON_TYPE: Final[str] = "json"
    TEXT_TYPE: Final[str] = "text"
    IMAGE_TYPE: Final[str] = "image"
    WORD_TYPE: Final[str] = "word"
    ARCHIVE_TYPE: Final[str] = "archive"
    MIME_PDF: Final[str] = "application/pdf"
    MIME_EXCEL: Final[str] = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    MIME_EXCEL_LEGACY: Final[str] = "application/vnd.ms-excel"
    MIME_CSV: Final[str] = "text/csv"
    MIME_JSON: Final[str] = "application/json"
    MIME_TEXT: Final[str] = "text/plain"
    MIME_PNG: Final[str] = "image/png"
    MIME_JPEG: Final[str] = "image/jpeg"
    MIME_GIF: Final[str] = "image/gif"
    MIME_WORD: Final[str] = (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    MIME_ZIP: Final[str] = "application/zip"
    ALLOWED_DOCUMENT_EXTENSIONS: Final[list[str]] = [
        PDF,
        EXCEL,
        EXCEL_LEGACY,
        CSV,
        WORD,
        WORD_LEGACY,
        TEXT,
    ]
    ALLOWED_IMAGE_EXTENSIONS: Final[list[str]] = [
        IMAGE_PNG,
        IMAGE_JPG,
        IMAGE_JPEG,
        IMAGE_GIF,
    ]
    ALLOWED_ARCHIVE_EXTENSIONS: Final[list[str]] = [
        ARCHIVE_ZIP,
        ARCHIVE_RAR,
    ]

    @classmethod
    def get_extension(cls, file_type: str) -> str:
        """
        Get the file extension for a given file type.

        Args:
            file_type: The file type identifier.

        Returns:
            The file extension with dot prefix.

        Raises:
            ValueError: If the file type is not recognized.
        """
        extensions = {
            cls.PDF_TYPE: cls.PDF,
            cls.EXCEL_TYPE: cls.EXCEL,
            cls.CSV_TYPE: cls.CSV,
            cls.JSON_TYPE: cls.JSON,
            cls.TEXT_TYPE: cls.TEXT,
        }
        if file_type not in extensions:
            raise ValueError(f"Unknown file type: {file_type}")
        return extensions[file_type]

    @classmethod
    def is_allowed(
        cls, filename: str, allowed_extensions: list[str] | None = None
    ) -> bool:
        """
        Check if a file extension is allowed.

        Args:
            filename: The name of the file.
            allowed_extensions: List of allowed extensions (with dots). If None, uses default document extensions.

        Returns:
            True if the file extension is allowed, False otherwise.
        """
        if not filename:
            return False

        import os

        _, ext = os.path.splitext(filename.lower())
        ext = ext.lower()

        if allowed_extensions is None:
            allowed_extensions = cls.ALLOWED_DOCUMENT_EXTENSIONS

        return ext in allowed_extensions

    @classmethod
    def get_mime_type(cls, extension: str) -> str:
        """
        Get the MIME type for a given file extension.

        Args:
            extension: The file extension (with or without dot).

        Returns:
            The MIME type string.

        Raises:
            ValueError: If the extension is not recognized.
        """
        if not extension.startswith("."):
            extension = f".{extension}"
        extension = extension.lower()

        mime_types = {
            cls.PDF: cls.MIME_PDF,
            cls.EXCEL: cls.MIME_EXCEL,
            cls.EXCEL_LEGACY: cls.MIME_EXCEL_LEGACY,
            cls.CSV: cls.MIME_CSV,
            cls.JSON: cls.MIME_JSON,
            cls.TEXT: cls.MIME_TEXT,
            cls.IMAGE_PNG: cls.MIME_PNG,
            cls.IMAGE_JPG: cls.MIME_JPEG,
            cls.IMAGE_JPEG: cls.MIME_JPEG,
            cls.IMAGE_GIF: cls.MIME_GIF,
        }

        if extension not in mime_types:
            raise ValueError(f"Unknown file extension: {extension}")
        return mime_types[extension]


class FileLimits:
    """
    File handling limit constants.

    These constants define limits for file operations including
    naming, sizing, and validation constraints.
    """

    MAX_FILENAME_LENGTH: Final[int] = 255
    MAX_FILEPATH_LENGTH: Final[int] = 1000
    MAX_FILE_SIZE_MB: Final[int] = 500
    MAX_IMAGE_SIZE_MB: Final[int] = 5
    MAX_EXCEL_SIZE_MB: Final[int] = 50
    MAX_PDF_SIZE_MB: Final[int] = 100
    MIN_FILE_SIZE_BYTES: Final[int] = 1024
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
    AVATAR_UPLOAD_MAX_MB: Final[int] = 2
    DOCUMENT_UPLOAD_MAX_MB: Final[int] = 100
    SPREADSHEET_UPLOAD_MAX_MB: Final[int] = 50
    ARCHIVE_UPLOAD_MAX_MB: Final[int] = 500
    MAX_FILES_PER_BATCH: Final[int] = 100
    MAX_TOTAL_BATCH_SIZE_MB: Final[int] = 500
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
            return (
                False,
                f"Filename too long (max {cls.MAX_FILENAME_LENGTH} characters)",
            )

        for char in filename:
            if char in cls.FORBIDDEN_CHARS_IN_FILENAME:
                return False, f"Filename contains forbidden character: {char}"

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


class DatabasePoolConfig:
    """
    Database connection pool settings.

    These constants control the behavior of SQLAlchemy's connection pool
    for both SQLite (development) and PostgreSQL (production).
    """

    SIZE_DEFAULT: Final[int] = 20
    MAX_OVERFLOW: Final[int] = 30
    TIMEOUT_SECONDS: Final[int] = 30
    RECYCLE_SECONDS: Final[int] = 3600
    PRE_PING_ENABLED: Final[bool] = True
    ECHO_ENABLED: Final[bool] = False
    SQLITE_TIMEOUT_SECONDS: Final[int] = 20
    SQLITE_CACHE_SIZE: Final[int] = 10000
    SQLITE_WAL_AUTOCHECKPOINT: Final[int] = 1000
    SLOW_QUERY_THRESHOLD_MS: Final[float] = 100.0
    ENABLE_QUERY_LOGGING: Final[bool] = False
    QUERY_HISTORY_QUEUE_SIZE: Final[int] = 1000

    @classmethod
    def validate(cls) -> None:
        """
        Validate pool configuration consistency.

        Raises:
            ValueError: If configuration values are inconsistent.
        """
        if cls.MAX_OVERFLOW < 0:
            raise ValueError("MAX_OVERFLOW must be non-negative")
        if cls.SIZE_DEFAULT <= 0:
            raise ValueError("SIZE_DEFAULT must be positive")
        if cls.TIMEOUT_SECONDS <= 0:
            raise ValueError("TIMEOUT_SECONDS must be positive")


PDF_FILE = FileTypes.PDF_TYPE
EXCEL_FILE = FileTypes.EXCEL_TYPE
CSV_FILE = FileTypes.CSV_TYPE
MAX_FILENAME = FileLimits.MAX_FILENAME_LENGTH
MAX_FILEPATH = FileLimits.MAX_FILEPATH_LENGTH
POOL_SIZE = DatabasePoolConfig.SIZE_DEFAULT
MAX_OVERFLOW = DatabasePoolConfig.MAX_OVERFLOW
POOL_TIMEOUT = DatabasePoolConfig.TIMEOUT_SECONDS

__all__ = [
    "FileTypes",
    "FileLimits",
    "DatabasePoolConfig",
]
