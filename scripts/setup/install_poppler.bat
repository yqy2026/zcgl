@echo off
chcp 65001 >nul
echo ========================================
echo    Poppler 安装脚本
echo ========================================
echo.

REM 检查是否已安装poppler
echo [INFO] 检查Poppler安装状态...
pdfinfo --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [SUCCESS] Poppler 已安装
    echo [INFO] 版本信息:
    pdfinfo --version
    goto :end
)

echo [WARNING] Poppler 未安装，开始下载...

REM 创建下载目录
if not exist "downloads" mkdir downloads
cd downloads

echo [INFO] 正在下载Poppler...
REM 使用PowerShell下载Poppler
powershell -Command "& {Invoke-WebRequest -Uri 'https://github.com/oschwartz10612/poppler-windows/releases/download/v24.08.0-0/poppler-24.08.0-0.zip' -OutFile 'poppler.zip'}"

if %errorlevel% neq 0 (
    echo [ERROR] 下载失败，尝试备用链接...
    powershell -Command "& {Invoke-WebRequest -Uri 'http://blog.alivate.com.au/wp-content/uploads/2018/10/poppler-0.68.0.zip' -OutFile 'poppler.zip'}"

    if %errorlevel% neq 0 (
        echo [ERROR] 所有下载链接都失败
        echo [INFO] 请手动下载Poppler:
        echo 1. 访问: https://github.com/oschwartz10612/poppler-windows/releases/
        echo 2. 下载 poppler-xx.x.x-Release.zip
        echo 3. 解压到 C:\Program Files\poppler
        echo 4. 添加 bin目录到系统PATH
        goto :manual_install
    )
)

echo [SUCCESS] 下载完成，开始解压...

REM 检查系统架构
if exist "C:\Program Files (x86)" (
    set POPPLER_DIR=C:\Program Files (x86)\poppler
) else (
    set POPPLER_DIR=C:\Program Files\poppler
)

REM 创建安装目录
if not exist "%POPPLER_DIR%" mkdir "%POPPLER_DIR%"

REM 解压文件
echo [INFO] 解压到: %POPPLER_DIR%
powershell -Command "& {Expand-Archive -Path 'poppler.zip' -DestinationPath '%POPPLER_DIR%' -Force }"

if %errorlevel% neq 0 (
    echo [ERROR] 解压失败，请手动解压
    goto :manual_install
)

REM 添加到PATH
echo [INFO] 配置环境变量...
setx PATH "%PATH%;%POPPLER_DIR%\bin" /M

echo [INFO] 验证安装...
timeout /t 3 /nobreak >nul
pdfinfo --version

if %errorlevel% equ 0 (
    echo [SUCCESS] Poppler 安装成功！
    echo [INFO] 版本信息:
    pdfinfo --version
) else (
    echo [ERROR] 安装可能失败，请手动验证
)

goto :end

:manual_install
echo.
echo ========================================
echo           手动安装指导
echo ========================================
echo.
echo 1. 访问Poppler下载页面:
echo    https://github.com/oschwartz10612/poppler-windows/releases/
echo.
echo 2. 下载最新版本: poppler-xx.x.x-Release.zip
echo.
echo 3. 解压到: C:\Program Files\poppler
echo.
echo 4. 添加到系统PATH:
echo    - 右键"此电脑" → 属性 → 高级系统设置 → 环境变量
echo    - 在系统变量的Path中添加: C:\Program Files\poppler\bin
echo.
echo 5. 验证安装:
echo    pdfinfo --version
echo.

:end
echo.
echo ========================================
echo Poppler 安装脚本执行完成
echo ========================================
echo.
echo 下一步:
echo 1. 重启命令提示符
echo 2. 重新测试PDF智能导入功能
echo.
pause