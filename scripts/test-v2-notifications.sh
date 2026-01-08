#!/bin/bash
# V2.0 通知系统快速测试脚本

echo "================================"
echo "V2.0 通知系统测试"
echo "================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查后端服务
echo -n "检查后端服务... "
if curl -s http://localhost:8002/docs > /dev/null 2>&1; then
    echo -e "${GREEN}运行中${NC}"
    BACKEND_RUNNING=true
else
    echo -e "${RED}未运行${NC}"
    echo "请先启动后端: cd backend && python run_dev.py"
    BACKEND_RUNNING=false
fi

echo ""

# 测试通知 API（需要 TOKEN）
if [ "$BACKEND_RUNNING" = true ]; then
    echo "请输入您的访问 Token（从浏览器开发者工具获取）："
    read -r TOKEN

    if [ -n "$TOKEN" ]; then
        echo ""
        echo "================================"
        echo "测试通知 API"
        echo "================================"
        echo ""

        # 1. 获取通知列表
        echo -n "1. 获取通知列表... "
        RESPONSE=$(curl -s -X GET "http://localhost:8002/api/v1/notifications/?page=1&limit=10" \
            -H "Authorization: Bearer $TOKEN")
        if echo "$RESPONSE" | grep -q "items\|total"; then
            echo -e "${GREEN}成功${NC}"
            echo "$RESPONSE" | python -m json.tool 2>/dev/null || echo "$RESPONSE"
        else
            echo -e "${RED}失败${NC}"
            echo "$RESPONSE"
        fi
        echo ""

        # 2. 获取未读计数
        echo -n "2. 获取未读计数... "
        RESPONSE=$(curl -s -X GET "http://localhost:8002/api/v1/notifications/unread-count" \
            -H "Authorization: Bearer $TOKEN")
        if echo "$RESPONSE" | grep -q "unread_count"; then
            echo -e "${GREEN}成功${NC}"
            echo "$RESPONSE" | python -m json.tool 2>/dev/null || echo "$RESPONSE"
        else
            echo -e "${RED}失败${NC}"
            echo "$RESPONSE"
        fi
        echo ""

        # 3. 手动触发扫描任务
        echo -n "3. 触发合同到期扫描... "
        RESPONSE=$(curl -s -X POST "http://localhost:8002/api/v1/notifications/run-tasks" \
            -H "Authorization: Bearer $TOKEN")
        if echo "$RESPONSE" | grep -q "expiring_contracts\|timestamp"; then
            echo -e "${GREEN}成功${NC}"
            echo "$RESPONSE" | python -m json.tool 2>/dev/null || echo "$RESPONSE"
        else
            echo -e "${RED}失败${NC}"
            echo "$RESPONSE"
        fi
        echo ""
    fi
fi

# 检查数据库
echo "================================"
echo "检查数据库"
echo "================================"
echo ""

if [ -f "backend/land_property.db" ]; then
    echo -n "notifications 表是否存在... "
    RESULT=$(sqlite3 backend/land_property.db "SELECT name FROM sqlite_master WHERE type='table' AND name='notifications';")
    if [ -n "$RESULT" ]; then
        echo -e "${GREEN}存在${NC}"

        echo -n "表字段数量... "
        COUNT=$(sqlite3 backend/land_property.db "SELECT COUNT(*) FROM pragma_table_info('notifications');")
        echo -e "${GREEN}${COUNT} 个字段${NC}"

        echo -n "索引数量... "
        COUNT=$(sqlite3 backend/land_property.db "SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND tbl_name='notifications' AND name NOT LIKE 'sqlite_%';")
        echo -e "${GREEN}${COUNT} 个索引${NC}"

        echo -n "当前通知数量... "
        COUNT=$(sqlite3 backend/land_property.db "SELECT COUNT(*) FROM notifications;")
        echo -e "${GREEN}${COUNT} 条${NC}"
    else
        echo -e "${RED}不存在${NC}"
        echo "请运行: cd backend && alembic upgrade head"
    fi
else
    echo -e "${YELLOW}数据库文件不存在${NC}"
fi

echo ""

# 检查前端服务
echo "================================"
echo "前端验证"
echo "================================"
echo ""

echo -n "前端开发服务器... "
if curl -s http://localhost:5173 > /dev/null 2>&1; then
    echo -e "${GREEN}运行中${NC}"
    echo ""
    echo "请手动验证以下功能："
    echo "  1. 访问 http://localhost:5173"
    echo "  2. 登录系统"
    echo "  3. 点击右上角铃铛图标"
    echo "  4. 验证通知中心显示"
    echo ""
    echo "详情页验证："
    echo "  1. 访问 /project/{id} 验证项目详情页"
    echo "  2. 访问 /ownership/{id} 验证权属方详情页"
else
    echo -e "${RED}未运行${NC}"
    echo "请启动前端: cd frontend && npm run dev"
fi

echo ""
echo "================================"
echo "测试完成"
echo "================================"
