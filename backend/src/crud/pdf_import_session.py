from collections.abc import Iterable

from sqlalchemy.orm import Session

from ..models.pdf_import_session import PDFImportSession


class PDFImportSessionCRUD:
    """PDF 导入会话 CRUD 操作"""

    def get_by_session_id(
        self, db: Session, session_id: str
    ) -> PDFImportSession | None:
        """根据会话ID获取导入会话"""
        return (
            db.query(PDFImportSession)
            .filter(PDFImportSession.session_id == session_id)
            .first()
        )

    def get_session_map(
        self, db: Session, session_ids: Iterable[str]
    ) -> dict[str, PDFImportSession]:
        """批量获取会话ID到会话对象映射"""
        session_id_list = [session_id for session_id in session_ids if session_id]
        if not session_id_list:
            return {}
        sessions = (
            db.query(PDFImportSession)
            .filter(PDFImportSession.session_id.in_(session_id_list))
            .all()
        )
        return {session.session_id: session for session in sessions}
