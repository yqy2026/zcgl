# 前端诊断指南

## 概述

本项目提供了一套完整的前端自动化诊断工具，使用 Puppeteer 驱动真实 Chrome 浏览器进行前端健康检查。

## ★ Insight ─────────────────────────────────────

**为什么需要自动化前端诊断？**

1. **真实浏览器环境**: 捕获只有在真实浏览器中才会出现的问题（如 CORS、内存泄漏）
2. **运行时错误**: TypeScript/Oxlint 只能检查静态代码，无法捕获运行时错误
3. **性能监控**: 自动测量页面加载时间、资源大小、网络请求耗时
4. **回归预防**: CI/CD 中自动检测新增错误，防止发布问题版本

**工具架构:**
- **Puppeteer**: 自动化 Chrome 浏览器操作
- **Reporter**: 生成 HTML/JSON 格式的诊断报告
- **Console Capture**: 捕获所有控制台日志（log, warn, error）
- **Network Monitor**: 监控所有网络请求，识别失败的 API 调用

─────────────────────────────────────────────────

## 快速开始

### 1. 基础诊断（推荐）

```bash
# 确保前端开发服务器运行在 :5173
cd frontend && pnpm dev

# 在另一个终端运行诊断
cd frontend && pnpm diagnose
```

**输出:**
- 终端显示实时进度
- 生成 JSON 报告: `test-results/frontend/diagnostics/diagnostic-report-*.json`
- 生成 HTML 报告: `test-results/frontend/diagnostics/diagnostic-report-*.html`
- 保存页面截图: `test-results/frontend/diagnostics/screenshots/`

### 2. 可视化模式（调试用）

```bash
# 显示浏览器窗口，方便观察检查过程
pnpm diagnose:headful
```

### 3. 自定义路由检查

```bash
# 只检查特定页面
BASE_URL=http://localhost:5173 PAGES=/dashboard,/assets/list pnpm diagnose

# 或使用预设
pnpm diagnose:routes
```

## 诊断命令参考

| 命令 | 说明 | 适用场景 |
|------|------|---------|
| `pnpm diagnose` | 完整诊断（headless） | CI/CD、快速检查 |
| `pnpm diagnose:headful` | 可视化诊断 | 调试、演示 |
| `pnpm diagnose:routes` | 检查核心路由 | 日常开发 |
| `pnpm diagnose:custom` | 自定义检查脚本 | 高级用法 |
| `pnpm diagnose:report` | 打开最新报告 | 查看结果 |

## 诊断报告说明

### HTML 报告结构

```
┌─────────────────────────────────────┐
│  ✅/❌ 前端诊断通过/发现问题          │
│  环境 | URL | 时间                    │
├─────────────────────────────────────┤
│  检查页面 | 控制台错误 | 失败请求    │  ← 汇总统计
├─────────────────────────────────────┤
│  📄 页面 1: /dashboard              │
│     ✓ DOM加载: 600ms                │
│     ✓ 完全加载: 1200ms              │
│     ✓ 错误: 0 | 警告: 2             │
│     [截图]                          │
├─────────────────────────────────────┤
│  📋 控制台日志 (详细)                │
│  🌐 失败的网络请求 (如果有)          │
└─────────────────────────────────────┘
```

### 关键指标

| 指标 | 说明 | 正常范围 |
|------|------|---------|
| **DOM加载** | DOM 树构建完成时间 | < 1s |
| **完全加载** | 所有资源加载完成 | < 3s |
| **控制台错误** | JavaScript 运行时错误 | 0 |
| **控制台警告** | Deprecation 警告等 | 越少越好 |
| **失败请求** | HTTP 4xx/5xx 错误 | 0 |

## 常见问题诊断

### 问题 1: 页面空白或无法加载

**症状:** 截图显示空白页面

**诊断步骤:**
1. 打开 HTML 报告，查看控制台错误
2. 检查是否有 React 渲染错误
3. 查看网络请求，确认 API 是否正常

