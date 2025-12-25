#!/usr/bin/env python
"""
基础OCR测试 - 移除Unicode字符
测试PaddleOCR的基本功能
"""

import logging
import os
import sys
import time
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_basic_paddleocr():
    """测试基础PaddleOCR功能"""
    print("开始基础PaddleOCR测试...")

    try:
        import fitz
        from paddleocr import PaddleOCR

        # 查找测试样本
        samples_dir = Path(__file__).parent.parent.parent / "tools" / "pdf-samples"
        pdf_files = list(samples_dir.glob("*.pdf"))

        if not pdf_files:
            print("未找到PDF测试样本")
            return

        test_file = str(pdf_files[0])
        print(f"测试文件: {Path(test_file).name}")

        # 初始化PaddleOCR
        print("\n1. 初始化PaddleOCR...")
        ocr = PaddleOCR(lang='ch')
        print("[成功] PaddleOCR初始化成功")

        # 处理PDF第一页
        print("\n2. 提取PDF页面图像...")
        doc = fitz.open(test_file)
        page = doc[0]
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2倍分辨率
        img_bytes = pix.tobytes("png")
        doc.close()
        print(f"[成功] 页面图像提取完成 ({len(img_bytes)} bytes)")

        # 使用predict方法进行OCR
        print("\n3. 使用predict方法进行OCR...")
        start_time = time.time()
        result = ocr.predict(img_bytes)
        processing_time = time.time() - start_time

        print(f"处理时间: {processing_time:.3f}秒")

        if result and result[0]:
            text = result[0][0][0]  # 文本
            confidence = result[0][0][1]  # 置信度

            print("[成功] OCR识别完成")
            print(f"  文本长度: {len(text)}字符")
            print(f"  置信度: {confidence:.3f}")
            print(f"  文本预览: {text[:100]}...")

            # 测试中文NLP处理
            if len(text) > 5:
                print("\n4. 测试中文NLP处理...")
                try:
                    from services.chinese_nlp_processor import get_chinese_nlp_processor
                    processor = get_chinese_nlp_processor()
                    nlp_result = processor.process_chinese_text(text)

                    print("[成功] NLP处理完成")
                    print(f"  识别姓名: {len(nlp_result['names'])}")
                    print(f"  识别电话: {len(nlp_result['phones'])}")
                    print(f"  识别地址: {len(nlp_result['addresses'])}")

                    # 显示部分识别结果
                    if nlp_result['names']:
                        print(f"  姓名示例: {nlp_result['names'][0]['full_name']}")
                    if nlp_result['phones']:
                        print(f"  电话示例: {nlp_result['phones'][0]['phone_number']}")

                except Exception as e:
                    print(f"[错误] NLP处理失败: {e}")

        else:
            print("[警告] OCR未识别到文本")

        return True

    except ImportError as e:
        print(f"[错误] 导入失败: {e}")
        return False
    except Exception as e:
        print(f"[错误] 测试失败: {e}")
        return False

def test_pdf_analysis():
    """分析PDF文件特征"""
    print("\n开始PDF文件分析...")

    try:
        import fitz

        # 查找测试样本
        samples_dir = Path(__file__).parent.parent.parent / "tools" / "pdf-samples"
        pdf_files = list(samples_dir.glob("*.pdf"))

        if not pdf_files:
            print("未找到PDF测试样本")
            return

        test_file = str(pdf_files[0])
        print(f"分析文件: {Path(test_file).name}")

        doc = fitz.open(test_file)

        print("PDF基本信息:")
        print(f"  页面数: {doc.page_count}")
        print(f"  文件大小: {os.path.getsize(test_file) / (1024*1024):.2f} MB")

        # 分析前5页
        text_pages = 0
        image_pages = 0
        total_text_length = 0

        for i in range(min(5, doc.page_count)):
            page = doc[i]
            text = page.get_text()
            images = page.get_images()

            if len(text.strip()) > 0:
                text_pages += 1
                total_text_length += len(text)
                print(f"  页面 {i+1}: 文本页面 ({len(text)}字符)")
            elif len(images) > 0:
                image_pages += 1
                print(f"  页面 {i+1}: 扫描页面 ({len(images)}个图像)")
            else:
                print(f"  页面 {i+1}: 空页面")

        doc.close()

        print("\n分析结果:")
        print(f"  文本页面: {text_pages}")
        print(f"  扫描页面: {image_pages}")
        print(f"  总文本长度: {total_text_length}字符")

        if total_text_length == 0:
            print("  [结论] 纯扫描件，必须使用OCR")
        elif total_text_length < 100:
            print("  [结论] 大部分为扫描件，需要OCR辅助")
        else:
            print("  [结论] 包含可提取文本")

        return True

    except Exception as e:
        print(f"[错误] PDF分析失败: {e}")
        return False

