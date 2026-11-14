"""Archive persistence; callers authorize and lock the business target."""

from uuid import uuid4

from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from sqlalchemy.sql.elements import ColumnElement

from ..models.archive_document import ArchiveDocument
from ..models.attachment import Attachment
from ..models.property_certificate import PropertyCertificate


class ArchiveDocumentRepository:
    async def target_rows(
        self, db: AsyncSession, *, target_type: str, target_id: str, document_type: str
    ) -> list[tuple[ArchiveDocument, Attachment]]:
        rows = (
            await db.execute(
                select(ArchiveDocument, Attachment)
                .join(Attachment, Attachment.id == ArchiveDocument.attachment_id)
                .where(
                    ArchiveDocument.target_type == target_type,
                    ArchiveDocument.target_id == target_id,
                    ArchiveDocument.document_type == document_type,
                )
            )
        ).all()
        return [(d, a) for d, a in rows]

    async def register_target(
        self,
        db: AsyncSession,
        *,
        target_type: str,
        target_id: str,
        document_type: str,
        attachment: Attachment,
        replaces_document_id: str | None = None,
    ) -> ArchiveDocument:
        rows = await self.target_rows(
            db,
            target_type=target_type,
            target_id=target_id,
            document_type=document_type,
        )
        document = ArchiveDocument(  # type: ignore[call-arg]
            id=str(uuid4()),
            target_type=target_type,
            target_id=target_id,
            document_type=document_type,
            attachment_id=attachment.id,
            document_version=max((d.document_version for d, _ in rows), default=0) + 1,
            replaces_document_id=replaces_document_id,
            uploaded_by=attachment.created_by,
            uploaded_at=attachment.created_at,
        )
        db.add(document)
        await db.flush()
        return document

    async def get_document(
        self, db: AsyncSession, *, document_id: str
    ) -> ArchiveDocument | None:
        return (
            await db.execute(
                select(ArchiveDocument).where(ArchiveDocument.id == document_id)
            )
        ).scalar_one_or_none()

    async def lock_certificate(self, db: AsyncSession, *, certificate_id: str) -> bool:
        return (
            await db.execute(
                select(PropertyCertificate.id)
                .where(PropertyCertificate.id == certificate_id)
                .with_for_update()
            )
        ).scalar_one_or_none() is not None

    @staticmethod
    def _certificate(certificate_id: str) -> tuple[ColumnElement[bool], ...]:
        return (
            ArchiveDocument.target_type == "property_certificate",
            ArchiveDocument.target_id == certificate_id,
            ArchiveDocument.document_type == "property_certificate",
        )

    async def list_for_certificate(
        self, db: AsyncSession, *, certificate_id: str, include_history: bool = False
    ) -> list[tuple[ArchiveDocument, Attachment]]:
        statement = (
            select(ArchiveDocument, Attachment)
            .join(Attachment, Attachment.id == ArchiveDocument.attachment_id)
            .where(*self._certificate(certificate_id))
        )
        if not include_history:
            successor = aliased(ArchiveDocument)
            statement = statement.where(
                ~exists(
                    select(successor.id).where(
                        successor.replaces_document_id == ArchiveDocument.id
                    )
                )
            )
        rows = (
            await db.execute(statement.order_by(ArchiveDocument.document_version))
        ).all()
        return [(document, attachment) for document, attachment in rows]

    async def get_for_attachment(
        self, db: AsyncSession, *, certificate_id: str, attachment_id: str
    ) -> ArchiveDocument | None:
        return (
            await db.execute(
                select(ArchiveDocument).where(
                    *self._certificate(certificate_id),
                    ArchiveDocument.attachment_id == attachment_id,
                )
            )
        ).scalar_one_or_none()

    async def get_successor(
        self, db: AsyncSession, *, document_id: str
    ) -> ArchiveDocument | None:
        return (
            await db.execute(
                select(ArchiveDocument).where(
                    ArchiveDocument.replaces_document_id == document_id
                )
            )
        ).scalar_one_or_none()

    async def find_by_hash(
        self, db: AsyncSession, *, certificate_id: str, content_hash: str
    ) -> ArchiveDocument | None:
        return (
            await db.execute(
                select(ArchiveDocument)
                .join(Attachment, Attachment.id == ArchiveDocument.attachment_id)
                .where(
                    *self._certificate(certificate_id),
                    Attachment.file_hash == content_hash,
                )
                .order_by(ArchiveDocument.document_version)
                .limit(1)
            )
        ).scalar_one_or_none()

    async def has_for_certificate(
        self, db: AsyncSession, *, certificate_id: str
    ) -> bool:
        return bool(
            (
                await db.execute(
                    select(exists().where(*self._certificate(certificate_id)))
                )
            ).scalar_one()
        )

    async def register(
        self,
        db: AsyncSession,
        *,
        certificate_id: str,
        attachment: Attachment,
        replaces_document_id: str | None = None,
    ) -> ArchiveDocument:
        version = (
            await db.execute(
                select(
                    func.coalesce(func.max(ArchiveDocument.document_version), 0)
                ).where(*self._certificate(certificate_id))
            )
        ).scalar_one()
        document = ArchiveDocument(  # type: ignore[call-arg]
            id=str(uuid4()),
            document_type="property_certificate",
            target_type="property_certificate",
            target_id=certificate_id,
            attachment_id=attachment.id,
            document_version=version + 1,
            replaces_document_id=replaces_document_id,
            uploaded_by=attachment.created_by,
            uploaded_at=attachment.created_at,
        )
        db.add(document)
        await db.flush()
        return document


archive_document_repository = ArchiveDocumentRepository()
