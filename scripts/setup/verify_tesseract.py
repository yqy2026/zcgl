#!/usr/bin/env python3
"""
Tesseract OCR 安装验证脚本
用于验证Tesseract OCR是否正确安装并可以使用
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command):
    """执行命令并返回结果"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=30
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "命令执行超时"
    except Exception as e:
        return False, "", f"执行错误: {str(e)}"

def check_tesseract_installation():
    """检查Tesseract是否安装"""
    print("🔍 正在检查Tesseract OCR安装状态...")

    # 检查tesseract命令
    success, stdout, stderr = run_command("tesseract --version")

    if success:
        print("✅ Tesseract OCR 已安装")
        print(f"版本信息:\n{stdout}")
        return True
    else:
        print("❌ Tesseract OCR 未安装或未添加到PATH")
        print(f"错误信息: {stderr}")
        return False

def check_language_support():
    """检查语言包支持"""
    print("\n🌍 正在检查语言包支持...")

    success, stdout, stderr = run_command("tesseract --list-langs")

    if success:
        print("✅ 语言包检查成功")
        print(f"可用语言包:\n{stdout}")

        # 检查中文支持
        if 'chi_sim' in stdout:
            print("✅ 简体中文语言包已安装")
        else:
            print("⚠️  简体中文语言包未安装，可能影响中文识别")

        if 'eng' in stdout:
            print("✅ 英文语言包已安装")
        else:
            print("⚠️  英文语言包未安装")

        return stdout
    else:
        print("❌ 无法获取语言包列表")
        print(f"错误信息: {stderr}")
        return None

def test_ocr_functionality():
    """测试OCR功能"""
    print("\n🧪 正在测试OCR功能...")

    # 首先检查是否有测试PDF
    test_pdf = Path("test_contract.pdf")
    if not test_pdf.exists():
        print("⚠️  未找到测试PDF文件，跳过OCR功能测试")
        return False

    try:
        # 尝试使用Python进行OCR测试
        from pdf2image import convert_from_path
        import pytesseract
        from PIL import Image
        import tempfile

        print("正在转换PDF为图像...")

        # 将PDF转换为图像
        with tempfile.TemporaryDirectory() as temp_dir:
            images = convert_from_path(str(test_pdf), dpi=200)

            if images:
                print(f"✅ PDF转换成功，共 {len(images)} 页")

                # 测试第一页的OCR
                image = images[0]
                text = pytesseract.image_to_string(image, lang='chi_sim+eng')

                if text.strip():
                    print("✅ OCR功能测试成功")
                    print(f"识别的文本预览:\n{text[:200]}...")
                    return True
                else:
                    print("⚠️  OCR功能测试完成，但未识别到文本")
                    return False
            else:
                print("❌ PDF转换为图像失败")
                return False

    except Exception as e:
        print(f"❌ OCR功能测试失败: {str(e)}")
        return False

def generate_installation_guide():
    """生成安装指导"""
    print("\n📋 生成安装指导...")

    guide = """
# Tesseract OCR 快速安装指导

## 自动安装（推荐）
1. 使用Chocolatey: `choco install tesseract`
2. 使用Scoop: `scoop install tesseract`

## 手动安装
1. 访问: https://github.com/UB-Mannheim/tesseract/wiki
2. 下载Windows安装包
3. 安装时勾选中文语言包（chi_sim）
4. 添加安装目录到系统PATH

## 验证安装
运行此脚本或执行:
```cmd
tesseract --version
tesseract --list-langs
```

## 完成后
重启PDF导入服务，然后测试您的扫描件PDF。
"""

    with open("TESSERACT_QUICK_GUIDE.md", "w", encoding="utf-8") as f:
        f.write(guide)

    print("✅ 安装指导已保存到 TESSERACT_QUICK_GUIDE.md")

def main():
    """主函数"""
    print("=" * 60)
    print("🔧 Tesseract OCR 安装验证工具")
    print("=" * 60)

    # 检查安装
    if not check_tesseract_installation():
        print("\n🚀 请先安装Tesseract OCR")
        generate_installation_guide()
        return False

    # 检查语言包
    languages = check_language_support()
    if not languages:
        return False

    # 测试OCR功能
    ocr_works = test_ocr_functionality()

    print("\n" + "=" * 60)
    print("📊 验证结果总结:")
    print("=" * 60)

    if check_tesseract_installation():
        print("✅ Tesseract OCR: 已安装")
    else:
        print("❌ Tesseract OCR: 未安装")

    if languages and 'chi_sim' in languages:
        print("✅ 中文语言包: 已安装")
    else:
        print("⚠️  中文语言包: 未安装或不可用")

    if ocr_works:
        print("✅ OCR功能: 测试通过")
    else:
        print("⚠️  OCR功能: 需要进一步测试")

    print("\n💡 下一步:")
    if check_tesseract_installation() and languages:
        print("1. 重启PDF导入服务")
        print("2. 重新测试您的扫描件PDF")
        print("3. 如果仍有问题，请检查PDF质量和语言包")
    else:
        print("1. 根据上述指导完成Tesseract安装")
        print("2. 重新运行此验证脚本")

    return True

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 验证已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 验证过程中发生错误: {str(e)}")
        sys.exit(1)