def test_ocr_methods():
    """测试不同的OCR方法"""
    print("\n开始OCR方法对比测试...")

    try:
        import fitz
        from paddleocr import PaddleOCR

        # 查找测试样本
        samples_dir = Path(__file__).parent.parent.parent / "tools" / "pdf-samples"
        pdf_files = list(samples_dir.glob("*.pdf"))

        if not pdf_files:
            print("未找到PDF测试样本")
            return

        test_file = str(pdf_files[0])

        # 提取第一页图像
        doc = fitz.open(test_file)
        page = doc[0]
        pix = page.get_pixmap()
        img_bytes = pix.tobytes("png")
        doc.close()

        results = {}

        # 方法1: predict
        print("\n测试方法1: predict")
        try:
            ocr1 = PaddleOCR(lang='ch')
            start_time = time.time()
            result1 = ocr1.predict(img_bytes)
            time1 = time.time() - start_time

            if result1 and result1[0]:
                text1 = result1[0][0][0]
                results['predict'] = {
                    'success': True,
                    'text_length': len(text1),
                    'time': time1,
                    'text_preview': text1[:50]
                }
                print(f"  [成功] 文本长度: {len(text1)}, 用时: {time1:.3f}秒")
            else:
                results['predict'] = {'success': False, 'time': time1}
                print(f"  [失败] 无文本结果, 用时: {time1:.3f}秒")

        except Exception as e:
            results['predict'] = {'success': False, 'error': str(e)}
            print(f"  [失败] {e}")

        # 方法2: ocr
        print("\n测试方法2: ocr")
        try:
            ocr2 = PaddleOCR(lang='ch')
            start_time = time.time()
            result2 = ocr2.ocr(img_bytes)
            time2 = time.time() - start_time

            if result2 and result2[0]:
                text2 = ""
                for line in result2[0]:
                    text2 += line[1][0] + "\n"
                results['ocr'] = {
                    'success': True,
                    'text_length': len(text2),
                    'time': time2,
                    'text_preview': text2[:50]
                }
                print(f"  [成功] 文本长度: {len(text2)}, 用时: {time2:.3f}秒")
            else:
                results['ocr'] = {'success': False, 'time': time2}
                print(f"  [失败] 无文本结果, 用时: {time2:.3f}秒")

        except Exception as e:
            results['ocr'] = {'success': False, 'error': str(e)}
            print(f"  [失败] {e}")

        # 找到最佳方法
        successful_methods = [k for k, v in results.items() if v.get('success', False)]
        if successful_methods:
            best_method = max(successful_methods,
                          key=lambda k: results[k]['text_length'])
            best_result = results[best_method]

            print(f"\n[结论] 最佳方法: {best_method}")
            print(f"  文本长度: {best_result['text_length']}字符")
            print(f"  处理时间: {best_result['time']:.3f}秒")
            print(f"  文本预览: {best_result['text_preview']}...")
        else:
            print("\n[结论] 所有方法均失败")

        return successful_methods

    except Exception as e:
        print(f"[错误] OCR方法测试失败: {e}")
        return []

def main():
    """主函数"""
    print("=" * 60)
    print("PDF智能处理系统 - 基础OCR测试")
    print("=" * 60)

    # PDF分析
    if test_pdf_analysis():
        print("[成功] PDF分析完成")
    else:
        print("[失败] PDF分析失败")
        return

    # OCR测试
    if test_basic_paddleocr():
        print("[成功] 基础OCR测试完成")
    else:
        print("[失败] 基础OCR测试失败")
        return

    # OCR方法对比
    successful_methods = test_ocr_methods()
    if successful_methods:
        print(f"[成功] 找到可用OCR方法: {successful_methods}")
    else:
        print("[失败] 所有OCR方法均失败")

    print("\n" + "=" * 60)
    print("基础OCR测试完成")
    print("=" * 60)

if __name__ == "__main__":
    main()
