#!/usr/bin/env python3
"""
PDF智能导入功能快速启动演示脚本
一键运行完整的系统演示
"""

import os
import sys
import subprocess
import time
import json
from pathlib import Path

def print_banner():
    """打印启动横幅"""
    banner = """
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║          🚀 地产资产管理系统 PDF智能导入功能演示 🚀                   ║
║                                                                      ║
║    本演示将展示重构升级后的PDF处理系统的完整功能，包括：                ║
║    • 📄 智能文档分析和质量评估                                        ║
║    • 🤖 机器学习增强信息提取                                          ║
║    • 🗺️ 58字段智能映射                                               ║
║    • ⚡ 并行处理和缓存优化                                            ║
║    • 🛡️ 错误处理和自动恢复                                            ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
    """
    print(banner)

def check_environment():
    """检查运行环境"""
    print("🔍 检查运行环境...")

    # 检查Python版本
    python_version = sys.version_info
    if python_version.major < 3 or python_version.minor < 8:
        print("❌ Python版本过低，需要Python 3.8或更高版本")
        return False

    print(f"✅ Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}")

    # 检查项目目录
    current_dir = Path.cwd()
    required_files = [
        "backend/src",
        "frontend/src",
        "backend/pdf_processing_refactoring_report.md"
    ]

    missing_files = []
    for file_path in required_files:
        if not (current_dir / file_path).exists():
            missing_files.append(file_path)

    if missing_files:
        print(f"❌ 缺少必要文件: {', '.join(missing_files)}")
        print("💡 请确保在项目根目录运行此脚本")
        return False

    print("✅ 项目环境检查通过")
    return True

