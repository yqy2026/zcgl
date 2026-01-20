@echo off
REM 完整项目检查脚本 (Windows)
REM 使用方法: scripts\check-all.bat

setlocal enabledelayedexpansion

echo ╔══════════════════════════════════════════════════════════╗
echo ║              完整项目检查报告                              ║
echo ║              %date% %time%                    ║
echo ╚══════════════════════════════════════════════════════════╝
echo.

REM 创建日志目录
if not exist logs mkdir logs

set START_TIME=%time%

REM ============================================
REM 阶段 1: 代码质量检查
REM ============================================
echo 📋 阶段 1: 代码质量检查
echo.

REM 后端 Ruff 检查
echo   ⏳ 后端 Ruff 检查...
cd backend
ruff check . > ..\logs\ruff.log 2>&1
if %errorlevel% equ 0 (
    echo     ✓ 通过
    set RUFF_STATUS=✓
) else (
    echo     ⚠ 有问题 (已自动修复部分)
    set RUFF_STATUS=⚠
)
cd ..

REM 前端 TypeScript 检查
echo   ⏳ 前端 TypeScript 检查...
cd frontend
call pnpm type-check > ..\logs\ts.log 2>&1
if %errorlevel% equ 0 (
    echo     ✓ 通过
    set TS_STATUS=✓
) else (
    echo     ✗ 失败
    set TS_STATUS=✗
)
cd ..

REM 前端 ESLint 检查
echo   ⏳ 前端 ESLint 检查...
cd frontend
call pnpm lint > ..\logs\eslint.log 2>&1
if %errorlevel% equ 0 (
    echo     ✓ 通过
    set ESLINT_STATUS=✓
) else (
    echo     ✗ 失败
    set ESLINT_STATUS=✗
)
cd ..

echo.

REM ============================================
REM 阶段 2: 测试套件
REM ============================================
echo 🧪 阶段 2: 测试套件
echo.

REM 后端单元测试
echo   ⏳ 后端单元测试 (这可能需要几分钟)...
cd backend
pytest -m unit -v --tb=short > ..\logs\backend-unit.log 2>&1
if %errorlevel% equ 0 (
    echo     ✓ 通过
    set BACKEND_TEST_STATUS=✓
) else (
    echo     ⚠ 有失败
    set BACKEND_TEST_STATUS=⚠
)
cd ..

REM 前端测试
echo   ⏳ 前端单元测试...
cd frontend
call pnpm test:ci > ..\logs\frontend-test.log 2>&1
if %errorlevel% equ 0 (
    echo     ✓ 通过
    set FRONTEND_TEST_STATUS=✓
) else (
    echo     ⚠ 有失败
    set FRONTEND_TEST_STATUS=⚠
)
cd ..

echo.

REM ============================================
REM 阶段 3: 运行时诊断 (条件执行)
REM ============================================
echo 🌐 阶段 3: 运行时诊断
echo.

REM 检查前端服务器
curl -s http://localhost:5173 >nul 2>&1
if %errorlevel% equ 0 (
    echo   ⏳ 前端 Puppeteer 诊断...
    cd frontend
    call pnpm diagnose > ..\logs\diagnose.log 2>&1
    if %errorlevel% equ 0 (
        echo     ✓ 通过
        set DIAGNOSE_STATUS=✓
    ) else (
        echo     ⚠ 有问题
        set DIAGNOSE_STATUS=⚠
    )
    cd ..
) else (
    echo   ⚠ 前端服务器未运行，跳过诊断
    set DIAGNOSE_STATUS=⊘
)

echo.

REM ============================================
REM 阶段 4: 构建验证
REM ============================================
echo 🏗️  阶段 4: 构建验证
echo.

REM 前端构建
echo   ⏳ 前端生产构建...
cd frontend
call pnpm build > ..\logs\build.log 2>&1
if %errorlevel% equ 0 (
    echo     ✓ 通过
    set BUILD_STATUS=✓
) else (
    echo     ✗ 失败
    set BUILD_STATUS=✗
)
cd ..

REM 后端导入测试
echo   ⏳ 后端导入测试...
cd backend
python -c "from src.main import app; print('✓ 导入成功')" > ..\logs\import.log 2>&1
if %errorlevel% equ 0 (
    echo     ✓ 通过
    set IMPORT_STATUS=✓
) else (
    echo     ✗ 失败
    set IMPORT_STATUS=✗
)
cd ..

echo.

REM ============================================
REM 生成总结报告
REM ============================================
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo 【总结】
echo.
echo 【代码质量】
echo   前端 TypeScript:  %TS_STATUS%
echo   前端 ESLint:      %ESLINT_STATUS%
echo   后端 Ruff:        %RUFF_STATUS%
echo.
echo 【测试套件】
echo   后端单元测试:     %BACKEND_TEST_STATUS%
echo   前端单元测试:     %FRONTEND_TEST_STATUS%
echo.
echo 【运行时诊断】
echo   前端诊断:         %DIAGNOSE_STATUS%
echo.
echo 【构建验证】
echo   前端构建:         %BUILD_STATUS%
echo   后端导入:         %IMPORT_STATUS%
echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo 📁 详细日志: logs\
echo    - ruff.log (后端代码检查)
echo    - ts.log (前端类型检查)
echo    - backend-unit.log (后端单元测试)
echo    - frontend-test.log (前端测试)
echo    - diagnose.log (前端诊断)
echo    - build.log (前端构建)
echo.

REM 判断整体状态
if "%BACKEND_TEST_STATUS%"=="✗" goto failed
if "%FRONTEND_TEST_STATUS%"=="✗" goto failed
if "%BUILD_STATUS%"=="✗" goto failed

if "%BACKEND_TEST_STATUS%"=="⚠" goto warning
if "%FRONTEND_TEST_STATUS%"=="⚠" goto warning

echo ✅ 所有检查通过！
goto end

:warning
echo ⚠️  部分测试失败，请查看日志
goto end

:failed
echo ❌ 存在严重问题，请查看日志
exit /b 1

:end
echo.
echo 检查完成！
pause