**常见原因:**
```typescript
// ❌ 错误示例: 未处理 null/undefined
{data.items.map(item => <Item />)}  // data.items 为 null 时崩溃

// ✅ 正确示例: 使用可选链和默认值
{data?.items?.map(item => <Item />) ?? <Empty />}
```

### 问题 2: API 请求失败

**症状:** HTML 报告 "失败的网络请求" 部分显示红色错误

**诊断步骤:**
1. 在报告中找到失败的 API 端点
2. 检查状态码（401 认证失败、403 权限不足、500 服务器错误）
3. 使用 `diagnose:headful` 打开 Chrome DevTools Network 标签

**常见原因:**
- **CORS 错误**: 后端未配置允许的源
- **认证失败**: Cookie 未正确设置
- **超时**: 后端响应时间过长

### 问题 3: 性能问题

**症状:** DOM加载 > 3s，完全加载 > 5s

**诊断步骤:**
1. 查看报告中 "总请求数" 和 "总大小"
2. 识别大文件（如未压缩的图片）
3. 使用 Chrome DevTools Lighthouse 进一步分析

**优化建议:**
```typescript
// ❌ 错误: 一次性加载所有数据
const { data } = await api.get('/assets');  // 返回 10000 条记录

// ✅ 正确: 分页加载
const { data } = await api.get('/assets?page=1&size=20');
```

### 问题 4: React Hydration 错误

**症状:** 控制台显示 "Hydration failed" 或 "Text content does not match"

**诊断步骤:**
1. 在报告中查看堆栈跟踪
2. 找到报错的组件文件
3. 检查服务端渲染和客户端渲染的不一致

**常见原因:**
```typescript
// ❌ 错误: 使用 Date.now() 导致不一致
function Time() {
  return <div>{Date.now()}</div>;  // 每次渲染结果不同
}

// ✅ 正确: 使用 useEffect 只在客户端渲染
function Time() {
  const [time, setTime] = useState(null);
  useEffect(() => setTime(Date.now()), []);
  return <div>{time}</div>;
}
```

## 高级用法

### 1. 检查特定用户场景

创建自定义检查脚本 `scripts/diagnose/check-user-flow.ts`:

```typescript
import { FrontendDiagnostics } from './puppeteer-check';

async function checkUserFlow() {
  const diagnostics = new FrontendDiagnostics();

  // 模拟用户登录
  const browser = await puppeteer.launch({ headless: false });
  const page = await browser.newPage();

  await page.goto('http://localhost:5173/login');
  await page.type('#username', 'admin');
  await page.type('#password', 'password');
  await page.click('button[type="submit"]');

  // 等待跳转到 dashboard
  await page.waitForNavigation();

  // 检查 dashboard 是否正常
  const metrics = await diagnostics.checkPage(page, 'http://localhost:5173/dashboard', '/dashboard');

  console.log('Dashboard metrics:', metrics);

  await browser.close();
}

checkUserFlow();
```

### 2. 集成到 CI/CD

在 `.github/workflows/frontend-ci.yml` 中:

```yaml
name: Frontend CI

on: [push, pull_request]

jobs:
  diagnose:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '20'

      - name: Install dependencies
        run: cd frontend && pnpm install

      - name: Build frontend
        run: cd frontend && pnpm build

      - name: Start dev server
        run: cd frontend && pnpm preview &

      - name: Wait for server
        run: sleep 10

      - name: Run diagnostics
        run: cd frontend && pnpm diagnose
        env:
          BASE_URL: http://localhost:4173
          HEADLESS: true

      - name: Upload reports
        uses: actions/upload-artifact@v3
        with:
          name: diagnostic-reports
          path: test-results/frontend/diagnostics/
```

### 3. 监控生产环境

```bash
# 定期检查生产环境
BASE_URL=https://your-domain.com pnpm diagnose

# 使用 cron 每小时检查
0 * * * * cd /path/to/project/frontend && pnpm diagnose
```

## 手动 Chrome DevTools 调试

虽然自动化检查很强大，但有些问题仍需手动调试。

### 打开 Chrome DevTools

