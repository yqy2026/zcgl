"""Certificate revisions survive independent sessions and concurrent replacement."""

import asyncio
import struct
import zlib
from contextlib import asynccontextmanager
from io import BytesIO
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from starlette.datastructures import Headers, UploadFile

from src.core.exception_handler import BaseBusinessError
from src.crud.archive_document import archive_document_repository
from src.models.archive_document import ArchiveDocument
from src.models.attachment import Attachment
from src.models.operation_log import OperationLog
from src.models.property_certificate import PropertyCertificate
from src.services.property_certificate.attachment_service import (
    PropertyCertificateAttachmentService,
)
from src.services.property_certificate.service import PropertyCertificateService

pytestmark = pytest.mark.e2e


def png(value: int) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data))
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(bytes([0, value, value, value])))
        + chunk(b"IEND", b"")
    )


def upload(value: int) -> UploadFile:
    return UploadFile(
        file=BytesIO(png(value)),
        filename=f"certificate-{value}.png",
        headers=Headers({"content-type": "image/png"}),
    )


@asynccontextmanager
async def facts(database_url: str, root: Path):
    engine = create_async_engine(
        database_url.replace("postgresql+psycopg://", "postgresql+asyncpg://", 1),
        poolclass=NullPool,
    )
    maker = async_sessionmaker(engine, expire_on_commit=False)
    certificate_id = str(uuid4())
    service = PropertyCertificateAttachmentService()
    service.uploads_root = root
    try:
        async with maker() as db:
            db.add(
                PropertyCertificate(
                    id=certificate_id,
                    certificate_number=f"ARCHIVE-{uuid4().hex}",
                    certificate_type="real_estate",
                )
            )
            await db.commit()
        yield maker, service, certificate_id
    finally:
        async with maker() as db:
            # Delete only this test's generated records, descendants first.
            documents = (
                (
                    await db.execute(
                        select(ArchiveDocument.id)
                        .where(ArchiveDocument.target_id == certificate_id)
                        .order_by(ArchiveDocument.document_version.desc())
                    )
                )
                .scalars()
                .all()
            )
            for document_id in documents:
                await db.execute(
                    delete(ArchiveDocument).where(ArchiveDocument.id == document_id)
                )
            await db.execute(
                delete(Attachment).where(
                    Attachment.owner_type == "property_certificate",
                    Attachment.owner_id == certificate_id,
                )
            )
            await db.execute(
                delete(OperationLog).where(OperationLog.resource_id == certificate_id)
            )
            await db.execute(
                delete(PropertyCertificate).where(
                    PropertyCertificate.id == certificate_id
                )
            )
            await db.commit()
        await engine.dispose()


def test_revision_preserves_history_and_blocks_destructive_paths(
    test_database_url: str, tmp_path: Path
) -> None:
    async def run() -> None:
        async with facts(test_database_url, tmp_path) as (
            maker,
            service,
            certificate_id,
        ):
            async with maker() as db:
                original = await service.append(
                    db,
                    certificate_id=certificate_id,
                    file=upload(0),
                    user_id="archive-test",
                )
            async with maker() as db:
                replacement = await service.replace(
                    db,
                    certificate_id=certificate_id,
                    attachment_id=original.attachment.id,
                    file=upload(1),
                    user_id="archive-test",
                )
            async with maker() as reader:
                current = await service.list(reader, certificate_id=certificate_id)
                history = await service.list(
                    reader, certificate_id=certificate_id, include_history=True
                )
                assert [item.attachment.id for item in current] == [
                    replacement.attachment.id
                ]
                assert [item.document.document_version for item in history] == [1, 2]
                assert [item.is_current for item in history] == [False, True]
                assert replacement.document.replaces_document_id == original.document.id
                result = await service.prepare_download(
                    reader,
                    certificate_id=certificate_id,
                    attachment_id=original.attachment.id,
                    user_id="archive-test",
                )
                assert result.path.read_bytes() == png(0)
            assert (tmp_path / replacement.attachment.storage_key).read_bytes() == png(
                1
            )
            for attachment_id in (original.attachment.id, replacement.attachment.id):
                async with maker() as db:
                    with pytest.raises(BaseBusinessError) as error:
                        await service.delete(
                            db,
                            certificate_id=certificate_id,
                            attachment_id=attachment_id,
                        )
                    assert error.value.code == "ARCHIVE_HISTORY_PROTECTED"
            async with maker() as db:
                with pytest.raises(BaseBusinessError) as error:
                    await PropertyCertificateService(db).delete_certificate(
                        certificate_id
                    )
                assert error.value.code == "ARCHIVE_HISTORY_PROTECTED"
            async with maker() as db:
                with pytest.raises(IntegrityError):
                    await db.execute(
                        delete(Attachment).where(
                            Attachment.id == original.attachment.id
                        )
                    )
                await db.rollback()
            async with maker() as db:
                with pytest.raises(BaseBusinessError) as error:
                    await service.append(
                        db,
                        certificate_id=certificate_id,
                        file=upload(0),
                        user_id="archive-test",
                    )
                assert error.value.code == "ARCHIVE_DUPLICATE_CONTENT"

    asyncio.run(run())


