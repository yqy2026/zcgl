"""Tests for the ordered page text pipeline."""

from threading import Event, Lock, Thread

import fitz
import pytest
from PIL import Image

from src.services.document.page_text_pipeline import OrderedPageTextPipeline


def test_pdf_page_with_text_keeps_pdf_text_without_ocr(tmp_path):
    path = tmp_path / "digital.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Digital contract page")
    document.save(path)
    document.close()

    ocr_calls = []
    pipeline = OrderedPageTextPipeline(ocr_engine=lambda image: ocr_calls.append(image))

    result = pipeline.extract_pdf_pages(path)

    assert result.pages[0].text_source == "pdf_text"
    assert result.pages[0].text_lines == ["Digital contract page"]
    assert ocr_calls == []


def test_blank_pdf_page_uses_rapidocr_as_its_only_text_source(tmp_path):
    path = tmp_path / "scanned.pdf"
    document = fitz.open()
    document.new_page()
    document.save(path)
    document.close()

    pipeline = OrderedPageTextPipeline(ocr_engine=lambda image: ["OCR contract"])
    result = pipeline.extract_pdf_pages(path)

    assert result.pages[0].text_source == "rapidocr"
    assert result.pages[0].text_lines == ["OCR contract"]
    assert result.pages[0].error is None


def test_empty_rapidocr_result_is_a_successful_empty_page(tmp_path):
    class EmptyRapidOCRResult:
        txts = None
        scores = None
        boxes = None

    path = tmp_path / "empty-ocr.pdf"
    document = fitz.open()
    document.new_page()
    document.save(path)
    document.close()

    result = OrderedPageTextPipeline(
        ocr_engine=lambda image: EmptyRapidOCRResult()
    ).extract_pdf_pages(path)

    assert result.pages[0].text_source == "rapidocr"
    assert result.pages[0].text_lines == []
    assert result.pages[0].ocr_lines == []
    assert result.pages[0].error is None


def test_page_ocr_failure_preserves_following_page_order_and_text(tmp_path):
    path = tmp_path / "mixed.pdf"
    document = fitz.open()
    document.new_page()
    page = document.new_page()
    page.insert_text((72, 72), "Second digital contract page")
    document.save(path)
    document.close()

    def failing_ocr(image):
        raise RuntimeError("OCR failed")

    result = OrderedPageTextPipeline(ocr_engine=failing_ocr).extract_pdf_pages(path)

    assert [page.page_number for page in result.pages] == [1, 2]
    assert result.pages[0].error is not None
    assert result.pages[0].error.code == "page_ocr_failed"
    assert result.pages[1].text_source == "pdf_text"
    assert result.pages[1].text_lines == ["Second digital contract page"]


def test_png_is_processed_as_one_rapidocr_page(tmp_path):
    path = tmp_path / "certificate.png"
    Image.new("RGB", (32, 32), "white").save(path)

    result = OrderedPageTextPipeline(
        ocr_engine=lambda image: ["Certificate text"]
    ).extract_image_page(path)

    assert len(result.pages) == 1
    assert result.pages[0].text_source == "rapidocr"
    assert result.pages[0].text_lines == ["Certificate text"]


def test_rotated_image_is_processed_as_one_rapidocr_page(tmp_path):
    path = tmp_path / "rotated-certificate.png"
    Image.new("RGB", (32, 64), "white").rotate(90, expand=True).save(path)

    result = OrderedPageTextPipeline(
        ocr_engine=lambda image: ["Rotated certificate text"]
    ).extract_image_page(path)

    assert result.pages[0].text_source == "rapidocr"
    assert result.pages[0].text_lines == ["Rotated certificate text"]


def test_default_pipeline_reuses_preheated_runtime_engine(monkeypatch):
    from src.services.document import page_text_pipeline

    def engine(image):
        return []

    monkeypatch.setattr(
        "src.core.document_processing_runtime.get_rapidocr_engine", lambda: engine
    )

    pipeline = page_text_pipeline.get_ordered_page_text_pipeline()

    assert pipeline.ocr_engine is engine


