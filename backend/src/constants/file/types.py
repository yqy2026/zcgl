"""
File type constants.

Provides standardized file type definitions and extensions
to avoid magic strings in file handling code.
"""

from typing import Final


class FileTypes:
    """
    File type constants.

    These constants define the supported file types, their MIME types,
    and file extensions used throughout the application.
    """

    # Common file extensions (with dot prefix)
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

    # File type identifiers (without dot)
    PDF_TYPE: Final[str] = "pdf"
    EXCEL_TYPE: Final[str] = "excel"
    CSV_TYPE: Final[str] = "csv"
    JSON_TYPE: Final[str] = "json"
    TEXT_TYPE: Final[str] = "text"
    IMAGE_TYPE: Final[str] = "image"
    WORD_TYPE: Final[str] = "word"
    ARCHIVE_TYPE: Final[str] = "archive"

    # MIME types
    MIME_PDF: Final[str] = "application/pdf"
    MIME_EXCEL: Final[str] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    MIME_EXCEL_LEGACY: Final[str] = "application/vnd.ms-excel"
    MIME_CSV: Final[str] = "text/csv"
    MIME_JSON: Final[str] = "application/json"
    MIME_TEXT: Final[str] = "text/plain"
    MIME_PNG: Final[str] = "image/png"
    MIME_JPEG: Final[str] = "image/jpeg"
    MIME_GIF: Final[str] = "image/gif"
    MIME_WORD: Final[str] = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    MIME_ZIP: Final[str] = "application/zip"

    # Allowed extensions for uploads
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
    def is_allowed(cls, filename: str, allowed_extensions: list[str] | None = None) -> bool:
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
        # Normalize extension (ensure it has a dot and is lowercase)
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


# Legacy compatibility aliases (deprecated, will be removed in v2.0)
PDF_FILE = FileTypes.PDF_TYPE
EXCEL_FILE = FileTypes.EXCEL_TYPE
CSV_FILE = FileTypes.CSV_TYPE

