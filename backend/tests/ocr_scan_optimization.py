#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OCR扫描件优化测试脚本
专门处理扫描件PDF的OCR文本提取问题
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Any

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('ocr_optimization.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

class OCRScanOptimization:
    """OCR扫描件优化类"""

    def __init__(self):
        self.optimization_results = {
            "test_file": "",
            "original_ocr": {},
            "optimized_ocr": {},
            "improvements": {},
            "recommendations": []
        }

    async def test_ocr_with_different_settings(self, pdf_path: str) -> Dict[str, Any]:
        """测试不同OCR设置的效果"""
        logger.info(f"开始OCR优化测试: {Path(pdf_path).name}")

        results = {
            "file_info": self._analyze_pdf_file(pdf_path),
            "ocr_tests": {},
            "best_result": {},
            "recommendations": []
        }

        try:
            # 测试1: 使用新的PaddleOCR参数
            logger.info("测试1: 使用新的PaddleOCR参数")
            results["ocr_tests"]["new_paddleocr"] = await self._test_new_paddleocr(pdf_path)

            # 测试2: 使用图像预处理
            logger.info("测试2: 使用图像预处理")
            results["ocr_tests"]["preprocessed_ocr"] = await self._test_preprocessed_ocr(pdf_path)

            # 测试3: 使用多分辨率
            logger.info("测试3: 使用多分辨率处理")
            results["ocr_tests"]["multi_resolution"] = await self._test_multi_resolution(pdf_path)

            # 测试4: 使用PyMuPDF文本提取作为补充
            logger.info("测试4: 使用PyMuPDF文本提取")
            results["ocr_tests"]["pymupdf_text"] = await self._test_pymupdf_extraction(pdf_path)

            # 测试5: 组合方法
            logger.info("测试5: 组合方法")
            results["ocr_tests"]["combined_method"] = await self._test_combined_method(pdf_path)

            # 找到最佳结果
            results["best_result"] = self._find_best_ocr_result(results["ocr_tests"])

            # 生成建议
            results["recommendations"] = self._generate_recommendations(results)

            return results

        except Exception as e:
            logger.error(f"OCR优化测试失败: {e}")
            results["error"] = str(e)
            return results

    def _analyze_pdf_file(self, pdf_path: str) -> Dict[str, Any]:
        """分析PDF文件特征"""
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(pdf_path)
            page_count = doc.page_count

            # 分析页面特征
            page_info = []
            total_text_length = 0
            has_images = False

            for i, page in enumerate(doc):
                text = page.get_text()
                text_length = len(text.strip())
                total_text_length += text_length

                # 检查是否有图像
                image_list = page.get_images()
                page_has_images = len(image_list) > 0
                if page_has_images:
                    has_images = True

                page_info.append({
                    "page_num": i + 1,
                    "text_length": text_length,
                    "has_images": page_has_images,
                    "image_count": len(image_list),
                    "is_scanned_page": text_length < 50 and page_has_images
                })

            doc.close()

            # 判断是否为扫描件
            scanned_ratio = sum(1 for p in page_info if p["is_scanned_page"]) / len(page_info)

            return {
                "file_path": pdf_path,
                "page_count": page_count,
                "total_text_length": total_text_length,
                "avg_text_per_page": total_text_length / page_count if page_count > 0 else 0,
                "has_images": has_images,
                "scanned_page_ratio": scanned_ratio,
                "is_likely_scanned": scanned_ratio > 0.5,
                "page_details": page_info[:3]  # 只保留前3页详情
            }

        except Exception as e:
            logger.error(f"PDF文件分析失败: {e}")
            return {"error": str(e)}

    async def _test_new_paddleocr(self, pdf_path: str) -> Dict[str, Any]:
        """测试新的PaddleOCR参数"""
        try:
            import time
            import fitz
            from paddleocr import PaddleOCR

            start_time = time.time()

            # 使用新的参数
            ocr = PaddleOCR(
                use_textline_orientation=True,
                lang='ch',
                use_gpu=False  # 确保使用CPU
            )

            doc = fitz.open(pdf_path)
            all_text = []
            total_confidence = 0
            text_count = 0

            # 只处理前3页进行测试
            for page in doc[:3]:
                # 渲染为图像
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 提高分辨率
                img_bytes = pix.tobytes("png")

                # OCR识别
                result = ocr.ocr(img_bytes, cls=True)

                if result and result[0]:
                    page_text = ""
                    page_confidence = 0

                    for line in result[0]:
                        text = line[1][0]
                        confidence = line[1][1]

                        page_text += text + "\n"
                        page_confidence += confidence

                    all_text.append(page_text)
                    total_confidence += page_confidence / len(result[0]) if result[0] else 0
                    text_count += 1

            doc.close()

            total_time = time.time() - start_time
            combined_text = "\n".join(all_text)
            avg_confidence = total_confidence / text_count if text_count > 0 else 0

            return {
                "success": True,
                "processing_time": total_time,
                "text_length": len(combined_text),
                "text_preview": combined_text[:200] + "..." if len(combined_text) > 200 else combined_text,
                "avg_confidence": avg_confidence,
                "pages_processed": text_count,
                "method": "new_paddleocr"
            }

        except Exception as e:
            logger.error(f"新PaddleOCR测试失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "method": "new_paddleocr"
            }

    async def _test_preprocessed_ocr(self, pdf_path: str) -> Dict[str, Any]:
        """测试带图像预处理的OCR"""
        try:
            import time
            import fitz
            from paddleocr import PaddleOCR
            from PIL import Image
            import io

            start_time = time.time()

            ocr = PaddleOCR(
                use_textline_orientation=True,
                lang='ch'
            )

            doc = fitz.open(pdf_path)
            all_text = []
            total_confidence = 0
            text_count = 0

            for page in doc[:3]:
                # 渲染为图像
                pix = page.get_pixmap(matrix=fitz.Matrix(3, 3))  # 高分辨率
                img_bytes = pix.tobytes("png")

                # 图像预处理
                image = Image.open(io.BytesIO(img_bytes))

                # 转换为灰度
                if image.mode != 'L':
                    image = image.convert('L')

                # 增强对比度
                from PIL import ImageEnhance
                enhancer = ImageEnhance.Contrast(image)
                image = enhancer.enhance(2.0)

                # 增强锐度
                enhancer = ImageEnhance.Sharpness(image)
                image = enhancer.enhance(2.0)

                # 转换回字节
                img_buffer = io.BytesIO()
                image.save(img_buffer, format='PNG')
                processed_img_bytes = img_buffer.getvalue()

                # OCR识别
                result = ocr.ocr(processed_img_bytes, cls=True)

                if result and result[0]:
                    page_text = ""
                    page_confidence = 0

                    for line in result[0]:
                        text = line[1][0]
                        confidence = line[1][1]

                        page_text += text + "\n"
                        page_confidence += confidence

                    all_text.append(page_text)
                    total_confidence += page_confidence / len(result[0]) if result[0] else 0
                    text_count += 1

            doc.close()

            total_time = time.time() - start_time
            combined_text = "\n".join(all_text)
            avg_confidence = total_confidence / text_count if text_count > 0 else 0

            return {
                "success": True,
                "processing_time": total_time,
                "text_length": len(combined_text),
                "text_preview": combined_text[:200] + "..." if len(combined_text) > 200 else combined_text,
                "avg_confidence": avg_confidence,
                "pages_processed": text_count,
                "method": "preprocessed_ocr"
            }

        except Exception as e:
            logger.error(f"预处理OCR测试失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "method": "preprocessed_ocr"
            }

    async def _test_multi_resolution(self, pdf_path: str) -> Dict[str, Any]:
        """测试多分辨率处理"""
        try:
            import time
            import fitz
            from paddleocr import PaddleOCR

            start_time = time.time()

            ocr = PaddleOCR(
                use_textline_orientation=True,
                lang='ch'
            )

            doc = fitz.open(pdf_path)
            best_text = ""
            best_confidence = 0

            # 测试不同分辨率
            resolutions = [1.5, 2.0, 3.0]

            for scale in resolutions:
                try:
                    test_text = ""
                    test_confidence = 0
                    test_count = 0

                    for page in doc[:2]:  # 只测试前2页
                        pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale))
                        img_bytes = pix.tobytes("png")

                        result = ocr.ocr(img_bytes, cls=True)

                        if result and result[0]:
                            page_text = ""
                            page_confidence = 0

                            for line in result[0]:
                                text = line[1][0]
                                confidence = line[1][1]

                                page_text += text + "\n"
                                page_confidence += confidence

                            test_text += page_text
                            test_confidence += page_confidence / len(result[0]) if result[0] else 0
                            test_count += 1

                    avg_confidence = test_confidence / test_count if test_count > 0 else 0

                    # 如果这个分辨率效果更好，保存结果
                    if len(test_text) > len(best_text) or avg_confidence > best_confidence:
                        best_text = test_text
                        best_confidence = avg_confidence

                        logger.info(f"分辨率 {scale}x 效果更好，文本长度: {len(test_text)}")

                except Exception as e:
                    logger.warning(f"分辨率 {scale}x 测试失败: {e}")
                    continue

            doc.close()

            total_time = time.time() - start_time

            return {
                "success": True,
                "processing_time": total_time,
                "text_length": len(best_text),
                "text_preview": best_text[:200] + "..." if len(best_text) > 200 else best_text,
                "avg_confidence": best_confidence,
                "best_resolution": f"Found in resolution tests",
                "method": "multi_resolution"
            }

        except Exception as e:
            logger.error(f"多分辨率测试失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "method": "multi_resolution"
            }

    async def _test_pymupdf_extraction(self, pdf_path: str) -> Dict[str, Any]:
        """测试PyMuPDF文本提取"""
        try:
            import time
            import fitz

            start_time = time.time()

            doc = fitz.open(pdf_path)

            # 测试不同的文本提取方法
            methods_results = {}

            # 方法1: 普通文本提取
            text = ""
            for page in doc:
                page_text = page.get_text()
                text += page_text + "\n"

            methods_results["plain_text"] = {
                "text_length": len(text),
                "preview": text[:200]
            }

            # 方法2: 带格式的文本提取
            text_formatted = ""
            for page in doc:
                page_text = page.get_text("text")
                text_formatted += page_text + "\n"

            methods_results["formatted_text"] = {
                "text_length": len(text_formatted),
                "preview": text_formatted[:200]
            }

            # 方法3: 单词和页面布局分析
            words = []
            for page in doc:
                page_words = page.get_text("words")
                if page_words:
                    words.extend(page_words)

            # 拼接单词
            text_words = " ".join([word[4] for word in words])  # word[4]是单词文本

            methods_results["words_extraction"] = {
                "text_length": len(text_words),
                "word_count": len(words),
                "preview": text_words[:200]
            }

            doc.close()

            total_time = time.time() - start_time

            # 选择最佳结果
            best_method = max(methods_results.keys(), key=lambda k: methods_results[k]["text_length"])
            best_result = methods_results[best_method]

            return {
                "success": True,
                "processing_time": total_time,
                "text_length": best_result["text_length"],
                "text_preview": best_result["preview"],
                "best_method": best_method,
                "all_methods": methods_results,
                "method": "pymupdf_extraction"
            }

        except Exception as e:
            logger.error(f"PyMuPDF提取测试失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "method": "pymupdf_extraction"
            }

    async def _test_combined_method(self, pdf_path: str) -> Dict[str, Any]:
        """测试组合方法"""
        try:
            import time

            start_time = time.time()

            # 获取各种方法的结果
            results = {}

            # PyMuPDF提取
            pymupdf_result = await self._test_pymupdf_extraction(pdf_path)
            if pymupdf_result["success"]:
                results["pymupdf"] = pymupdf_result

            # 新的PaddleOCR
            paddleocr_result = await self._test_new_paddleocr(pdf_path)
            if paddleocr_result["success"]:
                results["paddleocr"] = paddleocr_result

            # 预处理OCR（如果有PIL）
            try:
                preprocessed_result = await self._test_preprocessed_ocr(pdf_path)
                if preprocessed_result["success"]:
                    results["preprocessed"] = preprocessed_result
            except ImportError:
                logger.warning("PIL未安装，跳过预处理测试")

            # 选择最佳结果
            if results:
                best_method = max(results.keys(),
                              key=lambda k: results[k]["text_length"])
                best_result = results[best_method]

                return {
                    "success": True,
                    "processing_time": time.time() - start_time,
                    "text_length": best_result["text_length"],
                    "text_preview": best_result["text_preview"],
                    "best_method": best_method,
                    "all_results": results,
                    "method": "combined_method"
                }
            else:
                return {
                    "success": False,
                    "error": "All combined methods failed",
                    "method": "combined_method"
                }

        except Exception as e:
            logger.error(f"组合方法测试失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "method": "combined_method"
            }

    def _find_best_ocr_result(self, ocr_tests: Dict[str, Any]) -> Dict[str, Any]:
        """找到最佳的OCR结果"""
        successful_tests = {k: v for k, v in ocr_tests.items() if v.get("success", False)}

        if not successful_tests:
            return {
                "best_method": "none",
                "text_length": 0,
                "text_preview": ""
            }

        # 按文本长度排序
        best_test = max(successful_tests.items(),
                      key=lambda item: item[1].get("text_length", 0))

        best_method, best_result = best_test

        return {
            "best_method": best_method,
            "text_length": best_result.get("text_length", 0),
            "text_preview": best_result.get("text_preview", ""),
            "confidence": best_result.get("avg_confidence", 0),
            "processing_time": best_result.get("processing_time", 0)
        }

    def _generate_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """生成优化建议"""
        recommendations = []

        file_info = results.get("file_info", {})
        ocr_tests = results.get("ocr_tests", {})

        # 基于文件特征的建议
        if file_info.get("is_likely_scanned"):
            recommendations.append("PDF可能为扫描件，建议使用高分辨率OCR处理")
            recommendations.append("启用图像预处理以提高文本识别准确率")

        if file_info.get("scanned_page_ratio", 0) > 0.8:
            recommendations.append("大部分页面为扫描件，推荐使用专门的OCR引擎")

        # 基于测试结果的建议
        successful_tests = [k for k, v in ocr_tests.items() if v.get("success", False)]

        if len(successful_tests) == 0:
            recommendations.append("所有OCR方法均失败，建议检查PDF文件完整性")
            recommendations.append("尝试将PDF转换为图像再进行OCR识别")
        elif len(successful_tests) == 1:
            recommendations.append(f"只有{successful_tests[0]}方法成功，建议专注于该方法优化")

        # 查找最佳方法
        best_result = results.get("best_result", {})
        best_method = best_result.get("best_method", "")

        if best_method == "pymupdf_extraction":
            recommendations.append("PyMuPDF文本提取效果最佳，建议优先使用原生文本提取")
        elif best_method == "preprocessed_ocr":
            recommendations.append("预处理OCR效果最佳，建议启用图像增强功能")
        elif best_method == "multi_resolution":
            recommendations.append("多分辨率处理效果最佳，建议动态调整分辨率参数")

        # 性能相关建议
        total_time = sum(
            test.get("processing_time", 0)
            for test in ocr_tests.values()
            if test.get("success", False)
        )

        if total_time > 30:
            recommendations.append("处理时间较长，建议考虑优化处理流程")

        # 文本长度相关建议
        max_text_length = max(
            test.get("text_length", 0)
            for test in ocr_tests.values()
            if test.get("success", False)
        )

        if max_text_length < 100:
            recommendations.append("识别文本较少，可能是PDF质量问题")
            recommendations.append("尝试提高DPI设置或使用更专业的OCR工具")

        return recommendations

    def generate_optimization_report(self, results: Dict[str, Any]) -> str:
        """生成优化报告"""
        report = []
        report.append("=" * 80)
        report.append("OCR扫描件优化测试报告")
        report.append("=" * 80)

        file_info = results.get("file_info", {})
        if file_info:
            report.append("【文件分析】")
            report.append(f"  文件: {Path(file_info.get('file_info', '')).name}")
            report.append(f"  页面数: {file_info.get('page_count', 0)}")
            report.append(f"  是否扫描件: {'是' if file_info.get('is_likely_scanned') else '否'}")
            report.append(f"  扫描页面比例: {file_info.get('scanned_page_ratio', 0):.1%}")
            report.append("")

        best_result = results.get("best_result", {})
        if best_result:
            report.append("【最佳结果】")
            report.append(f"  最佳方法: {best_result.get('best_method', 'unknown')}")
            report.append(f"  文本长度: {best_result.get('text_length', 0)}字符")
            report.append(f"  置信度: {best_result.get('confidence', 0):.3f}")
            report.append(f"  处理时间: {best_result.get('processing_time', 0):.3f}秒")
            report.append("")

        ocr_tests = results.get("ocr_tests", {})
        if ocr_tests:
            report.append("【方法对比】")
            for method, result in ocr_tests.items():
                if result.get("success", False):
                    report.append(f"  {method}:")
                    report.append(f"    文本长度: {result.get('text_length', 0)}字符")
                    report.append(f"    置信度: {result.get('avg_confidence', 0):.3f}")
                    report.append(f"    处理时间: {result.get('processing_time', 0):.3f}秒")
                else:
                    report.append(f"  {method}: 失败 - {result.get('error', 'unknown error')}")
            report.append("")

        recommendations = results.get("recommendations", [])
        if recommendations:
            report.append("【优化建议】")
            for i, rec in enumerate(recommendations, 1):
                report.append(f"  {i}. {rec}")
            report.append("")

        report.append("=" * 80)
        report.append("报告生成完成")
        report.append("=" * 80)

        return "\n".join(report)

async def main():
    """主函数"""
    print("OCR扫描件优化测试")
    print("开始OCR优化测试...")

    # 查找测试样本
    samples_dir = Path(__file__).parent.parent.parent / "tools" / "pdf-samples"
    pdf_files = list(samples_dir.glob("*.pdf"))

    if not pdf_files:
        print("未找到PDF测试样本")
        return

    # 使用第一个样本进行测试
    test_file = str(pdf_files[0])
    print(f"测试文件: {Path(test_file).name}")

    optimizer = OCRScanOptimization()

    try:
        # 运行优化测试
        results = await optimizer.test_ocr_with_different_settings(test_file)

        # 生成并输出报告
        report = optimizer.generate_optimization_report(results)
        print(report)

        # 保存结果
        import json
        results_file = "ocr_optimization_results.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"\n详细结果已保存到: {results_file}")

        # 保存报告
        report_file = "ocr_optimization_report.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"优化报告已保存到: {report_file}")

        return results

    except Exception as e:
        logger.error(f"OCR优化测试失败: {e}")
        print(f"测试失败: {e}")
        return None

if __name__ == "__main__":
    asyncio.run(main())