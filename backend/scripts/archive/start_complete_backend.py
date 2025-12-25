#!/usr/bin/env python3
"""
修复版完整后端启动脚本
解决所有已知的依赖和配置问题
"""

import os
import subprocess
import sys
from pathlib import Path

# 设置项目根目录
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))


def setup_environment():
    """设置环境变量"""
    print("设置环境变量...")

    # 设置必要的环境变量
    os.environ["SECRET_KEY"] = (
        "a-strong-secret-key-for-development-environment-with-at-least-32-chars-long"
    )
    os.environ["DATABASE_URL"] = "sqlite:///./assets_management.db"
    os.environ["ENVIRONMENT"] = "development"

    print("环境变量设置完成")


def check_dependencies():
    """检查并安装依赖"""
    print(" 检查依赖...")

    required_packages = [
        "fastapi",
        "uvicorn",
        "sqlalchemy",
        "pydantic",
        "python-multipart",
        "python-jose",
        "passlib",
        "bcrypt",
        "pymupdf",
        "pdfplumber",
        "pillow",
        "paddleocr",
        "python-magic",
    ]

    missing_packages = []

    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f" {package}")
        except ImportError:
            print(f" {package} - 缺失")
            missing_packages.append(package)

    if missing_packages:
        print(f" 安装缺失的依赖: {missing_packages}")
        try:
            subprocess.run(
                ["uv", "add", *missing_packages],
                check=True,
                capture_output=True,
                text=True,
            )
            print(" 依赖安装完成")
        except subprocess.CalledProcessError as e:
            print(f" 依赖安装失败: {e}")
            return False

    return True


def fix_pdf_import_service():
    """修复PDF导入服务问题"""
    print(" 修复PDF导入服务...")

    # 检查PDF导入服务文件
    pdf_service_path = project_root / "src" / "services" / "pdf_import_service.py"

    if not pdf_service_path.exists():
        print(" PDF导入服务文件不存在")
        return False

    # 检查文件内容
    try:
        with open(pdf_service_path, encoding="utf-8") as f:
            content = f.read()

        # 检查是否有PDFImportService类
        if "class PDFImportService" not in content:
            print(" PDFImportService类不存在")
            return False

        print(" PDF导入服务检查通过")
        return True

    except Exception as e:
        print(f" PDF导入服务检查失败: {e}")
        return False


def fix_ocr_service():
    """修复OCR服务问题"""
    print(" 修复OCR服务...")

    ocr_service_path = (
        project_root / "src" / "services" / "document" / "optimized_ocr_service.py"
    )

    if not ocr_service_path.exists():
        print(" OCR服务文件不存在")
        return False

    try:
        with open(ocr_service_path, encoding="utf-8") as f:
            content = f.read()

        # 检查是否有show_log参数
        if "show_log=False" in content:
            print(" 移除show_log参数...")
            content = content.replace("show_log=False", "")

            with open(ocr_service_path, "w", encoding="utf-8") as f:
                f.write(content)

            print(" OCR服务修复完成")
        else:
            print(" OCR服务检查通过")

        return True

    except Exception as e:
        print(f" OCR服务修复失败: {e}")
        return False


def start_complete_backend():
    """启动完整后端"""
    print(" 启动完整后端...")

    try:
        # 设置环境变量
        setup_environment()

        # 检查依赖
        if not check_dependencies():
            print(" 依赖检查失败")
            return False

        # 修复PDF导入服务
        if not fix_pdf_import_service():
            print(" PDF导入服务修复失败")
            return False

        # 修复OCR服务
        if not fix_ocr_service():
            print(" OCR服务修复失败")
            return False

        print(" 所有检查通过，启动完整后端...")

        # 启动完整后端
        os.environ["SECRET_KEY"] = (
            "a-strong-secret-key-for-development-environment-with-at-least-32-chars-long"
        )
        subprocess.run(
            [
                "uv",
                "run",
                "python",
                "-m",
                "uvicorn",
                "src.main:app",
                "--host",
                "0.0.0.0",
                "--port",
                "8002",
                "--reload",
            ]
        )

        return True

    except KeyboardInterrupt:
        print("\n 后端服务已停止")
        return True
    except Exception as e:
        print(f" 启动失败: {e}")
        return False


def main():
    """主函数"""
    print(" 地产资产管理系统 - 完整后端启动器")
    print("=" * 50)

    success = start_complete_backend()

    if success:
        print(" 完整后端启动成功")
    else:
        print(" 完整后端启动失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
