# 前端诊断命令

使用 Puppeteer 自动化运行 Chrome 浏览器，检查前端页面的运行时错误、网络请求问题和性能指标。

## 使用场景

当你需要：
- 快速检查前端是否有运行时错误
- 验证新代码是否引入了控制台错误
- 检查 API 请求是否正常
- 监控页面加载性能
- 在提交代码前进行全面前端检查

## 执行前检查

1. **确认开发服务器运行**
   ```bash
   # 检查前端是否在运行
   curl http://localhost:5173 > /dev/null 2>&1 && echo "✓ 前端运行中" || echo "✗ 前端未启动"
   ```

2. **如未启动，启动开发服务器**
   ```bash
   cd frontend && pnpm dev
   ```

## 执行步骤

### 步骤 1: 选择诊断模式

**快速诊断** (推荐日常使用):
```bash
cd frontend && pnpm diagnose
```

**可视化诊断** (调试用):
```bash
cd frontend && pnpm diagnose:headful
```

**特定路由诊断**:
```bash
cd frontend && pnpm diagnose:routes
```

### 步骤 2: 等待诊断完成

诊断过程会：
1. 启动 Chrome 浏览器（headless 或 headful 模式）
2. 逐个访问配置的页面
3. 收集控制台日志、网络请求、性能指标
4. 生成页面截图
5. 生成诊断报告

### 步骤 3: 查看报告

**自动打开 HTML 报告**:
```bash
cd frontend && pnpm diagnose:report
```

**或手动打开**:
```bash
# Windows
start frontend/diagnostics/diagnostic-report-*.html

# Mac
open frontend/diagnostics/diagnostic-report-*.html

# Linux
xdg-open frontend/diagnostics/diagnostic-report-*.html
```

## 报告解读

### ✅ 诊断通过

如果看到绿色 "✓ 前端诊断通过"，说明：
- 所有页面无控制台错误
- 无失败的 API 请求
- 页面加载性能正常

### ❌ 发现问题

如果看到红色 "✗ 发现前端问题"，检查：

**1. 控制台错误部分**
- 查看错误堆栈跟踪
- 定位到具体的文件和行号
- 修复错误后重新诊断

**2. 失败的网络请求部分**
- 检查 HTTP 状态码（401/403/500）
- 确认 API 端点是否正常
- 检查认证凭证是否有效

**3. 性能指标部分**
- DOM加载 > 1s: 需要优化
- 完全加载 > 3s: 需要优化
- 请求数过多: 考虑合并请求

## 常见问题诊断

### 问题 1: 页面空白

**可能原因**:
```typescript
// ❌ 未处理 null/undefined
{data.items.map(item => <Item />)}

// ✅ 正确处理
{data?.items?.map(item => <Item />) ?? <Empty />}
```

### 问题 2: API 请求 401

**可能原因**:
- Cookie 未正确设置
- 认证令牌过期
- 后端认证服务异常

**解决方法**:
1. 检查后端是否运行
2. 使用 `diagnose:headful` 打开 DevTools
3. 查看 Application -> Cookies

### 问题 3: 性能问题

**优化建议**:
```typescript
// ❌ 一次性加载所有数据
const { data } = await api.get('/assets');  // 10000 条记录

// ✅ 分页加载
const { data } = await api.get('/assets?page=1&size=20');
```

## 高级用法

### 检查特定页面

```bash
# 环境变量配置
PAGES=/dashboard,/assets/list,/maintenance/requests pnpm diagnose
```

### 自定义超时时间

```bash
# 默认 30 秒，增加到 60 秒
TIMEOUT=60000 pnpm diagnose
```

### 保存报告历史

```bash
# 创建存档目录
mkdir -p frontend/diagnostics/archive/$(date +%Y-%m-%d)

# 移动旧报告
mv frontend/diagnostics/*.json frontend/diagnostics/archive/$(date +%Y-%m-%d)/
```

## 集成到工作流

### 提交代码前

```bash
# 完整检查流程
pnpm audit:ui          # ESLint + TypeScript + Stylelint
pnpm diagnose          # Puppeteer 运行时检查
git commit             # 确认无问题后提交
```

### CI/CD 集成

```yaml
# .github/workflows/frontend-ci.yml
- name: Run frontend diagnostics
  run: |
    cd frontend
    pnpm build
    pnpm preview &
    sleep 10
    pnpm diagnose
  env:
    BASE_URL: http://localhost:4173
    HEADLESS: true
```

## 相关文件

- 诊断脚本: `frontend/scripts/diagnose/puppeteer-check.ts`
- 详细文档: `frontend/docs/frontend-diagnostics.md`
- 快速指南: `frontend/scripts/diagnose/README.md`

## 故障排除

### Puppeteer 安装失败

```bash
# 使用国内镜像
export PUPPETEER_DOWNLOAD_HOST=https://registry.npmmirror.com/-/binary/chromium-browser-snapshots
pnpm install -D puppeteer
```

### 超时错误

```bash
# 增加超时时间
TIMEOUT=60000 pnpm diagnose
```

### 截图目录权限错误

```bash
# Windows: 以管理员身份运行
# Linux/Mac:
chmod -R 755 frontend/diagnostics
```

---

**输出格式**: JSON + HTML 报告
**执行时间**: ~30-60 秒（取决于页面数量）
**依赖**: Puppeteer, Chrome/Chromium
