#!/usr/bin/env python3
"""
PaddleOCR安装脚本
为PDF导入系统安装和配置PaddleOCR高精度中文识别
"""

import logging
import os
import subprocess
import sys

# 设置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def check_system_requirements():
    """检查系统要求"""
    logger.info("检查系统要求...")

    requirements = {"python_version": (3, 8), "platform": ["win32", "linux", "darwin"]}

    # 检查Python版本
    python_version = sys.version_info[:2]
    if python_version < requirements["python_version"]:
        logger.error(
            f"Python版本过低: {python_version}, 需要: {requirements['python_version']}"
        )
        return False

    logger.info(f"✓ Python版本: {python_version}")

    # 检查平台
    import platform

    current_platform = platform.system().lower()
    if current_platform == "windows":
        platform_code = "win32"
    elif current_platform == "linux":
        platform_code = "linux"
    elif current_platform == "darwin":
        platform_code = "darwin"
    else:
        logger.error(f"不支持的平台: {current_platform}")
        return False

    logger.info(f"✓ 平台: {platform_code}")

    return True


def install_paddleocr():
    """安装PaddleOCR"""
    logger.info("开始安装PaddleOCR...")

    # 基础包列表
    base_packages = ["paddlepaddle", "paddleocr", "pillow", "opencv-python"]

    # 可选包列表
    optional_packages = [
        "shapely",  # 几何计算
        "imgaug",  # 图像增强
        "pyclipper",  # 裁剪算法
    ]

    success_count = 0
    total_packages = len(base_packages) + len(optional_packages)

    # 安装基础包
    for package in base_packages:
        logger.info(f"安装基础包: {package}")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "uv", "pip", "install", package],
                capture_output=True,
                text=True,
                timeout=600,
            )

            if result.returncode == 0:
                logger.info(f"✓ {package} 安装成功")
                success_count += 1
            else:
                logger.error(f"✗ {package} 安装失败: {result.stderr}")
                # 尝试使用pip
                try:
                    result = subprocess.run(
                        [sys.executable, "-m", "pip", "install", package],
                        capture_output=True,
                        text=True,
                        timeout=600,
                    )
                    if result.returncode == 0:
                        logger.info(f"✓ {package} (通过pip) 安装成功")
                        success_count += 1
                except:
                    logger.error(f"✗ {package} (通过pip) 也安装失败")

        except subprocess.TimeoutExpired:
            logger.error(f"✗ {package} 安装超时")
        except Exception as e:
            logger.error(f"✗ {package} 安装异常: {e}")

    # 安装可选包
    for package in optional_packages:
        logger.info(f"安装可选包: {package}")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "uv", "pip", "install", package],
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:
                logger.info(f"✓ {package} 安装成功")
                success_count += 1
            else:
                logger.warning(f"⚠ {package} 安装失败（可选）: {result.stderr}")
                success_count += 0.5  # 部分计数

        except Exception as e:
            logger.warning(f"⚠ {package} 安装异常（可选）: {e}")

    logger.info(f"安装完成: {success_count}/{total_packages} 个包安装成功")
    return success_count >= len(base_packages)  # 至少基础包都安装成功


def test_paddleocr_installation():
    """测试PaddleOCR安装"""
    logger.info("测试PaddleOCR安装...")

    try:
        # 测试导入
        import paddleocr

        logger.info("✓ PaddleOCR导入成功")

        # 测试OCR功能
        # 初始化引擎（默认启用 MKLDNN 加速，CPU 模式）
        # 兼容不同版本：优先使用 use_textline_orientation，失败回退到 use_angle_cls；移除不兼容的 show_log
        base_args = {
            "lang": "ch",
            "use_gpu": False,
            "enable_mkldnn": True,
        }
        try:
            ocr = paddleocr.PaddleOCR(
                **base_args,
                use_textline_orientation=True,
            )
        except Exception as e:
            msg = str(e)
            if "Unknown argument" in msg and "use_textline_orientation" in msg:
                # 回退到旧参数名
                ocr = paddleocr.PaddleOCR(
                    **base_args,
                    use_angle_cls=True,
                )
            elif "Unknown argument" in msg and "enable_mkldnn" in msg:
                # 某些版本不支持 enable_mkldnn 参数，移除后重试
                base_args.pop("enable_mkldnn", None)
                ocr = paddleocr.PaddleOCR(
                    **base_args,
                    use_textline_orientation=True,
                )
            else:
                raise
        logger.info("✓ PaddleOCR引擎初始化成功")

        # 创建简单测试图像
        import numpy as np
        from PIL import Image, ImageDraw

        # 创建测试图像
        img = Image.new("RGB", (300, 100), color="white")
        draw = ImageDraw.Draw(img)
        draw.text((10, 30), "测试OCR识别", fill="black")

        # 转换为numpy数组
        img_array = np.array(img)

        # 执行OCR测试
        result = ocr.ocr(img_array, cls=True)

        if result and result[0]:
            detected_text = result[0][0][1][0]
            logger.info(f"✓ OCR测试成功，识别结果: {detected_text}")
            return True
        else:
            logger.warning("⚠ OCR测试未识别到文本")
            return False

    except ImportError as e:
        logger.error(f"✗ PaddleOCR导入失败: {e}")
        return False
    except Exception as e:
        logger.error(f"✗ PaddleOCR测试失败: {e}")
        return False