def test_shared_pipeline_serializes_ocr_calls(tmp_path):
    path = tmp_path / "certificate.png"
    Image.new("RGB", (32, 32), "white").save(path)
    first_started = Event()
    release_first = Event()
    state_lock = Lock()
    calls = 0
    active = 0
    max_active = 0

    def engine(image):
        nonlocal active, calls, max_active
        with state_lock:
            calls += 1
            active += 1
            max_active = max(max_active, active)
            is_first_call = calls == 1
        if is_first_call:
            first_started.set()
            assert release_first.wait(timeout=1)
        with state_lock:
            active -= 1
        return ["Certificate text"]

    pipeline = OrderedPageTextPipeline(ocr_engine=engine)
    first = Thread(target=pipeline.extract_image_page, args=(path,))
    second = Thread(target=pipeline.extract_image_page, args=(path,))
    first.start()
    assert first_started.wait(timeout=1)
    second.start()
    assert calls == 1
    release_first.set()
    first.join(timeout=1)
    second.join(timeout=1)

    assert not first.is_alive()
    assert not second.is_alive()
    assert calls == 2
    assert max_active == 1


def test_page_timeout_is_a_recoverable_page_error(tmp_path, monkeypatch):
    from src.services.document import page_text_pipeline

    path = tmp_path / "timeout.pdf"
    document = fitz.open()
    document.new_page()
    document.save(path)
    document.close()
    clock = iter([0.0, 0.0, 0.0, 11.0, 11.0])
    monkeypatch.setattr(page_text_pipeline, "monotonic", lambda: next(clock))

    result = page_text_pipeline.OrderedPageTextPipeline(
        ocr_engine=lambda image: [], page_timeout_seconds=10
    ).extract_pdf_pages(path)

    assert result.pages[0].error is not None
    assert result.pages[0].error.code == "page_timeout"


def test_pdf_page_limit_is_a_terminal_pipeline_error(tmp_path):
    from src.services.document.page_text_pipeline import PagePipelineError

    path = tmp_path / "too-many-pages.pdf"
    document = fitz.open()
    document.new_page()
    document.new_page()
    document.save(path)
    document.close()

    pipeline = OrderedPageTextPipeline(ocr_engine=lambda image: [], max_pdf_pages=1)

    with pytest.raises(PagePipelineError, match="pdf_page_limit"):
        pipeline.extract_pdf_pages(path)


def test_image_larger_than_resource_limit_is_terminal(tmp_path):
    from src.services.document.page_text_pipeline import PagePipelineError

    path = tmp_path / "large.png"
    Image.new("RGB", (32, 32), "white").save(path)
    pipeline = OrderedPageTextPipeline(ocr_engine=lambda image: [], max_raster_bytes=1)

    with pytest.raises(PagePipelineError, match="page_resource_limit"):
        pipeline.extract_image_page(path)


def test_document_timeout_after_a_page_is_terminal(tmp_path, monkeypatch):
    from src.services.document import page_text_pipeline
    from src.services.document.page_text_pipeline import PagePipelineError

    path = tmp_path / "slow-document.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Digital contract page")
    document.save(path)
    document.close()
    clock = iter([0.0, 0.0, 181.0])
    monkeypatch.setattr(page_text_pipeline, "monotonic", lambda: next(clock))

    pipeline = OrderedPageTextPipeline(ocr_engine=lambda image: [])

    with pytest.raises(PagePipelineError, match="document_timeout"):
        pipeline.extract_pdf_pages(path)


def test_default_pipeline_processes_a_normal_24_page_contract(tmp_path):
    path = tmp_path / "normal-contract.pdf"
    document = fitz.open()
    for page_number in range(24):
        page = document.new_page()
        page.insert_text(
            (72, 72), f"Contract page {page_number + 1} contains readable lease terms"
        )
    document.save(path)
    document.close()

    result = OrderedPageTextPipeline(ocr_engine=lambda image: []).extract_pdf_pages(
        path
    )

    assert [page.page_number for page in result.pages] == list(range(1, 25))
    assert all(page.text_source == "pdf_text" for page in result.pages)