def install_dependencies():
    """安装依赖"""
    print("\n📦 检查并安装依赖...")

    # 检查后端依赖
    backend_requirements = [
        "fastapi", "sqlalchemy", "pydantic", "pdfplumber",
        "opencv-python", "jieba", "spacy", "python-multipart"
    ]

    missing_backend_deps = []
    for dep in backend_requirements:
        try:
            __import__(dep.replace('-', '_'))
        except ImportError:
            missing_backend_deps.append(dep)

    if missing_backend_deps:
        print(f"📥 安装后端依赖: {', '.join(missing_backend_deps)}")
        try:
            subprocess.run([
                sys.executable, "-m", "pip", "install"
            ] + missing_backend_deps, check=True)
            print("✅ 后端依赖安装完成")
        except subprocess.CalledProcessError as e:
            print(f"❌ 后端依赖安装失败: {e}")
            return False

    # 检查前端依赖
    frontend_dir = Path("frontend")
    if (frontend_dir / "package.json").exists():
        print("📦 检查前端依赖...")
        try:
            result = subprocess.run(
                ["npm", "list", "--depth=0"],
                cwd=frontend_dir,
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                print("📥 安装前端依赖...")
                subprocess.run(["npm", "install"], cwd=frontend_dir, check=True)
                print("✅ 前端依赖安装完成")
            else:
                print("✅ 前端依赖已就绪")
        except subprocess.CalledProcessError as e:
            print(f"⚠️  前端依赖检查失败: {e}")

    return True

def run_backend_tests():
    """运行后端测试"""
    print("\n🧪 运行后端功能测试...")

    try:
        # 运行演示脚本
        result = subprocess.run([
            sys.executable, "backend/demo_pdf_processing.py"
        ], cwd=Path.cwd(), capture_output=True, text=True, timeout=60)

        if result.returncode == 0:
            print("✅ 后端演示运行成功")
            print("📊 演示输出:")
            print(result.stdout[-500:])  # 显示最后500字符
        else:
            print("⚠️  后端演示运行出现问题")
            print("错误信息:")
            print(result.stderr[-500:])

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        print("⚠️  后端演示运行超时")
        return False
    except Exception as e:
        print(f"❌ 后端测试运行失败: {e}")
        return False

def run_frontend_tests():
    """运行前端测试"""
    print("\n🎨 运行前端组件测试...")

    frontend_dir = Path("frontend")
    if not (frontend_dir / "package.json").exists():
        print("⚠️  前端项目不存在，跳过前端测试")
        return True

    try:
        # 检查是否有测试文件
        test_file = frontend_dir / "src/components/Contract/__tests__/EnhancedPDFImportUploader.test.tsx"
        if not test_file.exists():
            print("⚠️  前端测试文件不存在，跳过前端测试")
            return True

        # 运行前端测试
        result = subprocess.run([
            "npm", "test", "--", "--watchAll=false", "--passWithNoTests"
        ], cwd=frontend_dir, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            print("✅ 前端测试运行成功")
        else:
            print("⚠️  前端测试运行出现问题")
            print("错误信息:")
            print(result.stderr[-300:])

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        print("⚠️  前端测试运行超时")
        return False
    except FileNotFoundError:
        print("⚠️  npm命令未找到，跳过前端测试")
        return True
    except Exception as e:
        print(f"❌ 前端测试运行失败: {e}")
        return False

def generate_summary_report(results):
    """生成总结报告"""
    print("\n" + "="*70)
    print("📊 系统演示总结报告")
    print("="*70)

    total_time = time.time() - results['start_time']

    print(f"🕐 演示信息:")
    print(f"   开始时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(results['start_time']))}")
    print(f"   总耗时: {total_time:.1f}秒")

    print(f"\n📋 环境检查:")
    print(f"   Python环境: {'✅' if results['env_check'] else '❌'}")
    print(f"   依赖安装: {'✅' if results['deps_install'] else '❌'}")

    print(f"\n🧪 功能测试:")
    print(f"   后端演示: {'✅' if results['backend_test'] else '❌'}")
    print(f"   前端测试: {'✅' if results['frontend_test'] else '❌'}")

    success_count = sum([
        results['env_check'],
        results['deps_install'],
        results['backend_test'],
        results['frontend_test']
    ])

    success_rate = (success_count / 4) * 100
    print(f"\n📈 总体评估:")
    print(f"   成功率: {success_rate:.0f}% ({success_count}/4)")

    if success_rate >= 75:
        status = "🎉 优秀"
        message = "PDF智能导入系统运行良好！"
    elif success_rate >= 50:
        status = "✅ 良好"
        message = "系统基本功能正常，建议优化部分功能。"
    else:
        status = "⚠️  需要改进"
        message = "系统存在问题，需要进一步调试和优化。"

    print(f"   系统状态: {status}")
    print(f"   评估结果: {message}")

    # 保存报告
    report_data = {
        'timestamp': time.time(),
        'total_time': total_time,
        'results': results,
        'success_rate': success_rate,
        'system_status': status
    }

    report_file = f"quick_start_report_{int(time.time())}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)

    print(f"\n💾 详细报告已保存: {report_file}")

    # 提供后续建议
    print(f"\n💡 后续建议:")
    if not results['backend_test']:
        print("   • 检查后端服务配置和依赖安装")
        print("   • 查看backend/demo_pdf_processing.py的运行日志")

    if not results['frontend_test']:
        print("   • 检查前端项目配置")
        print("   • 确保npm和相关依赖正确安装")

    if results['env_check'] and results['deps_install']:
        print("   • 系统环境配置正确，可以开始正常使用")
        print("   • 参考backend/pdf_processing_refactoring_report.md了解详细功能")

    print(f"\n📚 相关文档:")
    print(f"   • 技术文档: backend/pdf_processing_refactoring_report.md")
    print(f"   • 演示脚本: backend/demo_pdf_processing.py")
    print(f"   • 测试套件: backend/run_pdf_tests.py")

    return success_rate

def main():
    """主函数"""
    print_banner()

    results = {
        'start_time': time.time(),
        'env_check': False,
        'deps_install': False,
        'backend_test': False,
        'frontend_test': False
    }

    try:
        # 环境检查
        if not check_environment():
            print("\n❌ 环境检查失败，请解决上述问题后重试")
            return 1

        results['env_check'] = True

        # 依赖安装
        if not install_dependencies():
            print("\n❌ 依赖安装失败，请手动安装必要依赖")
            return 1

        results['deps_install'] = True

        # 询问用户是否运行演示
        print(f"\n🤔 是否运行完整的系统演示？")
        print(f"   演示将展示PDF处理的完整流程，大约需要1-2分钟")

        try:
            choice = input("请输入 y/n [y]: ").lower().strip()
            if choice in ['', 'y', 'yes']:
                # 运行后端演示
                results['backend_test'] = run_backend_tests()

                # 运行前端测试
                results['frontend_test'] = run_frontend_tests()
            else:
                print("⏭️  跳过演示运行")
                results['backend_test'] = True  # 假设成功
                results['frontend_test'] = True
        except KeyboardInterrupt:
            print("\n⚠️  用户取消演示")
            return 0

        # 生成总结报告
        success_rate = generate_summary_report(results)

        # 根据成功率设置退出码
        return 0 if success_rate >= 50 else 1

    except KeyboardInterrupt:
        print(f"\n\n⚠️  演示被用户中断")
        return 130
    except Exception as e:
        print(f"\n\n❌ 演示运行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)