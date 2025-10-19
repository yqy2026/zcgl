@echo off
chcp 65001 >nul
echo ========================================
echo    Tesseract OCR 自动安装脚本
echo ========================================
echo.

REM 检查是否已安装tesseract
echo [INFO] 检查Tesseract OCR安装状态...
tesseract --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [SUCCESS] Tesseract OCR 已安装
    echo [INFO] 检查语言包...
    tesseract --list-langs
    goto :end
)

echo [WARNING] Tesseract OCR 未安装，开始下载...

REM 创建下载目录
if not exist "downloads" mkdir downloads
cd downloads

echo [INFO] 正在下载Tesseract OCR安装包...
REM 使用PowerShell下载安装包
powershell -Command "& {Invoke-WebRequest -Uri 'https://github.com/UB-Mannheim/tesseract/releases/download/v5.3.3/tesseract-ocr-w64-setup-5.3.3.exe' -OutFile 'tesseract-setup.exe'}"

if %errorlevel% neq 0 (
    echo [ERROR] 下载失败，请手动下载
    echo [INFO] 请访问: https://github.com/UB-Mannheim/tesseract/wiki
    echo [INFO] 下载Windows安装包并手动安装
    goto :manual_install
)

echo [SUCCESS] 下载完成，开始安装...
echo [INFO] 请在安装程序中勾选中文语言包 (Chinese Simplified)
echo [INFO] 建议安装路径: C:\Program Files\Tesseract-OCR
echo.

REM 启动安装程序
start /wait tesseract-setup.exe

echo [INFO] 安装完成，配置环境变量...
REM 添加到PATH
setx PATH "%PATH%;C:\Program Files\Tesseract-OCR" /M

echo [INFO] 验证安装...
timeout /t 3 /nobreak >nul
tesseract --version

if %errorlevel% equ 0 (
    echo [SUCCESS] Tesseract OCR 安装成功！
    echo [INFO] 检查可用语言包:
    tesseract --list-langs
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
echo 1. 访问: https://github.com/UB-Mannheim/tesseract/wiki
echo 2. 下载 tesseract-ocr-w64-setup-5.x.x.exe
echo 3. 运行安装程序，勾选以下语言包:
echo    - Chinese (Simplified) - 简体中文
echo    - English - 英文
echo 4. 安装路径建议: C:\Program Files\Tesseract-OCR
echo 5. 添加安装路径到系统PATH环境变量
echo.
echo 完成安装后，重新运行此脚本进行验证。

:end
echo.
echo ========================================
echo 安装脚本执行完成
echo ========================================
echo.
echo 下一步:
echo 1. 重启命令提示符
echo 2. 重新测试PDF智能导入功能
echo.
pause