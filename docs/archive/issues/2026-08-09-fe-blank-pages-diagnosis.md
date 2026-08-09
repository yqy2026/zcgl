# 前端「空白页/冻结页」点检问题诊断报告（2026-08-09）

**状态**: ✅ 已修复（fix 提交 `470d0810` / `56a038d0`，冒烟回归 `34c8f40a`）
**分析日期**: 2026-08-09
**触发场景**: 日常开发点检（WebBridge 浏览器），报 `/assets/list`、`/contracts`、`/parties`、`/ledger`、`/system` 5 个核心页「空白 `<main>` + 无 API 请求」，以及一次「URL 已切 `/assets/list` 但 DOM 冻结为上一页」观察。

---

## 一、结论摘要

1. **「空白页」是真实的，根因是访问了未注册路由**：`/contracts`、`/parties`、`/ledger`、`/system` 均不在 `frontend/src/routes/AppRoutes.tsx` 路由表（规范路径分别为 `/contract-center/list`、`/system/parties`、`/operations/ledger`，`/ledger` 为 `/operations/ledger`）。React Router 无匹配时渲染 `null`，`App.tsx` 无 `*` 兜底 → `<main>` 静默空白、无任何错误提示、无 API 请求。**前端渲染本身健康**。
2. **「冻结页」观察无法在标准浏览器复现**，结合实验证据高度怀疑为 **WebBridge 后台标签页 DOM 快照伪影**（该标签 `active=False`，快照不刷新）。
3. **交接文档的主根因假设（AnimatePresence `mode="wait"` + 后台 rAF 节流 → 新路由永不挂载）被严格实验推翻**。

## 二、诊断过程与证据

### 2.1 假设 H1：后台 rAF 冻结 → 路由切换卡死 —— ❌ 被推翻

| 实验 | 方法 | 结果 |
|------|------|------|
| 后台标签导航 | Playwright headless 双标签（后台 rAF 降至 2fps）内点击菜单「资产台账」 | 3s 内正常渲染，GREEN |
| rAF 运行时 patch | 导航前 `window.requestAnimationFrame = () => 0` | 正常渲染，GREEN |
| rAF 严格实验 | **init-script 页面加载前 patch** + 计数器证明 framer-motion 确实调用 patch 版 rAF（`rafCalls=4`）且永不回调 | **仍正常渲染，GREEN → 假设推翻** |

结论：framer-motion 不依赖 rAF tick 完成动画/挂载（有兜底机制）。**不要再往动画/rAF 方向查此类问题。**

### 2.2 假设 H2：死路由渲染 null → 空白 —— ✅ 坐实

`App.tsx` 的 `<Routes>` 无 `*` 兜底；实测（Playwright 标准浏览器）：

| URL | main 内容 | API 请求 | 判定 |
|-----|----------|---------|------|
| `/assets/list` | ✅ 完整渲染 | ✅ 3 个 | 正常 |
| `/contracts` `/parties` `/ledger` `/system` | ❌ mainChildren=0 | ❌ 0 个 | **未注册路由 → 空白** |
| `/contract-center/list` `/operations/ledger` `/system/parties` | ✅ 正常 | ✅ | 对照正常 |

2 轮复跑 100% 复现（确定性）。

### 2.3 「冻结页」（10:37 观察）——无法复现，疑似 WebBridge 伪影

- 菜单点击导航 `/assets/list`、直接导航、后台标签、rAF 冻结四种场景均正常渲染；
- WebBridge 自报该标签页 `active=False`（后台），后台标签页 DOM 快照不刷新是工具常见行为；
- WebBridge 会话已结束，无法直接复核 → 留待下次点检时先激活标签页复核再下结论。

## 三、修复（TDD，先红后绿）

1. **`fix(frontend)`**：`pages/NotFoundPage.tsx`（antd `Result` 404 + 返回工作台）+ `App.tsx` `<Route path="*">` 兜底。回归测试 `App.notfound.test.tsx`（渲染 `<App />` 断言死路由出 404，修复前红/后绿）。
2. **`fix(backend)`**：`system/backup.py:90` 路由字面量 `@router.get("/list[Any]")` → `/list`（同次点检发现：`/system/backup/list` 404 而 `/list[Any]` 意外可达；既有测试全为函数级调用、绕过路由注册，测不到该缺陷）。回归测试为路由表断言（`test_backup_layering.py`）。
3. **回归锁**：`tests/e2e/smoke/main-pages-render.spec.ts`——5 个规范路径必须渲染内容标记（非空白非 404），死路由必须渲染 404 页。

## 四、验证

- CI Pipeline 全绿（9 job，含 Frontend E2E 25 passed / 1.8m）；本地 backup 39 测试、routes 10 测试、lint/type-check/build 全过。
- 本地浏览器实测：5 个死 URL → 404 页；规范路径正常；`/system/backup/list` → 401（路由存在），`/list[Any]` → 404。

## 五、遗留与建议

1. **WebBridge 点检规范**：点检先核对 URL 是否注册路由（`routes/AppRoutes.tsx`）；疑似冻结先激活标签页复核。
2. **Playwright 本地浏览器**：项目锁定 chromium-1208（headless shell）本机下载未完成，验证期间临时用 chromium-1228 完整版驱动；下载完成后本地可跑全量 e2e。
3. **403/404 语义**：`InlineForbidden`（403 权限拒绝）与 `NotFoundPage`（404 路由缺失）现均为 antd Result 风格，位置均在 AppLayout 内，无冲突。