def update_configuration():
    """更新配置文件"""
    logger.info("更新PaddleOCR配置...")

    try:
        config_dir = os.path.join(os.path.dirname(__file__), "..", "src", "config")
        os.makedirs(config_dir, exist_ok=True)

        config_file = os.path.join(config_dir, "paddleocr_config.py")

        config_content = '''"""
PaddleOCR配置文件
自动生成的配置，可根据需要调整
"""

# PaddleOCR基础配置
PADDLEOCR_BASE_CONFIG = {
    # 模型设置
    # 文字方向分类（兼容新旧版本参数名）
    "use_textline_orientation": True,  # 新版参数，推荐
    "use_angle_cls": True,             # 旧版参数，作为回退
    "lang": "ch",                 # 中文模式
    "use_gpu": False,             # CPU模式（可设置为True启用GPU）
    "gpu_mem": 8000,              # GPU内存限制（MB）
    "enable_mkldnn": True,        # 在CPU上启用MKLDNN加速

    # 检测参数
    "det_db_thresh": 0.3,        # 检测阈值
    "det_db_box_thresh": 0.6,    # 文本框阈值
    "det_model_dir": None,       # 自定义检测模型路径

    # 识别参数
    "rec_batch_num": 6,          # 识别批处理大小
    "rec_model_dir": None,       # 自定义识别模型路径
    "drop_score": 0.5,           # 识别置信度阈值

    # 性能设置
    # "show_log": False,           # 某些版本不支持该参数，避免在初始化中使用
    "use_mp": True,              # 启用多进程
    "total_process_num": 1,      # 进程数

    # 高级设置
    "det_algorithm": "DB++",     # 检测算法
    "rec_algorithm": "SVTR_LCNet", # 识别算法
    "use_space_char": True,      # 启用空格字符
}

# 中文合同优化配置
CHINESE_CONTRACT_CONFIG = {
    **PADDLEOCR_BASE_CONFIG,
    "det_db_thresh": 0.2,        # 降低检测阈值，提高敏感度
    "det_db_box_thresh": 0.5,    # 降低文本框阈值
    "drop_score": 0.3,          # 降低置信度阈值
    "rec_batch_num": 1,         # 单张处理提高精度
}

# 快速处理配置
FAST_PROCESSING_CONFIG = {
    **PADDLEOCR_BASE_CONFIG,
    "det_db_thresh": 0.4,        # 提高检测阈值，提高速度
    "rec_batch_num": 8,         # 增加批处理大小
    "drop_score": 0.6,          # 提高置信度阈值
}

# 混合OCR引擎优先级
OCR_ENGINE_PRIORITY = {
    "chinese_contract": ["paddleocr", "tesseract"],
    "english_document": ["tesseract", "paddleocr"],
    "mixed_content": ["paddleocr", "tesseract"],
    "simple_text": ["tesseract", "paddleocr"],
    "auto": ["paddleocr", "tesseract"]
}

def get_config_for_document_type(doc_type: str) -> dict:
    """根据文档类型获取配置"""
    if doc_type == "chinese_contract":
        return CHINESE_CONTRACT_CONFIG
    elif doc_type == "fast":
        return FAST_PROCESSING_CONFIG
    else:
        return PADDLEOCR_BASE_CONFIG
'''

        with open(config_file, "w", encoding="utf-8") as f:
            f.write(config_content)

        logger.info(f"✓ 配置文件已创建: {config_file}")
        return True

    except Exception as e:
        logger.error(f"✗ 配置文件创建失败: {e}")
        return False


