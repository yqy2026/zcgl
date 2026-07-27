"""Fail-loud preflight contract for the local document-processing runtime."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from importlib import import_module, metadata
from pathlib import Path
from types import ModuleType
from typing import Protocol, cast

from .exception_handler import ConfigurationError

DEPENDENCY_SPECS = {
    "pymupdf": ("pymupdf", "1.24.14"),
    "rapidocr": ("rapidocr", "3.9.1"),
    "onnxruntime": ("onnxruntime", "1.20.1"),
}
_RAPIDOCR_ENGINE: object | None = None

MODEL_SHA256 = {
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


class DocumentProcessingRuntimeError(ConfigurationError):
    """Structured startup failure for a required local document component."""

    def __init__(
        self,
        runtime_error_code: str,
        component: str,
        message: str,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(
            message,
            config_key="DOCUMENT_PROCESSING_RUNTIME",
            details={
                "runtime_error_code": runtime_error_code,
                "component": component,
                **(details or {}),
            },
        )


class DocumentProcessingRuntimeProbe(Protocol):
    """System boundary used by startup to inspect installed runtime artifacts."""

    def load_dependency(self, module_name: str) -> None: ...

    def dependency_version(self, distribution_name: str) -> str: ...

    def model_sha256(self, filename: str) -> str: ...

    def initialize_engine(self) -> object: ...


class InstalledDocumentProcessingRuntimeProbe:
    """Inspect dependencies and models installed in the current process."""

    def __init__(self) -> None:
        self._modules: dict[str, ModuleType] = {}

    def load_dependency(self, module_name: str) -> None:
        self._modules[module_name] = import_module(module_name)

    def dependency_version(self, distribution_name: str) -> str:
        try:
            return metadata.version(distribution_name)
        except metadata.PackageNotFoundError as exc:
            raise ModuleNotFoundError(distribution_name) from exc

    def model_sha256(self, filename: str) -> str:
        rapidocr_module = self._modules.get("rapidocr")
        package_file = getattr(rapidocr_module, "__file__", None)
        if not isinstance(package_file, str):
            raise FileNotFoundError(filename)

        matches = list(Path(package_file).resolve().parent.rglob(filename))
        if len(matches) != 1:
            raise FileNotFoundError(filename)

        digest = hashlib.sha256()
        with matches[0].open("rb") as model_file:
            for block in iter(lambda: model_file.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    def initialize_engine(self) -> object:
        global _RAPIDOCR_ENGINE
        if _RAPIDOCR_ENGINE is not None:
            return _RAPIDOCR_ENGINE
        rapidocr_module = self._modules["rapidocr"]
        engine_factory = cast(
            Callable[[], object],
            getattr(rapidocr_module, "RapidOCR"),
        )
        _RAPIDOCR_ENGINE = engine_factory()
        return _RAPIDOCR_ENGINE


@dataclass(frozen=True)
class DocumentProcessingRuntimeReadiness:
    dependencies: dict[str, str]
    models: dict[str, str]
    engine_initialized: bool


def _validate_document_processing_runtime(
    probe: DocumentProcessingRuntimeProbe,
) -> DocumentProcessingRuntimeReadiness:
    dependencies: dict[str, str] = {}
    for distribution_name, (module_name, expected_version) in DEPENDENCY_SPECS.items():
        try:
            probe.load_dependency(module_name)
            installed_version = probe.dependency_version(distribution_name)
        except ModuleNotFoundError as exc:
            raise DocumentProcessingRuntimeError(
                "dependency_missing",
                distribution_name,
                f"Required document dependency is missing: {distribution_name}",
            ) from exc
        except Exception as exc:
            raise DocumentProcessingRuntimeError(
                "runtime_initialization_failed",
                distribution_name,
                f"Document dependency failed to load: {distribution_name}",
                details={"error_type": type(exc).__name__},
            ) from exc

        if installed_version != expected_version:
            raise DocumentProcessingRuntimeError(
                "dependency_version_mismatch",
                distribution_name,
                f"Required document dependency has an unexpected version: {distribution_name}",
                details={
                    "expected_version": expected_version,
                    "actual_version": installed_version,
                },
            )
        dependencies[distribution_name] = installed_version

    models: dict[str, str] = {}
    for filename, expected_digest in MODEL_SHA256.items():
        try:
            actual_digest = probe.model_sha256(filename)
        except FileNotFoundError as exc:
            raise DocumentProcessingRuntimeError(
                "model_missing",
                filename,
                f"Required RapidOCR model is missing: {filename}",
            ) from exc
        except OSError as exc:
            raise DocumentProcessingRuntimeError(
                "runtime_initialization_failed",
                filename,
                f"Required RapidOCR model cannot be read: {filename}",
                details={"error_type": type(exc).__name__},
            ) from exc

        if actual_digest != expected_digest:
            raise DocumentProcessingRuntimeError(
                "model_hash_mismatch",
                filename,
                f"RapidOCR model hash does not match the build manifest: {filename}",
                details={
                    "expected_sha256": expected_digest,
                    "actual_sha256": actual_digest,
                },
            )
        models[filename] = actual_digest

    try:
        probe.initialize_engine()
    except Exception as exc:
        raise DocumentProcessingRuntimeError(
            "runtime_initialization_failed",
            "rapidocr",
            "RapidOCR runtime initialization failed",
            details={"error_type": type(exc).__name__},
        ) from exc

    return DocumentProcessingRuntimeReadiness(
        dependencies=dependencies,
        models=models,
        engine_initialized=True,
    )


@lru_cache(maxsize=1)
def _validate_installed_document_processing_runtime() -> (
    DocumentProcessingRuntimeReadiness
):
    return _validate_document_processing_runtime(
        InstalledDocumentProcessingRuntimeProbe()
    )


def validate_document_processing_runtime(
    probe: DocumentProcessingRuntimeProbe | None = None,
) -> DocumentProcessingRuntimeReadiness:
    """Validate an explicit probe or the process-installed runtime once."""
    if probe is None:
        return _validate_installed_document_processing_runtime()
    return _validate_document_processing_runtime(probe)


def get_rapidocr_engine() -> object:
    """Return the process-wide RapidOCR instance initialized by preflight."""
    validate_document_processing_runtime()
    if _RAPIDOCR_ENGINE is None:  # pragma: no cover - preflight guarantees this
        raise RuntimeError("RapidOCR engine was not initialized")
    return _RAPIDOCR_ENGINE
