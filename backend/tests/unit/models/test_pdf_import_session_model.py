"""
PDF import session model metadata guards.

The Alembic baseline creates plain string columns for pdf import session status/step
fields. ORM metadata must therefore keep native PostgreSQL enums disabled and bind
the persisted labels to enum `.value` strings, otherwise async runtime queries will
look for missing PostgreSQL enum types such as `sessionstatus`.
"""

from __future__ import annotations

import pytest

from src.models.pdf_import_session import (
    PDFImportSession,
    ProcessingStep,
    SessionLog,
    SessionStatus,
)

pytestmark = pytest.mark.unit


class TestPdfImportSessionEnumStorageStrategy:
    def _enum_type(self, model_cls: type, column_name: str):
        return model_cls.__table__.c[column_name].type

    def test_status_should_use_non_native_value_labels(self) -> None:
        enum_type = self._enum_type(PDFImportSession, "status")
        assert enum_type.native_enum is False
        assert list(enum_type.enums) == [member.value for member in SessionStatus]

    def test_current_step_should_use_non_native_value_labels(self) -> None:
        enum_type = self._enum_type(PDFImportSession, "current_step")
        assert enum_type.native_enum is False
        assert list(enum_type.enums) == [member.value for member in ProcessingStep]

    def test_session_log_step_should_use_non_native_value_labels(self) -> None:
        enum_type = self._enum_type(SessionLog, "step")
        assert enum_type.native_enum is False
        assert list(enum_type.enums) == [member.value for member in ProcessingStep]
