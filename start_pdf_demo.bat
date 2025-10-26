@echo off
chcp 65001 >nul
echo.
echo ╔══════════════════════════════════════════════════════════════════════╗
echo ║                                                                      ║
echo ║          🚀 PDF智能导入功能演示 - 一键启动 🚀                          ║
echo ║                                                                      ║
echo ║    本演示将展示重构升级后的PDF处理系统的完整功能                        ║
echo ║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 错误: 未找到Python，请先安装Python 3.8或更高版本
    echo 💡 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ✅ Python环境检查通过
echo.

REM 显示菜单
:menu
echo 请选择操作:
echo.
echo 1. 🚀 完整演示 (推荐) - 自动检查环境并运行完整演示
echo 2. 🧪 仅运行测试 - 跳过环境检查，直接运行功能测试
echo 3. 📊 性能基准测试 - 运行性能基准测试
echo 4. 📖 查看使用文档 - 打开PDF导入功能使用指南
echo 5. 🛠️  环境检查 - 检查系统环境和依赖
echo 6. 📋 查看项目结构 - 显示当前项目文件结构
echo 0. 🚪 退出
echo.
set /p choice=请输入选择 (0-6):

if "%choice%"=="1" goto full_demo
if "%choice%"=="2" goto test_only
if "%choice%"=="3" goto benchmark
if "%choice%"=="4" goto view_docs
if "%choice%"=="5" goto env_check
if "%choice%"=="6" goto show_structure
if "%choice%"=="0" goto exit
echo.
echo ❌ 无效选择，请重新输入
echo.
goto menu

:full_demo
echo.
echo 🚀 启动完整演示...
echo 正在检查环境和依赖...
echo.
python quick_start_demo.py
pause
goto menu

:test_only
echo.
echo 🧪 运行功能测试...
echo.
if exist "backend\demo_pdf_processing.py" (
    echo ✅ 找到演示脚本
    cd backend
    python demo_pdf_processing.py
    cd ..
) else (
    echo ❌ 未找到演示脚本: backend\demo_pdf_processing.py
    echo 💡 请确保在项目根目录运行此脚本
)
pause
goto menu

:benchmark
echo.
echo 📊 运行性能基准测试...
echo.
if exist "backend\tests\performance_benchmark_pdf_processing.py" (
    echo ✅ 找到性能测试脚本
    cd backend
    python tests\performance_benchmark_pdf_processing.py
    cd ..
) else (
    echo ❌ 未找到性能测试脚本
    echo 💡 请确保测试文件存在
)
pause
goto menu

:view_docs
echo.
echo 📖 打开使用文档...
echo.
if exist "PDF_IMPORT_README.md" (
    echo ✅ 找到使用文档
    start PDF_IMPORT_README.md
) else (
    echo ❌ 未找到使用文档: PDF_IMPORT_README.md
    echo 💡 文档可能不存在或已被移动
)
pause
goto menu

:env_check
echo.
echo 🛠️  检查系统环境...
echo.

echo 🔍 检查Python版本:
python --version
echo.

echo 🔍 检查项目文件:
if exist "backend\src" (
    echo ✅ 后端源码目录存在
) else (
    echo ❌ 后端源码目录不存在
)

if exist "frontend\src" (
    echo ✅ 前端源码目录存在
) else (
    echo ❌ 前端源码目录不存在
)

if exist "backend\pdf_processing_refactoring_report.md" (
    echo ✅ 技术文档存在
) else (
    echo ❌ 技术文档不存在
)

echo.
echo 🔍 检查Python依赖:
echo 检查核心依赖包...

python -c "import fastapi; print('✅ fastapi')" 2>nul || echo "❌ fastapi 未安装"
python -c "import sqlalchemy; print('✅ sqlalchemy')" 2>nul || echo "❌ sqlalchemy 未安装"
python -c "import pydantic; print('✅ pydantic')" 2>nul || echo "❌ pydantic 未安装"
python -c "import pdfplumber; print('✅ pdfplumber')" 2>nul || echo "❌ pdfplumber 未安装"
python -c "import cv2; print('✅ opencv-python')" 2>nul || echo "❌ opencv-python 未安装"
python -c "import jieba; print('✅ jieba')" 2>nul || echo "❌ jieba 未安装"
python -c "import spacy; print('✅ spacy')" 2>nul || echo "❌ spacy 未安装"

echo.
echo 🔍 检查前端环境:
if exist "frontend\package.json" (
    echo ✅ 前端package.json存在
    npm --version >nul 2>&1
    if %errorlevel% equ 0 (
        echo ✅ npm已安装
        npm --version
    ) else (
        echo ❌ npm未安装
    )
) else (
    echo ❌ 前端项目不存在
)

echo.
echo 📊 环境检查完成
pause
goto menu

:show_structure
echo.
echo 📋 当前项目结构:
echo.
echo 📁 地产资产管理系统
echo ├── 📁 backend (后端服务)
echo │   ├── 📁 src (源代码)
echo │   │   ├── 📁 services (业务服务)
echo │   │   │   ├── 📄 enhanced_pdf_processor.py
echo │   │   │   ├── 📄 ml_enhanced_extractor.py
echo │   │   │   ├── 📄 enhanced_field_mapper.py
echo │   │   │   ├── 📄 parallel_pdf_processor.py
echo │   │   │   └── 📄 pdf_processing_monitor.py
echo │   │   └── 📁 api (API接口)
echo │   ├── 📁 tests (测试文件)
echo │   ├── 📄 demo_pdf_processing.py (演示脚本)
echo │   ├── 📄 run_pdf_tests.py (测试运行器)
echo │   └── 📄 pdf_processing_refactoring_report.md (技术文档)
echo ├── 📁 frontend (前端应用)
echo │   ├── 📁 src (源代码)
echo │   │   ├── 📁 components (组件)
echo │   │   │   └── 📁 Contract (合同组件)
echo │   │   │       ├── 📄 EnhancedPDFImportUploader.tsx
echo │   │   │       └── 📁 __tests__ (组件测试)
echo │   │   └── 📁 services (API服务)
echo │   └── 📄 package.json (依赖配置)
echo ├── 📄 quick_start_demo.py (快速启动脚本)
echo ├── 📄 PDF_IMPORT_README.md (使用指南)
echo └── 📄 start_pdf_demo.bat (Windows启动脚本)
echo.

REM 显示文件大小和修改时间
echo 📊 核心文件信息:
echo.
if exist "backend\src\services\enhanced_pdf_processor.py" (
    for %%f in ("backend\src\services\enhanced_pdf_processor.py") do echo 📄 增强PDF处理器: %%~zf KB, 修改时间: %%~tf
)

if exist "backend\demo_pdf_processing.py" (
    for %%f in ("backend\demo_pdf_processing.py") do echo 📄 演示脚本: %%~zf KB, 修改时间: %%~tf
)

if exist "PDF_IMPORT_README.md" (
    for %%f in ("PDF_IMPORT_README.md") do echo 📄 使用指南: %%~zf KB, 修改时间: %%~tf
)

echo.
pause
goto menu

:exit
echo.
echo 👋 感谢使用PDF智能导入功能演示！
echo.
echo 📚 更多信息:
echo • 技术文档: backend\pdf_processing_refactoring_report.md
echo • 使用指南: PDF_IMPORT_README.md
echo • 在线帮助: 运行 python quick_start_demo.py
echo.
timeout /t 3 >nul
exit /b 0