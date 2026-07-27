"""Startup contract tests for the local document-processing runtime."""

from __future__ import annotations

import socket
from dataclasses import dataclass, field

import pytest

from src.core.document_processing_runtime import (
    DocumentProcessingRuntimeError,
    validate_document_processing_runtime,
)

EXPECTED_DEPENDENCIES = {
    "pymupdf": "1.24.14",
    "rapidocr": "3.9.1",
    "onnxruntime": "1.20.1",
}
EXPECTED_MODELS = {
    "PP-OCRv6_det_small.onnx": (
        "090f04abcd9d9a7498bc4ebf677e4cb9bdce1fe4197ddb7e529f1ef44e1ff94f"
    ),
    "ch_ppocr_mobile_v2.0_cls_mobile.onnx": (
        "e47acedf663230f8863ff1ab0e64dd2d82b838fceb5957146dab185a89d6215c"
    ),
    "PP-OCRv6_rec_small.onnx": (
        "6f327246b50388f3c176ae304bd95767ea6dc0c9ae92153ef8cbe210b3c14884"
    ),
}


@dataclass
class RuntimeProbeStub:
    dependency_versions: dict[str, str] = field(
        default_factory=lambda: EXPECTED_DEPENDENCIES.copy()
    )
    model_hashes: dict[str, str] = field(default_factory=lambda: EXPECTED_MODELS.copy())
    missing_dependencies: set[str] = field(default_factory=set)
    initialization_error: Exception | None = None
    initialized: bool = False

    def load_dependency(self, module_name: str) -> None:
        if module_name in self.missing_dependencies:
            raise ModuleNotFoundError(module_name)

    def dependency_version(self, distribution_name: str) -> str:
        return self.dependency_versions[distribution_name]

    def model_sha256(self, filename: str) -> str:
        if filename not in self.model_hashes:
            raise FileNotFoundError(filename)
        return self.model_hashes[filename]

    def initialize_engine(self) -> object:
        if self.initialization_error is not None:
            raise self.initialization_error
        self.initialized = True
        return object()


@pytest.mark.unit
def test_preflight_reports_fixed_runtime_when_all_artifacts_match() -> None:
    probe = RuntimeProbeStub()

    result = validate_document_processing_runtime(probe)

    assert result.dependencies == EXPECTED_DEPENDENCIES
    assert result.models == EXPECTED_MODELS
    assert result.engine_initialized is True
    assert probe.initialized is True


@pytest.mark.unit
def test_preflight_identifies_the_missing_runtime_dependency() -> None:
    probe = RuntimeProbeStub(missing_dependencies={"rapidocr"})

    with pytest.raises(DocumentProcessingRuntimeError) as exc_info:
        validate_document_processing_runtime(probe)

    assert exc_info.value.details == {
        "config_key": "DOCUMENT_PROCESSING_RUNTIME",
        "runtime_error_code": "dependency_missing",
        "component": "rapidocr",
    }
    assert probe.initialized is False


@pytest.mark.unit
def test_preflight_rejects_a_runtime_dependency_version_drift() -> None:
    probe = RuntimeProbeStub()
    probe.dependency_versions["pymupdf"] = "1.24.13"

    with pytest.raises(DocumentProcessingRuntimeError) as exc_info:
        validate_document_processing_runtime(probe)

    assert exc_info.value.details == {
        "config_key": "DOCUMENT_PROCESSING_RUNTIME",
        "runtime_error_code": "dependency_version_mismatch",
        "component": "pymupdf",
        "expected_version": "1.24.14",
        "actual_version": "1.24.13",
    }
    assert probe.initialized is False


@pytest.mark.unit
def test_preflight_identifies_the_missing_rapidocr_model() -> None:
    probe = RuntimeProbeStub()
    probe.model_hashes.pop("PP-OCRv6_rec_small.onnx")

    with pytest.raises(DocumentProcessingRuntimeError) as exc_info:
        validate_document_processing_runtime(probe)

    assert exc_info.value.details == {
        "config_key": "DOCUMENT_PROCESSING_RUNTIME",
        "runtime_error_code": "model_missing",
        "component": "PP-OCRv6_rec_small.onnx",
    }
    assert probe.initialized is False


@pytest.mark.unit
def test_preflight_rejects_a_rapidocr_model_hash_mismatch() -> None:
    probe = RuntimeProbeStub()
    probe.model_hashes["PP-OCRv6_det_small.onnx"] = "0" * 64

    with pytest.raises(DocumentProcessingRuntimeError) as exc_info:
        validate_document_processing_runtime(probe)

    assert exc_info.value.details == {
        "config_key": "DOCUMENT_PROCESSING_RUNTIME",
        "runtime_error_code": "model_hash_mismatch",
        "component": "PP-OCRv6_det_small.onnx",
        "expected_sha256": EXPECTED_MODELS["PP-OCRv6_det_small.onnx"],
        "actual_sha256": "0" * 64,
    }
    assert probe.initialized is False


@pytest.mark.unit
def test_preflight_identifies_rapidocr_engine_initialization_failure() -> None:
    probe = RuntimeProbeStub(initialization_error=RuntimeError("invalid ONNX graph"))

    with pytest.raises(DocumentProcessingRuntimeError) as exc_info:
        validate_document_processing_runtime(probe)

    assert exc_info.value.details == {
        "config_key": "DOCUMENT_PROCESSING_RUNTIME",
        "runtime_error_code": "runtime_initialization_failed",
        "component": "rapidocr",
        "error_type": "RuntimeError",
    }
    assert probe.initialized is False


@pytest.mark.unit
def test_installed_runtime_uses_bundled_models_without_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def reject_network(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("document runtime preflight attempted network access")

    monkeypatch.setattr(socket.socket, "connect", reject_network)

    result = validate_document_processing_runtime()

    assert result.dependencies == EXPECTED_DEPENDENCIES
    assert result.models == EXPECTED_MODELS
    assert result.engine_initialized is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_app_lifespan_stops_when_document_runtime_preflight_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src import main as main_module

    startup_error = DocumentProcessingRuntimeError(
        "model_missing",
        "PP-OCRv6_det_small.onnx",
        "required model missing",
    )

    def fail_preflight() -> None:
        raise startup_error

    monkeypatch.setattr(
        main_module,
        "validate_document_processing_runtime",
        fail_preflight,
    )

    with pytest.raises(DocumentProcessingRuntimeError) as exc_info:
        async with main_module.lifespan(main_module.app):
            pass

    assert exc_info.value is startup_error


@pytest.mark.unit
def test_document_llm_defaults_disabled_without_remote_credentials() -> None:
    from src.core.config_llm import LlmSettings

    settings = LlmSettings()

    assert settings.DOCUMENT_LLM_ENABLED is False
    assert settings.DEEPSEEK_API_KEY is None
    assert settings.DEEPSEEK_MODEL is None
