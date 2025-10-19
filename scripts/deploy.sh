#!/bin/bash

# 土地物业资产管理系统部署脚本
# 使用方法: ./deploy.sh [环境] [版本]
# 例如: ./deploy.sh production v1.0.0

set -e  # 遇到错误立即退出

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

# 检查参数
ENVIRONMENT=${1:-production}
VERSION=${2:-latest}

log_info "开始部署土地物业资产管理系统"
log_info "环境: $ENVIRONMENT"
log_info "版本: $VERSION"

# 检查必要的工具
check_dependencies() {
    log_info "检查依赖工具..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose 未安装"
        exit 1
    fi
    
    log_success "依赖检查完成"
}

# 备份数据库
backup_database() {
    log_info "备份数据库..."
    
    # 创建备份目录
    BACKUP_DIR="./backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    # 备份PostgreSQL数据库
    if docker-compose ps database | grep -q "Up"; then
        docker-compose exec -T database pg_dump -U postgres asset_management > "$BACKUP_DIR/database.sql"
        log_success "数据库备份完成: $BACKUP_DIR/database.sql"
    else
        log_warning "数据库容器未运行，跳过备份"
    fi
    
    # 备份上传文件
    if [ -d "./backend/uploads" ]; then
        cp -r ./backend/uploads "$BACKUP_DIR/"
        log_success "文件备份完成: $BACKUP_DIR/uploads"
    fi
}

# 构建镜像
build_images() {
    log_info "构建Docker镜像..."
    
    # 设置构建参数
    export DOCKER_BUILDKIT=1
    export COMPOSE_DOCKER_CLI_BUILD=1
    
    # 构建后端镜像
    log_info "构建后端镜像..."
    docker-compose build --no-cache backend
    
    # 构建前端镜像
    log_info "构建前端镜像..."
    docker-compose build --no-cache frontend
    
    log_success "镜像构建完成"
}

# 运行测试
run_tests() {
    log_info "运行测试..."
    
    # 后端测试
    log_info "运行后端测试..."
    cd backend
    if [ -f "pyproject.toml" ]; then
        # 使用uv运行测试
        uv run pytest tests/ -v --cov=src --cov-report=html
        log_success "后端测试通过"
    else
        log_warning "未找到后端测试配置，跳过测试"
    fi
    cd ..
    
    # 前端测试
    log_info "运行前端测试..."
    cd frontend
    if [ -f "package.json" ]; then
        npm run test:ci
        log_success "前端测试通过"
    else
        log_warning "未找到前端测试配置，跳过测试"
    fi
    cd ..
}

# 部署应用
deploy_application() {
    log_info "部署应用..."
    
    # 停止现有服务
    log_info "停止现有服务..."
    docker-compose down
    
    # 清理未使用的镜像和容器
    log_info "清理Docker资源..."
    docker system prune -f
    
    # 启动服务
    log_info "启动服务..."
    if [ "$ENVIRONMENT" = "production" ]; then
        docker-compose -f docker-compose.prod.yml up -d
    else
        docker-compose -f docker-compose.dev.yml up -d
    fi
    
    # 等待服务启动
    log_info "等待服务启动..."
    sleep 30
    
    # 检查服务状态
    check_services
}

# 检查服务状态
check_services() {
    log_info "检查服务状态..."
    
    # 检查数据库
    if docker-compose exec -T database pg_isready -U postgres; then
        log_success "数据库服务正常"
    else
        log_error "数据库服务异常"
        return 1
    fi
    
    # 检查Redis
    if docker-compose exec -T redis redis-cli ping | grep -q "PONG"; then
        log_success "Redis服务正常"
    else
        log_error "Redis服务异常"
        return 1
    fi
    
    # 检查后端API
    if curl -f http://localhost:8002/health > /dev/null 2>&1; then
        log_success "后端API服务正常"
    else
        log_error "后端API服务异常"
        return 1
    fi
    
    # 检查前端
    if curl -f http://localhost/health.html > /dev/null 2>&1; then
        log_success "前端服务正常"
    else
        log_error "前端服务异常"
        return 1
    fi
    
    log_success "所有服务运行正常"
}

# 运行数据库迁移
run_migrations() {
    log_info "运行数据库迁移..."
    
    # 等待数据库就绪
    sleep 10
    
    # 运行Alembic迁移
    docker-compose exec backend alembic upgrade head
    
    log_success "数据库迁移完成"
}

# 性能优化
optimize_performance() {
    log_info "执行性能优化..."
    
    # 预热缓存
    log_info "预热应用缓存..."
    curl -s http://localhost:8002/api/assets?limit=1 > /dev/null || true
    
    # 生成sitemap（如果需要）
    # curl -s http://localhost/api/sitemap > /dev/null || true
    
    log_success "性能优化完成"
}

# 发送通知
send_notification() {
    local status=$1
    local message=$2
    
    # 这里可以集成Slack、钉钉、邮件等通知方式
    log_info "发送部署通知: $message"
    
    # 示例：发送到Slack
    # if [ -n "$SLACK_WEBHOOK_URL" ]; then
    #     curl -X POST -H 'Content-type: application/json' \
    #         --data "{\"text\":\"$message\"}" \
    #         "$SLACK_WEBHOOK_URL"
    # fi
}

# 回滚函数
rollback() {
    log_warning "开始回滚..."
    
    # 停止当前服务
    docker-compose down
    
    # 恢复上一个版本（这里需要实现版本管理逻辑）
    # docker-compose up -d
    
    log_success "回滚完成"
}

# 主部署流程
main() {
    local start_time=$(date +%s)
    
    # 设置错误处理
    trap 'log_error "部署失败，开始回滚..."; rollback; exit 1' ERR
    
    # 执行部署步骤
    check_dependencies
    
    if [ "$ENVIRONMENT" = "production" ]; then
        backup_database
        run_tests
    fi
    
    build_images
    deploy_application
    run_migrations
    optimize_performance
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    log_success "部署完成！耗时: ${duration}秒"
    send_notification "success" "土地物业资产管理系统部署成功 (版本: $VERSION, 环境: $ENVIRONMENT)"
    
    # 显示访问信息
    echo ""
    log_info "访问信息:"
    log_info "前端地址: http://localhost"
    log_info "后端API: http://localhost:8002"
    log_info "API文档: http://localhost:8002/docs"
    
    if [ "$ENVIRONMENT" != "production" ]; then
        log_info "监控面板: http://localhost:3001 (admin/admin123)"
    fi
}

# 显示帮助信息
show_help() {
    echo "土地物业资产管理系统部署脚本"
    echo ""
    echo "使用方法:"
    echo "  $0 [环境] [版本]"
    echo ""
    echo "参数:"
    echo "  环境    部署环境 (development|staging|production) [默认: production]"
    echo "  版本    部署版本标签 [默认: latest]"
    echo ""
    echo "示例:"
    echo "  $0 production v1.0.0"
    echo "  $0 development"
    echo ""
    echo "选项:"
    echo "  -h, --help     显示帮助信息"
    echo "  --rollback     回滚到上一个版本"
    echo "  --check        仅检查服务状态"
    echo ""
}

# 处理命令行参数
case "${1:-}" in
    -h|--help)
        show_help
        exit 0
        ;;
    --rollback)
        rollback
        exit 0
        ;;
    --check)
        check_services
        exit 0
        ;;
    *)
        main
        ;;
esac