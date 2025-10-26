#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
最终OCR测试
验证修复后的PaddleOCR集成是否正常工作
"""

import sys
import time
import logging
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_basic_ocr_functionality():
    """测试基础OCR功能"""
    print("开始基础OCR功能测试...")

    try:
        # 1. 测试PaddleOCR初始化
        print("1. 测试PaddleOCR初始化...")
        try:
            from paddleocr import PaddleOCR
            ocr = PaddleOCR(lang='ch', use_textline_orientation=True)
            print("   [成功] PaddleOCR初始化成功")
        except Exception as e:
            print(f"   [失败] PaddleOCR初始化失败: {e}")
            return False

        # 2. 测试PDF页面转换
        print("2. 测试PDF页面转换...")
        try:
            import fitz
            import numpy as np

            # 查找测试样本
            samples_dir = Path(__file__).parent.parent.parent / "tools" / "pdf-samples"
            pdf_files = list(samples_dir.glob("*.pdf"))

            if not pdf_files:
                print("   [跳过] 未找到PDF测试样本")
                return False

            test_file = str(pdf_files[0])
            print(f"   测试文件: {Path(test_file).name}")

            # 打开PDF并转换第一页
            doc = fitz.open(test_file)
            page = doc[0]

            # 转换为numpy数组
            pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
            img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.height, pix.width, pix.n))

            if pix.n == 4:  # RGBA -> RGB
                img_array = img_array[:, :, :3]

            doc.close()
            print(f"   [成功] PDF页面转换完成: {img_array.shape}")

        except Exception as e:
            print(f"   [失败] PDF页面转换失败: {e}")
            return False

        # 3. 测试OCR处理
        print("3. 测试OCR处理...")
        try:
            start_time = time.time()
            result = ocr.ocr(img_array, cls=True)
            processing_time = time.time() - start_time

            if result and len(result) > 0 and result[0]:
                texts = []
                confidences = []

                for line in result[0]:
                    if line and len(line) >= 2:
                        text = line[1][0]
                        confidence = line[1][1]
                        texts.append(text)
                        confidences.append(confidence)

                combined_text = '\n'.join(texts)
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

                print(f"   [成功] OCR处理完成")
                print(f"   处理时间: {processing_time:.3f}秒")
                print(f"   识别文本长度: {len(combined_text)}字符")
                print(f"   平均置信度: {avg_confidence:.3f}")
                print(f"   识别行数: {len(texts)}行")

                # 显示部分文本内容
                if combined_text:
                    preview = combined_text[:100].replace('\n', ' ')
                    print(f"   文本预览: {preview}...")

                return True
            else:
                print("   [警告] OCR未识别到文本")
                return False

        except Exception as e:
            print(f"   [失败] OCR处理失败: {e}")
            return False

    except Exception as e:
        print(f"[错误] 基础OCR功能测试失败: {e}")
        return False

def test_nlp_integration():
    """测试NLP集成"""
    print("\n开始NLP集成测试...")

    try:
        # 1. 测试NLP处理器
        print("1. 测试NLP处理器...")
        try:
            from services.chinese_nlp_processor import get_chinese_nlp_processor
            processor = get_chinese_nlp_processor()
            print("   [成功] NLP处理器初始化成功")
        except Exception as e:
            print(f"   [失败] NLP处理器初始化失败: {e}")
            return False

        # 2. 测试文本处理
        print("2. 测试文本处理...")
        try:
            test_text = """
            租赁合同

            甲方：王军
            身份证号：440105198001011234
            联系电话：13800138000
            地址：广州市番禺区洛浦南浦环岛西路29号1号商业楼14号铺

            租金：5000元/月
            租期：2025年4月1日至2028年3月31日

            本合同一式两份，甲乙双方各执一份，具有同等法律效力。
            """

            result = processor.process_chinese_text(test_text)
            print(f"   [成功] NLP处理完成")
            print(f"   提取姓名: {len(result['names'])}个")
            print(f"   提取电话: {len(result['phones'])}个")
            print(f"   提取地址: {len(result['addresses'])}个")
            print(f"   提取金额: {len(result['amounts'])}个")
            print(f"   提取日期: {len(result['dates'])}个")
            print(f"   提取身份证: {len(result['id_cards'])}个")
            print(f"   总实体数: {len(result['entities'])}个")

            # 显示部分提取结果
            if result['names']:
                name = result['names'][0]
                print(f"   姓名示例: {name['full_name']} (置信度: {name['confidence']:.3f})")
            if result['phones']:
                phone = result['phones'][0]
                print(f"   电话示例: {phone['phone_number']} (置信度: {phone['confidence']:.3f})")

            return True

        except Exception as e:
            print(f"   [失败] NLP处理失败: {e}")
            return False

    except Exception as e:
        print(f"[错误] NLP集成测试失败: {e}")
        return False

def test_system_readiness():
    """测试系统准备状态"""
    print("\n开始系统准备状态测试...")

    try:
        # 1. 测试统一PDF处理器
        print("1. 测试统一PDF处理器...")
        try:
            from services.unified_pdf_processor import unified_pdf_processor

            if unified_pdf_processor is None:
                print("   [失败] 统一PDF处理器未初始化")
                return False

            system_status = unified_pdf_processor.get_system_status()
            print(f"   [成功] 统一PDF处理器状态: {system_status['service_status']}")

            components = system_status['components']
            print(f"   OCR组件: {'就绪' if components['optimized_ocr'] else '未就绪'}")
            print(f"   NLP组件: {'就绪' if components['nlp_processor'] else '未就绪'}")
            print(f"   融合组件: {'就绪' if components['multi_engine_fusion'] else '未就绪'}")

            capabilities = system_status['capabilities']
            print("   系统能力:")
            for capability, status in capabilities.items():
                print(f"     {capability}: {'支持' if status else '不支持'}")

            return True

        except Exception as e:
            print(f"   [失败] 统一PDF处理器测试失败: {e}")
            return False

    except Exception as e:
        print(f"[错误] 系统准备状态测试失败: {e}")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("PDF智能处理系统 - 最终OCR测试")
    print("=" * 60)

    # 运行所有测试
    tests = [
        ("基础OCR功能", test_basic_ocr_functionality),
        ("NLP集成", test_nlp_integration),
        ("系统准备状态", test_system_readiness)
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n=== {test_name} ===")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"[异常] {test_name}测试异常: {e}")
            results.append((test_name, False))

    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    passed = 0
    total = len(results)

    for test_name, success in results:
        status = "[成功]" if success else "[失败]"
        print(f"{test_name}: {status}")
        if success:
            passed += 1

    print(f"\n通过测试: {passed}/{total}")
    print(f"成功率: {passed/total*100:.1f}%")

    if passed == total:
        print("\n[成功] 所有测试通过！系统已准备就绪。")
        print("优化后的PDF处理系统可以正常工作。")
    elif passed >= total * 0.8:
        print("\n[部分成功] 大部分测试通过，系统基本可用。")
    else:
        print("\n[失败] 多数测试失败，需要进一步调试。")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()