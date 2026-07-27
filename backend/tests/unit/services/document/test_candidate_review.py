"""Tests for deterministic extraction candidates and review actions."""

from datetime import date
from decimal import Decimal

import pytest

from src.services.document.candidate_review import (
    CandidateEvidence,
    CandidateReviewError,
    CandidateReviewService,
    FieldAction,
    FieldCandidate,
)
from src.services.document.page_text_pipeline import PageText


def _page(page_number: int, source: str, *lines: str) -> PageText:
    return PageText(
        page_number=page_number,
        text_source=source,  # type: ignore[arg-type]
        text_lines=list(lines),
        evidence=[line[:240] for line in lines[:3]],
    )


def test_duplicate_normalized_contract_values_merge_temporary_evidence():
    review = CandidateReviewService().build_contract_candidates(
        [
            _page(1, "pdf_text", "合同编号：HT-2026-001"),
            _page(2, "rapidocr", "合同编号: ht 2026 001"),
        ]
    )

    field = review.fields["contract_number"]

    assert field.conflict is False
    assert field.selected is None
    assert len(field.candidates) == 1
    assert field.candidates[0].value == "HT-2026-001"
    assert [item.page_number for item in field.candidates[0].evidence] == [1, 2]


def test_conflicting_rule_values_are_exposed_without_a_selection():
    review = CandidateReviewService().build_property_certificate_candidates(
        [
            _page(1, "pdf_text", "不动产权证号：粤(2026)001号"),
            _page(2, "pdf_text", "不动产权证号：粤(2026)002号"),
        ]
    )

    field = review.fields["certificate_number"]

    assert field.conflict is True
    assert field.selected is None
    assert {candidate.value for candidate in field.candidates} == {
        "粤(2026)001号",
        "粤(2026)002号",
    }


def test_contract_rule_rejects_invalid_date_range_and_amount():
    review = CandidateReviewService().build_contract_candidates(
        [
            _page(
                1,
                "pdf_text",
                "合同生效日期：2026-12-31",
                "合同到期日期：2026-01-01",
                "月租金：-100 元",
            )
        ]
    )

    assert "effective_from" not in review.fields
    assert "effective_to" not in review.fields
    assert "monthly_rent" not in review.fields
    assert set(review.rule_errors) == {"date_range_invalid", "amount_invalid"}


def test_contract_rules_extract_rental_term_dates_and_flexible_monthly_rent():
    review = CandidateReviewService().build_contract_candidates(
        [
            _page(
                1,
                "rapidocr",
                "\u79df\u8d41\u671f\u9650\uff1a2026\u5e741\u67081\u65e5\u81f32027\u5e741\u67081\u65e5",
                "\u6708\u79df\u91d1\u4e3a\u4eba\u6c11\u5e0112,000\u5143",
            )
        ]
    )

    assert review.fields["effective_from"].candidates[0].value == date(2026, 1, 1)
    assert review.fields["effective_to"].candidates[0].value == date(2027, 1, 1)
    assert review.fields["monthly_rent"].candidates[0].value == Decimal("12000")
    assert review.fields["monthly_rent"].candidates[0].confidence_tier == "low"


def test_unreviewed_low_confidence_candidate_blocks_confirmation():
    service = CandidateReviewService()
    review = service.build_property_certificate_candidates(
        [_page(1, "rapidocr", "建筑面积：100.5 平方米")]
    )

    with pytest.raises(CandidateReviewError, match="unreviewed_candidate"):
        service.apply_actions(review, [])


def test_actions_derive_field_sources_and_do_not_return_temporary_evidence():
    service = CandidateReviewService()
    review = service.build_property_certificate_candidates(
        [
            _page(
                1,
                "pdf_text",
                "不动产权证号：粤(2026)001号",
                "建筑面积：100.5 平方米",
            )
        ]
    )

    result = service.apply_actions(
        review,
        [
            FieldAction(
                field_key="certificate_number",
                action="accept_candidate",
                candidate_value="粤(2026)001号",
            ),
            FieldAction(
                field_key="building_area",
                action="correct_candidate",
                candidate_value=Decimal("100.5"),
                value=Decimal("101"),
            ),
            FieldAction(
                field_key="property_address",
                action="manual",
                value="深圳市南山区科技园",
            ),
            FieldAction(field_key="remarks", action="clear_optional"),
        ],
    )

    assert result.values == {
        "certificate_number": "粤(2026)001号",
        "building_area": Decimal("101"),
        "property_address": "深圳市南山区科技园",
        "remarks": None,
    }
    assert result.field_sources == {
        "certificate_number": "ocr_prefill_confirmed",
        "building_area": "ocr_prefill_corrected",
        "property_address": "manual",
    }
    assert not hasattr(result, "evidence")


def test_existing_value_only_allows_keep_existing():
    service = CandidateReviewService()
    review = service.build_contract_candidates(
        [_page(1, "pdf_text", "合同编号：HT-2026-001")]
    )

    with pytest.raises(CandidateReviewError, match="existing_value_protected"):
        service.apply_actions(
            review,
            [
                FieldAction(
                    field_key="contract_number",
                    action="accept_candidate",
                    candidate_value="HT-2026-001",
                )
            ],
            existing_values={"contract_number": "HT-OLD"},
        )

    result = service.apply_actions(
        review,
        [FieldAction(field_key="contract_number", action="keep_existing")],
        existing_values={"contract_number": "HT-OLD"},
    )

    assert result.values == {"contract_number": "HT-OLD"}
    assert result.field_sources == {}


def test_complete_manual_entry_works_without_any_candidate():
    result = CandidateReviewService().apply_actions(
        CandidateReviewService().build_contract_candidates([]),
        [
            FieldAction(field_key="contract_number", action="manual", value="HT-1"),
            FieldAction(
                field_key="effective_from", action="manual", value=date(2026, 1, 1)
            ),
        ],
    )

    assert result.values == {
        "contract_number": "HT-1",
        "effective_from": date(2026, 1, 1),
    }
    assert result.field_sources == {
        "contract_number": "manual",
        "effective_from": "manual",
    }


def test_duplicate_candidates_keep_the_strongest_confidence() -> None:
    pages = [
        PageText(
            page_number=1,
            text_source="pdf_text",
            text_lines=["\u5408\u540c\u7f16\u53f7: C-001"],
        ),
        PageText(
            page_number=2,
            text_source="rapidocr",
            text_lines=["\u5408\u540c\u7f16\u53f7: C-001"],
        ),
    ]

    review = CandidateReviewService().build_contract_candidates(pages)

    assert review.fields["contract_number"].candidates[0].confidence_tier == "high"


def test_property_certificate_enrichment_candidates_merge_without_auto_selection() -> (
    None
):
    reviewer = CandidateReviewService()
    review = reviewer.build_property_certificate_candidates(
        [
            PageText(
                page_number=1,
                text_source="pdf_text",
                text_lines=["\u8bc1\u4e66\u7f16\u53f7: CERT-001"],
            )
        ]
    )
    enriched = FieldCandidate(
        field_key="certificate_number",
        value="CERT-002",
        text_source="pdf_text",
        extractor="deepseek",
        evidence=(
            CandidateEvidence(
                page_number=1,
                text="certificate number CERT-002",
                text_source="pdf_text",
            ),
        ),
        confidence_tier="medium",
    )

    merged = reviewer.merge_property_certificate_candidates(review, (enriched,))

    assert merged.fields["certificate_number"].conflict is True
    assert {item.value for item in merged.fields["certificate_number"].candidates} == {
        "CERT-001",
        "CERT-002",
    }
