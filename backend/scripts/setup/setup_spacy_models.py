"""
设置spaCy中文模型
用于PDF处理的中文NLP支持
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import subprocess

import spacy

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_spacy_model(model_name: str = "zh_core_web_sm"):
    """检查spaCy模型是否已安装"""
    try:
        spacy.load(model_name)
        logger.info(f"spaCy模型 {model_name} 已安装")
        return True
    except OSError:
        logger.warning(f"spaCy模型 {model_name} 未安装")
        return False

def install_spacy_model(model_name: str = "zh_core_web_sm"):
    """安装spaCy模型"""
    try:
        logger.info(f"正在安装spaCy模型: {model_name}")

        # 使用python -m spacy download命令
        result = subprocess.run([
            sys.executable, "-m", "spacy", "download", model_name
        ], capture_output=True, text=True, timeout=300)

        if result.returncode == 0:
            logger.info(f"spaCy模型 {model_name} 安装成功")
            return True
        else:
            logger.error(f"spaCy模型安装失败: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        logger.error("spaCy模型安装超时")
        return False
    except Exception as e:
        logger.error(f"spaCy模型安装失败: {e}")
        return False

def test_spacy_model(model_name: str = "zh_core_web_sm"):
    """测试spaCy模型是否正常工作"""
    try:
        nlp = spacy.load(model_name)

        # 测试中文文本处理
        test_text = "这是一个测试文本，用于验证spaCy模型是否正常工作。"
        doc = nlp(test_text)

        # 提取一些基本信息验证模型功能
        tokens = [token.text for token in doc]
        entities = [(ent.text, ent.label_) for ent in doc.ents]

        logger.info("spaCy模型测试成功")
        logger.info(f"分词结果: {tokens[:5]}...")
        logger.info(f"实体识别: {entities}")

        return True

    except Exception as e:
        logger.error(f"spaCy模型测试失败: {e}")
        return False

def setup_spacy_fallback():
    """设置spaCy回退机制"""
    try:
        # 尝试安装并使用英文模型作为回退
        fallback_model = "en_core_web_sm"

        if not check_spacy_model(fallback_model):
            if install_spacy_model(fallback_model):
                logger.info("已安装英文模型作为回退")
                return fallback_model

        return None

    except Exception as e:
        logger.error(f"设置spaCy回退机制失败: {e}")
        return None

def main():
    """主函数"""
    logger.info("开始设置spaCy中文模型...")

    model_name = "zh_core_web_sm"

    # 检查模型是否已安装
    if check_spacy_model(model_name):
        # 测试模型
        if test_spacy_model(model_name):
            logger.info("✅ spaCy中文模型设置完成")
            return True
        else:
            logger.warning("spaCy模型已安装但测试失败")

    # 尝试安装模型
    if install_spacy_model(model_name):
        # 测试安装后的模型
        if test_spacy_model(model_name):
            logger.info("✅ spaCy中文模型安装并测试成功")
            return True
        else:
            logger.warning("spaCy模型安装后测试失败")

    # 设置回退机制
    logger.warning("尝试设置回退机制...")
    fallback = setup_spacy_fallback()

    if fallback:
        logger.info(f"✅ 已设置回退模型: {fallback}")
        logger.warning("⚠️ PDF处理功能可能有限，建议手动安装中文模型")
        return True
    else:
        logger.error("❌ spaCy模型设置失败")
        logger.info("请手动运行以下命令安装中文模型:")
        logger.info(f"python -m spacy download {model_name}")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("✅ spaCy模型设置完成")
        sys.exit(0)
    else:
        print("❌ spaCy模型设置失败")
        sys.exit(1)