1. 在浏览器中打开 `http://localhost:5173`
2. 按 `F12` 或 `Ctrl+Shift+I` (Windows) / `Cmd+Option+I` (Mac)

### 关键标签

| 标签 | 用途 | 快捷键 |
|------|------|--------|
| **Console** | 查看运行时错误、日志 | Ctrl+Shift+J |
| **Network** | 查看所有网络请求、性能 | Ctrl+Shift+E |
| **Elements** | 检查 DOM、CSS | Ctrl+Shift+C |
| **Sources** | 断点调试代码 | Ctrl+Shift+S |
| **Performance** | 性能分析、火焰图 | - |
| **Lighthouse** | 综合性能、可访问性检查 | - |

### Console 标签技巧

```javascript
// 1. 过滤只显示错误
// 在 Filter 输入框输入: -url:*/node_modules* -url:*/vite/*

// 2. 监控特定函数
console.log('Debug: user data', userData);

// 3. 性能测量
console.time('fetchAssets');
await fetchAssets();
console.timeEnd('fetchAssets');

// 4. 表格化显示对象
console.table(assets);
```

### Network 标签技巧

```javascript
// 1. 过滤 API 请求
// 在 Filter 输入框输入: /api/

// 2. 查看请求/响应详情
// 点击请求 → Headers / Preview / Response

// 3. 重新发送 XHR 请求
// 右键点击请求 → Replay XHR

// 4. 导出 HAR 文件
// 右键 → Save all as HAR with content
```

### React DevTools

```bash
# 安装 React DevTools 扩展
# Chrome: https://chrome.google.com/webstore/detail/react-developer-tools/
# Firefox: https://addons.mozilla.org/firefox/addon/react-devtools/

# 使用方式
1. 打开 DevTools
2. 点击 "Components" 标签
3. 选择组件查看 Props 和 State
4. 使用 "$r" 在 Console 中访问当前选中组件
```

## 最佳实践

### 1. 定期运行诊断

```bash
# 每天早上开发前
pnpm diagnose

# 提交代码前
pnpm audit:ui && pnpm diagnose
```

### 2. 保持报告历史

```bash
# 创建报告存档目录
mkdir -p test-results/frontend/diagnostics/archive/$(date +%Y-%m-%d)

# 移动旧报告
mv test-results/frontend/diagnostics/*.json test-results/frontend/diagnostics/archive/$(date +%Y-%m-%d)/
```

### 3. 设置性能基准

在 `scripts/diagnose/benchmarks.json` 中定义基准:

```json
{
  "performance": {
    "domContentLoaded": 1000,
    "loadComplete": 3000,
    "maxRequests": 50
  },
  "errors": {
    "maxConsoleErrors": 0,
    "maxConsoleWarnings": 5
  }
}
```

### 4. 错误告警

集成到 Slack/钉钉:

```typescript
// scripts/diagnose/notify.ts
async function sendAlert(report: DiagnosticReport) {
  if (!report.summary.success) {
    await fetch('https://hooks.slack.com/YOUR_WEBHOOK', {
      method: 'POST',
      body: JSON.stringify({
        text: `❌ 前端诊断失败\n错误数: ${report.summary.totalErrors}`,
      }),
    });
  }
}
```

## 故障排除

### Puppeteer 安装失败

```bash
# 问题: Chromium 下载失败
# 解决: 跳过 Chromium 下载，使用系统安装的 Chrome
PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true pnpm add -D puppeteer

# 或设置镜像
export PUPPETEER_DOWNLOAD_HOST=https://registry.npmmirror.com/-/binary/chromium-browser-snapshots
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
chmod -R 755 test-results/frontend/diagnostics
```

## 相关资源

- [Puppeteer 官方文档](https://pptr.dev/)
- [Chrome DevTools 协议](https://chromedevtools.github.io/devtools-protocol/)
- [Vite DevTools 集成](https://vitejs.dev/guide/features.html#dev-tools)
- [React Performance](https://react.dev/learn/render-and-commit)

---

**维护者:** Frontend Team
**最后更新:** 2026-01-20
