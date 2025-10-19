#!/bin/bash

# 性能测试脚本
set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# 检查必要工具
check_tools() {
    log_info "检查性能测试工具..."
    
    if ! command -v lighthouse &> /dev/null; then
        log_warning "Lighthouse 未安装，正在安装..."
        npm install -g lighthouse
    fi
    
    if ! command -v ab &> /dev/null; then
        log_warning "Apache Bench 未安装，请手动安装"
    fi
    
    log_success "工具检查完成"
}

# 前端性能测试
test_frontend_performance() {
    log_info "开始前端性能测试..."
    
    local url=${1:-"http://localhost:5173"}
    local output_dir="performance-reports/frontend"
    
    mkdir -p $output_dir
    
    # Lighthouse 测试
    log_info "运行 Lighthouse 测试..."
    lighthouse $url \
        --output=html \
        --output=json \
        --output-path="$output_dir/lighthouse-$(date +%Y%m%d_%H%M%S)" \
        --chrome-flags="--headless --no-sandbox" \
        --quiet
    
    log_success "前端性能测试完成，报告保存在 $output_dir"
}

# 后端性能测试
test_backend_performance() {
    log_info "开始后端性能测试..."
    
    local base_url=${1:-"http://localhost:8002"}
    local output_dir="performance-reports/backend"
    
    mkdir -p $output_dir
    
    # API 端点测试
    local endpoints=(
        "/health"
        "/api/v1/assets"
        "/api/v1/assets?page=1&limit=20"
        "/api/v1/statistics/basic"
    )
    
    for endpoint in "${endpoints[@]}"; do
        log_info "测试端点: $endpoint"
        
        # 使用 Apache Bench 进行压力测试
        if command -v ab &> /dev/null; then
            ab -n 1000 -c 10 -g "$output_dir/$(basename $endpoint)-$(date +%Y%m%d_%H%M%S).tsv" \
               "$base_url$endpoint" > "$output_dir/$(basename $endpoint)-$(date +%Y%m%d_%H%M%S).txt"
        fi
        
        # 使用 curl 测试响应时间
        local response_time=$(curl -o /dev/null -s -w "%{time_total}" "$base_url$endpoint")
        echo "端点 $endpoint 响应时间: ${response_time}s"
    done
    
    log_success "后端性能测试完成，报告保存在 $output_dir"
}

# 数据库性能测试
test_database_performance() {
    log_info "开始数据库性能测试..."
    
    local output_dir="performance-reports/database"
    mkdir -p $output_dir
    
    # 生成测试数据
    log_info "生成测试数据..."
    docker-compose exec backend python -c "
import asyncio
from src.database import get_db
from src.models.asset import Asset
from sqlalchemy.orm import Session
import random
import string

async def generate_test_data():
    db = next(get_db())
    
    # 生成1000条测试数据
    for i in range(1000):
        asset = Asset(
            property_name=f'测试物业_{i}',
            ownership_entity=f'权属方_{random.randint(1, 10)}',
            address=f'测试地址_{i}',
            actual_property_area=random.uniform(100, 1000),
            rentable_area=random.uniform(50, 800),
            rented_area=random.uniform(0, 500),
            ownership_status=random.choice(['已确权', '未确权', '部分确权']),
            property_nature=random.choice(['经营类', '非经营类']),
            usage_status=random.choice(['出租', '闲置', '自用', '公房', '其他'])
        )
        db.add(asset)
    
    db.commit()
    print('测试数据生成完成')

asyncio.run(generate_test_data())
"
    
    # 测试查询性能
    log_info "测试数据库查询性能..."
    docker-compose exec database psql -U postgres asset_management -c "
        EXPLAIN ANALYZE SELECT * FROM assets WHERE ownership_entity = '权属方_1';
        EXPLAIN ANALYZE SELECT * FROM assets WHERE property_nature = '经营类' ORDER BY created_at DESC LIMIT 20;
        EXPLAIN ANALYZE SELECT COUNT(*) FROM assets GROUP BY ownership_status;
    " > "$output_dir/query-performance-$(date +%Y%m%d_%H%M%S).txt"
    
    log_success "数据库性能测试完成"
}

