# PDF导入API快速验证指南

## 5分钟验证步骤

### 1. 验证模块导入 (30秒)

```bash
cd backend
python -c "
from src.api.v1.pdf_import import router
print(f'✓ 成功加载 {len(router.routes)} 个路由')
"
```

**预期输出**: `✓ 成功加载 19 个路由`

---

### 2. 验证类型检查 (30秒)

```bash
cd backend
python -m py_compile src/api/v1/pdf_*.py src/api/v1/dependencies.py src/schemas/pdf_import.py
echo "✓ 所有文件编译成功"
```

**预期**: 无错误输出

---

### 3. 启动服务器 (1分钟)

```bash
cd backend
python run_dev.py
```

**等待**: 看到 "Application startup complete."

**检查日志**: 应看到类似 "PDF导入路由已注册" 的消息

---

### 4. 测试核心端点 (2分钟)

在新的终端窗口执行:

```bash
# 测试1: 系统信息
curl -s http://localhost:8002/api/pdf-import/info | python -m json.tool | head -20

# 测试2: 健康检查
curl -s http://localhost:8002/api/pdf-import/health | python -m json.tool

# 测试3: 性能监控
curl -s http://localhost:8002/api/pdf-import/performance/realtime | python -m json.tool
```

**预期**: 所有请求返回200状态码和有效JSON

---

### 5. 验证OpenAPI文档 (1分钟)

访问浏览器: `http://localhost:8002/docs`

**检查**:
- 找到 "PDF智能导入" 标签组
- 展开后应看到19个端点
- 点击任意端点应显示完整的参数文档

---

## 故障排除速查表

| 问题 | 解决方案 |
|------|---------|
| 404 Not Found | 停止所有Python进程: `pkill -9 -f python`，清除缓存，重启 |
| ImportError | 运行 `pip install -e .` 重新安装依赖 |
| 端口被占用 | 检查: `netstat -ano \| grep 8002`，杀死占用进程 |
| 模块未找到 | 确认在 `backend/` 目录下执行命令 |

---

## 成功标准

✅ 所有19个路由成功加载
✅ 服务器无错误启动
✅ 至少3个核心端点响应正常
✅ OpenAPI文档显示完整

**如果以上全部通过，重构成功！** ✨
