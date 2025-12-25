#!/usr/bin/env python3
"""
环境依赖配置脚本
检查和安装PDF导入功能所需的所有依赖
"""

import importlib
import os
import shutil
import subprocess
import sys


class EnvironmentSetup:
    """环境配置管理器"""

    def __init__(self):
        self.required_packages = {
            "OCR依赖": {
                "pytesseract": "0.3.13",
                "pdf2image": "1.17.0",
                "Pillow": "11.3.0",
                "opencv-python": "4.12.0"
            },
            "NLP依赖": {
                "spacy": "3.8.0",
                "jieba": "0.42.1",
                "fuzzywuzzy": "0.18.0",
                "python-Levenshtein": "0.25.1",
                "regex": "2023.0.0"
            },
            "PDF处理依赖": {
                "markitdown": "0.1.0",
                "pdfplumber": "0.11.0"
            },
            "异步处理依赖": {
                "aiofiles": "23.0.0"
            }
        }

        self.system_tools = {
            "Tesseract OCR": {
                "executable": "tesseract",
                "install_url": "https://github.com/UB-Mannheim/tesseract/wiki",
                "path_suggestions": [
                    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                    r"D:\Tesseract-OCR\tesseract.exe"
                ]
            },
            "Poppler": {
                "executable": "pdftoppm",
                "install_url": "http://blog.alivate.com.au/poppler-windows/",
                "path_suggestions": [
                    r"C:\Program Files\poppler\poppler-25.07.0\Library\bin\pdftoppm.exe",
                    r"C:\Program Files (x86)\poppler\poppler-25.07.0\Library\bin\pdftoppm.exe",
                    r"D:\poppler\poppler-25.07.0\Library\bin\pdftoppm.exe"
                ]
            },
            "FFmpeg": {
                "executable": "ffmpeg",
                "install_url": "https://ffmpeg.org/download.html",
                "path_suggestions": [
                    r"C:\ffmpeg\bin\ffmpeg.exe",
                    r"C:\Program Files\ffmpeg\bin\ffmpeg.exe"
                ]
            }
        }

    def check_package(self, package_name: str) -> tuple[bool, str]:
        """检查Python包是否已安装"""
        try:
            if package_name == "opencv-python":
                import cv2
                version = cv2.__version__
            elif package_name == "Pillow":
                from PIL import Image
                version = Image.__version__
            elif package_name == "python-Levenshtein":
                import Levenshtein
                version = Levenshtein.__version__
            else:
                module = importlib.import_module(package_name)
                version = getattr(module, '__version__', 'unknown')
            return True, version
        except ImportError:
            return False, "Not installed"
        except Exception as e:
            return False, str(e)

    def check_system_tool(self, tool_name: str, tool_info: dict) -> tuple[bool, str]:
        """检查系统工具是否可用"""
        # 首先检查PATH
        path = shutil.which(tool_info["executable"])
        if path:
            return True, path

        # 检查建议路径
        for suggestion in tool_info["path_suggestions"]:
            if os.path.exists(suggestion):
                return True, suggestion

        return False, "Not found"

    def install_package(self, package_name: str) -> tuple[bool, str]:
        """安装Python包"""
        try:
            result = subprocess.run([
                sys.executable, "-m", "pip", "install", package_name
            ], capture_output=True, text=True, timeout=300)

            if result.returncode == 0:
                return True, "Installation successful"
            else:
                return False, result.stderr
        except subprocess.TimeoutExpired:
            return False, "Installation timeout"
        except Exception as e:
            return False, str(e)

    def run_environment_check(self) -> dict:
        """运行完整的环境检查"""
        results = {
            "python_version": sys.version,
            "packages": {},
            "system_tools": {},
            "summary": {
                "total_packages": 0,
                "installed_packages": 0,
                "missing_packages": [],
                "total_tools": 0,
                "available_tools": 0,
                "missing_tools": []
            }
        }

        print("=== PDF导入功能环境检查 ===")
        print(f"Python版本: {sys.version}")
        print()

        # 检查Python包
        print("检查Python依赖包...")
        for category, packages in self.required_packages.items():
            print(f"\n{category}:")
            results["packages"][category] = {}

            for package, required_version in packages.items():
                installed, version = self.check_package(package)
                results["packages"][category][package] = {
                    "installed": installed,
                    "version": version,
                    "required_version": required_version
                }

                status = "OK" if installed else "MISSING"
                print(f"  [{status}] {package}: {version}")

                results["summary"]["total_packages"] += 1
                if installed:
                    results["summary"]["installed_packages"] += 1
                else:
                    results["summary"]["missing_packages"].append(package)

        # 检查系统工具
        print("\n检查系统工具...")
        for tool_name, tool_info in self.system_tools.items():
            print(f"\n{tool_name}:")
            available, path = self.check_system_tool(tool_name, tool_info)
            results["system_tools"][tool_name] = {
                "available": available,
                "path": path,
                "install_url": tool_info["install_url"]
            }

            status = "OK" if available else "MISSING"
            print(f"  [{status}] {tool_info['executable']}: {path}")

            results["summary"]["total_tools"] += 1
            if available:
                results["summary"]["available_tools"] += 1
            else:
                results["summary"]["missing_tools"].append(tool_name)

        # 打印摘要
        print("\n" + "="*50)
        print("环境检查摘要:")
        print(f"Python包: {results['summary']['installed_packages']}/{results['summary']['total_packages']} 已安装")
        print(f"系统工具: {results['summary']['available_tools']}/{results['summary']['total_tools']} 可用")

        if results["summary"]["missing_packages"]:
            print(f"\n缺失的Python包: {', '.join(results['summary']['missing_packages'])}")

        if results["summary"]["missing_tools"]:
            print(f"\n缺失的系统工具: {', '.join(results['summary']['missing_tools'])}")

        return results

    def setup_missing_packages(self, missing_packages: list[str]) -> dict:
        """安装缺失的Python包"""
        results = {}

        print("\n=== 安装缺失的Python包 ===")

        for package in missing_packages:
            print(f"\n安装 {package}...")
            success, message = self.install_package(package)
            results[package] = {"success": success, "message": message}

            status = "OK" if success else "FAIL"
            print(f"[{status}] {package}: {message}")

        return results

    def generate_setup_instructions(self) -> str:
        """生成安装说明"""
        instructions = """
=== PDF导入功能环境配置说明 ===

1. Python依赖包安装：
   pip install pytesseract>=0.3.13
   pip install pdf2image>=1.17.0
   pip install Pillow>=11.3.0
   pip install opencv-python>=4.12.0
   pip install spacy>=3.8.0
   pip install jieba>=0.42.1
   pip install fuzzywuzzy>=0.18.0
   pip install python-Levenshtein>=0.25.1
   pip install regex>=2023.0.0
   pip install markitdown>=0.1.0
   pip install pdfplumber>=0.11.0
   pip install aiofiles>=23.0.0

2. 系统工具安装：

   Tesseract OCR:
   - 下载地址: https://github.com/UB-Mannheim/tesseract/wiki
   - 建议安装路径: C:\\Program Files\\Tesseract-OCR
   - 确保将安装目录添加到系统PATH环境变量

   Poppler:
   - 下载地址: http://blog.alivate.com.au/poppler-windows/
   - 建议安装路径: C:\\Program Files\\poppler
   - 确保将bin目录添加到系统PATH环境变量

   FFmpeg (可选):
   - 下载地址: https://ffmpeg.org/download.html
   - 用于多媒体文件处理

3. 中文语言包安装：
   - 下载中文语言包 chi_sim
   - 放置到Tesseract安装目录的tessdata文件夹

4. 验证安装：
   运行 python scripts/environment_setup.py check
"""
        return instructions

def main():
    """主函数"""
    setup = EnvironmentSetup()

    if len(sys.argv) > 1 and sys.argv[1] == "check":
        # 仅检查环境
        results = setup.run_environment_check()

        # 如果有缺失的包，询问是否安装
        if results["summary"]["missing_packages"]:
            print(f"\n发现 {len(results['summary']['missing_packages'])} 个缺失的Python包")
            response = input("是否现在安装? (y/n): ")
            if response.lower() == 'y':
                setup.setup_missing_packages(results["summary"]["missing_packages"])
    else:
        # 显示完整说明
        print(setup.generate_setup_instructions())

        # 运行环境检查
        results = setup.run_environment_check()

if __name__ == "__main__":
    main()