# 内存使用测试
test_memory_usage() {
    log_info "开始内存使用测试..."
    
    local output_dir="performance-reports/memory"
    mkdir -p $output_dir
    
    # 监控Docker容器内存使用
    log_info "监控容器内存使用..."
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}" \
        > "$output_dir/memory-usage-$(date +%Y%m%d_%H%M%S).txt"
    
    log_success "内存使用测试完成"
}

# 生成性能报告
generate_performance_report() {
    log_info "生成性能测试报告..."
    
    local report_file="performance-reports/summary-$(date +%Y%m%d_%H%M%S).md"
    
    cat > $report_file << EOF
# 性能测试报告

生成时间: $(date)

## 测试环境
- 操作系统: $(uname -s)
- CPU: $(nproc) 核心
- 内存: $(free -h | awk '/^Mem:/ {print $2}')
- Docker版本: $(docker --version)

## 前端性能
- Lighthouse 报告: performance-reports/frontend/
- 主要指标:
  - First Contentful Paint (FCP)
  - Largest Contentful Paint (LCP)
  - Cumulative Layout Shift (CLS)
  - Time to Interactive (TTI)

## 后端性能
- API 响应时间测试: performance-reports/backend/
- 主要端点性能:
  - /health: 健康检查
  - /api/v1/assets: 资产列表
  - /api/v1/statistics/basic: 基础统计

## 数据库性能
- 查询性能分析: performance-reports/database/
- 索引优化建议
- 慢查询分析

## 内存使用
- 容器内存使用: performance-reports/memory/
- 内存泄漏检测
- 垃圾回收分析

## 优化建议
1. 前端优化:
   - 启用代码分割
   - 优化图片资源
   - 使用CDN加速
   - 启用Gzip压缩

2. 后端优化:
   - 数据库连接池优化
   - 缓存策略实施
   - API响应压缩
   - 异步处理优化

3. 数据库优化:
   - 添加必要索引
   - 查询语句优化
   - 分页查询优化
   - 定期维护统计信息

## 性能监控
- 建议使用APM工具持续监控
- 设置性能告警阈值
- 定期进行性能回归测试
EOF

    log_success "性能测试报告已生成: $report_file"
}

# 清理测试数据
cleanup_test_data() {
    log_info "清理测试数据..."
    
    docker-compose exec backend python -c "
from src.database import get_db
from src.models.asset import Asset

db = next(get_db())
test_assets = db.query(Asset).filter(Asset.property_name.like('测试物业_%')).all()
for asset in test_assets:
    db.delete(asset)
db.commit()
print(f'已清理 {len(test_assets)} 条测试数据')
"
    
    log_success "测试数据清理完成"
}

# 主函数
main() {
    case "$1" in
        "all")
            check_tools
            test_frontend_performance $2
            test_backend_performance $2
            test_database_performance
            test_memory_usage
            generate_performance_report
            cleanup_test_data
            ;;
        "frontend")
            check_tools
            test_frontend_performance $2
            ;;
        "backend")
            test_backend_performance $2
            ;;
        "database")
            test_database_performance
            ;;
        "memory")
            test_memory_usage
            ;;
        "report")
            generate_performance_report
            ;;
        "cleanup")
            cleanup_test_data
            ;;
        *)
            echo "用法: $0 {all|frontend|backend|database|memory|report|cleanup} [url]"
            echo ""
            echo "命令说明:"
            echo "  all      - 运行所有性能测试"
            echo "  frontend - 前端性能测试"
            echo "  backend  - 后端性能测试"
            echo "  database - 数据库性能测试"
            echo "  memory   - 内存使用测试"
            echo "  report   - 生成性能报告"
            echo "  cleanup  - 清理测试数据"
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"