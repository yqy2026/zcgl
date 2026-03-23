from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.pdf_import_session import PDFImportSession
from .query_builder import PartyFilter, QueryBuilder


class PDFImportSessionCRUD:
    """PDF 导入会话 CRUD 操作"""

    def __init__(self) -> None:
        self.query_builder = QueryBuilder(PDFImportSession)

    async def get_by_session_id_async(
        self,
        db: AsyncSession,
        session_id: str,
        party_filter: PartyFilter | None = None,
    ) -> PDFImportSession | None:
        """根据会话ID获取导入会话（异步）"""
        stmt = select(PDFImportSession).where(PDFImportSession.session_id == session_id)
        if party_filter is not None:
            stmt = self.query_builder.apply_party_filter(stmt, party_filter)
        return (await db.execute(stmt)).scalars().first()

    async def get_session_map_async(
        self,
        db: AsyncSession,
        session_ids: Iterable[str],
        party_filter: PartyFilter | None = None,
    ) -> dict[str, PDFImportSession]:
        """批量获取会话ID到会话对象映射（异步）"""
        session_id_list = [session_id for session_id in session_ids if session_id]
        if not session_id_list:
            return {}
        stmt = select(PDFImportSession).where(
            PDFImportSession.session_id.in_(session_id_list)
        )
        if party_filter is not None:
            stmt = self.query_builder.apply_party_filter(stmt, party_filter)
        sessions = list((await db.execute(stmt)).scalars().all())
        return {session.session_id: session for session in sessions}


pdf_import_session_crud = PDFImportSessionCRUD()
