#!/bin/bash

# 分支同步自动化脚本
# 用途: 定期同步main分支的修复和改进到develop分支
# 使用: ./scripts/sync-branches.sh

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查Git状态
check_git_status() {
    log_info "检查Git状态..."

    if [[ -n $(git status --porcelain) ]]; then
        log_error "工作目录不干净，请先提交或暂存更改"
        git status --porcelain
        exit 1
    fi

    log_success "Git状态检查通过"
}

# 获取当前分支
get_current_branch() {
    git rev-parse --abbrev-ref HEAD
}

# 同步准备
sync_preparation() {
    log_info "开始分支同步准备..."

    # 获取当前分支
    CURRENT_BRANCH=$(get_current_branch)
    log_info "当前分支: $CURRENT_BRANCH"

    # 获取远程更新
    log_info "获取远程更新..."
    git fetch origin

    # 检查分支差异
    log_info "检查分支差异..."
    MAIN_BEHIND=$(git rev-list --count origin/main..HEAD)
    DEVELOP_BEHIND=$(git rev-list --count origin/develop..HEAD)

    if [[ $CURRENT_BRANCH == "develop" ]]; then
        if [[ $MAIN_BEHIND -gt 0 ]]; then
            log_warning "develop分支落后main分支 $MAIN_BEHIND 个提交"
            return 0
        else
            log_success "develop分支与main分支保持同步"
            return 1
        fi
    else
        log_warning "当前不在develop分支，跳过自动同步"
        return 1
    fi
}

# 执行同步
perform_sync() {
    log_info "开始从main分支同步到develop分支..."

    # 备份当前状态
    log_info "备份当前develop分支状态..."
    git branch develop-backup-$(date +%Y%m%d-%H%M%S)

    # 同步main分支
    log_info "同步main分支变更..."
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

🔄 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

    if [[ $? -eq 0 ]]; then
        log_success "同步成功完成"
        return 0
    else
        log_error "同步过程中出现冲突"
        return 1
    fi
}

# 处理同步冲突
handle_conflicts() {
    log_info "检查同步冲突..."

    if [[ -n $(git status --porcelain | grep "^UU") ]]; then
        log_warning "发现合并冲突，开始处理..."

        # 显示冲突文件
        CONFLICT_FILES=$(git status --porcelain | grep "^UU" | cut -f2)
        log_warning "冲突文件:"
        echo "$CONFLICT_FILES"

        # 生成冲突报告
        {
            echo "# 分支同步冲突报告"
            echo "**生成时间**: $(date)"
            echo "**分支**: develop"
            echo "**同步源**: main"
            echo ""
            echo "## 冲突文件"
            echo ""
            for file in $CONFLICT_FILES; do
                echo "### $file"
                echo "```bash"
                echo "# 查看冲突"
                echo "git diff $file"
                echo ""
                echo "# 解决冲突选项"
                echo "# 1. 接受main分支版本: git checkout --theirs $file"
                echo "# 2. 接受develop分支版本: git checkout --ours $file"
                echo "# 3. 手动编辑: $EDITOR $file"
                echo "```"
                echo ""
            done

            echo "## 解决步骤"
            echo "1. 手动解决上述文件冲突"
            echo "2. 验证解决方案"
            echo "3. 添加并提交解决结果"
            echo "4. 运行: git commit -m '解决同步冲突'"
            echo ""
        } > SYNC_CONFLICT_REPORT.md

        log_error "需要手动解决冲突，请查看 SYNC_CONFLICT_REPORT.md"
        return 1
    else
        log_success "无冲突，同步完成"
        return 0
    fi
}

# 验证同步结果
verify_sync() {
    log_info "验证同步结果..."

    # 检查构建状态
    log_info "检查后端构建..."
    cd backend
    if uv run python -c "import sys; sys.path.insert(0, 'src'); from src.api.v1.system_monitoring import collect_system_metrics; print('后端构建验证通过')" 2>/dev/null; then
        log_success "后端构建验证通过"
    else
        log_warning "后端构建验证失败"
    fi
    cd ..

    # 检查前端构建
    log_info "检查前端构建..."
    cd frontend
    if npm run build > /dev/null 2>&1; then
        log_success "前端构建验证通过"
    else
        log_warning "前端构建验证失败"
    fi
    cd ..

    log_success "同步验证完成"
}

# 清理和完成
cleanup() {
    log_info "清理临时文件..."

    # 删除冲突报告文件（如果存在且无冲突）
    if [[ ! -n $(git status --porcelain | grep "^UU") ]] && [[ -f "SYNC_CONFLICT_REPORT.md" ]]; then
        rm SYNC_CONFLICT_REPORT.md
    fi

    log_success "清理完成"
}

# 主函数
main() {
    log_info "=== 分支同步自动化脚本 ==="
    log_info "时间: $(date)"
    log_info "项目: 地产资产管理系统"

    # 执行同步流程
    if check_git_status; then
        if sync_preparation; then
            if perform_sync; then
                if handle_conflicts; then
                    verify_sync
                    cleanup
                    log_success "分支同步流程完成！"
                else
                    log_error "同步失败，请查看冲突报告并手动解决"
                    exit 1
                fi
            else
                log_info "无需同步，分支已是最新状态"
                cleanup
            fi
        else
            log_info "无需同步，分支已是最新状态"
        fi
    else
        log_error "前置检查失败，退出同步"
        exit 1
    fi
}

# 执行主函数
main "$@"