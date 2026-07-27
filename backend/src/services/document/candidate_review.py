"""Deterministic document candidates and explicit human review actions."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Literal

from .page_text_pipeline import PageText, TextSource

type CandidateValue = str | date | Decimal
ConfidenceTier = Literal["high", "medium", "low"]
ReviewActionKind = Literal[
    "accept_candidate",
    "correct_candidate",
    "manual",
    "clear_optional",
    "keep_existing",
]
FieldSource = Literal["manual", "ocr_prefill_confirmed", "ocr_prefill_corrected"]

_DATE_VALUE = r"(20\d{2}(?:[-/.年])\d{1,2}(?:[-/.月])\d{1,2}(?:日)?)"
_AMOUNT_VALUE = r"([-+]?\d+(?:,\d{3})*(?:\.\d+)?)"
_ACTION_KINDS = {
    "accept_candidate",
    "correct_candidate",
    "manual",
    "clear_optional",
    "keep_existing",
}


class CandidateReviewError(ValueError):
    """A fail-loud invalid candidate or human review action."""


@dataclass(frozen=True)
class CandidateEvidence:
    page_number: int
    text: str
    text_source: TextSource


@dataclass(frozen=True)
class FieldCandidate:
    field_key: str
    value: CandidateValue
    text_source: TextSource
    extractor: Literal["rule", "deepseek"]
    evidence: tuple[CandidateEvidence, ...]
    confidence_tier: ConfidenceTier
    review_status: Literal["pending"] = "pending"


@dataclass(frozen=True)
class FieldCandidates:
    candidates: tuple[FieldCandidate, ...]
    conflict: bool
    selected: None = None


@dataclass(frozen=True)
class CandidateReview:
    fields: dict[str, FieldCandidates]
    rule_errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class FieldAction:
    field_key: str
    action: ReviewActionKind
    candidate_value: CandidateValue | None = None
    value: CandidateValue | None = None


@dataclass(frozen=True)
class ReviewedFields:
    values: dict[str, CandidateValue | None]
    field_sources: dict[str, FieldSource]


@dataclass(frozen=True)
class _FieldPolicy:
    value_type: type[str] | type[date] | type[Decimal]
    optional: bool


_CONTRACT_FIELDS = {
    "contract_number": _FieldPolicy(str, False),
    "sign_date": _FieldPolicy(date, True),
    "effective_from": _FieldPolicy(date, False),
    "effective_to": _FieldPolicy(date, True),
    "monthly_rent": _FieldPolicy(Decimal, True),
    "contract_notes": _FieldPolicy(str, True),
}
_PROPERTY_CERTIFICATE_FIELDS = {
    "certificate_number": _FieldPolicy(str, False),
    "registration_date": _FieldPolicy(date, True),
    "property_address": _FieldPolicy(str, True),
    "building_area": _FieldPolicy(Decimal, True),
    "land_area": _FieldPolicy(Decimal, True),
    "remarks": _FieldPolicy(str, True),
}


class CandidateReviewService:
    """Build transient rule candidates and require explicit field decisions."""

    def merge_contract_candidates(
        self,
        review: CandidateReview,
        candidates: tuple[FieldCandidate, ...],
    ) -> CandidateReview:
        """Merge optional text-enrichment candidates into deterministic results."""
        drafts = {
            field_key: list(field.candidates)
            for field_key, field in review.fields.items()
        }
        for candidate in candidates:
            if candidate.field_key not in _CONTRACT_FIELDS:
                raise CandidateReviewError("unknown_field")
            drafts.setdefault(candidate.field_key, []).append(candidate)
        return CandidateReview(
            fields=self._merge_fields(
                drafts, {"contract_number": self._contract_number_key}
            ),
            rule_errors=review.rule_errors,
        )

    def merge_property_certificate_candidates(
        self,
        review: CandidateReview,
        candidates: tuple[FieldCandidate, ...],
    ) -> CandidateReview:
        """Merge optional text-enrichment candidates into certificate results."""
        drafts = {
            field_key: list(field.candidates)
            for field_key, field in review.fields.items()
        }
        for candidate in candidates:
            if candidate.field_key not in _PROPERTY_CERTIFICATE_FIELDS:
                raise CandidateReviewError("unknown_field")
            drafts.setdefault(candidate.field_key, []).append(candidate)
        return CandidateReview(
            fields=self._merge_fields(drafts, {}),
            rule_errors=review.rule_errors,
        )

    def build_contract_candidates(self, pages: list[PageText]) -> CandidateReview:
        range_starts, range_ends = self._extract_labeled_date_range(
            pages,
            r"(?:\u79df\u8d41\u671f\u9650|\u79df\u8d41\u671f\u95f4|\u79df\u671f|\u5408\u540c\u671f\u9650)",
        )
        drafts: dict[str, list[FieldCandidate]] = {
            "contract_number": self._extract_strings(
                pages,
                r"(?:\u5408\u540c\u7f16\u53f7|\u5408\u540c\u53f7)\s*[:\uff1a]\s*(.+)",
                "contract_number",
            ),
            "sign_date": self._extract_dates(
                pages,
                r"(?:\u7b7e\u8ba2\u65e5\u671f|\u7b7e\u7ea6\u65e5\u671f)\s*[:\uff1a]\s*",
                "sign_date",
            ),
            "effective_from": self._extract_dates(
                pages,
                r"(?:\u5408\u540c\u751f\u6548\u65e5\u671f|\u751f\u6548\u65e5\u671f|\u8d77\u59cb\u65e5\u671f)\s*[:\uff1a]\s*",
                "effective_from",
            )
            + range_starts,
            "effective_to": self._extract_dates(
                pages,
                r"(?:\u5408\u540c\u5230\u671f\u65e5\u671f|\u5230\u671f\u65e5\u671f|\u7ec8\u6b62\u65e5\u671f)\s*[:\uff1a]\s*",
                "effective_to",
            )
            + range_ends,
            "monthly_rent": self._extract_labeled_amounts(
                pages,
                r"(?:\u6708\u79df\u91d1|\u6bcf\u6708\u79df\u91d1)",
                "monthly_rent",
            ),
        }
        errors = self._invalid_amount_errors(
            pages,
            drafts["monthly_rent"],
            "(?:\u6708\u79df\u91d1|\u6bcf\u6708\u79df\u91d1)",
        )
        fields = self._merge_fields(
            drafts, {"contract_number": self._contract_number_key}
        )
        if self._has_invalid_date_range(fields, "effective_from", "effective_to"):
            fields.pop("effective_from", None)
            fields.pop("effective_to", None)
            errors.append("date_range_invalid")
        return CandidateReview(fields=fields, rule_errors=tuple(sorted(set(errors))))

    def build_property_certificate_candidates(
        self, pages: list[PageText]
    ) -> CandidateReview:
        drafts = {
            "certificate_number": self._extract_strings(
                pages,
                r"(?:不动产权证(?:书)?号|证书编号|证号)\s*[：:]\s*([^\s]+)",
                "certificate_number",
            ),
            "registration_date": self._extract_dates(
                pages, r"(?:登记日期|发证日期)\s*[：:]\s*", "registration_date"
            ),
            "property_address": self._extract_strings(
                pages,
                r"(?:坐落|房屋坐落|不动产坐落)\s*[：:]\s*(.+)",
                "property_address",
            ),
            "building_area": self._extract_amounts(
                pages, r"(?:建筑面积)\s*[：:]\s*", "building_area"
            ),
            "land_area": self._extract_amounts(
                pages, r"(?:土地面积)\s*[：:]\s*", "land_area"
            ),
        }
        errors = self._invalid_amount_errors(pages, drafts["building_area"], "建筑面积")
        errors.extend(
            self._invalid_amount_errors(pages, drafts["land_area"], "土地面积")
        )
        return CandidateReview(
            fields=self._merge_fields(drafts, {}),
            rule_errors=tuple(sorted(set(errors))),
        )

    def apply_actions(
        self,
        review: CandidateReview,
        actions: list[FieldAction],
        *,
        existing_values: dict[str, CandidateValue] | None = None,
    ) -> ReviewedFields:
        existing = existing_values or {}
        policies = self._policies_for_review(review, actions)
        actions_by_field: dict[str, FieldAction] = {}
        for action in actions:
            if action.action not in _ACTION_KINDS:
                raise CandidateReviewError("invalid_action")
            if action.field_key not in policies:
                raise CandidateReviewError("unknown_field")
            if action.field_key in actions_by_field:
                raise CandidateReviewError("duplicate_field_action")
            actions_by_field[action.field_key] = action

        unreviewed = set(review.fields) - set(actions_by_field)
        if unreviewed:
            raise CandidateReviewError("unreviewed_candidate")

        values: dict[str, CandidateValue | None] = {}
        sources: dict[str, FieldSource] = {}
        for field_key, action in actions_by_field.items():
            policy = policies[field_key]
            existing_value = existing.get(field_key)
            if existing_value is not None:
                if action.action != "keep_existing":
                    raise CandidateReviewError("existing_value_protected")
                self._require_empty_action_values(action)
                values[field_key] = existing_value
                continue
            if action.action == "keep_existing":
                raise CandidateReviewError("missing_existing_value")
            if action.action == "accept_candidate":
                candidate = self._find_candidate(review, action)
                self._require_empty_value(action)
                values[field_key] = candidate.value
                sources[field_key] = "ocr_prefill_confirmed"
            elif action.action == "correct_candidate":
                candidate = self._find_candidate(review, action)
                value = self._require_value(action)
                self._validate_value(policy, value)
                if value == candidate.value:
                    raise CandidateReviewError("candidate_not_corrected")
                values[field_key] = value
                sources[field_key] = "ocr_prefill_corrected"
            elif action.action == "manual":
                if action.candidate_value is not None:
                    raise CandidateReviewError("manual_action_has_candidate")
                value = self._require_value(action)
                self._validate_value(policy, value)
                values[field_key] = value
                sources[field_key] = "manual"
            elif action.action == "clear_optional":
                if not policy.optional:
                    raise CandidateReviewError("required_field_cannot_be_cleared")
                self._require_empty_action_values(action)
                values[field_key] = None
        self._validate_resolved_contract_dates(values)
        return ReviewedFields(values=values, field_sources=sources)

    @staticmethod
    def _policies_for_review(
        review: CandidateReview, actions: list[FieldAction]
    ) -> dict[str, _FieldPolicy]:
        field_keys = set(review.fields) | {action.field_key for action in actions}
        if field_keys & set(_CONTRACT_FIELDS) and field_keys & set(
            _PROPERTY_CERTIFICATE_FIELDS
        ):
            raise CandidateReviewError("mixed_document_fields")
        if field_keys & set(_CONTRACT_FIELDS):
            return _CONTRACT_FIELDS
        return _PROPERTY_CERTIFICATE_FIELDS

    @staticmethod
    def _extract_strings(
        pages: list[PageText], pattern: str, field_key: str
    ) -> list[FieldCandidate]:
        regex = re.compile(pattern)
        candidates: list[FieldCandidate] = []
        for page in pages:
            if page.text_source is None:
                continue
            for line in page.text_lines:
                match = regex.search(line)
                if match is None:
                    continue
                value = match.group(1).strip().rstrip("，。；;")
                if value:
                    candidates.append(
                        CandidateReviewService._candidate(field_key, value, page, line)
                    )
        return candidates

    @staticmethod
    def _extract_dates(
        pages: list[PageText], prefix: str, field_key: str
    ) -> list[FieldCandidate]:
        regex = re.compile(prefix + _DATE_VALUE)
        candidates: list[FieldCandidate] = []
        for page in pages:
            if page.text_source is None:
                continue
            for line in page.text_lines:
                match = regex.search(line)
                if match is None:
                    continue
                parsed = CandidateReviewService._parse_date(match.group(1))
                if parsed is not None:
                    candidates.append(
                        CandidateReviewService._candidate(field_key, parsed, page, line)
                    )
        return candidates

    @staticmethod
    def _extract_labeled_date_range(
        pages: list[PageText], label_pattern: str
    ) -> tuple[list[FieldCandidate], list[FieldCandidate]]:
        label_regex = re.compile(label_pattern)
        date_regex = re.compile(_DATE_VALUE)
        starts: list[FieldCandidate] = []
        ends: list[FieldCandidate] = []
        for page in pages:
            if page.text_source is None:
                continue
            for line in page.text_lines:
                normalized_line = re.sub(r"\s+", "", line)
                label_match = label_regex.search(normalized_line)
                if label_match is None:
                    continue
                dates = [
                    CandidateReviewService._parse_date(match.group(1))
                    for match in date_regex.finditer(
                        normalized_line[label_match.end() :]
                    )
                ]
                parsed_dates = [value for value in dates if value is not None]
                if len(parsed_dates) < 2:
                    continue
                starts.append(
                    CandidateReviewService._candidate(
                        "effective_from", parsed_dates[0], page, line
                    )
                )
                ends.append(
                    CandidateReviewService._candidate(
                        "effective_to", parsed_dates[1], page, line
                    )
                )
        return starts, ends

    @staticmethod
    def _extract_labeled_amounts(
        pages: list[PageText], label_pattern: str, field_key: str
    ) -> list[FieldCandidate]:
        regex = re.compile(label_pattern + r"\D{0,20}?" + _AMOUNT_VALUE)
        candidates: list[FieldCandidate] = []
        for page in pages:
            if page.text_source is None:
                continue
            for line in page.text_lines:
                match = regex.search(re.sub(r"\s+", "", line))
                if match is None:
                    continue
                try:
                    amount = Decimal(match.group(1).replace(",", ""))
                except InvalidOperation:
                    continue
                if amount > 0:
                    candidates.append(
                        CandidateReviewService._candidate(field_key, amount, page, line)
                    )
        return candidates

    @staticmethod
    def _extract_amounts(
        pages: list[PageText], prefix: str, field_key: str
    ) -> list[FieldCandidate]:
        regex = re.compile(prefix + _AMOUNT_VALUE)
        candidates: list[FieldCandidate] = []
        for page in pages:
            if page.text_source is None:
                continue
            for line in page.text_lines:
                match = regex.search(line)
                if match is None:
                    continue
                try:
                    amount = Decimal(match.group(1).replace(",", ""))
                except InvalidOperation:
                    continue
                if amount > 0:
                    candidates.append(
                        CandidateReviewService._candidate(field_key, amount, page, line)
                    )
        return candidates

    @staticmethod
    def _candidate(
        field_key: str, value: CandidateValue, page: PageText, line: str
    ) -> FieldCandidate:
        text_source = page.text_source
        if text_source is None:
            raise CandidateReviewError("page_text_source_required")
        return FieldCandidate(
            field_key=field_key,
            value=value,
            text_source=text_source,
            extractor="rule",
            evidence=(
                CandidateEvidence(
                    page_number=page.page_number,
                    text=line[:240],
                    text_source=text_source,
                ),
            ),
            confidence_tier="high" if text_source == "pdf_text" else "low",
        )

    @staticmethod
    def _parse_date(raw_value: str) -> date | None:
        normalized = (
            raw_value.replace("\u5e74", "-")
            .replace("\u6708", "-")
            .replace("\u65e5", "")
        )
        normalized = normalized.replace("/", "-").replace(".", "-")
        normalized = re.sub(r"[()\uff08\uff09\s]", "", normalized)
        match = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", normalized)
        if match is None:
            return None
        try:
            return date(*(int(part) for part in match.groups()))
        except ValueError:
            return None

    @staticmethod
    def _contract_number_key(value: CandidateValue) -> str:
        return re.sub(r"[\s_-]+", "-", str(value)).upper()

    @staticmethod
    def _normal_key(value: CandidateValue) -> str:
        if isinstance(value, Decimal):
            return str(value.normalize())
        if isinstance(value, date):
            return value.isoformat()
        return re.sub(r"\s+", "", value).casefold()

    def _merge_fields(
        self,
        drafts: dict[str, list[FieldCandidate]],
        normalizers: dict[str, Callable[[CandidateValue], str]],
    ) -> dict[str, FieldCandidates]:
        fields: dict[str, FieldCandidates] = {}
        for field_key, candidates in drafts.items():
            merged: dict[str, FieldCandidate] = {}
            normalizer = normalizers.get(field_key, self._normal_key)
            for candidate in candidates:
                key = normalizer(candidate.value)
                previous = merged.get(key)
                if previous is None:
                    merged[key] = candidate
                else:
                    merged[key] = FieldCandidate(
                        field_key=previous.field_key,
                        value=previous.value,
                        text_source=previous.text_source,
                        extractor=previous.extractor,
                        evidence=previous.evidence + candidate.evidence,
                        confidence_tier=min(
                            previous.confidence_tier,
                            candidate.confidence_tier,
                            key=("high", "medium", "low").index,
                        ),
                    )
            if merged:
                values = tuple(merged.values())
                fields[field_key] = FieldCandidates(
                    candidates=values,
                    conflict=len(values) > 1,
                )
        return fields

    @staticmethod
    def _has_invalid_date_range(
        fields: dict[str, FieldCandidates], start_key: str, end_key: str
    ) -> bool:
        start = fields.get(start_key)
        end = fields.get(end_key)
        if start is None or end is None or start.conflict or end.conflict:
            return False
        start_value = start.candidates[0].value
        end_value = end.candidates[0].value
        if not isinstance(start_value, date) or not isinstance(end_value, date):
            return False
        return start_value >= end_value

    @staticmethod
    def _invalid_amount_errors(
        pages: list[PageText], candidates: list[FieldCandidate], labels: str
    ) -> list[str]:
        if candidates:
            return []
        label_pattern = re.compile(rf"(?:{labels})\s*[：:]")
        return [
            "amount_invalid"
            for page in pages
            for line in page.text_lines
            if label_pattern.search(line)
        ]

    @staticmethod
    def _find_candidate(review: CandidateReview, action: FieldAction) -> FieldCandidate:
        if action.candidate_value is None:
            raise CandidateReviewError("candidate_value_required")
        field = review.fields.get(action.field_key)
        if field is None:
            raise CandidateReviewError("candidate_not_found")
        for candidate in field.candidates:
            if candidate.value == action.candidate_value:
                return candidate
        raise CandidateReviewError("candidate_not_found")

    @staticmethod
    def _require_value(action: FieldAction) -> CandidateValue:
        if action.value is None:
            raise CandidateReviewError("action_value_required")
        return action.value

    @staticmethod
    def _require_empty_value(action: FieldAction) -> None:
        if action.value is not None:
            raise CandidateReviewError("unexpected_action_value")

    def _require_empty_action_values(self, action: FieldAction) -> None:
        if action.value is not None or action.candidate_value is not None:
            raise CandidateReviewError("unexpected_action_value")

    @staticmethod
    def _validate_value(policy: _FieldPolicy, value: CandidateValue) -> None:
        if policy.value_type is str:
            if not isinstance(value, str) or value.strip() == "":
                raise CandidateReviewError("invalid_field_value")
        elif policy.value_type is date:
            if type(value) is not date:
                raise CandidateReviewError("invalid_field_value")
        elif policy.value_type is Decimal:
            if not isinstance(value, Decimal) or value <= 0:
                raise CandidateReviewError("invalid_field_value")

    @staticmethod
    def _validate_resolved_contract_dates(
        values: dict[str, CandidateValue | None],
    ) -> None:
        start = values.get("effective_from")
        end = values.get("effective_to")
        if type(start) is date and type(end) is date and end <= start:
            raise CandidateReviewError("date_range_invalid")
