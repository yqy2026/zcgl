"""Property-certificate extraction sessions with explicit human review."""
# mypy: disable-error-code=override

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.crud.asset import asset_crud
from src.crud.attachment import attachment_crud
from src.crud.property_certificate import property_certificate_crud
from src.models.associations import property_cert_assets
from src.models.attachment import Attachment
from src.models.property_certificate import CertificateType
from src.schemas.property_certificate import PropertyCertificateCreate
from src.services.file_upload import UploadPurpose
from src.services.file_upload.staged_files import (
    StagedFile,
    StagedFileService,
    StoredFile,
)
from src.services.party import party_service

from .candidate_review import (
    CandidateReviewError,
    CandidateReviewService,
    CandidateValue,
)
from .contract_extraction_workflow import ContractExtractionWorkflow
from .deepseek_text_enrichment import DeepSeekTextEnricher
from .extraction_sessions import ExtractionSessionRepository
from .page_text_pipeline import OrderedPageTextPipeline, PageText


class PropertyCertificateConflictError(ValueError):
    """The reviewed certificate number already belongs to a record."""


class PropertyCertificateExtractionWorkflow(ContractExtractionWorkflow):
    """Create or append only reviewed property-certificate data and attachments."""

    def __init__(
        self,
        *,
        repository: ExtractionSessionRepository,
        pipeline: OrderedPageTextPipeline,
        reviewer: CandidateReviewService,
        enricher: DeepSeekTextEnricher,
        lifecycle: StagedFileService,
    ) -> None:
        super().__init__(
            repository=repository,
            pipeline=pipeline,
            reviewer=reviewer,
            enricher=enricher,
            lifecycle=lifecycle,
        )

    def create(
        self, *, staged: StagedFile, context: Mapping[str, str]
    ) -> dict[str, Any]:
        session_id = uuid4().hex
        try:
            pages = self._extract_pages(staged)
            review = self._reviewer.build_property_certificate_candidates(pages)
            enrichment = self._enricher.enrich(
                "property_certificate", pages, session_id=session_id
            )
            if enrichment.status == "success":
                review = self._reviewer.merge_property_certificate_candidates(
                    review, enrichment.candidates
                )
            errors = list(review.rule_errors)
            errors.extend(page.error.code for page in pages if page.error is not None)
            if enrichment.status == "failed":
                errors.append("enrichment_failed")
            session = self._repository.create(
                session_id=session_id,
                target_type="property_certificate",
                staged_file_key=staged.storage_key,
                candidates=self._serialize_review(review),
                context={**self._session_context(staged), **dict(context)},
                errors=sorted(set(errors)),
            )
        except Exception:
            self._lifecycle.discard_staged(staged)
            raise
        return self.public_session(session)

    async def create_existing(
        self,
        *,
        db: AsyncSession,
        asset_id: str,
        certificate_id: str,
        attachment_id: str,
    ) -> dict[str, Any]:
        attachment = await self._assert_existing_chain(
            db=db,
            asset_id=asset_id,
            certificate_id=certificate_id,
            attachment_id=attachment_id,
        )
        source_path = (self._lifecycle.storage_root / attachment.storage_key).resolve()
        if not source_path.is_file():
            raise CandidateReviewError("attachment_file_not_found")
        session_id = uuid4().hex
        pages = self._extract_existing_attachment_pages(
            source_path, attachment.file_type
        )
        review = self._reviewer.build_property_certificate_candidates(pages)
        enrichment = self._enricher.enrich(
            "property_certificate", pages, session_id=session_id
        )
        if enrichment.status == "success":
            review = self._reviewer.merge_property_certificate_candidates(
                review, enrichment.candidates
            )
        errors = list(review.rule_errors)
        errors.extend(page.error.code for page in pages if page.error is not None)
        if enrichment.status == "failed":
            errors.append("enrichment_failed")
        session = self._repository.create(
            session_id=session_id,
            target_type="property_certificate",
            staged_file_key=attachment.storage_key,
            candidates=self._serialize_review(review),
            context={
                "mode": "existing",
                "source_kind": "existing_attachment",
                "asset_id": asset_id,
                "certificate_id": certificate_id,
                "existing_attachment_id": attachment_id,
            },
            errors=sorted(set(errors)),
        )
        return self.public_session(session)

    def cancel(self, session_id: str) -> None:
        session = self._repository.get(session_id)
        if session is None:
            from .extraction_sessions import ExtractionSessionStateError

            raise ExtractionSessionStateError("session_not_found")
        staged_file_key = self._repository.delete_terminal(session_id, "cancelled")
        context = self._require_mapping(session, "context")
        if context.get("source_kind") != "existing_attachment":
            self._lifecycle.discard_path(self._staged_path(staged_file_key))

    async def confirm(
        self,
        *,
        session_id: str,
        actions: Sequence[Mapping[str, str | None]],
        certificate_type: str,
        holder_party_ids: list[str],
        attach_staged: bool,
        db: AsyncSession,
        current_user_id: str,
        link_existing_certificate_id: str | None = None,
    ) -> str:
        session = self._repository.transition(
            session_id, "ready_for_review", "confirming"
        )
        stored = None
        context: Mapping[str, str] | None = None
        try:
            review = self._deserialize_review(session["candidates"])
            reviewed = self._reviewer.apply_actions(
                review, self._deserialize_actions(list(actions))
            )
            context = self._require_mapping(session, "context")
            mode = context.get("mode")
            if mode == "new" and link_existing_certificate_id is None:
                certificate_id, stored = await self._confirm_new(
                    db=db,
                    context=context,
                    values=reviewed.values,
                    certificate_type=certificate_type,
                    holder_party_ids=holder_party_ids,
                    staged=self._staged_from_session(session, context),
                    current_user_id=current_user_id,
                )
            elif mode == "new":
                assert link_existing_certificate_id is not None
                certificate_id, stored = await self._confirm_conflict_link(
                    db=db,
                    context=context,
                    values=reviewed.values,
                    certificate_id=link_existing_certificate_id,
                    staged=self._staged_from_session(session, context),
                    attach_staged=attach_staged,
                    current_user_id=current_user_id,
                )
            elif mode == "existing":
                certificate_id = await self._confirm_existing_reference(
                    db=db,
                    context=context,
                )
            else:
                raise CandidateReviewError("invalid_property_certificate_mode")
            await db.commit()
        except (CandidateReviewError, PropertyCertificateConflictError):
            await db.rollback()
            self._repository.transition(session_id, "confirming", "ready_for_review")
            raise
        except Exception as operation_error:
            cleanup_error: BaseException | None = None
            if stored is not None:
                try:
                    self._lifecycle.compensate_promotion(stored)
                except BaseException as exc:
                    cleanup_error = exc
            try:
                await db.rollback()
            finally:
                self._repository.transition(
                    session_id, "confirming", "ready_for_review"
                )
            if cleanup_error is not None:
                raise cleanup_error from operation_error
            raise

        staged_file_key = self._repository.delete_after_status(session_id, "confirming")
        assert context is not None
        if stored is None and context.get("source_kind") != "existing_attachment":
            self._lifecycle.discard_path(self._staged_path(staged_file_key))
        return certificate_id

    async def _confirm_new(
        self,
        *,
        db: AsyncSession,
        context: Mapping[str, str],
        values: Mapping[str, CandidateValue | None],
        certificate_type: str,
        holder_party_ids: list[str],
        staged: StagedFile,
        current_user_id: str,
    ) -> tuple[str, StoredFile]:
        certificate_number = self._string_value(values, "certificate_number").strip()
        try:
            parsed_certificate_type = CertificateType(certificate_type)
        except ValueError as exc:
            raise CandidateReviewError("invalid_certificate_type") from exc
        if (
            parsed_certificate_type is not CertificateType.OTHER
            and self._optional_string(values, "property_address") is None
        ):
            raise CandidateReviewError("property_address_required")
        asset_id = context.get("asset_id", "").strip()
        if asset_id == "":
            raise CandidateReviewError("asset_context_required")
        normalized_holder_party_ids = self._normalize_ids(holder_party_ids)
        if len(normalized_holder_party_ids) == 0:
            raise CandidateReviewError("holder_party_ids_required")
        existing = await property_certificate_crud.get_by_certificate_number_async(
            db, certificate_number
        )
        if existing is not None:
            raise PropertyCertificateConflictError("certificate_number_conflict")
        assets = await asset_crud.get_multi_by_ids_async(
            db, ids=[asset_id], include_deleted=False
        )
        if {str(asset.id) for asset in assets} != {asset_id}:
            raise CandidateReviewError("asset_not_found")
        await party_service.assert_parties_approved(
            db,
            party_ids=normalized_holder_party_ids,
            operation="property_certificate:create",
        )
        certificate = await property_certificate_crud.create_with_owners_async(
            db,
            obj_in=PropertyCertificateCreate.model_validate(
                self._certificate_payload(
                    certificate_number=certificate_number,
                    certificate_type=parsed_certificate_type,
                    values=values,
                    holder_party_ids=normalized_holder_party_ids,
                    asset_id=asset_id,
                )
            ),
            owner_ids=normalized_holder_party_ids,
            asset_ids=[asset_id],
            created_by=current_user_id,
            commit=False,
        )
        stored = self._lifecycle.promote(
            staged,
            owner_type="property_certificate",
            owner_id=str(certificate.id),
        )
        await attachment_crud.create(
            db,
            data={
                "owner_type": "property_certificate",
                "owner_id": str(certificate.id),
                "file_name": staged.original_filename,
                "file_type": staged.canonical_extension.lstrip("."),
                "file_size": staged.size_bytes,
                "file_hash": staged.sha256,
                "storage_key": stored.storage_key,
                "created_by": current_user_id,
            },
            commit=False,
        )
        return str(certificate.id), stored

    async def _confirm_conflict_link(
        self,
        *,
        db: AsyncSession,
        context: Mapping[str, str],
        values: Mapping[str, CandidateValue | None],
        certificate_id: str,
        staged: StagedFile,
        attach_staged: bool,
        current_user_id: str,
    ) -> tuple[str, StoredFile | None]:
        asset_id = context.get("asset_id", "").strip()
        selected_certificate_id = certificate_id.strip()
        certificate_number = self._string_value(values, "certificate_number").strip()
        if asset_id == "" or selected_certificate_id == "":
            raise CandidateReviewError("existing_context_required")
        certificate = await property_certificate_crud.get(db, selected_certificate_id)
        if (
            certificate is None
            or str(certificate.certificate_number).strip() != certificate_number
        ):
            raise CandidateReviewError("certificate_link_invalid")
        await self._assert_certificate_asset_link(
            db=db,
            asset_id=asset_id,
            certificate_id=selected_certificate_id,
        )
        if not attach_staged:
            return selected_certificate_id, None
        stored = self._lifecycle.promote(
            staged,
            owner_type="property_certificate",
            owner_id=selected_certificate_id,
        )
        await attachment_crud.create(
            db,
            data={
                "owner_type": "property_certificate",
                "owner_id": selected_certificate_id,
                "file_name": staged.original_filename,
                "file_type": staged.canonical_extension.lstrip("."),
                "file_size": staged.size_bytes,
                "file_hash": staged.sha256,
                "storage_key": stored.storage_key,
                "created_by": current_user_id,
            },
            commit=False,
        )
        return selected_certificate_id, stored

    async def _confirm_existing_reference(
        self,
        *,
        db: AsyncSession,
        context: Mapping[str, str],
    ) -> str:
        attachment = await self._assert_existing_chain(
            db=db,
            asset_id=context.get("asset_id", ""),
            certificate_id=context.get("certificate_id", ""),
            attachment_id=context.get("existing_attachment_id", ""),
        )
        del attachment
        return context["certificate_id"]

    async def _assert_existing_chain(
        self,
        *,
        db: AsyncSession,
        asset_id: str,
        certificate_id: str,
        attachment_id: str,
    ) -> Attachment:
        normalized_asset_id = asset_id.strip()
        normalized_certificate_id = certificate_id.strip()
        normalized_attachment_id = attachment_id.strip()
        if (
            normalized_asset_id == ""
            or normalized_certificate_id == ""
            or normalized_attachment_id == ""
        ):
            raise CandidateReviewError("existing_context_required")
        certificate = await property_certificate_crud.get(db, normalized_certificate_id)
        if certificate is None:
            raise CandidateReviewError("certificate_not_found")
        await self._assert_certificate_asset_link(
            db=db,
            asset_id=normalized_asset_id,
            certificate_id=normalized_certificate_id,
        )
        attachment = await attachment_crud.get_for_owner(
            db,
            attachment_id=normalized_attachment_id,
            owner_type="property_certificate",
            owner_id=normalized_certificate_id,
        )
        if attachment is None:
            raise CandidateReviewError("certificate_attachment_chain_invalid")
        return attachment

    @staticmethod
    async def _assert_certificate_asset_link(
        *,
        db: AsyncSession,
        asset_id: str,
        certificate_id: str,
    ) -> None:
        linked_asset = await db.execute(
            select(property_cert_assets.c.asset_id).where(
                property_cert_assets.c.certificate_id == certificate_id,
                property_cert_assets.c.asset_id == asset_id,
            )
        )
        if linked_asset.scalar_one_or_none() is None:
            raise CandidateReviewError("certificate_asset_chain_invalid")

    def _extract_existing_attachment_pages(
        self, path: Path, file_type: str
    ) -> list[PageText]:
        if file_type == "pdf":
            return self._pipeline.extract_pdf_pages(path).pages
        if file_type in {"jpg", "jpeg", "png"}:
            return self._pipeline.extract_image_page(path).pages
        raise CandidateReviewError("attachment_file_type_invalid")

    def _extract_pages(self, staged: StagedFile) -> list[PageText]:
        if staged.canonical_extension == ".pdf":
            return self._pipeline.extract_pdf_pages(staged.path).pages
        return self._pipeline.extract_image_page(staged.path).pages

    @staticmethod
    def _session_context(staged: StagedFile) -> dict[str, str]:
        return {
            "staged_filename": staged.original_filename,
            "staged_extension": staged.canonical_extension,
            "staged_mime": staged.canonical_mime,
            "staged_size": str(staged.size_bytes),
            "staged_sha256": staged.sha256,
        }

    def _staged_from_session(
        self, session: Mapping[str, Any], context: Mapping[str, str]
    ) -> StagedFile:
        storage_key = session.get("staged_file_key")
        if not isinstance(storage_key, str):
            raise CandidateReviewError("staged_file_invalid")
        parts = Path(storage_key).parts
        if len(parts) != 3 or parts[0] != ".staging" or not parts[1]:
            raise CandidateReviewError("staged_file_invalid")
        try:
            size_bytes = int(context["staged_size"])
        except (KeyError, ValueError) as exc:
            raise CandidateReviewError("staged_file_invalid") from exc
        if size_bytes < 0:
            raise CandidateReviewError("staged_file_invalid")
        extension = context.get("staged_extension", "")
        if extension not in {".pdf", ".jpg", ".jpeg", ".png"}:
            raise CandidateReviewError("staged_file_invalid")
        return StagedFile(
            stage_id=parts[1],
            purpose=UploadPurpose.PROPERTY_CERTIFICATE_EXTRACTION,
            original_filename=context.get("staged_filename", ""),
            canonical_extension=extension,
            canonical_mime=context.get("staged_mime", ""),
            size_bytes=size_bytes,
            sha256=context.get("staged_sha256", ""),
            storage_key=storage_key,
            path=(self._lifecycle.storage_root / storage_key).resolve(),
            created_at=datetime.now(),
        )

    @staticmethod
    def _normalize_ids(values: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            normalized = value.strip()
            if normalized != "" and normalized not in seen:
                seen.add(normalized)
                result.append(normalized)
        return result

    @classmethod
    def _certificate_payload(
        cls,
        *,
        certificate_number: str,
        certificate_type: CertificateType,
        values: Mapping[str, CandidateValue | None],
        holder_party_ids: list[str],
        asset_id: str,
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "certificate_number": certificate_number,
            "certificate_type": certificate_type,
            "asset_ids": [asset_id],
            "holder_party_ids": holder_party_ids,
        }
        for field_key in (
            "registration_date",
            "property_address",
            "remarks",
        ):
            value = values.get(field_key)
            if value is not None:
                payload[field_key] = value
        for field_key in ("building_area", "land_area"):
            value = values.get(field_key)
            if isinstance(value, Decimal):
                payload[field_key] = str(value)
        return payload

    @staticmethod
    def _parse_action_value(value: str | None, field_key: str) -> CandidateValue | None:
        if value is None:
            return None
        if field_key in {"registration_date"}:
            return datetime.fromisoformat(value).date()
        if field_key in {"building_area", "land_area"}:
            return Decimal(value)
        return value
