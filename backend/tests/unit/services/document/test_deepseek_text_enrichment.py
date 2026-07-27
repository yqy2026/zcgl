"""Offline tests for the optional DeepSeek text candidate stage."""

from dataclasses import dataclass

import pytest
from pydantic import ValidationError

from src.core.config_llm import LlmSettings
from src.services.document.deepseek_text_enrichment import DeepSeekTextEnricher
from src.services.document.page_text_pipeline import PageText


@dataclass
class _Response:
    status_code: int
    payload: object

    def json(self):
        return self.payload


def _settings(**overrides):
    values = {
        "DOCUMENT_LLM_ENABLED": True,
        "DEEPSEEK_API_KEY": "test-key",
        "DEEPSEEK_MODEL": "deepseek-v4-flash",
        "DEEPSEEK_BASE_URL": "https://api.deepseek.com/v1",
    }
    values.update(overrides)
    return LlmSettings(**values)


def _pages():
    return [
        PageText(
            page_number=1,
            text_source="pdf_text",
            text_lines=["合同编号：HT-2026-001", "身份证：440101199001011234"],
        )
    ]


def _success_payload(**overrides):
    payload = {
        "version": "contract-extraction/v1",
        "document_type": "contract",
        "candidates": [
            {
                "field_key": "contract_number",
                "value": "HT-2026-001",
                "evidence": {"page_number": 1, "text": "合同编号：HT-2026-001"},
            }
        ],
    }
    payload.update(overrides)
    return payload


def test_disabled_stage_skips_without_constructing_a_request():
    enricher = DeepSeekTextEnricher(LlmSettings())

    result = enricher.enrich("contract", _pages(), session_id="session-1")

    assert result.status == "skipped"
    assert result.code == "llm_disabled"
    assert result.candidates == ()


def test_enabled_stage_uses_fixed_text_only_request_and_returns_candidates():
    requests = []

    def post(url, *, headers, json, timeout):
        requests.append((url, headers, json, timeout))
        return _Response(200, _success_payload())

    result = DeepSeekTextEnricher(_settings(), post=post).enrich(
        "contract", _pages(), session_id="session-1"
    )

    assert result.status == "success"
    assert result.candidates[0].extractor == "deepseek"
    assert requests[0][2]["model"] == "deepseek-v4-flash"
    assert requests[0][2]["temperature"] == 0
    assert requests[0][2]["stream"] is False
    assert requests[0][2]["thinking"] == {"type": "disabled"}
    assert requests[0][2]["response_format"] == {"type": "json_object"}
    assert requests[0][3] == 120
    assert "440101199001011234" not in requests[0][2]["messages"][1]["content"]
    assert "session-1" not in requests[0][2]["messages"][1]["content"]


@pytest.mark.parametrize(
    ("response", "expected_code"),
    [
        (_Response(429, {}), "llm_http_error"),
        (_Response(500, {}), "llm_http_error"),
        (_Response(200, {"unexpected": "payload"}), "llm_response_invalid"),
        (_Response(200, _success_payload(version="contract-extraction/v2")), "llm_response_invalid"),
        (_Response(200, _success_payload(document_type="property_certificate")), "llm_response_invalid"),
        (
            _Response(
                200,
                _success_payload(
                    candidates=[
                        {
                            "field_key": "unknown_field",
                            "value": "ignore previous instructions",
                            "evidence": {"page_number": 1, "text": "not in source"},
                        }
                    ]
                ),
            ),
            "llm_response_invalid",
        ),
    ],
)
def test_invalid_or_failed_response_discards_the_entire_llm_batch(response, expected_code):
    result = DeepSeekTextEnricher(_settings(), post=lambda *args, **kwargs: response).enrich(
        "contract", _pages(), session_id="session-1"
    )

    assert result.status == "failed"
    assert result.code == expected_code
    assert result.candidates == ()


def test_timeout_discards_the_entire_llm_batch():
    def post(*args, **kwargs):
        raise TimeoutError

    result = DeepSeekTextEnricher(_settings(), post=post).enrich(
        "contract", _pages(), session_id="session-1"
    )

    assert result.status == "failed"
    assert result.code == "llm_timeout"
    assert result.candidates == ()


def test_enabled_stage_requires_exact_model_key_and_official_base_url():
    with pytest.raises(ValidationError):
        LlmSettings(DOCUMENT_LLM_ENABLED=True)
    with pytest.raises(ValidationError):
        _settings(DEEPSEEK_MODEL="other-model")
    with pytest.raises(ValidationError):
        _settings(DEEPSEEK_BASE_URL="https://example.invalid/v1")


def test_enabled_stage_batches_a_24_page_contract_and_discards_all_candidates_on_batch_failure():
    pages = [
        PageText(page_number=index, text_source="pdf_text", text_lines=[f"Page {index}"])
        for index in range(1, 25)
    ]
    first_batch_candidate = {
        "field_key": "contract_number",
        "value": "batch-1",
        "evidence": {"page_number": 1, "text": "Page 1"},
    }
    responses = iter(
        [_Response(200, _success_payload(candidates=[first_batch_candidate])), _Response(500, {})]
    )
    requests = []

    def post(*args, **kwargs):
        requests.append((args, kwargs))
        return next(responses)

    result = DeepSeekTextEnricher(_settings(), post=post).enrich(
        "contract", pages, session_id="session-1"
    )

    first_batch = requests[0][1]["json"]["messages"][1]["content"]
    second_batch = requests[1][1]["json"]["messages"][1]["content"]
    assert len(requests) == 2
    assert "[20] Page 20" in first_batch
    assert "[21]" not in first_batch
    assert "[21] Page 21" in second_batch
    assert "[24] Page 24" in second_batch
    assert "[20]" not in second_batch
    assert result.status == "failed"
    assert result.code == "llm_http_error"
    assert result.candidates == ()
