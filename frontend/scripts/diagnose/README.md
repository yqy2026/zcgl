# 前端诊断工具

基于 Puppeteer 的自动化前端诊断系统，用于检测前端页面错误、网络请求问题和性能指标。

## 快速开始

### 1. 验证安装

```bash
cd frontend
pnpm diagnose:test
```

如果看到 "✅ 所有测试通过!"，说明 Puppeteer 已正确安装。

### 2. 运行诊断

**重要:** 确保前端开发服务器正在运行:

```bash
# 终端 1: 启动开发服务器
cd frontend && pnpm dev

# 终端 2: 运行诊断
cd frontend && pnpm diagnose
```

### 3. 查看报告

诊断完成后，会生成两个报告文件:

- **JSON 报告**: `frontend/diagnostics/diagnostic-report-<timestamp>.json`
- **HTML 报告**: `frontend/diagnostics/diagnostic-report-<timestamp>.html`
- **页面截图**: `frontend/diagnostics/screenshots/`

打开 HTML 报告查看可视化结果:

```bash
# Windows
start frontend/diagnostics/diagnostic-report-*.html

# Mac
open frontend/diagnostics/diagnostic-report-*.html

# Linux
xdg-open frontend/diagnostics/diagnostic-report-*.html

# 或使用命令
pnpm diagnose:report
```

## 命令参考

| 命令 | 说明 |
|------|------|
| `pnpm diagnose` | 完整诊断 (headless 模式) |
| `pnpm diagnose:headful` | 可视化诊断 (显示浏览器窗口) |
| `pnpm diagnose:routes` | 检查核心路由 (/dashboard, /assets/list, /rental/contracts) |
| `pnpm diagnose:test` | 测试 Puppeteer 是否正确安装 |
| `pnpm diagnose:report` | 打开最新的诊断报告 |

## 自定义配置

### 检查特定页面

```bash
PAGES=/dashboard,/assets/list,/maintenance/requests pnpm diagnose
```

### 自定义基础 URL

```bash
BASE_URL=http://localhost:3000 pnpm diagnose
```

### 设置超时时间 (默认 30 秒)

```bash
TIMEOUT=60000 pnpm diagnose
```

### 显示浏览器窗口 (调试用)

```bash
HEADLESS=false pnpm diagnose
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `BASE_URL` | `http://localhost:5173` | 前端服务器地址 |
| `PAGES` | `/` (检查所有默认路由) | 要检查的页面列表 (逗号分隔) |
| `HEADLESS` | `true` | 是否使用无头模式 |
| `TIMEOUT` | `30000` | 页面加载超时时间 (毫秒) |

## 诊断报告内容

### 汇总统计

- 检查页面总数
- 控制台错误数
- 控制台警告数
- 失败的网络请求数
- 有问题的页面数

### 页面级别指标

每个页面会记录:

- **DOM 加载时间**: DOMContentLoaded 事件触发时间
- **完全加载时间**: 所有资源加载完成时间
- **总请求数**: 发起的 HTTP 请求数量
- **失败请求数**: HTTP 4xx/5xx 响应数量
- **控制台错误**: JavaScript 运行时错误数量
- **控制台警告**: Deprecation 警告等
- **页面截图**: 整页截图 PNG 文件

### 详细日志

- **控制台日志**: 所有 console.log/warn/error 信息，包括时间戳和位置
- **网络请求**: 所有 HTTP 请求的详细信息 (URL, 方法, 状态码, 耗时, 大小)
- **失败请求**: 专门列出所有失败的 API 调用，便于快速定位问题

## 常见问题

### Q: Puppeteer 安装失败

**解决方案:**

```bash
# 跳过 Chromium 下载，使用系统 Chrome
PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true pnpm add -D puppeteer

# 或使用国内镜像
export PUPPETEER_DOWNLOAD_HOST=https://registry.npmmirror.com/-/binary/chromium-browser-snapshots
pnpm install -D puppeteer
```

### Q: 超时错误

**解决方案:**

```bash
# 增加超时时间
TIMEOUT=60000 pnpm diagnose
```

### Q: 部分页面检查失败

可能原因:
1. 页面需要登录权限 → 先登录再检查
2. 页面有路由配置错误 → 检查 `src/routes/` 配置
3. 页面依赖特定数据 → 使用 MSW mock 数据

### Q: 截图目录权限错误

**解决方案:**

```bash
# Windows: 以管理员身份运行终端

# Linux/Mac:
chmod -R 755 frontend/diagnostics
```

## CI/CD 集成

### GitHub Actions 示例

```yaml
name: Frontend Diagnostics

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

      - name: Install pnpm
        uses: pnpm/action-setup@v2
        with:
          version: 8

      - name: Install dependencies
        run: cd frontend && pnpm install

      - name: Build frontend
        run: cd frontend && pnpm build

      - name: Start preview server
        run: cd frontend && pnpm preview &

      - name: Wait for server
        run: sleep 10

      - name: Run diagnostics
        run: cd frontend && pnpm diagnose
        env:
          BASE_URL: http://localhost:4173
          HEADLESS: true

      - name: Upload diagnostic reports
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: diagnostic-reports
          path: frontend/diagnostics/
```

## 高级用法

### 1. 创建自定义检查脚本

参考 `scripts/diagnose/puppeteer-check.ts` 创建自定义检查:

```typescript
import { FrontendDiagnostics } from './puppeteer-check';

const diagnostics = new FrontendDiagnostics();

const report = await diagnostics.runDiagnostics({
  baseUrl: 'http://localhost:5173',
  pages: ['/dashboard', '/assets/list'],
  headless: false,  // 显示浏览器窗口
  timeout: 60000,
});

console.log('诊断结果:', report.summary);
```

### 2. 监控生产环境

```bash
# 定期检查生产环境
BASE_URL=https://your-domain.com pnpm diagnose

# 设置 cron 任务 (每小时检查)
0 * * * * cd /path/to/frontend && pnpm diagnose
```

### 3. 错误告警

集成到 Slack/钉钉/企业微信:

```typescript
// 在诊断完成后发送通知
if (!report.summary.success) {
  await notify.send({
    title: '前端诊断失败',
    message: `发现 ${report.summary.totalErrors} 个错误`,
    reportUrl: 'https://your-cdn.com/diagnostic-report.html',
  });
}
```

## 文件结构

```
frontend/
├── scripts/
│   └── diagnose/
│       ├── puppeteer-check.ts    # 主诊断脚本
│       ├── types.ts              # 类型定义
│       ├── reporter.ts           # 报告生成器
│       └── test.ts               # 测试脚本
├── diagnostics/                  # 诊断输出目录
│   ├── diagnostic-report-*.json  # JSON 报告
│   ├── diagnostic-report-*.html  # HTML 报告
│   └── screenshots/              # 页面截图
│       └── *.png
└── docs/
    └── frontend-diagnostics.md   # 详细文档
```

## 相关文档

- [完整诊断指南](../../docs/frontend-diagnostics.md)
- [Puppeteer 官方文档](https://pptr.dev/)
- [Chrome DevTools 文档](https://developer.chrome.com/docs/devtools/)

## 维护者

Frontend Team <frontend@example.com>

---

**最后更新:** 2026-01-20