def test_concurrent_replacements_have_one_successor(
    test_database_url: str, tmp_path: Path
) -> None:
    async def run() -> None:
        async with facts(test_database_url, tmp_path) as (
            maker,
            service,
            certificate_id,
        ):
            async with maker() as db:
                original = await service.append(
                    db,
                    certificate_id=certificate_id,
                    file=upload(0),
                    user_id="archive-test",
                )

            async def replace(value: int):
                async with maker() as db:
                    return await service.replace(
                        db,
                        certificate_id=certificate_id,
                        attachment_id=original.attachment.id,
                        file=upload(value),
                        user_id="archive-test",
                    )

            results = await asyncio.gather(
                replace(1), replace(2), return_exceptions=True
            )
            errors = [result for result in results if isinstance(result, BaseException)]
            assert len(errors) == 1
            assert isinstance(errors[0], BaseBusinessError)
            assert errors[0].code == "ARCHIVE_VERSION_STALE"
            async with maker() as reader:
                history = await service.list(
                    reader, certificate_id=certificate_id, include_history=True
                )
                assert len(history) == 2
                assert [item.document.document_version for item in history] == [1, 2]
                assert sum(item.is_current for item in history) == 1
            assert len(list((tmp_path / "files").rglob("*.png"))) == 2

    asyncio.run(run())


def test_failed_archive_registration_rolls_back_only_new_file(
    test_database_url: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def run() -> None:
        async with facts(test_database_url, tmp_path) as (
            maker,
            service,
            certificate_id,
        ):
            async with maker() as db:
                original = await service.append(
                    db,
                    certificate_id=certificate_id,
                    file=upload(0),
                    user_id="archive-test",
                )
            with monkeypatch.context() as patch:
                patch.setattr(
                    archive_document_repository,
                    "register",
                    AsyncMock(side_effect=RuntimeError("registration failed")),
                )
                async with maker() as db:
                    with pytest.raises(RuntimeError, match="registration failed"):
                        await service.replace(
                            db,
                            certificate_id=certificate_id,
                            attachment_id=original.attachment.id,
                            file=upload(1),
                            user_id="archive-test",
                        )
            async with maker() as reader:
                history = await service.list(
                    reader, certificate_id=certificate_id, include_history=True
                )
                assert [item.attachment.id for item in history] == [
                    original.attachment.id
                ]
                attachments = (
                    (
                        await reader.execute(
                            select(Attachment).where(
                                Attachment.owner_id == certificate_id
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                assert len(attachments) == 1
            files = list((tmp_path / "files").rglob("*.png"))
            assert len(files) == 1
            assert files[0].read_bytes() == png(0)

    asyncio.run(run())