def create_test_script():
    """创建测试脚本"""
    logger.info("创建PaddleOCR测试脚本...")

    try:
        test_script = os.path.join(os.path.dirname(__file__), "test_paddleocr.py")

        test_content = '''#!/usr/bin/env python3
"""
PaddleOCR功能测试脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.paddleocr_service import paddleocr_service
from src.services.hybrid_ocr_service import hybrid_ocr_service

def test_paddleocr():
    """测试PaddleOCR服务"""
    print("=== PaddleOCR服务测试 ===")

    # 检查系统信息
    info = paddleocr_service.get_ocr_system_info()
    print(f"PaddleOCR可用: {info['paddleocr_available']}")
    print(f"引擎已加载: {info['ocr_engine_loaded']}")

    if info['paddleocr_available']:
        print("✓ PaddleOCR服务可用")

        # 显示功能特性
        features = info['features']
        print("功能特性:")
        for feature, enabled in features.items():
            print(f"  {feature}: {'✓' if enabled else '✗'}")
    else:
        print("✗ PaddleOCR服务不可用")
        return False

    return True

def test_hybrid_ocr():
    """测试混合OCR服务"""
    print("\\n=== 混合OCR服务测试 ===")

    # 检查系统信息
    info = hybrid_ocr_service.get_system_info()
    print(f"可用引擎: {info['engines_available']}")
    print(f"引擎总数: {info['total_engines']}")

    if info['total_engines'] > 0:
        print("✓ 混合OCR服务可用")

        # 显示引擎信息
        for name, engine in info['engines'].items():
            print(f"\\n引擎: {engine['name']}")
            print(f"  优势: {', '.join(engine['strengths'])}")
            print(f"  适用场景: {', '.join(engine['preferred_for'])}")
    else:
        print("✗ 混合OCR服务不可用")
        return False

    return True

def test_integration():
    """测试集成"""
    print("\\n=== 集成测试 ===")

    try:
        # 测试PDF导入系统是否能识别PaddleOCR
        from src.services.enhanced_pdf_converter import enhanced_pdf_converter_service

        # 检查系统信息
        ocr_info = enhanced_pdf_converter_service.get_ocr_system_info()
        print(f"OCR依赖可用: {ocr_info['ocr_available']}")
        print(f"Tesseract可用: {ocr_info['tesseract_available']}")

        print("✓ 集成测试完成")
        return True

    except Exception as e:
        print(f"✗ 集成测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("PaddleOCR功能测试")
    print("=" * 50)

    success = True

    success &= test_paddleocr()
    success &= test_hybrid_ocr()
    success &= test_integration()

    print("\\n" + "=" * 50)
    if success:
        print("✓ 所有测试通过")
        return 0
    else:
        print("✗ 部分测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
'''

        with open(test_script, "w", encoding="utf-8") as f:
            f.write(test_content)

        logger.info(f"✓ 测试脚本已创建: {test_script}")
        return True

    except Exception as e:
        logger.error(f"✗ 测试脚本创建失败: {e}")
        return False


def main():
    """主安装函数"""
    logger.info("开始PaddleOCR安装配置...")
    print("=" * 60)
    print("PaddleOCR安装配置程序")
    print("用于PDF智能导入系统的高精度中文识别")
    print("=" * 60)

    # 步骤1: 检查系统要求
    if not check_system_requirements():
        logger.error("系统要求检查失败，安装终止")
        return 1

    # 步骤2: 安装PaddleOCR
    if not install_paddleocr():
        logger.error("PaddleOCR安装失败")
        return 1

    # 步骤3: 测试安装
    if not test_paddleocr_installation():
        logger.error("PaddleOCR安装测试失败")
        return 1

    # 步骤4: 更新配置
    if not update_configuration():
        logger.error("配置更新失败")
        return 1

    # 步骤5: 创建测试脚本
    if not create_test_script():
        logger.error("测试脚本创建失败")
        return 1

    # 完成
    print("\n" + "=" * 60)
    print("✓ PaddleOCR安装配置完成！")
    print("=" * 60)
    print("已安装的组件:")
    print("  • PaddleOCR核心库")
    print("  • PaddlePaddle深度学习框架")
    print("  • 图像处理依赖 (PIL, OpenCV)")
    print("  • 混合OCR服务")
    print("\n下一步:")
    print("  1. 运行测试: python scripts/test_paddleocr.py")
    print("  2. 重启后端服务以加载新的OCR引擎")
    print("  3. 在PDF导入中享受更高精度的中文识别")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
