"""
PDF session service.

Provides basic session management for PDF import sessions.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...crud.pdf_import_session import pdf_import_session_crud
from ...models.pdf_import_session import PDFImportSession, ProcessingStep, SessionStatus


class PDFSessionService:
    """Manage PDF import sessions in the database."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_session(self, session_id: str) -> PDFImportSession | None:
        return await pdf_import_session_crud.get_by_session_id_async(
            self.db, session_id=session_id
        )

    async def create_session(
        self,
        *,
        session_id: str,
        original_filename: str,
        file_size: int,
        file_path: str,
        content_type: str,
        organization_id: int | None,
        processing_options: dict[str, Any] | None = None,
    ) -> PDFImportSession:
        session = PDFImportSession()
        session.session_id = session_id
        session.original_filename = original_filename
        session.file_size = file_size
        session.file_path = file_path
        session.content_type = content_type
        session.organization_id = organization_id
        session.status = SessionStatus.UPLOADED
        session.current_step = ProcessingStep.FILE_UPLOAD
        session.progress_percentage = 0.0
        if processing_options is not None:
            session.processing_options = processing_options

        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session
