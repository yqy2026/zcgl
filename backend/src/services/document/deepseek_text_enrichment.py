"""Optional, fail-closed DeepSeek text candidates for document review."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Literal, Protocol

import httpx

from src.constants.document_processing_constants import DOCUMENT_PAGES_PER_BATCH
from src.core.config_llm import LlmSettings

from .candidate_review import CandidateEvidence, CandidateValue, FieldCandidate
from .page_text_pipeline import PageText

MAX_TEXT_CHARS = 200_000
MAX_TOKENS = 8192
TIMEOUT_SECONDS = 120
MODEL = "deepseek-v4-flash"
_PROMPTS = {
    "contract": ("contract-extraction/v1", "Extract only contract field candidates."),
    "property_certificate": (
        "property-certificate-extraction/v1",
        "Extract only property certificate field candidates.",
    ),
}
_FIELDS = {
    "contract": {
        "contract_number": str,
        "sign_date": date,
        "effective_from": date,
        "effective_to": date,
        "monthly_rent": Decimal,
        "contract_notes": str,
    },
    "property_certificate": {
        "certificate_number": str,
        "registration_date": date,
        "property_address": str,
        "building_area": Decimal,
        "land_area": Decimal,
        "remarks": str,
    },
}


class _Response(Protocol):
    status_code: int

    def json(self) -> object: ...


Post = Callable[..., _Response]


@dataclass(frozen=True)
class DeepSeekEnrichmentResult:
    status: Literal["success", "skipped", "failed"]
    code: str | None
    candidates: tuple[FieldCandidate, ...] = ()


class DeepSeekTextEnricher:
    """Call DeepSeek only for text candidates and discard any invalid batch."""

    def __init__(self, settings: LlmSettings, *, post: Post | None = None) -> None:
        self.settings = settings
        self._post = post or self._post_with_httpx

    def enrich(
        self,
        document_type: Literal["contract", "property_certificate"],
        pages: list[PageText],
        *,
        session_id: str,
    ) -> DeepSeekEnrichmentResult:
        del session_id
        if not self.settings.DOCUMENT_LLM_ENABLED:
            return DeepSeekEnrichmentResult("skipped", "llm_disabled")
        if document_type not in _PROMPTS:
            return DeepSeekEnrichmentResult("failed", "llm_input_invalid")

        batches = [
            pages[start : start + DOCUMENT_PAGES_PER_BATCH]
            for start in range(0, len(pages), DOCUMENT_PAGES_PER_BATCH)
        ] or [pages]
        candidates: list[FieldCandidate] = []
        for batch in batches:
            result = self._enrich_batch(document_type, batch)
            if result.status != "success":
                return result
            candidates.extend(result.candidates)
        return DeepSeekEnrichmentResult("success", None, tuple(candidates))

    def _enrich_batch(
        self,
        document_type: Literal["contract", "property_certificate"],
        pages: list[PageText],
    ) -> DeepSeekEnrichmentResult:
        if len(pages) > DOCUMENT_PAGES_PER_BATCH:
            return DeepSeekEnrichmentResult("failed", "llm_input_invalid")

        text = self._redacted_page_text(pages)
        if len(text) > MAX_TEXT_CHARS:
            return DeepSeekEnrichmentResult("failed", "llm_input_invalid")
        version, system_prompt = _PROMPTS[document_type]
        try:
            response = self._post(
                f"{self.settings.DEEPSEEK_BASE_URL.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {self.settings.DEEPSEEK_API_KEY}"},
                json={
                    "model": MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": text},
                    ],
                    "thinking": {"type": "disabled"},
                    "temperature": 0,
                    "stream": False,
                    "response_format": {"type": "json_object"},
                    "max_tokens": MAX_TOKENS,
                },
                timeout=TIMEOUT_SECONDS,
            )
        except (TimeoutError, httpx.TimeoutException):
            return DeepSeekEnrichmentResult("failed", "llm_timeout")
        except Exception:
            return DeepSeekEnrichmentResult("failed", "llm_request_failed")
        if response.status_code != 200:
            return DeepSeekEnrichmentResult("failed", "llm_http_error")
        try:
            candidates = self._validate_response(
                response.json(), document_type, version, pages
            )
        except (TypeError, ValueError, KeyError, InvalidOperation, json.JSONDecodeError):
            return DeepSeekEnrichmentResult("failed", "llm_response_invalid")
        return DeepSeekEnrichmentResult("success", None, tuple(candidates))

    @staticmethod
    def _post_with_httpx(url: str, **kwargs: Any) -> _Response:
        return httpx.post(url, **kwargs)

    @staticmethod
    def _redacted_page_text(pages: list[PageText]) -> str:
        lines: list[str] = []
        for page in pages:
            if page.text_source is None:
                continue
            for line in page.text_lines:
                text = re.sub(r"\b\d{17}[\dXx]\b", "[REDACTED_ID]", line)
                text = re.sub(r"\b1\d{10}\b", "[REDACTED_PHONE]", text)
                lines.append(f"[{page.page_number}] {text}")
        return "\n".join(lines)

    @staticmethod
    def _validate_response(
        payload: object,
        document_type: str,
        version: str,
        pages: list[PageText],
    ) -> list[FieldCandidate]:
        if not isinstance(payload, dict) or set(payload) != {
            "version",
            "document_type",
            "candidates",
        }:
            raise ValueError("schema")
        if payload["version"] != version or payload["document_type"] != document_type:
            raise ValueError("version")
        raw_candidates = payload["candidates"]
        if not isinstance(raw_candidates, list):
            raise ValueError("candidates")

        pages_by_number = {page.page_number: page for page in pages}
        candidates: list[FieldCandidate] = []
        for raw in raw_candidates:
            if not isinstance(raw, dict) or set(raw) != {
                "field_key",
                "value",
                "evidence",
            }:
                raise ValueError("candidate_schema")
            field_key = raw["field_key"]
            if not isinstance(field_key, str) or field_key not in _FIELDS[document_type]:
                raise ValueError("field")
            evidence = raw["evidence"]
            if not isinstance(evidence, dict) or set(evidence) != {
                "page_number",
                "text",
            }:
                raise ValueError("evidence_schema")
            page_number = evidence["page_number"]
            evidence_text = evidence["text"]
            if not isinstance(page_number, int) or not isinstance(evidence_text, str):
                raise ValueError("evidence")
            page = pages_by_number.get(page_number)
            if page is None or page.text_source is None:
                raise ValueError("evidence_reference")
            if evidence_text not in page.text_lines:
                raise ValueError("evidence_reference")
            value = DeepSeekTextEnricher._parse_value(
                raw["value"], _FIELDS[document_type][field_key]
            )
            candidates.append(
                FieldCandidate(
                    field_key=field_key,
                    value=value,
                    text_source=page.text_source,
                    extractor="deepseek",
                    evidence=(
                        CandidateEvidence(
                            page_number,
                            evidence_text[:240],
                            page.text_source,
                        ),
                    ),
                    confidence_tier="medium",
                )
            )
        return candidates

    @staticmethod
    def _parse_value(
        raw_value: object, target_type: type[CandidateValue]
    ) -> CandidateValue:
        if target_type is str:
            if not isinstance(raw_value, str) or raw_value.strip() == "":
                raise ValueError("string")
            return raw_value.strip()
        if target_type is date:
            if not isinstance(raw_value, str):
                raise ValueError("date")
            return date.fromisoformat(raw_value)
        if target_type is Decimal:
            if not isinstance(raw_value, str):
                raise ValueError("decimal")
            value = Decimal(raw_value)
            if value <= 0:
                raise ValueError("decimal")
            return value
        raise ValueError("type")
