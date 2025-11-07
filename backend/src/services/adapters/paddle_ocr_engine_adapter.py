from typing import Any

"""
PaddleOCREngineAdapter

一个符�?IOCRService 接口的适配器，直接使用 PaddleOCR 处理 PDF�?该适配器用�?DI 提供者在需要时切换�?PaddleOCR 引擎�?
注意：为避免启动时的重量级初始化，相关库在方法内延迟导入�?"""

import asyncio
import time
import logging
import os

logger = logging.getLogger(__name__)


class PaddleOCREngineAdapter:
    def __init__(self) -> None:
        self._stats = {
            "total_pages": 0,
            "processed_pages": 0,
            "total_text_length": 0,
            "avg_confidence": 0.0,
            "total_processing_time": 0.0,
            "pages_with_text": 0,
            "pages_without_text": 0,
        }

    async def process_pdf_document(
        self,
        pdf_path: str,
        max_pages: int = 10,
        max_concurrency: int | None = None,
        use_preprocessing: bool = True,
    ) -> dict[str, Any]:
        start = time.time()

        # 延迟导入，避免启动失�?        try:
            from pdf2image import convert_from_path
            from paddleocr import PaddleOCR
        except Exception as e:
            logger.error(f"PaddleOCR �?pdf2image 导入失败: {e}")
            return {"success": False, "error": str(e)}

        try:
            pages = convert_from_path(pdf_path, dpi=300)
        except Exception as e:
            logger.error(f"PDF 转图片失�? {e}")
            return {"success": False, "error": f"convert_from_path 失败: {e}"}

        if max_pages is not None:
            pages = pages[:max_pages]

        # 初始�?OCR 引擎（中文，从环境变量读取配置）
        try:
            lang = os.getenv("OCR_LANG", "ch")
            use_gpu = os.getenv("OCR_USE_GPU", "false").lower() in {"1", "true", "yes"}
            use_angle_cls = os.getenv("OCR_USE_ANGLE_CLS", "true").lower() in {"1", "true", "yes"}
            enable_mkldnn = os.getenv("OCR_ENABLE_MKLDNN", "true").lower() in {"1", "true", "yes"}
            det_limit_side_len = int(os.getenv("OCR_DET_LIMIT_SIDE_LEN", "960"))
            rec_batch_num = int(os.getenv("OCR_REC_BATCH_NUM", "6"))
            det_db_thresh = float(os.getenv("OCR_DET_DB_THRESH", "0.3"))
            drop_score = float(os.getenv("OCR_DROP_SCORE", "0.5"))

            base_args = {
                "lang": lang,
                "use_gpu": use_gpu,
                "det_limit_side_len": det_limit_side_len,
                "rec_batch_num": rec_batch_num,
                "det_db_thresh": det_db_thresh,
                "drop_score": drop_score,
            }
            if enable_mkldnn:
                base_args["enable_mkldnn"] = True

            use_textline_orientation = os.getenv("OCR_USE_TEXTLINE_ORIENTATION", "true").lower() in {"1", "true", "yes"}
            try:
                ocr = PaddleOCR(
                    **base_args,
                    use_textline_orientation=use_textline_orientation,
                )
            except Exception as e:
                msg = str(e)
                if "Unknown argument" in msg and "use_textline_orientation" in msg:
                    try:
                        ocr = PaddleOCR(
                            **base_args,
                            use_angle_cls=use_angle_cls,
                        )
                    except Exception as e2:
                        if "Unknown argument" in str(e2) and "enable_mkldnn" in str(e2):
                            base_args.pop("enable_mkldnn", None)
                            ocr = PaddleOCR(
                                **base_args,
                                use_angle_cls=use_angle_cls,
                            )
                        else:
                            raise
                else:
                    if "Unknown argument" in msg and "enable_mkldnn" in msg:
                        base_args.pop("enable_mkldnn", None)
                        ocr = PaddleOCR(
                            **base_args,
                            use_textline_orientation=use_textline_orientation,
                        )
                    else:
                        raise
        except Exception as e:
            logger.error(f"PaddleOCR 初始化失�? {e}")
            return {"success": False, "error": f"OCR 初始化失�? {e}"}

        semaphore = asyncio.Semaphore(max_concurrency or len(pages) or 1)

        async def _process(idx: int, pil_img) -> dict[str, Any]:
            async with semaphore:
                try:
                    # OCR 推理
                    result = await asyncio.to_thread(ocr.ocr, pil_img, cls=False)
                    text_lines: list[str] = []
                    confidences: list[float] = []
                    for line in (result[0] or []):
                        txt = line[1][0]
                        conf = float(line[1][1] or 0.0)
                        text_lines.append(txt)
                        confidences.append(conf)

                    page_text = "\n".join(text_lines)
                    avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

                    return {
                        "page_index": idx,
                        "text": page_text,
                        "confidence": avg_conf,
                        "used_preprocessing": use_preprocessing,
                    }
                except Exception as e:
                    logger.error(f"页面 {idx + 1} OCR 失败: {e}")
                    return {
                        "page_index": idx,
                        "text": "",
                        "confidence": 0.0,
                        "error": str(e),
                    }

        tasks = [
            _process(i, p)
            for i, p in enumerate(pages)
        ]

        page_results = await asyncio.gather(*tasks)

        combined_text = "\n".join([pr.get("text", "") for pr in page_results])
        confidences = [float(pr.get("confidence", 0.0)) for pr in page_results if pr.get("confidence") is not None]

        total_time = time.time() - start
        processed_pages = len(page_results)
        pages_with_text = sum(1 for pr in page_results if len(pr.get("text", "")) > 0)

        self._stats.update(
            {
                "total_pages": processed_pages,
                "processed_pages": processed_pages,
                "total_text_length": len(combined_text),
                "avg_confidence": sum(confidences) / len(confidences) if confidences else 0.0,
                "total_processing_time": total_time,
                "pages_with_text": pages_with_text,
                "pages_without_text": processed_pages - pages_with_text,
            }
        )

        return {
            "success": True,
            "combined_text": combined_text,
            "page_results": page_results,
            "processing_stats": self._stats.copy(),
            "concurrency_used": int(max_concurrency or 0),
            "pages_per_second": processed_pages / total_time if total_time > 0 else 0.0,
        }

    async def process_pdf_page(self, page: Any, page_num: int, use_preprocessing: bool = True) -> Any:
        """处理单页。若需要直接处�?PyMuPDF 页面，可先转换为 PIL.Image 再调�?OCR。此处给出简单占位实现�?""
        try:
            from paddleocr import PaddleOCR
            import numpy as np
        except Exception as e:
            logger.error(f"PaddleOCR/Numpy 导入失败: {e}")
            return {"page_index": page_num, "text": "", "confidence": 0.0, "error": str(e)}

        try:
            lang = os.getenv("OCR_LANG", "ch")
            use_gpu = os.getenv("OCR_USE_GPU", "false").lower() in {"1", "true", "yes"}
            use_angle_cls = os.getenv("OCR_USE_ANGLE_CLS", "true").lower() in {"1", "true", "yes"}
            enable_mkldnn = os.getenv("OCR_ENABLE_MKLDNN", "true").lower() in {"1", "true", "yes"}
            det_limit_side_len = int(os.getenv("OCR_DET_LIMIT_SIDE_LEN", "960"))
            rec_batch_num = int(os.getenv("OCR_REC_BATCH_NUM", "6"))
            det_db_thresh = float(os.getenv("OCR_DET_DB_THRESH", "0.3"))
            drop_score = float(os.getenv("OCR_DROP_SCORE", "0.5"))
            base_args = {
                "lang": lang,
                "use_gpu": use_gpu,
                "det_limit_side_len": det_limit_side_len,
                "rec_batch_num": rec_batch_num,
                "det_db_thresh": det_db_thresh,
                "drop_score": drop_score,
            }
            if enable_mkldnn:
                base_args["enable_mkldnn"] = True

            use_textline_orientation = os.getenv("OCR_USE_TEXTLINE_ORIENTATION", "true").lower() in {"1", "true", "yes"}
            try:
                ocr = PaddleOCR(
                    **base_args,
                    use_textline_orientation=use_textline_orientation,
                )
            except Exception as e:
                msg = str(e)
                if "Unknown argument" in msg and "use_textline_orientation" in msg:
                    try:
                        ocr = PaddleOCR(
                            **base_args,
                            use_angle_cls=use_angle_cls,
                        )
                    except Exception as e2:
                        if "Unknown argument" in str(e2) and "enable_mkldnn" in str(e2):
                            base_args.pop("enable_mkldnn", None)
                            ocr = PaddleOCR(
                                **base_args,
                                use_angle_cls=use_angle_cls,
                            )
                        else:
                            raise
                else:
                    if "Unknown argument" in msg and "enable_mkldnn" in msg:
                        base_args.pop("enable_mkldnn", None)
                        ocr = PaddleOCR(
                            **base_args,
                            use_textline_orientation=use_textline_orientation,
                        )
                    else:
                        raise
            # page 需�?numpy/pil 图片；此处假设已�?numpy array �?PIL.Image
            result = await asyncio.to_thread(ocr.ocr, page, cls=False)
            text_lines = [line[1][0] for line in (result[0] or [])]
            confidences = [float(line[1][1] or 0.0) for line in (result[0] or [])]
            page_text = "\n".join(text_lines)
            avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
            return {"page_index": page_num, "text": page_text, "confidence": avg_conf}
        except Exception as e:
            logger.error(f"页面 {page_num + 1} OCR 失败: {e}")
            return {"page_index": page_num, "text": "", "confidence": 0.0, "error": str(e)}

    def get_performance_report(self) -> dict[str, Any]:
        return {
            "engine": "paddle",
            "stats": self._stats.copy(),
        }