#!/usr/bin/env python
"""
简化的OCR兼容性测试
测试PaddleOCR的最新API兼容性
"""

import logging
import sys
import time
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_paddleocr_compatibility():
    """测试PaddleOCR兼容性"""
    print("开始PaddleOCR兼容性测试...")

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

        # 测试最基础的PaddleOCR初始化
        print("\n1. 测试PaddleOCR初始化...")
        try:
            ocr = PaddleOCR(lang='ch')
            print("✅ PaddleOCR初始化成功")
        except Exception as e:
            print(f"❌ PaddleOCR初始化失败: {e}")
            return

        # 测试基础OCR功能
        print("\n2. 测试基础OCR功能...")
        try:
            doc = fitz.open(test_file)

            # 只处理第一页
            page = doc[0]
            pix = page.get_pixmap()
            img_bytes = pix.tobytes("png")
            doc.close()

            # 使用新的predict方法
            print("   使用predict方法...")
            result = ocr.predict(img_bytes)

            if result and result[0]:
                text = result[0][0][0]  # 提取文本
                confidence = result[0][0][1]  # 提取置信度

                print("✅ OCR识别成功")
                print(f"   文本长度: {len(text)}字符")
                print(f"   置信度: {confidence:.3f}")
                print(f"   文本预览: {text[:100]}...")

                # 测试中文NLP处理
                if len(text) > 10:
                    print("\n3. 测试中文NLP处理...")
                    try:
                        from services.chinese_nlp_processor import (
                            get_chinese_nlp_processor,
                        )
                        processor = get_chinese_nlp_processor()
                        nlp_result = processor.process_chinese_text(text)

                        print("✅ NLP处理成功")
                        print(f"   识别姓名: {len(nlp_result['names'])}")
                        print(f"   识别电话: {len(nlp_result['phones'])}")
                        print(f"   识别地址: {len(nlp_result['addresses'])}")

                    except Exception as e:
                        print(f"❌ NLP处理失败: {e}")

            else:
                print("❌ OCR未识别到文本")

        except Exception as e:
            print(f"❌ OCR处理失败: {e}")

        # 测试OCR和预测方法
        print("\n4. 测试不同的OCR方法...")

        try:
            # 方法1: predict (新方法)
            print("   方法1: predict (推荐)")
            ocr1 = PaddleOCR(lang='ch')
            start_time = time.time()
            result1 = ocr1.predict(img_bytes)
            time1 = time.time() - start_time

            if result1 and result1[0]:
                text1 = result1[0][0][0]
                print(f"     ✅ predict方法成功 - 文本长度: {len(text1)}, 用时: {time1:.3f}秒")
            else:
                print(f"     ❌ predict方法无结果 - 用时: {time1:.3f}秒")

        except Exception as e:
            print(f"     ❌ predict方法失败: {e}")

        try:
            # 方法2: ocr (旧方法，但无cls参数)
            print("   方法2: ocr (传统)")
            ocr2 = PaddleOCR(lang='ch')
            start_time = time.time()
            result2 = ocr2.ocr(img_bytes)  # 移除cls参数
            time2 = time.time() - start_time

            if result2 and result2[0]:
                text2 = result2[0][0][0]
                print(f"     ✅ ocr方法成功 - 文本长度: {len(text2)}, 用时: {time2:.3f}秒")
            else:
                print(f"     ❌ ocr方法无结果 - 用时: {time2:.3f}秒")

        except Exception as e:
            print(f"     ❌ ocr方法失败: {e}")

        # 性能统计
        print("\n5. OCR性能统计...")
        print("   PaddleOCR版本兼容性测试完成")
        print("   推荐使用predict方法替代旧的ocr方法")
        print("   移除不支持的参数：use_gpu, show_log, cls=True")

    except ImportError as e:
        print(f"❌ 导入PaddleOCR失败: {e}")
        print("   请确保PaddleOCR已正确安装")
    except Exception as e:
        print(f"❌ 测试过程中出现意外错误: {e}")

def test_pdf_text_extraction():
    """测试PDF文本提取"""
    print("\n开始PDF文本提取测试...")

    try:
        import fitz

        # 查找测试样本
        samples_dir = Path(__file__).parent.parent.parent / "tools" / "pdf-samples"
        pdf_files = list(samples_dir.glob("*.pdf"))

        if not pdf_files:
            print("未找到PDF测试样本")
            return

        test_file = str(pdf_files[0])
        print(f"测试文件: {Path(test_file).name}")

        doc = fitz.open(test_file)

        print("PDF信息:")
        print(f"  页面数: {doc.page_count}")

        total_text = ""
        text_pages = 0
        image_pages = 0

        for i, page in enumerate(doc[:5]):  # 只检查前5页
            text = page.get_text()
            if len(text.strip()) > 0:
                text_pages += 1
                total_text += text + "\n"
                print(f"  页面 {i+1}: 有文本 ({len(text)}字符)")
            else:
                images = page.get_images()
                if len(images) > 0:
                    image_pages += 1
                    print(f"  页面 {i+1}: 扫描件 ({len(images)}个图像)")
                else:
                    print(f"  页面 {i+1}: 空页面")

        doc.close()

        print("\n文本提取总结:")
        print(f"  有文本页面: {text_pages}")
        print(f"  扫描件页面: {image_pages}")
        print(f"  总文本长度: {len(total_text)}字符")

        if len(total_text) > 0:
            print(f"  文本预览: {total_text[:200]}...")
        else:
            print("  [警告] 这是一个纯扫描件，需要OCR处理")

    except Exception as e:
        print(f"❌ PDF文本提取失败: {e}")

def main():
    """主函数"""
    print("=" * 60)
    print("PDF智能处理系统 - OCR兼容性测试")
    print("=" * 60)

    # 测试PDF文本提取
    test_pdf_text_extraction()

    # 测试PaddleOCR兼容性
    test_paddleocr_compatibility()

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    main()
