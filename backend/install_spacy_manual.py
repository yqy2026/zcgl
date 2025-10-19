#!/usr/bin/env python
"""
手动安装spaCy模型脚本
提供多种安装方法，适用于不同的网络环境
"""

import sys
import subprocess
import os
from pathlib import Path

def run_command(cmd, description="", timeout=300):
    """运行命令并显示结果"""
    print(f"\n🔄 {description}")
    print(f"命令: {' '.join(cmd) if isinstance(cmd, list) else cmd}")

    try:
        if isinstance(cmd, str):
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        else:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

        if result.returncode == 0:
            print(f"✅ {description} - 成功")
            if result.stdout.strip():
                print(f"输出: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ {description} - 失败")
            if result.stderr.strip():
                print(f"错误: {result.stderr.strip()}")
            return False
    except subprocess.TimeoutExpired:
        print(f"⏰ {description} - 超时")
        return False
    except Exception as e:
        print(f"❌ {description} - 异常: {e}")
        return False

def check_spacy_models():
    """检查已安装的spaCy模型"""
    print("\n🔍 检查已安装的spaCy模型...")

    models_to_check = ["zh_core_web_sm", "en_core_web_sm"]
    installed_models = []

    for model in models_to_check:
        try:
            import spacy
            spacy.load(model)
            print(f"✅ {model} - 已安装")
            installed_models.append(model)
        except OSError:
            print(f"❌ {model} - 未安装")
        except Exception as e:
            print(f"❌ {model} - 检查失败: {e}")

    return installed_models

def method1_direct_download():
    """方法1: 直接使用spacy download命令"""
    print("\n📥 方法1: 使用spaCy直接下载")

    models = ["zh_core_web_sm", "en_core_web_sm"]
    success_count = 0

    for model in models:
        # 使用uv运行python -m spacy download
        cmd = [sys.executable, "-m", "spacy", "download", model]
        if run_command(cmd, f"安装 {model} 模型"):
            success_count += 1

    return success_count == len(models)

def method2_pip_install():
    """方法2: 使用pip直接安装包"""
    print("\n📦 方法2: 使用pip安装包")

    models = {
        "zh_core_web_sm": "https://github.com/explosion/spacy-models/releases/download/zh_core_web_sm-3.7.1/zh_core_web_sm-3.7.1.tar.gz",
        "en_core_web_sm": "https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1.tar.gz"
    }

    success_count = 0

    for model_name, url in models.items():
        # 首先尝试使用uv pip
        cmd = ["uv", "pip", "install", url]
        if run_command(cmd, f"使用uv安装 {model_name}"):
            success_count += 1
            continue

        # 如果uv失败，尝试传统pip
        cmd = [sys.executable, "-m", "pip", "install", url]
        if run_command(cmd, f"使用pip安装 {model_name}"):
            success_count += 1

    return success_count == len(models)

def method3_conda_install():
    """方法3: 使用conda安装（如果有conda环境）"""
    print("\n🐍 方法3: 使用conda安装")

    # 检查是否有conda
    conda_check = run_command(["conda", "--version"], "检查conda", timeout=10)
    if not conda_check:
        print("❌ 未找到conda，跳过此方法")
        return False

    models = ["spacy-model-zh_core_web_sm", "spacy-model-en_core_web_sm"]
    success_count = 0

    for model in models:
        cmd = ["conda", "install", "-c", "conda-forge", model, "-y"]
        if run_command(cmd, f"使用conda安装 {model}"):
            success_count += 1

    return success_count == len(models)

def method4_local_install():
    """方法4: 本地安装指导"""
    print("\n💾 方法4: 本地安装指导")
    print("如果以上方法都失败，请按以下步骤手动下载和安装：")
    print()
    print("1. 手动下载模型文件：")
    print("   - 中文模型: https://github.com/explosion/spacy-models/releases/download/zh_core_web_sm-3.7.1/zh_core_web_sm-3.7.1.tar.gz")
    print("   - 英文模型: https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1.tar.gz")
    print()
    print("2. 下载完成后，运行以下命令：")
    print("   cd backend")
    print("   uv pip install /path/to/zh_core_web_sm-3.7.1.tar.gz")
    print("   uv pip install /path/to/en_core_web_sm-3.7.1.tar.gz")
    print()
    print("3. 或者将下载的文件放在backend目录下，然后运行：")
    print("   uv pip install zh_core_web_sm-3.7.1.tar.gz")
    print("   uv pip install en_core_web_sm-3.7.1.tar.gz")

    return False

def test_models():
    """测试模型是否正常工作"""
    print("\n🧪 测试spaCy模型...")

    try:
        import spacy

        # 测试中文模型
        try:
            nlp = spacy.load("zh_core_web_sm")
            test_text = "这是一个测试文本，用于验证spaCy中文模型是否正常工作。"
            doc = nlp(test_text)
            print(f"✅ 中文模型测试成功")
            print(f"   测试文本: {test_text}")
            print(f"   分词结果: {[token.text for token in doc[:5]]}...")
        except Exception as e:
            print(f"❌ 中文模型测试失败: {e}")

        # 测试英文模型
        try:
            nlp = spacy.load("en_core_web_sm")
            test_text = "This is a test text to verify the English spaCy model works correctly."
            doc = nlp(test_text)
            print(f"✅ 英文模型测试成功")
            print(f"   测试文本: {test_text}")
            print(f"   分词结果: {[token.text for token in doc[:5]]}...")
        except Exception as e:
            print(f"❌ 英文模型测试失败: {e}")

    except ImportError:
        print("❌ spaCy未安装")

def main():
    """主函数"""
    print("🚀 spaCy模型手动安装脚本")
    print("=" * 50)

    # 检查当前状态
    installed = check_spacy_models()

    if len(installed) == 2:
        print("\n✅ 所有模型已安装，无需重复安装")
        test_models()
        return True

    print(f"\n📊 需要安装 {2 - len(installed)} 个模型")

    # 尝试不同的安装方法
    methods = [
        ("直接下载", method1_direct_download),
        ("pip安装", method2_pip_install),
        ("conda安装", method3_conda_install),
    ]

    success = False
    for method_name, method_func in methods:
        print(f"\n🔄 尝试{method_name}方法...")
        if method_func():
            success = True
            break
        print(f"❌ {method_name}方法失败")

    # 提供本地安装指导
    if not success:
        method4_local_install()

    # 最终检查
    print("\n" + "=" * 50)
    print("🔍 最终检查安装状态...")
    final_installed = check_spacy_models()

    if len(final_installed) == 2:
        print("\n🎉 所有模型安装成功！")
        test_models()
        return True
    elif len(final_installed) > 0:
        print(f"\n⚠️ 部分模型安装成功 ({len(final_installed)}/2)")
        test_models()
        return False
    else:
        print("\n❌ 所有模型安装失败")
        print("请参考方法4进行本地安装")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)