"""Contract extraction session orchestration with explicit human review."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.contract_group import ContractDirection, GroupRelationType, RevenueMode
from src.schemas.contract_group import (
    ContractCreate,
    ContractGroupCreate,
    LeaseDetailCreate,
)
from src.services.contract.contract_group_service import contract_group_service
from src.services.file_upload.staged_files import StagedFile, StagedFileService
from src.services.party import party_service

from .candidate_review import (
    CandidateEvidence,
    CandidateReview,
    CandidateReviewError,
    CandidateReviewService,
    CandidateValue,
    FieldAction,
    FieldCandidate,
    FieldCandidates,
    ReviewActionKind,
)
from .deepseek_text_enrichment import DeepSeekTextEnricher
from .extraction_sessions import (
    ExtractionSessionRepository,
    ExtractionSessionStateError,
)
from .page_text_pipeline import OrderedPageTextPipeline


class ContractExtractionWorkflow:
    """Keep extraction evidence temporary and write only reviewed contract fields."""

    def __init__(
        self,
        *,
        repository: ExtractionSessionRepository,
        pipeline: OrderedPageTextPipeline,
        reviewer: CandidateReviewService,
        enricher: DeepSeekTextEnricher,
        lifecycle: StagedFileService,
    ) -> None:
        self._repository = repository
        self._pipeline = pipeline
        self._reviewer = reviewer
        self._enricher = enricher
        self._lifecycle = lifecycle

    def create(self, *, staged: StagedFile, context: Mapping[str, str]) -> dict[str, Any]:
        session_id = uuid4().hex
        try:
            pages = self._pipeline.extract_pdf_pages(staged.path).pages
            review = self._reviewer.build_contract_candidates(pages)
            enrichment = self._enricher.enrich("contract", pages, session_id=session_id)
            if enrichment.status == "success":
                review = self._reviewer.merge_contract_candidates(review, enrichment.candidates)
            errors = list(review.rule_errors)
            errors.extend(page.error.code for page in pages if page.error is not None)
            if enrichment.status == "failed":
                errors.append("enrichment_failed")
            session = self._repository.create(
                session_id=session_id,
                target_type="contract",
                staged_file_key=staged.storage_key,
                candidates=self._serialize_review(review),
                context=dict(context),
                errors=sorted(set(errors)),
            )
        except Exception:
            self._lifecycle.discard_staged(staged)
            raise
        return self.public_session(session)

    def get(self, session_id: str) -> dict[str, Any] | None:
        session = self._repository.get(session_id)
        return None if session is None else self.public_session(session)

    def cancel(self, session_id: str) -> None:
        staged_file_key = self._repository.delete_terminal(session_id, "cancelled")
        self._lifecycle.discard_path(self._staged_path(staged_file_key))

    async def confirm(
        self,
        *,
        session_id: str,
        actions: list[Mapping[str, str | None]],
        party_ids: Mapping[str, str],
        asset_ids: list[str],
        db: AsyncSession,
        current_user_id: str,
    ) -> str:
        session = self._repository.transition(session_id, "ready_for_review", "confirming")
        try:
            review = self._deserialize_review(session["candidates"])
            reviewed = self._reviewer.apply_actions(review, self._deserialize_actions(actions))
            values = reviewed.values
            for field_key in ("contract_number", "sign_date", "effective_from"):
                if values.get(field_key) is None:
                    raise CandidateReviewError("required_field_unreviewed")
            contract_id = await self._create_contract(
                db=db,
                context=self._require_mapping(session, "context"),
                values=values,
                party_ids=party_ids,
                asset_ids=asset_ids,
                current_user_id=current_user_id,
            )
            await db.commit()
        except CandidateReviewError:
            self._repository.transition(session_id, "confirming", "ready_for_review")
            raise
        except Exception:
            await db.rollback()
            self._repository.transition(session_id, "confirming", "ready_for_review")
            raise

        staged_file_key = self._repository.delete_after_status(session_id, "confirming")
        self._lifecycle.discard_path(self._staged_path(staged_file_key))
        return contract_id

    async def _create_contract(
        self,
        *,
        db: AsyncSession,
        context: Mapping[str, str],
        values: Mapping[str, CandidateValue | None],
        party_ids: Mapping[str, str],
        asset_ids: list[str],
        current_user_id: str,
    ) -> str:
        required_party_keys = {
            "operator_party_id",
            "owner_party_id",
            "lessor_party_id",
            "lessee_party_id",
        }
        if set(party_ids) != required_party_keys or any(
            not value.strip() for value in party_ids.values()
        ):
            raise CandidateReviewError("explicit_party_ids_required")

        operator_party = await party_service.get_party(
            db, party_id=party_ids["operator_party_id"]
        )
        if operator_party is None:
            raise CandidateReviewError("party_not_found")

        revenue_mode = RevenueMode(context["revenue_mode"])
        effective_from = self._date_value(values, "effective_from")
        group = await contract_group_service.create_contract_group(
            db,
            obj_in=ContractGroupCreate.model_validate(
                {
                    "project_id": context["project_id"],
                    "revenue_mode": revenue_mode,
                    "operator_party_id": party_ids["operator_party_id"],
                    "owner_party_id": party_ids["owner_party_id"],
                    "effective_from": effective_from,
                    "effective_to": self._optional_date(values, "effective_to"),
                    "asset_ids": asset_ids,
                }
            ),
            group_code=await contract_group_service.generate_group_code(
                db,
                operator_party_id=party_ids["operator_party_id"],
                operator_party_code=operator_party.code,
            ),
            current_user=current_user_id,
            commit=False,
        )
        monthly_rent = values.get("monthly_rent")
        lease_detail = None
        if revenue_mode is RevenueMode.LEASE and isinstance(monthly_rent, Decimal):
            lease_detail = LeaseDetailCreate.model_validate(
                {
                    "rent_amount": monthly_rent,
                    "monthly_rent_base": monthly_rent,
                }
            )
        contract = await contract_group_service.add_contract_to_group(
            db,
            obj_in=ContractCreate.model_validate(
                {
                    "contract_group_id": group.contract_group_id,
                    "contract_number": self._string_value(values, "contract_number"),
                    "contract_direction": ContractDirection(context["contract_direction"]),
                    "group_relation_type": GroupRelationType(context["group_relation_type"]),
                    "lessor_party_id": party_ids["lessor_party_id"],
                    "lessee_party_id": party_ids["lessee_party_id"],
                    "sign_date": self._date_value(values, "sign_date"),
                    "effective_from": effective_from,
                    "effective_to": self._optional_date(values, "effective_to"),
                    "contract_notes": self._optional_string(values, "contract_notes"),
                    "asset_ids": asset_ids,
                    "lease_detail": lease_detail,
                }
            ),
            current_user=current_user_id,
            commit=False,
        )
        return contract.contract_id


    @staticmethod
    def _require_mapping(session: Mapping[str, Any], key: str) -> Mapping[str, str]:
        value = session.get(key)
        if not isinstance(value, Mapping) or not all(
            isinstance(item, str) for item in value.values()
        ):
            raise ExtractionSessionStateError("session_context_invalid")
        return value

    @staticmethod
    def _date_value(values: Mapping[str, CandidateValue | None], key: str) -> date:
        value = values.get(key)
        if type(value) is not date:
            raise CandidateReviewError("required_field_unreviewed")
        return value

    @staticmethod
    def _optional_date(
        values: Mapping[str, CandidateValue | None], key: str
    ) -> date | None:
        value = values.get(key)
        if value is None:
            return None
        if type(value) is not date:
            raise CandidateReviewError("invalid_field_value")
        return value

    @staticmethod
    def _string_value(values: Mapping[str, CandidateValue | None], key: str) -> str:
        value = values.get(key)
        if not isinstance(value, str) or value.strip() == "":
            raise CandidateReviewError("required_field_unreviewed")
        return value

    @staticmethod
    def _optional_string(
        values: Mapping[str, CandidateValue | None], key: str
    ) -> str | None:
        value = values.get(key)
        if value is None:
            return None
        if not isinstance(value, str):
            raise CandidateReviewError("invalid_field_value")
        return value

    def _staged_path(self, storage_key: str) -> Path:
        return (self._lifecycle.storage_root / storage_key).resolve()

    @staticmethod
    def _serialize_value(value: CandidateValue) -> str:
        return str(value) if not isinstance(value, date) else value.isoformat()

    @classmethod
    def _serialize_review(cls, review: CandidateReview) -> dict[str, Any]:
        return {
            "fields": {
                field_key: {
                    "conflict": field.conflict,
                    "candidates": [
                        {
                            "value": cls._serialize_value(candidate.value),
                            "value_type": cls._value_type(candidate.value),
                            "confidence": candidate.confidence_tier,
                            "evidence": [
                                {
                                    "page_number": evidence.page_number,
                                    "text": evidence.text,
                                }
                                for evidence in candidate.evidence
                            ],
                        }
                        for candidate in field.candidates
                    ],
                }
                for field_key, field in review.fields.items()
            }
        }

    @staticmethod
    def _value_type(value: CandidateValue) -> str:
        if type(value) is date:
            return "date"
        if isinstance(value, Decimal):
            return "decimal"
        return "string"

    @classmethod
    def _deserialize_review(cls, payload: object) -> CandidateReview:
        if not isinstance(payload, Mapping):
            raise ExtractionSessionStateError("session_candidates_invalid")
        raw_fields = payload.get("fields")
        if not isinstance(raw_fields, Mapping):
            raise ExtractionSessionStateError("session_candidates_invalid")
        fields: dict[str, FieldCandidates] = {}
        for field_key, raw_field in raw_fields.items():
            if not isinstance(field_key, str) or not isinstance(raw_field, Mapping):
                raise ExtractionSessionStateError("session_candidates_invalid")
            raw_candidates = raw_field.get("candidates")
            if not isinstance(raw_candidates, list):
                raise ExtractionSessionStateError("session_candidates_invalid")
            candidates = tuple(
                cls._deserialize_candidate(field_key, raw) for raw in raw_candidates
            )
            fields[field_key] = FieldCandidates(
                candidates=candidates,
                conflict=bool(raw_field.get("conflict")),
            )
        return CandidateReview(fields=fields)

    @staticmethod
    def _deserialize_candidate(field_key: str, raw: object) -> FieldCandidate:
        if not isinstance(raw, Mapping):
            raise ExtractionSessionStateError("session_candidates_invalid")
        value = ContractExtractionWorkflow._parse_value(
            raw.get("value"), raw.get("value_type")
        )
        raw_evidence = raw.get("evidence")
        if not isinstance(raw_evidence, list):
            raise ExtractionSessionStateError("session_candidates_invalid")
        evidence = tuple(
            CandidateEvidence(
                page_number=int(item["page_number"]),
                text=str(item["text"]),
                text_source="pdf_text",
            )
            for item in raw_evidence
            if isinstance(item, Mapping)
        )
        if len(evidence) != len(raw_evidence):
            raise ExtractionSessionStateError("session_candidates_invalid")
        confidence = raw.get("confidence", "low")
        if confidence not in {"high", "medium", "low"}:
            raise ExtractionSessionStateError("session_candidates_invalid")
        return FieldCandidate(
            field_key=field_key,
            value=value,
            text_source="pdf_text",
            extractor="rule",
            evidence=evidence,
            confidence_tier=confidence,
        )

    @staticmethod
    def _parse_value(raw: object, value_type: object) -> CandidateValue:
        if not isinstance(raw, str) or value_type not in {"string", "date", "decimal"}:
            raise ExtractionSessionStateError("session_candidates_invalid")
        if value_type == "date":
            return date.fromisoformat(raw)
        if value_type == "decimal":
            return Decimal(raw)
        return raw

    @classmethod
    def _deserialize_actions(
        cls, actions: list[Mapping[str, str | None]]
    ) -> list[FieldAction]:
        result: list[FieldAction] = []
        for raw in actions:
            field_key = raw.get("field_key")
            action = raw.get("action")
            if not isinstance(field_key, str) or not isinstance(action, str):
                raise CandidateReviewError("invalid_action")
            result.append(
                FieldAction(
                    field_key=field_key,
                    action=cast(ReviewActionKind, action),
                    candidate_value=cls._parse_action_value(
                        raw.get("candidate_value"), field_key
                    ),
                    value=cls._parse_action_value(raw.get("value"), field_key),
                )
            )
        return result

    @staticmethod
    def _parse_action_value(value: str | None, field_key: str) -> CandidateValue | None:
        if value is None:
            return None
        if field_key in {"sign_date", "effective_from", "effective_to"}:
            return date.fromisoformat(value)
        if field_key == "monthly_rent":
            return Decimal(value)
        return value

    @staticmethod
    def public_session(session: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "session_id": session["session_id"],
            "target_type": session["target_type"],
            "status": session["status"],
            "candidates": session["candidates"],
            "errors": session["errors"],
        }
