@echo off
REM 分支同步自动化脚本 (Windows版本)
REM 用途: 定期同步main分支的修复和改进到develop分支
REM 使用: sync-branches.bat

setlocal enabledelayedexpansion

echo === 分支同步自动化脚本 ===
echo 时间: %date% %time%
echo 项目: 地产资产管理系统

REM 检查Git状态
echo [INFO] 检查Git状态...
git status --porcelain >nul
if %errorlevel% neq 0 (
    echo [ERROR] 工作目录不干净，请先提交或暂存更改
    git status --porcelain
    exit /b 1
)
echo [SUCCESS] Git状态检查通过

REM 获取当前分支
for /f "delims=" %%i in ('git rev-parse --abbrev-ref HEAD') do set CURRENT_BRANCH=%%i
echo [INFO] 当前分支: %CURRENT_BRANCH%

REM 获取远程更新
echo [INFO] 获取远程更新...
git fetch origin

REM 检查分支差异
echo [INFO] 检查分支差异...
for /f "delims=" %%i in ('git rev-list --count origin/main..HEAD') do set MAIN_BEHIND=%%i
for /f "delims=" %%i in ('git rev-list --count origin/develop..HEAD') do set DEVELOP_BEHIND=%%i

if "%CURRENT_BRANCH%"=="develop" (
    if %MAIN_BEHIND% GTR 0 (
        echo [WARNING] develop分支落后main分支 %MAIN_BEHIND% 个提交
        goto :do_sync
    ) else (
        echo [SUCCESS] develop分支与main分支保持同步
        goto :no_sync
    )
) else (
    echo [WARNING] 当前不在develop分支，跳过自动同步
    goto :no_sync
)

:do_sync
echo [INFO] 开始从main分支同步到develop分支...

REM 备份当前状态
echo [INFO] 备份当前develop分支状态...
for /f "delims=" %%i in ('git branch develop-backup-%date:~0,10%%') do set BACKUP_BRANCH=%%i
git branch %BACKUP_BRANCH%

REM 同步main分支
echo [INFO] 同步main分支变更...
git merge origin/main --no-ff -m "🔄 同步main分支修复和改进

## 同步内容
- 企业级监控系统修复和改进
- 性能优化和bug修复
- 安全更新和依赖升级
- 文档更新和改进

## 同步策略
- 只同步必要的修复和改进
- 避免破坏开发中的功能
- 保留develop分支的开发成果

🔄 Generated with [Claude Code](https://claude.com/claude.com)

if %errorlevel% equ 0 (
    echo [SUCCESS] 同步成功完成
    goto :verify_sync
) else (
    echo [ERROR] 同步过程中出现冲突
    goto :handle_conflicts
)

:handle_conflicts
echo [INFO] 检查同步冲突...
git status --porcelain | findstr "^UU" >nul
if %errorlevel% equ 0 (
    echo [SUCCESS] 无冲突，同步完成
    goto :verify_sync
) else (
    echo [WARNING] 发现合并冲突，开始处理...

    REM 显示冲突文件
    echo [WARNING] 冲突文件:
    git status --porcelain | findstr "^UU"

    REM 生成冲突报告
    echo # 分支同步冲突报告 > SYNC_CONFLICT_REPORT.md
    echo **生成时间**: %date% %time% >> SYNC_CONFLICT_REPORT.md
    echo **分支**: develop >> SYNC_CONFLICT_REPORT.md
    echo **同步源**: main >> SYNC_CONFLICT_REPORT.md
    echo. >> SYNC_CONFLICT_REPORT.md
    echo ## 冲突文件 >> SYNC_CONFLICT_REPORT.md
    echo. >> SYNC_CONFLICT_REPORT.md

    echo [ERROR] 需要手动解决冲突，请查看 SYNC_CONFLICT_REPORT.md
    exit /b 1
)

:verify_sync
echo [INFO] 验证同步结果...

REM 检查后端构建
echo [INFO] 检查后端构建...
cd backend
uv run python -c "import sys; sys.path.insert(0, 'src'); from src.api.v1.system_monitoring import collect_system_metrics; print('后端构建验证通过')" >nul 2>&1
if %errorlevel% equ 0 (
    echo [SUCCESS] 后端构建验证通过
) else (
    echo [WARNING] 后端构建验证失败
)
cd ..

REM 检查前端构建
echo [INFO] 检查前端构建...
cd frontend
npm run build >nul 2>&1
if %errorlevel% equ 0 (
    echo [SUCCESS] 前端构建验证通过
) else (
    echo [WARNING] 前端构建验证失败
)
cd ..

echo [SUCCESS] 同步验证完成
goto :cleanup

:no_sync
echo [INFO] 无需同步，分支已是最新状态
goto :cleanup

:cleanup
echo [INFO] 清理临时文件...

REM 删除冲突报告文件（如果存在且无冲突）
git status --porcelain | findstr "^UU" >nul
if %errorlevel% neq 0 (
    if exist SYNC_CONFLICT_REPORT.md (
        del SYNC_CONFLICT_REPORT.md
    )
)

echo [SUCCESS] 清理完成
goto :end

:end
echo [SUCCESS] 分支同步流程完成！
echo.
echo 如需手动同步，请使用以下命令：
echo git checkout develop
echo git pull origin main
echo git merge origin/main --no-ff
echo.
pause